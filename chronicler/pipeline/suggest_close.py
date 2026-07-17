"""
30-day suggested_close check — build spec item 10 (design doc section 9.8).

A scheduled/on-run check: any 'open' thread whose updated_at is 30+ days in
the past, and which isn't already flagged, gets suggested_close=1 plus a
close_suggestion review_queue row. Nothing closes automatically — the user
confirms by flipping status: closed themselves in Obsidian (9.8 / 13.3).

Idempotent by construction: the query only selects threads where
suggested_close is not already 1, so re-running never double-flags. If a
user manually resets suggested_close: false via sync-back and the thread is
still stale on the next run, it gets re-flagged — that's by design, not a
bug (see 9.8).

Usage:
    python3 pipeline/suggest_close.py [--days 30]
"""
import argparse

from db import get_connection, init_db

PARSER_VERSION = "suggest_close_v1"
DEFAULT_DAYS = 30


def run(days: int):
    init_db()
    conn = get_connection()
    cur = conn.cursor()

    candidates = cur.execute(
        """SELECT thread_id, updated_at FROM threads
           WHERE status = 'open'
             AND suggested_close = 0
             AND updated_at IS NOT NULL
             AND julianday('now') - julianday(updated_at) >= ?""",
        (days,),
    ).fetchall()

    for row in candidates:
        cur.execute(
            "UPDATE threads SET suggested_close = 1 WHERE thread_id = ?",
            (row["thread_id"],),
        )
        cur.execute(
            """INSERT INTO review_queue (type, thread_id, confidence, status, note, created_at)
               VALUES ('close_suggestion', ?, NULL, 'pending', ?, datetime('now'))""",
            (
                row["thread_id"],
                f"Thread open with no activity since {row['updated_at']} "
                f"({days}+ days) — suggest review for closing.",
            ),
        )

    # Item 8 — log this check as its own batch (no raw file to hash).
    cur.execute(
        """INSERT INTO ingestion_log (source, account, file_hash, imported_at,
                                       rows_new, rows_changed, rows_skipped, parser_version)
           VALUES ('all', NULL, NULL, datetime('now'), ?, 0, 0, ?)""",
        (len(candidates), PARSER_VERSION),
    )

    conn.commit()
    conn.close()

    print(f"Threads flagged suggested_close (stale {days}+ days): {len(candidates)}")
    for row in candidates:
        print(f"  {row['thread_id']}: last updated {row['updated_at']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS)
    args = parser.parse_args()
    run(args.days)
