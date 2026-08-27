"""ingest_local_transcripts.py -- Phase 2 of
docs/COWORK_BRIEF_local_transcript_intake.md: map parsed local transcripts
(chronicler/pipeline/local_transcripts.py, Phase 1) into `threads`/`messages`
and write them, behind `--apply` (dry-run by default, per the brief).

**Dev vault only until Phase 3.** This writes through the standard
`db.get_connection()` / `CHRONICLER_HOME` mechanism, same as every other
normalizer -- it never hardcodes a DB path. Point `CHRONICLER_HOME` (or
`CHRONICLER_DB_PATH`) at the dev vault before running this; nothing here
enforces that, the brief's working rules do.

Rulings this module encodes (docs/COWORK_REPORT_local_transcript_intake.md,
Phase 1 report, confirmed with Tim before this was written):

1. **Content sensitivity -- conversation records only.** `messages.content`
   holds only the `user`/assistant `text` conversation `local_transcripts.py`
   already isolates. Tool traffic, file contents, and `thinking` blocks never
   reach the DB -- excluded upstream, at parse time, not filtered here.
2. **Attribution -- CLI sessions get `project_confidence='exact'` directly**
   from the session's real `cwd` (Phase 2 addition to `local_transcripts.py`:
   `ParsedSession.cwd`, read straight off a record's own `cwd` field, never
   decoded from the lossy `encoded_cwd` folder name) matched against the
   project registry by folder-name segment, reusing
   `extract_path_mentions.match_path`'s compact/alias matching. **Cowork
   sessions never get a direct link** -- their cwd encodes the session's own
   outputs dir, no project signal (investigation note) -- they land with
   `project_confidence='none'` and pick up a link later through the ordinary
   evidence pipeline (path_mention/filename_xref -> relink), same as every
   other ambiguous thread.
3. **`source` = `"claude-local"`** -- new value alongside `claude` (export)
   / `gemini`, permanently distinguishable from export-derived Claude
   threads even though both can describe the same personal-estate
   conversation (dedupe against the export is Phase 3's problem, not this
   one -- ruling 6).
4. **`account` = `f"{source}-{estate}"`**, estate from the machine's own
   config (`l5gntools.config.machine()["estate"]`), never inferred from
   thread content. Refuses loudly if the machine has no estate configured
   (or it's still the template default `"unknown"`) rather than writing
   threads into a wall this estate can't see through (DECISIONS 0025).
5. **`thread_id`** is the session's own uuid (`ParsedSession.thread_id`,
   stable, source-native) -- a re-run of the same file updates in place,
   never duplicates. **`message_id`** is the record's own `uuid` when present
   (every real user/assistant record has one, per Phase 0/1), else a
   synthetic sha256 hash of `thread_id:seq`, per the schema's own comment.
6. **Idempotency**: every run re-parses the full file and upserts every
   thread/message it contains (`ON CONFLICT ... DO UPDATE`, same pattern as
   normalize_claude.py) -- correct by construction for a store where files
   only ever grow: re-running with no new lines writes the same rows back
   unchanged, and a session appended to since the last run adds exactly the
   new messages, because each message's identity is its own source-native
   uuid, not its position in the file.
7. **`raw_ref`** is the absolute path back to the source `.jsonl` (the file
   is never copied into the vault -- it lives in the CLI/Cowork store, read
   in place). `parser_version` = "local_transcripts_v1".

Usage:
    python3 pipeline/ingest_local_transcripts.py            # dry-run, report only
    python3 pipeline/ingest_local_transcripts.py --apply    # write
    python3 pipeline/ingest_local_transcripts.py --apply --host NAME
"""
from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

from db import get_connection, init_db, resolve_registry_path, iter_folder_backed_entries
from l5gntools.config import machine

from local_transcripts import (
    STORES, ParsedSession, TranscriptFile, parse_session,
)
from extract_path_mentions import compact, MIN_KEY_LEN

SOURCE = "claude-local"
PARSER_VERSION = "local_transcripts_v1"

_SEG_SPLIT_RE = re.compile(r"[\\/:]+")

# Same infrastructure-segment guard as extract_path_mentions, imported
# indirectly would create a tighter coupling than warranted -- these are the
# path-noise segments a real Windows `cwd` can contain before it ever reaches
# a repo folder, and a session parked in one of them must never false-match
# a project by accident.
_PATH_NOISE = {
    "users", "user", "github", "gitlab", "documents", "document", "downloads",
    "desktop", "appdata", "roaming", "local", "locallow", "c", "d", "e",
}


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def synthetic_message_id(thread_id: str, seq: int) -> str:
    return hashlib.sha256(f"{thread_id}:{seq}".encode("utf-8")).hexdigest()[:32]


# ---------------------------------------------------------------------------
# Attribution (ruling 2) -- CLI sessions only, from the real `cwd`.
# ---------------------------------------------------------------------------

