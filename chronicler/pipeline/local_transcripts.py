"""local_transcripts.py -- read-only discovery, parse, and census of the local
Claude transcript stores (CLI and Cowork desktop). Phase 1 of
docs/COWORK_BRIEF_local_transcript_intake.md.

**This module only reads and reports.** It never touches chronicler.db and
never writes into either store -- per the brief's working rules, the source
files are inputs, not ours: copy out, never write in. Phase 2 (DB ingest,
behind ``--apply``) is a separate module built on top of ``parse_session``
here; nothing in this file is wired to it yet.

Usage:
    python3 pipeline/local_transcripts.py            # human-readable census
    python3 pipeline/local_transcripts.py --json      # machine-readable

Two stores, one format
-----------------------
Phase 0 (docs/COWORK_REPORT_local_transcript_intake.md) opened 14 real files
across both stores and diffed them directly -- in one case the *same file*,
byte-identical, was found in both trees for one session. One record shape,
one parser (``parse_session``), and it is the store's ``entrypoint`` field
that tells sessions apart (``"cli"``, ``"sdk-cli"``, ``"claude-desktop"``),
never which directory a file happened to be found in.

Explicitly excluded -- never treated as conversation, and every exclusion
below is a Phase 0 finding, not a guess:
  - ``audit.jsonl``             -- tool-call-level audit, up to 8.9 MB each.
  - ``local_<id>.json``         -- Cowork session metadata; ~2/3 of its bytes
                                    are ``systemPrompt`` boilerplate, no
                                    messages array at all.
  - ``.claude/tasks/*.json``    -- task-list widget state (outside the
                                    ``projects/`` tree walked here, so never
                                    reached by discovery -- named for clarity).
  - record type ``attachment``  -- tool-visibility bookkeeping
                                    (``deferred_tools_delta``,
                                    ``agent_listing_delta`` subtypes seen).
  - record types ``mode``, ``permission-mode``, ``file-history-snapshot``,
    ``system`` -- session bookkeeping, carry no conversation text.
  - ``thinking`` content blocks on assistant messages -- model reasoning,
    not a reply; dropped rather than preserved (a call worth revisiting,
    not one Phase 1 needs to make).
  - ``tool_use`` / ``tool_result`` blocks -- tool traffic, not conversation.

Config
------
Both store roots are machine facts, resolved via ``l5gntools.config.machine()``
beside ``chronicler_home`` -- never hardcoded. See config/machines.json:
  - ``cli_transcripts_home``    e.g. ``C:/Users/<you>/.claude/projects``
  - ``cowork_transcripts_home`` the Cowork MSIX LocalCache session root, e.g.
    ``C:/Users/<you>/AppData/Local/Packages/Claude_<id>/LocalCache/Roaming/
    Claude/local-agent-mode-sessions``
An absent or unconfigured store is reported, never an error -- Phase 1's own
requirement ("Absent store -> report it, don't crash").
"""
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from l5gntools.config import machine

# ---------------------------------------------------------------------------
# Exclusions -- see module docstring for what each one is and why.
# ---------------------------------------------------------------------------

EXCLUDED_FILENAMES = frozenset({"audit.jsonl"})


def _winlong(path: Path) -> Path:
    """Extended-length form of an absolute Windows path (`\\\\?\\`-prefixed),
    so filesystem calls aren't capped by the legacy 260-character MAX_PATH.

    Real and hit in practice, not theoretical: Phase 4 UAT on 10280L
    (2026-07-28) found a live Cowork session whose full
    `<root>/<workspace-id>/<project-id>/local_<session-id>/.claude/projects/
    <encoded-cwd>` path measured 441 characters before the session's own
    `.jsonl` filename was even added -- the encoded-cwd segment folds the
    *entire* path back into itself, and that self-nesting is what pushes it
    past MAX_PATH. Every level below the truncation point looked like a
    directory that legitimately doesn't exist, exactly the "confident zero"
    class this module exists to catch, one call this module previously
    hadn't guarded: `Path.is_dir()` swallows the resulting `OSError`
    internally and returns `False`, same as an absent directory would.

    A no-op on non-Windows and a no-op if already prefixed, so callers can
    apply it unconditionally at the one point a store root is constructed;
    every path built from it via `/` inherits the prefix.
    """
    if os.name != "nt":
        return path
    s = str(path)
    if s.startswith("\\\\?\\"):
        return path
    return Path("\\\\?\\" + s)

