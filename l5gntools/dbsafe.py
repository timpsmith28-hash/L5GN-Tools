"""dbsafe -- the one place SQLite connection pragmas live (DECISIONS 0014).

ARCHITECTURE claims "one writer", but until now nothing enforced it: the review
endpoint (writer), the pipeline (writer), Datasette (reader) and ad-hoc `sqlite3`
sessions could all open the live vault concurrently, each with its own connection
settings. The 0013 false-`malformed` incident was the harmless symptom; a
worse-timed collision between two real writers is how actual corruption happens.

So the pragmas become a property of *how the file is opened*, not something an
operator remembers:

  * ``journal_mode=WAL``   -- one writer and many readers coexist; a reader can
    never see a torn page or a false-malformed state. WAL is persistent in the
    DB file, so setting it once sticks, but we set it on every read/write open
    so a freshly-created DB is never left in rollback-journal mode.
  * ``busy_timeout=5000``  -- a momentarily-blocked access waits and retries for
    five seconds instead of erroring out immediately.
  * ``foreign_keys=ON``    -- pre-existing invariant, kept here so there is one
    pragma block rather than two.

**Why this module lives in l5gntools and not in chronicler/pipeline/db.py.**
Both estates need it. `chronicler/pipeline/db.py` is the pipeline's connection
factory, but `l5gntools.backup` (VACUUM INTO source) and the vault scanners
(`vault_reader`, `project_trail`) also open the vault -- and the scanners are held
to the stdlib-only contract, which permits importing `l5gntools` and forbids
importing `chronicler`. Putting the helper here is therefore the only placement
that lets *every* path share one implementation instead of duplicating pragmas;
`chronicler/pipeline/db.py` re-exports from here, so `from db import
get_connection` keeps working unchanged for the pipeline.

Stdlib-only, no optional deps -- safe to import from anywhere in the toolkit.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

__all__ = ["JOURNAL_MODE", "BUSY_TIMEOUT_MS", "apply_pragmas", "connect",
           "connect_readonly", "journal_mode"]

JOURNAL_MODE = "WAL"
BUSY_TIMEOUT_MS = 5000


def apply_pragmas(conn: sqlite3.Connection, read_only: bool = False) -> sqlite3.Connection:
    """Apply the standing per-connection pragmas to an already-open connection.

    ``read_only=True`` skips ``journal_mode`` -- a ``mode=ro`` handle cannot
    change it and raises if asked -- but still sets ``busy_timeout``, which is
    exactly what a reader needs when the single writer holds the file for a
    moment. It does not need to set WAL: journal_mode is persisted in the file
    by whichever read/write connection set it.
    """
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS};")
    if not read_only:
        conn.execute(f"PRAGMA journal_mode = {JOURNAL_MODE};")
    return conn


def connect(db_path: Path | str, row_factory: bool = True) -> sqlite3.Connection:
    """Read/write connection with WAL + busy_timeout. The writer's entry point."""
    conn = sqlite3.connect(str(db_path), timeout=BUSY_TIMEOUT_MS / 1000)
    apply_pragmas(conn)
    if row_factory:
        conn.row_factory = sqlite3.Row
    return conn


def connect_readonly(db_path: Path | str, row_factory: bool = False) -> sqlite3.Connection:
    """``mode=ro`` connection that still honours busy_timeout.

    ``mode=ro`` guarantees the caller cannot write a single byte (the scanners'
    read-only contract, and backup's guarantee that snapshotting can never mutate
    the vault); the timeout gives it the wait-and-retry behaviour a reader wants
    against a live writer.
    """
    uri = f"file:{Path(db_path).as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=BUSY_TIMEOUT_MS / 1000)
    apply_pragmas(conn, read_only=True)
    if row_factory:
        conn.row_factory = sqlite3.Row
    return conn


def journal_mode(conn: sqlite3.Connection) -> str:
    """The connection's current journal mode, lowercased (``wal`` when correct)."""
    row = conn.execute("PRAGMA journal_mode;").fetchone()
    return str(row[0]).lower() if row else ""
