"""local_transcripts: discovery + parse + census of the local CLI/Cowork
transcript stores (COWORK_BRIEF_local_transcript_intake.md, Phase 1).

Hermetic: primes sys.path for the vendored pipeline, builds synthetic store
trees in a temp dir matching the record shapes Phase 0 found in real files
(docs/COWORK_REPORT_local_transcript_intake.md), and drives discovery/parse/
census against them. Touches no real store, no database, writes nothing
outside the temp dir.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

_PIPE = Path(__file__).resolve().parent.parent / "chronicler" / "pipeline"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _build_cli_store(root: Path) -> None:
    cwd_dir = root / "C--Users-x-repo"

    # A normal session: bookkeeping types mixed with two real turns, a
    # `thinking` block that must NOT surface as conversation, a trailing
    # line that fails to parse (must be recorded, not swallowed or fatal).
    _write(cwd_dir / "aaaa1111-1111-1111-1111-111111111111.jsonl", "\n".join([
        '{"type":"mode","mode":"normal","sessionId":"aaaa1111-1111-1111-1111-111111111111"}',
        '{"type":"user","message":{"role":"user","content":"hello there"},'
        '"uuid":"u1","timestamp":"2026-07-13T16:29:10.841Z","entrypoint":"cli",'
        '"cwd":"C:\\\\Users\\\\x\\\\repo"}',
        '{"type":"assistant","message":{"role":"assistant","content":'
        '[{"type":"thinking","thinking":"hmm"},{"type":"text","text":"hi back"}]},'
        '"uuid":"a1","timestamp":"2026-07-13T16:29:12.000Z","entrypoint":"cli"}',
        '{"type":"attachment","attachment":{"type":"deferred_tools_delta","addedNames":["Foo"]}}',
        '{"type":"custom-title","customTitle":"My Session"}',
        '{"type":"last-prompt","lastPrompt":"hello there"}',
        "this is not json",
        "",
    ]))

    # A subagent transcript -- must be discovered but flagged is_sidechain.
    _write(cwd_dir / "subagents" / "agent-bbbb.jsonl",
           '{"type":"user","message":{"role":"user","content":"subagent task"},'
           '"uuid":"su1","timestamp":"2026-07-14T00:00:00Z","entrypoint":"cli"}\n')

    # Explicitly excluded by filename -- must never appear in the census.
    _write(cwd_dir / "audit.jsonl", '{"type":"tool_call_audit","junk":true}\n')


def _build_cowork_store(root: Path) -> None:
    session_dir = root / "ws1" / "proj1" / "local_sess1"
    nested = session_dir / ".claude" / "projects" / "C--out-dir"
    _write(nested / "cccc2222-2222-2222-2222-222222222222.jsonl", "\n".join([
        '{"type":"user","message":{"role":"user","content":"cowork hi"},'
        '"uuid":"cu1","timestamp":"2026-07-15T00:00:00Z","entrypoint":"claude-desktop"}',
        '{"type":"assistant","message":{"role":"assistant","content":'
        '[{"type":"text","text":"cowork reply"}]},'
        '"uuid":"ca1","timestamp":"2026-07-15T00:00:05Z","entrypoint":"claude-desktop"}',
        '{"type":"ai-title","aiTitle":"Cowork thread"}',
        "",
    ]))

    # Explicitly excluded: the local_<id>.json sibling -- metadata only, no
    # messages array, must never be walked into or counted as a session.
    _write(root / "ws1" / "proj1" / "local_sess1.json",
           '{"sessionId":"local_sess1","systemPrompt":"lots of boilerplate"}\n')

    # Explicitly excluded: audit.jsonl inside the session folder too.
    _write(session_dir / "audit.jsonl", '{"type":"tool_call_audit"}\n')


def run() -> list[str]:
    v: list[str] = []
    if str(_PIPE) not in sys.path:
        sys.path.insert(0, str(_PIPE))
    import local_transcripts as lt

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        cli_root = td / "cli"
        cowork_root = td / "cowork"
        _build_cli_store(cli_root)
        _build_cowork_store(cowork_root)

        # --- discovery + parse -------------------------------------------------
        cli_sessions = {s.thread_id: s for s in
                         (lt.parse_session(tf) for tf in lt.discover_cli_store(cli_root))}
        cowork_sessions = {s.thread_id: s for s in
                            (lt.parse_session(tf) for tf in lt.discover_cowork_store(cowork_root))}

        if set(cli_sessions) != {"aaaa1111-1111-1111-1111-111111111111", "agent-bbbb"}:
            v.append(f"cli discovery wrong: {sorted(cli_sessions)}")
        if "audit" in " ".join(cli_sessions).lower():
            v.append("cli discovery picked up audit.jsonl")

        main_sess = cli_sessions.get("aaaa1111-1111-1111-1111-111111111111")
        if main_sess is not None:
            if [m[1:3] for m in main_sess.messages] != [("user", "hello there"), ("assistant", "hi back")]:
                v.append(f"cli main session messages wrong: {main_sess.messages}")
            if main_sess.cwd != "C:\\Users\\x\\repo":
                v.append(f"cli session cwd not captured: {main_sess.cwd!r}")
            if main_sess.messages[0][4] != "u1":
                v.append(f"cli session message uuid not captured: {main_sess.messages[0]}")
            if main_sess.title != "My Session":
                v.append(f"cli main session title wrong: {main_sess.title!r}")
            if main_sess.bookkeeping_records != 3:  # mode, attachment, last-prompt
                v.append(f"cli bookkeeping count wrong: {main_sess.bookkeeping_records}")
            if len(main_sess.parse_errors) != 1:
                v.append(f"cli parse_errors wrong: {main_sess.parse_errors}")
            if main_sess.entrypoints != {"cli"}:
                v.append(f"cli entrypoints wrong: {main_sess.entrypoints}")
            if any("hmm" in (m[2] or "") for m in main_sess.messages):
                v.append("cli session leaked a `thinking` block into messages")

        sub_sess = cli_sessions.get("agent-bbbb")
        if sub_sess is not None:
            if not sub_sess.is_sidechain:
                v.append("subagent transcript not flagged is_sidechain")
            if sub_sess.title != "subagent task":
                v.append(f"subagent transcript title not synthesised from first "
                         f"user message: {sub_sess.title!r}")

        if set(cowork_sessions) != {"cccc2222-2222-2222-2222-222222222222"}:
            v.append(f"cowork discovery wrong: {sorted(cowork_sessions)}")
        cw = cowork_sessions.get("cccc2222-2222-2222-2222-222222222222")
        if cw is not None:
            if cw.title != "Cowork thread":
                v.append(f"cowork title wrong: {cw.title!r}")
            if len(cw.messages) != 2:
                v.append(f"cowork messages wrong: {cw.messages}")
            if cw.entrypoints != {"claude-desktop"}:
                v.append(f"cowork entrypoints wrong: {cw.entrypoints}")
            if cw.store != "cowork":
                v.append(f"cowork session store label wrong: {cw.store!r}")

        # --- census: configured + present --------------------------------------
        real_machine = lt.machine
        try:
            lt.machine = lambda host=None: {
                "_hostname": "test-host",
                "cli_transcripts_home": str(cli_root),
                "cowork_transcripts_home": str(cowork_root),
            }
            report = lt.census()
        finally:
            lt.machine = real_machine

        cli_r = report["stores"]["cli"]
        if cli_r["status"] != "ok" or cli_r["sessions_found"] != 1 or cli_r["subagent_sessions_found"] != 1:
            v.append(f"census cli store wrong: {cli_r}")
        if cli_r["message_count"] != 3:  # 2 in main + 1 in subagent
            v.append(f"census cli message_count wrong: {cli_r['message_count']}")
        if cli_r["sessions_with_parse_failures"] != 1:
            v.append(f"census cli parse-failure count wrong: {cli_r['sessions_with_parse_failures']}")

        cw_r = report["stores"]["cowork"]
        if cw_r["status"] != "ok" or cw_r["sessions_found"] != 1:
            v.append(f"census cowork store wrong: {cw_r}")
        if cw_r["message_count"] != 2:
            v.append(f"census cowork message_count wrong: {cw_r['message_count']}")

        # --- census: absent store reported, not an error ------------------------
        try:
            lt.machine = lambda host=None: {"_hostname": "bare-host"}
            bare = lt.census()
        finally:
            lt.machine = real_machine
        if bare["stores"]["cli"]["status"] != "not configured":
            v.append(f"unconfigured cli store should report 'not configured': {bare['stores']['cli']}")

        # --- census: configured but missing on disk -----------------------------
        try:
            lt.machine = lambda host=None: {
                "_hostname": "missing-host",
                "cli_transcripts_home": str(td / "does-not-exist"),
            }
            missing = lt.census()
        finally:
            lt.machine = real_machine
        if missing["stores"]["cli"]["status"] != "configured but not found on disk":
            v.append(f"missing-on-disk store misreported: {missing['stores']['cli']}")

        # --- read-only: source files untouched -----------------------------------
        # mtimes unchanged after everything above -- discovery/parse/census must
        # never write into either store.
        target = cli_root / "C--Users-x-repo" / "aaaa1111-1111-1111-1111-111111111111.jsonl"
        before = target.stat().st_mtime
        lt.parse_session(next(iter(lt.discover_cli_store(cli_root))))
        after = target.stat().st_mtime
        if before != after:
            v.append("parse_session modified a source file's mtime")

    return v