def load_project_keymap() -> dict:
    """compact_key -> set(registry id), same shape and source as
    extract_path_mentions.load_project_keys, built fresh here rather than
    imported so this module has no hard dependency on that producer's
    internal registry-path constant."""
    import json
    registry_path = resolve_registry_path()
    if not registry_path.is_file():
        return {}
    with open(registry_path, "r", encoding="utf-8") as f:
        registry = json.load(f)
    keymap: dict = {}
    for entry in iter_folder_backed_entries(registry):
        tid = entry["id"]
        for src in [entry["canonical_name"]] + list(entry.get("aliases", [])):
            key = compact(src)
            if len(key) < MIN_KEY_LEN or key in _PATH_NOISE:
                continue
            keymap.setdefault(key, set()).add(tid)
    return keymap


def load_project_meta() -> dict:
    """registry id -> the registry entry, for the rows this module has to create.

    Same file and same iteration order as ``load_project_keymap`` above; kept as
    a second reader rather than folding both into one return value so the
    keymap's signature (which the tester substitutes) is unchanged."""
    import json
    registry_path = resolve_registry_path()
    if not registry_path.is_file():
        return {}
    with open(registry_path, "r", encoding="utf-8") as f:
        registry = json.load(f)
    return {e["id"]: e for e in iter_folder_backed_entries(registry)}


def upsert_project(cur, project_id: str, meta: dict) -> None:
    """Ensure a ``projects`` row exists for the registry id before a thread
    references it.

    ``threads.project_link`` is a foreign key into ``projects``, and every
    pipeline connection is opened with ``foreign_keys=ON``
    (``l5gntools.dbsafe.apply_pragmas``), so writing an attribution for a
    registry id with no row raises ``IntegrityError`` and takes the whole
    ingest down with it.

    ``relink.upsert_project`` already does exactly this, and says why: both
    writers must "produce identical rows for the same target instead of one
    keying on a folder name and the other on an id." This module is the second
    writer and did not have it -- ruling 2's attribution path was therefore
    unreachable in practice. It went unnoticed because the registry could not be
    resolved on this rig (``resolve_registry_path`` points at a path that does
    not exist here), so ``load_project_keymap`` returned ``{}`` and no
    attribution was ever attempted. Setting ``CHRONICLER_REGISTRY_PATH``
    exposed it as a hard failure on 2026-08-27.

    Same statement as relink's, deliberately -- a curated name never overwrites
    an existing one with NULL, and an existing ``repo_folder_path`` wins."""
    entry = meta.get(project_id, {})
    cur.execute(
        """INSERT INTO projects (project_id, name, repo_folder_path, source_system_id)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(project_id) DO UPDATE SET
             name=COALESCE(excluded.name, projects.name),
             repo_folder_path=COALESCE(projects.repo_folder_path, excluded.repo_folder_path)""",
        (project_id, entry.get("canonical_name", project_id),
         entry.get("repo_folder_path"), None),
    )


def match_cwd_to_project(cwd: str, keymap: dict) -> str | None:
    """The real `cwd`'s segments and adjacent segment-pairs, compact-matched
    against the registry -- same matching rule as extract_path_mentions'
    `match_path`, applied to a real filesystem path (not a lossy encoded
    one). Returns a registry id, or None (never guesses between multiple
    candidates -- an ambiguous cwd is not attribution, ruling 2 asked for
    'exact' or nothing)."""
    if not cwd:
        return None
    segs = [s for s in _SEG_SPLIT_RE.split(cwd) if s]
    hits: set = set()
    prev_key = None
    for seg in segs:
        key = compact(seg)
        if len(key) >= MIN_KEY_LEN and key not in _PATH_NOISE and key in keymap:
            hits |= keymap[key]
        if prev_key is not None:
            pair = prev_key + key
            if len(pair) >= MIN_KEY_LEN and pair not in _PATH_NOISE and pair in keymap:
                hits |= keymap.get(pair, set())
        prev_key = key
    if len(hits) == 1:
        return next(iter(hits))
    return None  # zero or ambiguous (>1) -- 'exact' means exact, not a guess


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------

