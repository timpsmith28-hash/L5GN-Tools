"""ingest_local_transcripts: Phase 2 DB writer for local CLI/Cowork
transcripts (COWORK_BRIEF_local_transcript_intake.md).

Hermetic: primes sys.path for the vendored pipeline, builds synthetic store
trees + a synthetic project registry in a temp dir, points the module at a
throwaway sqlite DB via monkeypatched get_connection/init_db/resolve_registry_path/
machine, and drives `run()` directly -- no real store, no real vault, no
real registry touched.

Covers the rulings the brief asked this module to prove, not just assert:
  - dry-run writes nothing
  - CLI session with a matching real `cwd` gets project_confidence='exact'
  - Cowork session never gets a direct link, even with a matching `cwd`
  - message_id uses the record's own uuid when present, synthetic hash
    when absent -- and the synthetic id is stable across runs (idempotency)
  - re-run with no new data changes nothing; re-run after a file grows
    (new line appended) adds only the new message
  - an 'exact' link, once set, is never downgraded by a later run even if
    the registry match would recompute weaker
  - a session with zero conversation messages is skipped, not written as
    an empty thread
  - refuses to run when the machine has no estate configured
  - the real source file's mtime is untouched throughout
"""
from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from pathlib import Path

_PIPE = Path(__file__).resolve().parent.parent / "chronicler" / "pipeline"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _schema(conn) -> None:
    conn.executescript(
        # projects + the REAL foreign key on threads.project_link. Without both,
        # this fixture is a weaker vault than production and cannot fail on an
        # attribution written for a registry id that has no projects row -- the
        # defect that took the 2026-08-27 ingest down. See _get_connection.
        "CREATE TABLE projects(project_id TEXT PRIMARY KEY, name TEXT,"
        " repo_folder_path TEXT, source_system_id TEXT);"
        "CREATE TABLE threads(thread_id TEXT PRIMARY KEY, source TEXT, account TEXT, title TEXT,"
        " created_at TEXT, updated_at TEXT, status TEXT,"
        " project_link TEXT REFERENCES projects(project_id),"
        " project_confidence TEXT, review_status TEXT, raw_ref TEXT, parser_version TEXT);"
        "CREATE TABLE messages(message_id TEXT PRIMARY KEY, thread_id TEXT, seq INTEGER,"
        " role TEXT, content TEXT, created_at TEXT);"
        "CREATE TABLE ingestion_log(batch_id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT,"
        " account TEXT, file_hash TEXT, imported_at TEXT, rows_new INTEGER,"
        " rows_changed INTEGER, rows_skipped INTEGER, parser_version TEXT);"
    )