# Record types that never carry conversation text. Every one of these is
# session/tool bookkeeping (Phase 0's findings), counted but never turned
# into a `messages` row. ``custom-title``/``ai-title`` are handled specially
# (consulted for the thread title) rather than folded in here, even though
# the parse loop skips them the same way for message purposes.
BOOKKEEPING_RECORD_TYPES = frozenset({
    "attachment", "mode", "permission-mode", "file-history-snapshot",
    "system", "queue-operation", "last-prompt",
})
TITLE_RECORD_TYPES = frozenset({"custom-title", "ai-title"})
MESSAGE_RECORD_TYPES = frozenset({"user", "assistant"})


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TranscriptFile:
    path: Path
    store: str          # "cli" or "cowork"
    encoded_cwd: str
    session_uuid: str    # from the filename, before parsing confirms it
    is_sidechain: bool   # under a subagents/ folder -- a subagent's own transcript


def _safe_subdirs(path: Path, errors: list | None, predicate=None) -> list[Path]:
    """Immediate subdirectories of ``path``, catching ``OSError`` explicitly
    instead of relying on ``Path.iterdir()``/``Path.is_dir()``, which swallow
    a permission failure internally and simply act as if the entry were not
    there. That distinction matters here specifically:
    docs/investigation/2026-07-27_cowork-transcript-store.md already found
    one case where a census pointed at the wrong (MSIX-virtualised) path
    returned "a confident zero with no hint that redirection is in play" --
    that time the path itself was wrong. This guards the *other* way the
    same symptom can happen: the path is right, but something (AppContainer
    ACLs, a locked-down corporate device policy) blocks a plain,
    non-packaged process from listing one level of it, and every level below
    a silently-empty listing looks like "no sessions" rather than "could not
    look". Every ``OSError`` met while listing or stat-ing an entry is
    appended to ``errors`` (when given) and the walk continues -- Phase 1's
    "listed, never swallowed" rule, applied to the filesystem itself and not
    just to record parsing.
    """
    try:
        entries = sorted(path.iterdir())
    except OSError as exc:
        if errors is not None:
            errors.append(f"cannot list {path}: {exc}")
        return []
    out: list[Path] = []
    for p in entries:
        try:
            is_dir = p.is_dir()
        except OSError as exc:
            if errors is not None:
                errors.append(f"cannot stat {p}: {exc}")
            continue
        if not is_dir:
            continue
        if predicate is not None and not predicate(p):
            continue
        out.append(p)
    return out


def _iter_projects_tree(projects_root: Path, store: str, errors: list | None = None):
    """Yield a TranscriptFile for every *.jsonl under a `.claude/projects`-shaped
    tree: `<projects_root>/<encoded-cwd>/<uuid>.jsonl` and
    `<projects_root>/<encoded-cwd>/subagents/agent-*.jsonl`.

    Anything that isn't a directory under ``projects_root`` (e.g. a stray
    file) is skipped, not errored on -- only ``.jsonl`` under an encoded-cwd
    folder is a session file by the brief's own description of the store.
    ``audit.jsonl`` is excluded by name; nothing else here is filtered, so an
    unexpected file surfaces as a parse failure in the caller's report rather
    than being silently absorbed. Filesystem access failures while walking go
    to ``errors`` via :func:`_safe_subdirs`, not into a silent empty result.
    """
    try:
        exists = projects_root.is_dir()
    except OSError as exc:
        if errors is not None:
            errors.append(f"cannot stat {projects_root}: {exc}")
        return
    if not exists:
        return
    for cwd_dir in _safe_subdirs(projects_root, errors):
        try:
            jsonl_paths = sorted(cwd_dir.rglob("*.jsonl"))
        except OSError as exc:
            if errors is not None:
                errors.append(f"cannot scan {cwd_dir}: {exc}")
            continue
        for jsonl_path in jsonl_paths:
            if jsonl_path.name in EXCLUDED_FILENAMES:
                continue
            is_side = "subagents" in jsonl_path.relative_to(cwd_dir).parts
            yield TranscriptFile(
                path=jsonl_path,
                store=store,
                encoded_cwd=cwd_dir.name,
                session_uuid=jsonl_path.stem,
                is_sidechain=is_side,
            )