def ingest_session(cur, sess: ParsedSession, source_file: Path, account: str,
                    keymap: dict, meta: dict) -> dict:
    project_id = None
    confidence = "none"
    review_status = "pending"
    if sess.store == "cli" and sess.cwd:
        project_id = match_cwd_to_project(sess.cwd, keymap)
        if project_id:
            confidence = "exact"
            review_status = "auto"
            # The FK target has to exist before the thread references it.
            upsert_project(cur, project_id, meta)
    # Cowork sessions (ruling 2): never attempted here -- project_link stays
    # None/'none'/'pending', picked up later by the evidence pipeline.

    cur.execute(
        """INSERT INTO threads (thread_id, source, account, title, created_at, updated_at,
                                 status, project_link, project_confidence, review_status,
                                 raw_ref, parser_version)
           VALUES (?, ?, ?, ?, ?, ?, 'open', ?, ?, ?, ?, ?)
           ON CONFLICT(thread_id) DO UPDATE SET
             title=excluded.title, updated_at=excluded.updated_at,
             -- 'exact' is source-native (schema comment): once set, automation
             -- never overwrites it with a weaker confidence on a later run.
             project_link=CASE WHEN threads.project_confidence='exact'
                                THEN threads.project_link ELSE excluded.project_link END,
             project_confidence=CASE WHEN threads.project_confidence='exact'
                                      THEN threads.project_confidence ELSE excluded.project_confidence END,
             review_status=CASE WHEN threads.project_confidence='exact'
                                 THEN threads.review_status ELSE excluded.review_status END""",
        (sess.thread_id, SOURCE, account, sess.title, sess.created_at, sess.updated_at,
         project_id, confidence, review_status, str(source_file), PARSER_VERSION),
    )

    new_messages = 0
    for seq, role, content, created_at, record_uuid in sess.messages:
        message_id = record_uuid or synthetic_message_id(sess.thread_id, seq)
        cur.execute(
            """INSERT INTO messages (message_id, thread_id, seq, role, content, created_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(message_id) DO UPDATE SET
                 content=excluded.content, seq=excluded.seq, created_at=excluded.created_at""",
            (message_id, sess.thread_id, seq, role, content, created_at),
        )
        new_messages += 1

    return {
        "thread_id": sess.thread_id, "store": sess.store, "messages": new_messages,
        "project_link": project_id, "project_confidence": confidence,
    }


def run(apply: bool, host: str | None = None) -> dict:
    cfg = machine(host)
    estate = cfg.get("estate")
    if not estate or estate == "unknown":
        raise SystemExit(
            "[ingest_local_transcripts] machine has no estate configured "
            f"(got {estate!r}) -- refusing to write threads into an "
            "unclassified estate. Set 'estate' in config/local.json for "
            f"host {cfg.get('_hostname')!r} first (DECISIONS 0025)."
        )
    account = f"{SOURCE}-{estate}"

    keymap = load_project_keymap()
    meta = load_project_meta()

    init_db()
    conn = get_connection()
    cur = conn.cursor()

    results = []
    log_rows = []
    try:
        for store_name, config_key, discover in STORES:
            root_str = cfg.get(config_key)
            if not root_str:
                continue
            root = Path(root_str)
            if not root.is_dir():
                continue
            for tf in discover(root):
                sess = parse_session(tf)
                if not sess.messages:
                    # Nothing conversational to write -- skip rather than
                    # insert an empty thread. Parse errors (if any) are
                    # reported either way, never silently dropped.
                    reason = ("no conversation messages" if not sess.parse_errors
                              else f"no conversation messages; {len(sess.parse_errors)} parse error(s)")
                    results.append({"thread_id": sess.thread_id, "store": store_name,
                                     "skipped": reason})
                    continue
                rec = ingest_session(cur, sess, tf.path, account, keymap, meta)
                rec["parse_errors"] = len(sess.parse_errors)
                results.append(rec)
                log_rows.append((SOURCE, account, file_hash(tf.path),
                                  len(sess.messages), PARSER_VERSION))

        if apply:
            cur.executemany(
                """INSERT INTO ingestion_log (source, account, file_hash, imported_at,
                                               rows_new, rows_changed, rows_skipped, parser_version)
                   VALUES (?, ?, ?, datetime('now'), ?, 0, 0, ?)""",
                log_rows,
            )
            conn.commit()
        else:
            conn.rollback()
    finally:
        conn.close()

    return {"account": account, "sessions": results}


def report(result: dict, apply: bool) -> None:
    sessions = result["sessions"]
    written = [s for s in sessions if "skipped" not in s]
    skipped = [s for s in sessions if "skipped" in s]
    linked = sum(1 for s in written if s.get("project_confidence") == "exact")
    total_messages = sum(s.get("messages", 0) for s in written)
    with_errors = sum(1 for s in written if s.get("parse_errors"))

    print(f"ingest_local_transcripts -- account {result['account']!r}")
    print(f"  sessions:          {len(written)}  ({linked} exact-linked)")
    print(f"  messages:          {total_messages}")
    if with_errors:
        print(f"  sessions with parse errors (still ingested, valid lines only): {with_errors}")
    if skipped:
        print(f"  skipped:           {len(skipped)}")
        for s in skipped:
            print(f"    {s['thread_id']}: {s['skipped']}")
    if apply:
        print("\nWritten. Re-run with no flags to verify idempotency (should report the same session/message counts).")
    else:
        print("\n(dry-run -- nothing written. Re-run with --apply to persist.)")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Phase 2: ingest local CLI/Cowork transcripts into "
                     "threads/messages. Dry-run by default.")
    ap.add_argument("--apply", action="store_true", help="write to the DB (default: dry-run)")
    ap.add_argument("--host", help="ingest as if run on this hostname (else the real one)")
    args = ap.parse_args()

    result = run(args.apply, args.host)
    report(result, args.apply)


if __name__ == "__main__":
    main()
