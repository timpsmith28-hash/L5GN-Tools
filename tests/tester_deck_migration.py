"""tester_deck_migration: db.ensure_deck_schema migrates a pre-existing vault
in place (Command Deck follow-up: "migrate an existing vault to the deck
schema").

The bug this closes: schema.sql declares candidate_project/rival_project via
`CREATE TABLE IF NOT EXISTS review_queue (...)`, which is a no-op on any DB
where review_queue already exists -- so a vault built before this brief never
gained those columns. Every other tester in the suite builds its DB fresh
from schema.sql, so that class of defect is invisible to the gate by
construction. This tester is the fix for the blind spot: it builds a DB in
the PRE-deck shape by hand (deliberately NOT from current schema.sql) and
proves the migration function repairs it.
"""
from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

_PIPE = Path(__file__).resolve().parent.parent / "chronicler" / "pipeline"
_SCHEMA = _PIPE / "schema.sql"

# The review_queue shape as it existed BEFORE this brief -- no
# candidate_project/rival_project, no review_rulings table. Hand-written on
# purpose; sourcing this from current schema.sql would defeat the point (it
# would build the post-migration shape and never exercise the migration path).
_PRE_DECK_SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS threads (
    thread_id           TEXT PRIMARY KEY,
    source               TEXT NOT NULL,
    account              TEXT NOT NULL,
    title                TEXT,
    created_at           TEXT,
    project_link         TEXT,
    project_confidence   TEXT
);

