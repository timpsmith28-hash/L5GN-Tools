"""set_substantive.py -- recompute threads.substantive from message counts.

A thread is 'substantive' when it has >= SUBSTANTIVE_MIN_MESSAGES messages (the
agreed cut from the DB freeze); otherwise it's a fragment. Fresh ingest inserts
threads with substantive NULL, so this backfills them -- and keeps existing rows
honest as reconciliation moves messages between threads. Idempotent, stdlib-only.
Runs as a DB-only pipeline stage just before render, so the frozen-schema
contract (substantive is always set) survives new ingests.
"""
from __future__ import annotations

from db import get_connection

# Keep in lockstep with finalize_db.SUBSTANTIVE_MIN_MESSAGES.
SUBSTANTIVE_MIN_MESSAGES = 4


def run() -> None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE threads SET substantive = CASE WHEN ("
        "  SELECT count(*) FROM messages m WHERE m.thread_id = threads.thread_id"
        f") >= {SUBSTANTIVE_MIN_MESSAGES} THEN 1 ELSE 0 END"
    )
    conn.commit()
    row = cur.execute(
        "SELECT COALESCE(SUM(substantive), 0) AS s, COUNT(*) AS n FROM threads"
    ).fetchone()
    conn.close()
    sub, total = row["s"], row["n"]
    print(f"set_substantive: {sub} substantive / {total - sub} fragment "
          f"of {total} threads (cut: >= {SUBSTANTIVE_MIN_MESSAGES} msgs)")


if __name__ == "__main__":
    run()
