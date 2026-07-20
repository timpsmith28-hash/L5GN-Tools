"""tester_dbsafe: every connection opens WAL + busy_timeout (DECISIONS 0014).

Hermetic -- builds a throwaway DB in a temp dir and asserts the *properties of the
connection*, not the source text, so the gate stays true if the implementation
moves. The load-bearing assertions:

  * a read/write connection reports ``journal_mode = wal``
  * the WAL setting persists in the file (a second, independent open still sees it)
  * every connection carries a non-zero busy_timeout -- including the read-only
    handle, which is the one a reader uses against a live writer
  * ``connect_readonly`` really is read-only (a write attempt raises)
  * a reader can open and query the DB while a writer holds an open transaction,
    which is the concrete false-``malformed`` / torn-read class this closes
"""
from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from l5gntools import dbsafe


def _seed(path: Path) -> None:
    conn = dbsafe.connect(path)
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT);")
    conn.execute("INSERT INTO t (v) VALUES ('seed');")
    conn.commit()
    conn.close()


def run() -> list[str]:
    v: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "t.db"
        _seed(db)

        # --- read/write connection is in WAL ---
        rw = dbsafe.connect(db)
        try:
            mode = dbsafe.journal_mode(rw)
            if mode != "wal":
                v.append(f"dbsafe: read/write connection reports journal_mode={mode!r}, "
                         "expected 'wal'")
            timeout = rw.execute("PRAGMA busy_timeout;").fetchone()[0]
            if int(timeout) != dbsafe.BUSY_TIMEOUT_MS:
                v.append(f"dbsafe: busy_timeout={timeout}, expected "
                         f"{dbsafe.BUSY_TIMEOUT_MS}")
            if rw.execute("PRAGMA foreign_keys;").fetchone()[0] != 1:
                v.append("dbsafe: foreign_keys not ON on a read/write connection")
        finally:
            rw.close()

        # --- WAL persists in the file: a fresh, plain open still sees it ---
        plain = sqlite3.connect(str(db))
        try:
            persisted = str(plain.execute("PRAGMA journal_mode;").fetchone()[0]).lower()
            if persisted != "wal":
                v.append(f"dbsafe: WAL did not persist in the file (a plain open "
                         f"reports {persisted!r}) -- the mode must be a property of "
                         "the DB, not of one connection")
        finally:
            plain.close()

        # --- read-only handle: timeout applied, writes impossible ---
        ro = dbsafe.connect_readonly(db)
        try:
            ro_timeout = ro.execute("PRAGMA busy_timeout;").fetchone()[0]
            if int(ro_timeout) != dbsafe.BUSY_TIMEOUT_MS:
                v.append(f"dbsafe: read-only busy_timeout={ro_timeout}, expected "
                         f"{dbsafe.BUSY_TIMEOUT_MS} -- the reader is exactly who "
                         "needs the retry window")
            try:
                ro.execute("INSERT INTO t (v) VALUES ('should not happen');")
                ro.commit()
                v.append("dbsafe: connect_readonly accepted a write -- mode=ro is not "
                         "in force")
            except sqlite3.OperationalError:
                pass  # correct: the handle cannot write
        finally:
            ro.close()

        # --- the point of the exercise: reader + open writer coexist ---
        writer = dbsafe.connect(db)
        reader = dbsafe.connect_readonly(db)
        try:
            writer.execute("BEGIN IMMEDIATE;")
            writer.execute("INSERT INTO t (v) VALUES ('uncommitted');")
            try:
                rows = reader.execute("SELECT COUNT(*) FROM t;").fetchone()[0]
            except sqlite3.DatabaseError as exc:
                v.append(f"dbsafe: reader errored while the writer held a "
                         f"transaction ({type(exc).__name__}: {exc}) -- WAL should "
                         "make this impossible")
            else:
                if rows != 1:
                    v.append(f"dbsafe: reader saw {rows} row(s) mid-write, expected "
                             "the last committed state (one row) -- a reader must "
                             "never see an uncommitted write")
            writer.rollback()
        finally:
            reader.close()
            writer.close()

    return v