CREATE TABLE IF NOT EXISTS review_queue (
    item_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    type                TEXT,
    thread_id           TEXT,
    candidate_thread_id TEXT,
    confidence          REAL,
    status              TEXT DEFAULT 'pending',
    note                TEXT,
    created_at          TEXT,
    resolved_at         TEXT
);
"""


def _table_info(conn, table):
    """Column shape as (name, type, notnull, pk) tuples, order-independent --
    ALTER TABLE ADD COLUMN always appends, but a fresh CREATE TABLE's column
    order is whatever schema.sql wrote, so comparing as a SET is the honest
    anti-drift check (same columns, not necessarily same physical order)."""
    return {(r[1], r[2], r[3], r[5]) for r in conn.execute(f"PRAGMA table_info({table})")}


def run() -> list[str]:
    v: list[str] = []
    if str(_PIPE) not in sys.path:
        sys.path.insert(0, str(_PIPE))
    import db as pipeline_db

    # --- 1/2: pre-deck DB migrates cleanly; a second call is a no-op ---
    with tempfile.TemporaryDirectory() as td:
        old_db = Path(td) / "old.db"
        conn = sqlite3.connect(str(old_db))
        conn.row_factory = sqlite3.Row
        conn.executescript(_PRE_DECK_SCHEMA)
        conn.execute(
            "INSERT INTO review_queue (type, thread_id, status, note, created_at) "
            "VALUES ('project_link', 'T1', 'pending', 'suggest -> x', '2026-06-01T00:00:00Z')")
        conn.commit()

        result = pipeline_db.ensure_deck_schema(conn)
        if result is not True:
            v.append(f"ensure_deck_schema: expected True on a real review_queue, got {result!r}")

        cols = {r[1] for r in conn.execute("PRAGMA table_info(review_queue)")}
        if not {"candidate_project", "rival_project"} <= cols:
            v.append(f"ensure_deck_schema: columns missing after migration: {cols}")

        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "review_rulings" not in tables:
            v.append("ensure_deck_schema: review_rulings table not created")

        # pre-existing data untouched
        row = conn.execute("SELECT type, thread_id, note FROM review_queue WHERE thread_id='T1'").fetchone()
        if row is None or row["note"] != "suggest -> x":
            v.append("ensure_deck_schema: pre-existing review_queue row was altered")

        # review_rulings is writable with the expected shape
        conn.execute(
            "INSERT INTO review_rulings (thread_id, candidate_project, verdict, ruled_at) "
            "VALUES ('T1', 'x', 'rejected', '2026-06-01T00:00:00Z')")
        conn.commit()

        snapshot_after_first = (
            _table_info(conn, "review_queue"),
            _table_info(conn, "review_rulings"),
            [dict(r) for r in conn.execute("SELECT * FROM review_queue ORDER BY item_id")],
            [dict(r) for r in conn.execute("SELECT * FROM review_rulings ORDER BY item_id")],
        )

        # second call: idempotent, no error, nothing changes
        try:
            result2 = pipeline_db.ensure_deck_schema(conn)
        except Exception as exc:  # noqa: BLE001
            result2 = None
            v.append(f"ensure_deck_schema: second call raised {type(exc).__name__}: {exc}")
        else:
            if result2 is not True:
                v.append(f"ensure_deck_schema: second call should return True, got {result2!r}")
            snapshot_after_second = (
                _table_info(conn, "review_queue"),
                _table_info(conn, "review_rulings"),
                [dict(r) for r in conn.execute("SELECT * FROM review_queue ORDER BY item_id")],
                [dict(r) for r in conn.execute("SELECT * FROM review_rulings ORDER BY item_id")],
            )
            if snapshot_after_second != snapshot_after_first:
                v.append("ensure_deck_schema: second call was not a no-op")

        conn.close()

    # --- 3: an empty DB (no review_queue at all) -> False, nothing created ---
    with tempfile.TemporaryDirectory() as td:
        empty_db = Path(td) / "empty.db"
        conn = sqlite3.connect(str(empty_db))
        result = pipeline_db.ensure_deck_schema(conn)
        if result is not False:
            v.append(f"ensure_deck_schema: expected False on an empty DB, got {result!r}")
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if tables:
            v.append(f"ensure_deck_schema: created table(s) on an empty DB: {tables}")
        conn.close()

    # --- 4: anti-drift -- a migrated pre-deck DB and a fresh schema.sql build
    #     must agree on review_queue's column set and review_rulings' shape ---
    with tempfile.TemporaryDirectory() as td:
        migrated_db = Path(td) / "migrated.db"
        conn = sqlite3.connect(str(migrated_db))
        conn.executescript(_PRE_DECK_SCHEMA)
        pipeline_db.ensure_deck_schema(conn)
        migrated_queue_cols = _table_info(conn, "review_queue")
        migrated_rulings_cols = _table_info(conn, "review_rulings")
        conn.close()

        fresh_db = Path(td) / "fresh.db"
        conn = sqlite3.connect(str(fresh_db))
        conn.executescript(_SCHEMA.read_text(encoding="utf-8"))
        fresh_queue_cols = _table_info(conn, "review_queue")
        fresh_rulings_cols = _table_info(conn, "review_rulings")
        conn.close()

        if migrated_queue_cols != fresh_queue_cols:
            v.append(
                "anti-drift: migrated review_queue columns differ from a fresh "
                f"schema.sql build -- migrated={migrated_queue_cols} fresh={fresh_queue_cols} "
                "(db.ensure_deck_schema and schema.sql have diverged)")
        if migrated_rulings_cols != fresh_rulings_cols:
            v.append(
                "anti-drift: migrated review_rulings columns differ from a fresh "
                f"schema.sql build -- migrated={migrated_rulings_cols} fresh={fresh_rulings_cols}")

    # --- 5: review/core's refusal path fires on an unmigrated DB and names
    #     the remedy; a migrated DB opens clean ---
    from chronicler.review import core as review_core

    with tempfile.TemporaryDirectory() as td:
        unmigrated_db = Path(td) / "unmigrated.db"
        conn = sqlite3.connect(str(unmigrated_db))
        conn.executescript(_PRE_DECK_SCHEMA)
        conn.close()

        try:
            review_core.connect(unmigrated_db)
            v.append("core.connect: did NOT refuse an unmigrated vault")
        except review_core.DeckSchemaNotMigratedError as exc:
            if "backfill_candidate_project.py" not in str(exc):
                v.append(f"core.connect: refusal message doesn't name the remedy: {exc}")
        except Exception as exc:  # noqa: BLE001
            v.append(f"core.connect: wrong exception type on an unmigrated vault: "
                     f"{type(exc).__name__}: {exc}")

        migrated_db2 = Path(td) / "migrated2.db"
        conn = sqlite3.connect(str(migrated_db2))
        conn.executescript(_PRE_DECK_SCHEMA)
        pipeline_db.ensure_deck_schema(conn)
        conn.close()
        try:
            good_conn = review_core.connect(migrated_db2)
            good_conn.close()
        except review_core.DeckSchemaNotMigratedError as exc:
            v.append(f"core.connect: refused a properly migrated vault: {exc}")

    return v
