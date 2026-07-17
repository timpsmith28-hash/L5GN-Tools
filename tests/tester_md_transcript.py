"""normalize_md_transcript: parse a markdown transcript into vault threads.

Hermetic: primes sys.path for the vendored pipeline, drives ingest_file against a
temp sqlite with just the columns it writes."""
from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

_PIPE = Path(__file__).resolve().parent.parent / "chronicler" / "pipeline"


def _schema(conn) -> None:
    conn.executescript(
        "CREATE TABLE threads(thread_id TEXT PRIMARY KEY, source TEXT, account TEXT, title TEXT,"
        " created_at TEXT, updated_at TEXT, status TEXT, project_link TEXT, project_confidence TEXT,"
        " review_status TEXT, raw_ref TEXT, parser_version TEXT, substantive INTEGER);"
        "CREATE TABLE messages(message_id TEXT PRIMARY KEY, thread_id TEXT, seq INTEGER, role TEXT,"
        " content TEXT, created_at TEXT);"
    )


def run() -> list[str]:
    v: list[str] = []
    if str(_PIPE) not in sys.path:
        sys.path.insert(0, str(_PIPE))
    import normalize_md_transcript as nmt

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        conn = sqlite3.connect(str(td / "t.db"))
        conn.row_factory = sqlite3.Row
        _schema(conn)

        # Frontmatter + Human/Claude markers (alias mapping) + 4 turns.
        md = td / "work-thread.md"
        md.write_text(
            "---\nsource: claude\naccount: claude-work-manual\ntitle: Sandbox Setup\n"
            "created_at: 2026-07-17\n---\n"
            "**User:**\nhello there\n\n**Assistant:**\nhi, how can I help?\n\n"
            "**Human:**\nmap Human to user please\n\n**Claude:**\nand Claude to assistant\n",
            encoding="utf-8")

        rec = nmt.ingest_file(conn, md)
        if rec["status"] != "ingested" or rec["messages"] != 4:
            return v + [f"md_transcript: ingest wrong: {rec}"]
        th = conn.execute("SELECT * FROM threads").fetchone()
        if th["account"] != "claude-work-manual" or th["title"] != "Sandbox Setup":
            v.append(f"md_transcript: thread meta wrong {th['account']}/{th['title']}")
        if th["substantive"] != 1:
            v.append("md_transcript: 4-turn thread should be substantive")
        if th["parser_version"] != "md_transcript_v1":
            v.append("md_transcript: parser_version not stamped")
        rows = conn.execute("SELECT seq, role, content FROM messages ORDER BY seq").fetchall()
        if [r["role"] for r in rows] != ["user", "assistant", "user", "assistant"]:
            v.append(f"md_transcript: role mapping wrong {[r['role'] for r in rows]}")
        if rows[2]["content"] != "map Human to user please":
            v.append("md_transcript: content not captured verbatim")

        # Idempotency: same file again -> skipped, no duplicate.
        if nmt.ingest_file(conn, md)["status"] != "skipped (exists)":
            v.append("md_transcript: re-ingest should skip an existing thread")
        if conn.execute("SELECT count(*) FROM threads").fetchone()[0] != 1:
            v.append("md_transcript: re-ingest should not duplicate the thread")

        # force -> re-ingests cleanly, replacing (not duplicating) messages.
        if nmt.ingest_file(conn, md, force=True)["status"] != "ingested":
            v.append("md_transcript: force should re-ingest")
        if conn.execute("SELECT count(*) FROM messages").fetchone()[0] != 4:
            v.append("md_transcript: force re-ingest should replace, not duplicate, messages")

        # No-frontmatter short transcript -> defaults + fragment flag.
        short = td / "short.md"
        short.write_text("**User:**\nq\n\n**Assistant:**\na\n", encoding="utf-8")
        r2 = nmt.ingest_file(conn, short)
        st = conn.execute("SELECT substantive, account FROM threads WHERE thread_id=?",
                          (r2["thread_id"],)).fetchone()
        if st["substantive"] != 0:
            v.append("md_transcript: a 2-turn thread should be a fragment")
        if st["account"] != "claude-work-manual":
            v.append("md_transcript: default account should apply without frontmatter")

        conn.close()
    return v
