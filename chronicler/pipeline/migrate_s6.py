"""
S6 schema migration (idempotent).

Brings an existing chronicler.db up to the shape S6 (relink.py) needs. Three
changes, each safe to apply zero-or-many times:

  1. `link_evidence` table (+ its two indexes) — created IF NOT EXISTS. If S4
     (xref_filenames.py) already created it and filled it with rows, those are
     left completely untouched; we only assert the shape is what S6 expects.
  2. `link_evidence_ids` column on `threads` — added via ALTER only when
     PRAGMA table_info shows it is missing (SQLite has no ADD COLUMN IF NOT
     EXISTS, so we check first). Existing rows get NULL, which relink reads as
     "never re-linked."
  3. `project_confidence` gains a new legal value, `evidence`. This is not a
     constraint change (the column is free-form TEXT), it is a *convention*:

         authority, low -> high:  none < fuzzy < evidence < manual
         ('exact' is source-native and, like 'manual', automation never
          overwrites it.)

     The rule S6 enforces: automation MAY upgrade fuzzy -> evidence, but only
     a human may change an `evidence` link to anything else. migrate_s6.py only
     records/prints this rule; relink.py is what honours it at write time.

Standing rules honoured: loud failure (a link_evidence table whose columns do
NOT match the S6 spec stops the run rather than silently coexisting), UTF-8,
UTC ISO-8601, single-transaction apply (all DDL lands or none does).

Sandbox note: like the rest of the pipeline, point CHRONICLER_DB_PATH at a
/tmp copy when running inside the Cowork sandbox (the mount can't do SQLite
locking), then cp the result back. On a normal machine just run it.

Usage:
    python3 pipeline/migrate_s6.py            # dry-run (default): report only
    python3 pipeline/migrate_s6.py --apply    # execute the migration
"""
import argparse

from db import get_connection, DB_PATH

# Exactly the columns S6 specifies for link_evidence (order-independent check).
EXPECTED_EVIDENCE_COLUMNS = {
    "evidence_id", "thread_id", "project", "signal",
    "weight", "detail", "produced_at", "producer_version",
}

LINK_EVIDENCE_DDL = """
CREATE TABLE IF NOT EXISTS link_evidence (
    evidence_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id        TEXT,
    project          TEXT,
    signal           TEXT,
    weight           REAL,
    detail           TEXT,
    produced_at      TEXT,
    producer_version TEXT
);
CREATE INDEX IF NOT EXISTS idx_link_evidence_thread ON link_evidence(thread_id);
CREATE INDEX IF NOT EXISTS idx_link_evidence_signal ON link_evidence(signal);
"""

AUTHORITY_NOTE = (
    "project_confidence authority (low->high): none < fuzzy < evidence < manual "
    "('exact' is source-native, never auto-overwritten). "
    "Automation may upgrade fuzzy->evidence; only a human may change evidence->anything."
)


def table_exists(conn, name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def columns_of(conn, table: str) -> set:
    return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def plan(conn):
    """Return a list of (action_key, human_description) for what would change."""
    actions = []

    # 1. link_evidence table.
    if not table_exists(conn, "link_evidence"):
        actions.append(("create_evidence", "CREATE link_evidence table + 2 indexes"))
    else:
        cols = columns_of(conn, "link_evidence")
        missing = EXPECTED_EVIDENCE_COLUMNS - cols
        extra = cols - EXPECTED_EVIDENCE_COLUMNS
        if missing or extra:
            # Loud failure: an existing table of the wrong shape is a real
            # problem, not something to paper over.
            raise SystemExit(
                "[migrate_s6] link_evidence exists but its columns do not match "
                f"the S6 spec.\n  missing: {sorted(missing) or 'none'}\n"
                f"  unexpected: {sorted(extra) or 'none'}\n"
                "Refusing to continue — inspect the table before migrating."
            )
        n = conn.execute("SELECT COUNT(*) AS c FROM link_evidence").fetchone()["c"]
        actions.append(("evidence_ok", f"link_evidence already present & correct "
                                       f"({n} existing rows, left untouched)"))

    # 2. threads.link_evidence_ids column.
    if "link_evidence_ids" not in columns_of(conn, "threads"):
        actions.append(("add_column", "ALTER threads ADD COLUMN link_evidence_ids TEXT"))
    else:
        actions.append(("column_ok", "threads.link_evidence_ids already present"))

    # 3. confidence convention — nothing structural, just recorded.
    actions.append(("note", AUTHORITY_NOTE))
    return actions


def apply_migration(conn, actions):
    did = []
    for key, _desc in actions:
        if key == "create_evidence":
            conn.executescript(LINK_EVIDENCE_DDL)
            did.append("created link_evidence")
        elif key == "add_column":
            conn.execute("ALTER TABLE threads ADD COLUMN link_evidence_ids TEXT")
            did.append("added threads.link_evidence_ids")
    conn.commit()
    return did


def run(apply: bool):
    conn = get_connection()
    try:
        actions = plan(conn)

        print("=" * 66)
        print("S6 schema migration" + ("" if apply else " (dry-run)"))
        print("=" * 66)
        print(f"DB: {DB_PATH}\n")
        for key, desc in actions:
            marker = {
                "create_evidence": "WILL CREATE ",
                "add_column": "WILL ALTER  ",
                "evidence_ok": "ok          ",
                "column_ok": "ok          ",
                "note": "convention  ",
            }.get(key, "            ")
            print(f"  {marker} {desc}")
        print("-" * 66)

        if not apply:
            pending = [d for k, d in actions if k in ("create_evidence", "add_column")]
            if pending:
                print(f"{len(pending)} change(s) pending. Re-run with --apply to execute.")
            else:
                print("Nothing to do — schema already at S6 (clean no-op).")
            return

        did = apply_migration(conn, actions)
        if did:
            print("Applied: " + "; ".join(did) + ".")
        else:
            print("Nothing to do — schema already at S6 (clean no-op).")
    finally:
        conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Idempotent S6 schema migration.")
    ap.add_argument("--apply", action="store_true",
                    help="Execute the migration (default is dry-run, report only).")
    args = ap.parse_args()
    run(args.apply)
