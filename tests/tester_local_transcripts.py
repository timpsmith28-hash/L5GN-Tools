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

    # A subagent sidechain inside the SAME conversation (local_sess1), with a
    # LATER message timestamp -- K1/K2 grouping must fold it into one
    # Conversation with the top-level file and take the newest time across
    # both, not just the top-level file's own time.
    _write(nested / "subagents" / "agent-dddd.jsonl",
           '{"type":"user","message":{"role":"user","content":"subagent side task"},'
           '"uuid":"sd1","timestamp":"2026-07-15T09:00:00Z","entrypoint":"claude-desktop"}\n')

    # A second, separate conversation folder with NO message timestamps at
    # all -- exercises the file_mtime fallback (folder_mtime is unreachable
    # in a fixture without manipulating mtimes directly, so file_mtime is
    # the fallback level under test here).
    session_dir2 = root / "ws1" / "proj1" / "local_sess2"
    nested2 = session_dir2 / ".claude" / "projects" / "C--out-dir2"
    _write(nested2 / "eeee3333-3333-3333-3333-333333333333.jsonl",
           '{"type":"mode","mode":"normal"}\n')


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

        if set(cowork_sessions) != {
            "cccc2222-2222-2222-2222-222222222222", "agent-dddd",
            "eeee3333-3333-3333-3333-333333333333",
        }:
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
        if (cw_r["status"] != "ok" or cw_r["sessions_found"] != 2
                or cw_r["subagent_sessions_found"] != 1):
            v.append(f"census cowork store wrong: {cw_r}")
        if cw_r["message_count"] != 3:  # 2 in top-level + 1 in subagent sidechain
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

        # --- MAX_PATH guard and honest filesystem failure (Phase 4 UAT, 10280L,
        #     2026-07-28) -------------------------------------------------------
        # A live Cowork session's path measured 441 chars before its own filename:
        # the encoded-cwd segment folds the whole path back into itself. Past
        # MAX_PATH, `Path.is_dir()` swallows the OSError and returns False, so the
        # store looked empty rather than unreadable -- the "confident zero" class.

        # 1. _winlong prefixes on Windows, is a no-op elsewhere, and is idempotent.
        #    os.name cannot be forced here: pathlib picks WindowsPath/PosixPath from
        #    it at instantiation, so faking it raises "cannot instantiate
        #    'WindowsPath' on your system". The prefixing branch is therefore only
        #    assertable on a Windows host -- which is the host that matters, since
        #    this whole guard exists for a Windows-only limit and the pre-commit
        #    gate runs there (see
        #    docs/investigation/2026-07-27_gate-green-on-linux-red-on-windows.md).
        if lt.os.name == "nt":
            got = str(lt._winlong(Path(r"C:\a\b")))
            if not got.startswith("\\\\?\\"):
                v.append(f"_winlong did not prefix an absolute path: {got!r}")
            if str(lt._winlong(Path(got))) != got:
                v.append("_winlong is not idempotent on an already-prefixed path")
        else:
            p = Path("/a/b")
            if lt._winlong(p) != p:
                v.append("_winlong is not a no-op off Windows")

        # 2. The guard lives on the discovery functions, NOT on the caller. This is
        #    the regression that actually bit: the first fix patched census() only,
        #    ingest_local_transcripts.py builds its own root, and so it kept
        #    silently finding 0 cowork sessions. Anyone moving this back to the
        #    call sites must fail here.
        for fn_name, root in (("discover_cli_store", cli_root),
                              ("discover_cowork_store", cowork_root)):
            seen: list[Path] = []
            real = lt._winlong
            try:
                lt._winlong = lambda p, _s=seen, _r=real: (_s.append(p), _r(p))[1]
                list(getattr(lt, fn_name)(root))
            finally:
                lt._winlong = real
            if not seen:
                v.append(f"{fn_name} does not apply the MAX_PATH guard itself -- "
                         "a caller building its own root would lose it")

        # 3. A filesystem failure is reported, never swallowed. Passing a FILE
        #    where a directory is expected raises NotADirectoryError (an OSError)
        #    deterministically on every platform, standing in for the ACL/long-path
        #    cases that are not reproducible in a fixture.
        not_a_dir = cli_root / "C--Users-x-repo" / "aaaa1111-1111-1111-1111-111111111111.jsonl"
        errs: list[str] = []
        if lt._safe_subdirs(not_a_dir, errs) != []:
            v.append("_safe_subdirs returned entries for a non-directory")
        if not errs:
            v.append("_safe_subdirs swallowed an OSError instead of reporting it")

        # 4. The census surfaces the channel, so a zero count can be distinguished
        #    from an unreadable store by a reader of the report.
        real_machine2 = lt.machine
        try:
            lt.machine = lambda host=None: {
                "_hostname": "test-host",
                "cli_transcripts_home": str(cli_root),
                "cowork_transcripts_home": str(cowork_root),
            }
            rep = lt.census()
        finally:
            lt.machine = real_machine2
        if "access_errors" not in rep["stores"]["cli"]:
            v.append("census store report has no access_errors key -- a zero "
                     "session count cannot be told apart from an unreadable store")

        # --- read-only: source files untouched -----------------------------------
        # mtimes unchanged after everything above -- discovery/parse/census must
        # never write into either store.
        target = cli_root / "C--Users-x-repo" / "aaaa1111-1111-1111-1111-111111111111.jsonl"
        before = target.stat().st_mtime
        lt.parse_session(next(iter(lt.discover_cli_store(cli_root))))
        after = target.stat().st_mtime
        if before != after:
            v.append("parse_session modified a source file's mtime")

        # --- K1: conversation_id surfaced, cowork only ----------------------
        cowork_tfs = list(lt.discover_cowork_store(cowork_root))
        cowork_sessions = [lt.parse_session(tf) for tf in cowork_tfs]
        conv_ids = {s.conversation_id for s in cowork_sessions if not s.is_sidechain
                    and "cccc2222" in s.thread_id}
        if conv_ids != {"local_sess1"}:
            v.append(f"cowork top-level session conversation_id wrong: {conv_ids}")
        sidechain_ids = {s.conversation_id for s in cowork_sessions if s.is_sidechain}
        if "local_sess1" not in sidechain_ids:
            v.append("subagent sidechain lost its conversation_id -- grouping "
                      "would silently split it into its own conversation")

        cli_tfs = list(lt.discover_cli_store(cli_root))
        cli_sessions = [lt.parse_session(tf) for tf in cli_tfs]
        if any(s.conversation_id is not None for s in cli_sessions):
            v.append("a CLI-store session was given a conversation_id -- "
                      "that store has no such grouping folder")

        # --- K1/K2: group_conversations + order_newest_first -----------------
        all_sessions = cowork_sessions + cli_sessions
        conversations = lt.group_conversations(all_sessions)
        by_id = {c.conversation_id: c for c in conversations}

        conv1 = by_id.get("local_sess1")
        if conv1 is None:
            v.append("local_sess1 did not come back as a Conversation")
        else:
            if len(conv1.sessions) != 2:
                v.append(f"local_sess1 should fold top-level + subagent into one "
                          f"conversation (2 files), got {len(conv1.sessions)}")
            if conv1.real_time_source != "last_message_timestamp":
                v.append(f"local_sess1 should resolve via last_message_timestamp, "
                          f"got {conv1.real_time_source!r}")
            # The subagent's later timestamp (09:00:00) must win over the
            # top-level file's own last message (00:00:05).
            if conv1.real_time != "2026-07-15T09:00:00Z":
                v.append(f"local_sess1 real_time should take the newest across "
                         f"both files, got {conv1.real_time!r}")

        conv2 = by_id.get("local_sess2")
        if conv2 is None:
            v.append("local_sess2 (no message timestamps) did not come back as "
                      "a Conversation -- must fall back to file_mtime, not vanish")
        elif conv2.real_time_source != "file_mtime":
            v.append(f"local_sess2 should fall back to file_mtime, got "
                      f"{conv2.real_time_source!r}")

        # A CLI session is its own conversation, keyed cli:<uuid>.
        cli_key = "cli:aaaa1111-1111-1111-1111-111111111111"
        if cli_key not in by_id:
            v.append("a CLI session did not get its own cli:<uuid> conversation key")

        included, excluded = lt.order_newest_first(conversations)
        if excluded:
            v.append(f"fixture has no unresolvable-timestamp conversation, but "
                      f"{len(excluded)} came back excluded: "
                      f"{[c.conversation_id for c in excluded]}")
        times = [c.real_time for c in included]
        if times != sorted(times, reverse=True):
            v.append("order_newest_first did not return conversations newest-first")

        # An unresolvable conversation (no message ts, unreadable path for
        # mtime) must be excluded and named, never silently dropped or
        # sorted to the end by omission.
        fake = lt.ParsedSession(
            thread_id="ffff0000-0000-0000-0000-000000000000", store="cowork",
            encoded_cwd="C--nowhere", path=Path("/nonexistent/path/x.jsonl"),
            conversation_id="local_ghost",
        )
        ghost_conversations = lt.group_conversations([fake])
        ghost = ghost_conversations[0]
        if not ghost.excluded or not ghost.exclude_reason:
            v.append("a conversation with no resolvable timestamp at all was not "
                      "excluded-and-named")
        ghost_included, ghost_excluded = lt.order_newest_first(ghost_conversations)
        if ghost_included or ghost not in ghost_excluded:
            v.append("order_newest_first did not route the unresolvable "
                      "conversation into 'excluded'")

    return v