def discover_cli_store(root: Path, errors: list | None = None):
    """The plain CLI store: `<root>/<encoded-cwd>/<uuid>.jsonl`."""
    yield from _iter_projects_tree(_winlong(root), "cli", errors)


def discover_cowork_store(root: Path, errors: list | None = None):
    """The Cowork desktop store: `<root>/<workspace-id>/<project-id>/
    local_<session-id>/.claude/projects/<encoded-cwd>/<uuid>.jsonl`
    (docs/investigation/2026-07-27_cowork-transcript-store.md). Everything
    at the `<project-id>` root that is not a `local_<session-id>` folder
    (the sibling `local_<id>.json` files, cache files) is skipped by the
    `local_` + is-a-directory check -- excluded by shape, not by walking
    around it, so a store layout change only needs a name/shape check
    updated here, not new traversal logic.

    ``_winlong`` is applied here, at the discovery entry point, rather than
    by each caller -- ``census()`` and ``ingest_local_transcripts.py`` build
    ``root`` independently, and the first version of this fix only patched
    the former, so ``ingest`` kept silently finding 0 cowork sessions (Phase
    4 UAT, 10280L, 2026-07-28) even after the census was fixed. One caller
    forgetting to apply a caller-side fix is exactly the failure mode a
    caller-side fix invites; putting it on the function everyone already
    calls closes that off structurally instead of by convention.
    """
    root = _winlong(root)
    try:
        exists = root.is_dir()
    except OSError as exc:
        if errors is not None:
            errors.append(f"cannot stat {root}: {exc}")
        return
    if not exists:
        return
    for workspace_dir in _safe_subdirs(root, errors):
        for project_dir in _safe_subdirs(workspace_dir, errors):
            for session_dir in _safe_subdirs(
                project_dir, errors, predicate=lambda p: p.name.startswith("local_")
            ):
                nested = session_dir / ".claude" / "projects"
                yield from _iter_projects_tree(nested, "cowork", errors)


# ---------------------------------------------------------------------------
# Parse
# ---------------------------------------------------------------------------

@dataclass
class ParsedSession:
    thread_id: str
    store: str
    encoded_cwd: str
    path: Path
    is_sidechain: bool = False
    title: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    entrypoints: set = field(default_factory=set)
    # The session's real, un-encoded cwd (e.g. "C:\Users\timps\Documents\
    # GitHub\L5GN-Tools"), read straight from a record's own `cwd` field --
    # NOT decoded from `encoded_cwd`. The encoding (":"/"\\"/"/" -> "-") is
    # one-way: a folder name that already contains "-" makes decoding
    # ambiguous, so anything that needs the real path (Phase 2 project
    # attribution) must read it from here, never reconstruct it.
    cwd: str | None = None
    # (seq, role, content, created_at, record_uuid) -- mirrors the `messages`
    # table shape; record_uuid is the source-native id (schema: "source-native
    # uuid where available, else synthetic hash"), None when a record has no
    # uuid of its own.
    messages: list = field(default_factory=list)
    total_records: int = 0
    bookkeeping_records: int = 0
    parse_errors: list = field(default_factory=list)  # (line_no, error)

    @property
    def byte_size(self) -> int:
        try:
            return self.path.stat().st_size
        except OSError:
            return 0