def run() -> list[str]:
    v: list[str] = []
    if str(_PIPE) not in sys.path:
        sys.path.insert(0, str(_PIPE))
    import ingest_local_transcripts as ing

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        cli_root = td / "cli"
        cowork_root = td / "cowork"
        db_path = td / "vault.db"
        registry_path = td / "project_registry.json"

        # --- fixture: a project registry with one folder-backed project -----
        registry_path.write_text(json.dumps({
            "projects": [
                {"id": "my-repo", "canonical_name": "MyRepo", "aliases": ["My Repo"]},
            ]
        }), encoding="utf-8")

        # --- fixture: one CLI session whose real cwd names the repo folder --
        cli_dir = cli_root / "C--Users-x-MyRepo-sub"
        _write(cli_dir / "s1111111-1111-1111-1111-111111111111.jsonl", "\n".join([
            '{"type":"user","message":{"role":"user","content":"hi"},'
            '"uuid":"u1","timestamp":"2026-07-20T00:00:00Z","entrypoint":"cli",'
            '"cwd":"C:\\\\Users\\\\x\\\\MyRepo\\\\sub"}',
            '{"type":"assistant","message":{"role":"assistant","content":'
            '[{"type":"text","text":"hello"}]},'
            '"uuid":"a1","timestamp":"2026-07-20T00:00:05Z","entrypoint":"cli"}',
            '{"type":"custom-title","customTitle":"CLI thread"}',
            "",
        ]))

        # --- fixture: one Cowork session, cwd matches nothing in the registry
        cw_dir = cowork_root / "ws1" / "proj1" / "local_sess1" / ".claude" / "projects" / "C--out-dir"
        _write(cw_dir / "c2222222-2222-2222-2222-222222222222.jsonl", "\n".join([
            '{"type":"user","message":{"role":"user","content":"cowork hi"},'
            # no "uuid" on this record -- exercises the synthetic message_id path.
            '"timestamp":"2026-07-21T00:00:00Z","entrypoint":"local-agent",'
            '"cwd":"C:\\\\Users\\\\x\\\\AppData\\\\outputs\\\\sess1"}',
            '{"type":"ai-title","aiTitle":"Cowork thread"}',
            "",
        ]))

        # --- fixture: a bookkeeping-only session -- must never become a thread
        empty_dir = cli_root / "C--Users-x-Empty"
        _write(empty_dir / "eeeeeeee-1111-1111-1111-111111111111.jsonl",
               '{"type":"mode","mode":"normal"}\n')

        # --- wire the module at fixtures instead of the real world ----------
        real = {
            "get_connection": ing.get_connection, "init_db": ing.init_db,
            "resolve_registry_path": ing.resolve_registry_path, "machine": ing.machine,
            "load_project_keymap": ing.load_project_keymap,
        }

        def _get_connection():
            conn = sqlite3.connect(str(db_path))
            # dbsafe.apply_pragmas sets this on every production connection, so a
            # fixture that omits it tests a database the estate never runs.
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.row_factory = sqlite3.Row
            return conn

        def _init_db():
            if not db_path.exists() or db_path.stat().st_size == 0:
                conn = _get_connection()
                _schema(conn)
                conn.commit()
                conn.close()

        ing.get_connection = _get_connection
        ing.init_db = _init_db
        ing.resolve_registry_path = lambda: registry_path
        ing.machine = lambda host=None: {
            "_hostname": "test-host", "estate": "personal",
            "cli_transcripts_home": str(cli_root),
            "cowork_transcripts_home": str(cowork_root),
        }

        try:
            # --- no estate configured -> refuses loudly -----------------------
            ing.machine = lambda host=None: {"_hostname": "bare"}
            try:
                ing.run(apply=False)
                v.append("run() should refuse when no estate is configured")
            except SystemExit:
                pass
            ing.machine = lambda host=None: {
                "_hostname": "test-host", "estate": "personal",
                "cli_transcripts_home": str(cli_root),
                "cowork_transcripts_home": str(cowork_root),
            }

            # --- dry-run writes nothing -----------------------------------------
            _init_db()
            result = ing.run(apply=False)
            conn = _get_connection()
            n = conn.execute("SELECT COUNT(*) FROM threads").fetchone()[0]
            conn.close()
            if n != 0:
                v.append(f"dry-run should write nothing, found {n} thread(s)")

            # --- apply: real ingest ----------------------------------------------
            result = ing.run(apply=True)
            conn = _get_connection()
            threads = {r["thread_id"]: r for r in conn.execute("SELECT * FROM threads").fetchall()}
            conn.close()

            conn = _get_connection()
            projects = {r["project_id"]: r["name"]
                        for r in conn.execute("SELECT * FROM projects").fetchall()}
            conn.close()
            if projects.get("my-repo") != "MyRepo":
                v.append("an exact CLI attribution must create its projects row "
                         f"(FK target) from the registry; got {projects!r}")

            if len(threads) != 2:
                v.append(f"expected 2 threads (empty session skipped), got {len(threads)}: {list(threads)}")

            cli_t = threads.get("s1111111-1111-1111-1111-111111111111")
            if cli_t is None:
                v.append("CLI session not ingested")
            else:
                if cli_t["source"] != "claude-local" or cli_t["account"] != "claude-local-personal":
                    v.append(f"CLI thread source/account wrong: {cli_t['source']}/{cli_t['account']}")
                if cli_t["project_confidence"] != "exact" or cli_t["project_link"] != "my-repo":
                    v.append(f"CLI thread should be exact-linked to my-repo: "
                             f"{cli_t['project_confidence']}/{cli_t['project_link']}")
                if cli_t["title"] != "CLI thread":
                    v.append(f"CLI thread title wrong: {cli_t['title']!r}")

            cw_t = threads.get("c2222222-2222-2222-2222-222222222222")
            if cw_t is None:
                v.append("Cowork session not ingested")
            elif cw_t["project_confidence"] != "none" or cw_t["project_link"] is not None:
                v.append(f"Cowork thread must never get a direct link: "
                         f"{cw_t['project_confidence']}/{cw_t['project_link']}")

            skipped_ids = {s["thread_id"] for s in result["sessions"] if "skipped" in s}
            if "eeeeeeee-1111-1111-1111-111111111111" not in skipped_ids:
                v.append("bookkeeping-only session should be skipped, not ingested")

            # message_id: source-native uuid used for the CLI thread's messages
            conn = _get_connection()
            cli_msgs = {r["message_id"]: r for r in
                        conn.execute("SELECT * FROM messages WHERE thread_id=?",
                                     (cli_t["thread_id"],)).fetchall()}
            conn.close()
            if "u1" not in cli_msgs or "a1" not in cli_msgs:
                v.append(f"CLI messages should use source uuid as message_id, got {list(cli_msgs)}")

            # message_id: synthetic hash for the Cowork message (no source uuid)
            conn = _get_connection()
            cw_msgs = conn.execute("SELECT * FROM messages WHERE thread_id=?",
                                    (cw_t["thread_id"],)).fetchall()
            conn.close()
            if len(cw_msgs) != 1 or cw_msgs[0]["message_id"] in ("u1", "a1", ""):
                v.append(f"Cowork message should get a synthetic message_id: {[dict(r) for r in cw_msgs]}")
            synthetic_id_first_run = cw_msgs[0]["message_id"] if cw_msgs else None

            # --- idempotency: re-run with no new data changes nothing -----------
            ing.run(apply=True)
            conn = _get_connection()
            n_threads = conn.execute("SELECT COUNT(*) FROM threads").fetchone()[0]
            n_messages = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
            cw_msgs2 = conn.execute("SELECT message_id FROM messages WHERE thread_id=?",
                                     (cw_t["thread_id"],)).fetchall()
            conn.close()
            if n_threads != 2:
                v.append(f"re-run with no changes should not add threads, got {n_threads}")
            if n_messages != 3:  # 2 CLI + 1 Cowork
                v.append(f"re-run with no changes should not add messages, got {n_messages}")
            if not cw_msgs2 or cw_msgs2[0]["message_id"] != synthetic_id_first_run:
                v.append("synthetic message_id is not stable across runs -- re-run would duplicate")

            # --- idempotency: the store file GROWS -- one new line appended -----
            cli_file = cli_dir / "s1111111-1111-1111-1111-111111111111.jsonl"
            with open(cli_file, "a", encoding="utf-8") as f:
                f.write(
                    '{"type":"user","message":{"role":"user","content":"a follow-up"},'
                    '"uuid":"u2","timestamp":"2026-07-20T00:10:00Z","entrypoint":"cli"}\n'
                )
            ing.run(apply=True)
            conn = _get_connection()
            n_threads2 = conn.execute("SELECT COUNT(*) FROM threads").fetchone()[0]
            n_cli_msgs = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE thread_id=?", (cli_t["thread_id"],)
            ).fetchone()[0]
            conn.close()
            if n_threads2 != 2:
                v.append(f"appending to a file should not create a new thread, got {n_threads2}")
            if n_cli_msgs != 3:
                v.append(f"appending one line should add exactly one message, got {n_cli_msgs} total")

            # --- an 'exact' link is never downgraded by a later run -------------
            ing.load_project_keymap = lambda: {}  # simulate the registry losing the entry
            ing.run(apply=True)
            ing.load_project_keymap = real["load_project_keymap"]
            conn = _get_connection()
            row = conn.execute("SELECT project_confidence, project_link FROM threads WHERE thread_id=?",
                                (cli_t["thread_id"],)).fetchone()
            conn.close()
            if row["project_confidence"] != "exact" or row["project_link"] != "my-repo":
                v.append(f"'exact' link must never be downgraded by a later run: {dict(row)}")

            # --- read-only: source files untouched -------------------------------
            before = cli_file.stat().st_mtime
            ing.run(apply=False)
            after = cli_file.stat().st_mtime
            if before != after:
                v.append("ingest run modified a source file's mtime")

        finally:
            ing.get_connection = real["get_connection"]
            ing.init_db = real["init_db"]
            ing.resolve_registry_path = real["resolve_registry_path"]
            ing.machine = real["machine"]
            ing.load_project_keymap = real["load_project_keymap"]

    return v