def _message_text(content) -> str | None:
    """Conversation text only. A plain string is a human turn verbatim; a
    list is an assistant `message.content` block array -- only `text` blocks
    are conversation, `tool_use`/`tool_result`/`thinking` are not (Phase 0).
    Returns None (not '') when there is nothing conversational in the
    record, so callers can tell "no text" from "empty text"."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [
            b.get("text", "") for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        ]
        text = "\n".join(p for p in parts if p)
        return text or None
    return None


def parse_session(tf: TranscriptFile) -> ParsedSession:
    """Parse one `.jsonl` file into an in-memory shape mirroring
    `threads`/`messages` (Phase 1's acceptance shape). Never raises on a
    malformed line or an unrecognised record type -- both are recorded in
    `parse_errors` and parsing continues, per the brief's "listed, never
    swallowed" requirement.
    """
    sess = ParsedSession(
        thread_id=tf.session_uuid, store=tf.store, encoded_cwd=tf.encoded_cwd,
        path=tf.path, is_sidechain=tf.is_sidechain,
    )
    custom_title: str | None = None
    ai_title: str | None = None
    seq = 0

    try:
        raw_text = tf.path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        sess.parse_errors.append((0, f"unreadable: {exc}"))
        return sess

    for line_no, line in enumerate(raw_text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        sess.total_records += 1
        try:
            rec = json.loads(line)
        except json.JSONDecodeError as exc:
            sess.parse_errors.append((line_no, f"bad JSON: {exc}"))
            continue
        if not isinstance(rec, dict):
            sess.parse_errors.append((line_no, f"record is not an object: {type(rec).__name__}"))
            continue

        rtype = rec.get("type")
        ep = rec.get("entrypoint")
        if ep:
            sess.entrypoints.add(ep)
        raw_cwd = rec.get("cwd")
        if raw_cwd and sess.cwd is None:
            sess.cwd = raw_cwd

        if rtype == "custom-title":
            custom_title = rec.get("customTitle") or custom_title
            continue
        if rtype == "ai-title":
            ai_title = rec.get("aiTitle") or ai_title
            continue
        if rtype in BOOKKEEPING_RECORD_TYPES:
            sess.bookkeeping_records += 1
            continue
        if rtype not in MESSAGE_RECORD_TYPES:
            sess.parse_errors.append((line_no, f"unrecognised record type: {rtype!r}"))
            continue

        message = rec.get("message") or {}
        role = message.get("role") or rtype
        ts = rec.get("timestamp")
        if ts:
            sess.created_at = sess.created_at or ts
            sess.updated_at = ts

        text = _message_text(message.get("content"))
        if text:
            sess.messages.append((seq, role, text, ts, rec.get("uuid")))
            seq += 1

    sess.title = custom_title or ai_title
    if sess.title is None and sess.messages:
        # No `custom-title`/`ai-title` record (Phase 0: subagent transcripts
        # in particular never carry one) -- synthesise from the first human
        # turn, per Phase 0's own open question on this.
        first_user = next((m[2] for m in sess.messages if m[1] == "user"), None)
        if first_user:
            sess.title = (first_user[:80] + "…") if len(first_user) > 80 else first_user
    return sess


# ---------------------------------------------------------------------------
# Census -- the Phase 1 report. Read-only; touches no database.
# ---------------------------------------------------------------------------

STORES = (
    ("cli", "cli_transcripts_home", discover_cli_store),
    ("cowork", "cowork_transcripts_home", discover_cowork_store),
)


def census(host: str | None = None) -> dict:
    """Sessions found per store, message counts, date range, total bytes,
    the encoded-cwd of each, and anything that failed to parse -- listed,
    never swallowed. No DB touched. No writes anywhere."""
    cfg = machine(host)
    report: dict = {"host": cfg.get("_hostname"), "stores": {}}

    for name, config_key, discover in STORES:
        configured = cfg.get(config_key)
        store_report: dict = {"config_key": config_key, "configured_root": configured}

        if not configured:
            store_report["status"] = "not configured"
            report["stores"][name] = store_report
            continue

        root = Path(configured)
        if not root.is_dir():
            store_report["status"] = "configured but not found on disk"
            report["stores"][name] = store_report
            continue

        # The MAX_PATH guard (`_winlong`) is applied inside discover_*
        # itself, not here -- ingest_local_transcripts.py builds its own
        # `root` independently of census() and must get the same guard
        # without having to remember to ask for it.
        access_errors: list[str] = []
        sessions: list[ParsedSession] = []
        for tf in discover(root, access_errors):
            sessions.append(parse_session(tf))

        top_level = [s for s in sessions if not s.is_sidechain]
        sidechain = [s for s in sessions if s.is_sidechain]
        dates = sorted(
            d for s in sessions for d in (s.created_at, s.updated_at) if d
        )
        failures = [
            {"file": str(s.path), "errors": s.parse_errors}
            for s in sessions if s.parse_errors
        ]

        store_report.update({
            "status": "ok",
            "sessions_found": len(top_level),
            "subagent_sessions_found": len(sidechain),
            "encoded_cwds": sorted({s.encoded_cwd for s in sessions}),
            "message_count": sum(len(s.messages) for s in sessions),
            "bookkeeping_record_count": sum(s.bookkeeping_records for s in sessions),
            "total_bytes": sum(s.byte_size for s in sessions),
            "date_range": [dates[0], dates[-1]] if dates else None,
            "entrypoints_seen": sorted({ep for s in sessions for ep in s.entrypoints}),
            "sessions_with_parse_failures": len(failures),
            "parse_failures": failures,
            "access_errors": access_errors,
        })
        report["stores"][name] = store_report

    return report


# ---------------------------------------------------------------------------
# CLI -- reports only. Never ingests, never writes.
# ---------------------------------------------------------------------------

def _print_human(report: dict) -> None:
    print(f"local_transcripts census -- host {report['host']!r}")
    for name, sr in report["stores"].items():
        print(f"\n[{name}] root: {sr['configured_root']}")
        if sr["status"] != "ok":
            print(f"  status: {sr['status']}")
            continue
        print(f"  sessions:            {sr['sessions_found']}"
              f"  (+{sr['subagent_sessions_found']} subagent)")
        print(f"  messages:            {sr['message_count']}")
        print(f"  bookkeeping records: {sr['bookkeeping_record_count']}")
        print(f"  total bytes:         {sr['total_bytes']:,}")
        print(f"  date range:          {sr['date_range']}")
        print(f"  entrypoints seen:    {sr['entrypoints_seen']}")
        print(f"  encoded cwds:        {len(sr['encoded_cwds'])}")
        if sr.get("access_errors"):
            print(f"  ** {len(sr['access_errors'])} filesystem access error(s) while walking -- "
                  f"sessions_found above is NOT proof the store is empty **")
            for err in sr["access_errors"]:
                print(f"     {err}")
        if sr["sessions_with_parse_failures"]:
            print(f"  ** parse failures:   {sr['sessions_with_parse_failures']} session(s) **")
            for f in sr["parse_failures"]:
                print(f"     {f['file']}")
                for line_no, err in f["errors"]:
                    print(f"       line {line_no}: {err}")
        else:
            print("  parse failures:      none")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Read-only discovery + census of local Claude transcript "
                     "stores (CLI + Cowork). Never touches the database, "
                     "never writes into either store.")
    ap.add_argument("--json", action="store_true", help="emit the report as JSON")
    ap.add_argument("--host", help="census as if run on this hostname (else the real one)")
    args = ap.parse_args()

    report = census(args.host)
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        _print_human(report)


if __name__ == "__main__":
    main()
