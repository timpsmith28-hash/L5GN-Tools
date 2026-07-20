"""
Chronicler DB helper.

Thin wrapper around sqlite3 (stdlib — no CLI needed, no extra install).
Run standalone to (re)create the schema:

    python3 pipeline/db.py

Import from normalizers to get a connection:

    from db import get_connection
    conn = get_connection()

Every connection is opened in WAL mode with a busy_timeout (DECISIONS 0014).
This is the *structural* half of single-writer: WAL lets the one writer and many
readers coexist without a reader seeing a torn page (the false-`malformed` class,
0013), and busy_timeout makes a momentarily-blocked access wait-and-retry instead
of erroring out.

The pragmas themselves live in `l5gntools.dbsafe`, not here, and this module
re-exports them. Reason: the vault is also opened by `l5gntools.backup` (the
VACUUM INTO source) and by the vault scanners, and the scanners are held to the
stdlib-only contract that permits importing `l5gntools` and forbids importing
`chronicler`. One shared implementation therefore has to sit on the l5gntools
side. Callers here are unaffected -- `from db import get_connection` is unchanged.
"""
import os
import sqlite3
from pathlib import Path

from l5gntools.dbsafe import (  # noqa: F401 -- re-exported for pipeline callers
    BUSY_TIMEOUT_MS,
    JOURNAL_MODE,
    apply_pragmas,
    connect_readonly,
    journal_mode,
)

PIPELINE_DIR = Path(__file__).resolve().parent
# CHRONICLER_HOME is the runtime data root (raw_* inputs, vault_staging, the DB).
# It defaults to the folder holding this vendored code, but on a deploy target
# (the knight) set CHRONICLER_HOME to the data volume so per-machine data and the
# shared toolkit code stay separate.
CHRONICLER_ROOT = Path(os.environ.get("CHRONICLER_HOME", str(PIPELINE_DIR.parent)))
# CHRONICLER_DB_PATH overrides just the DB location (defaults under CHRONICLER_ROOT);
# also the escape hatch for filesystems without SQLite file locking (fuse sandboxes).
DB_PATH = Path(os.environ.get("CHRONICLER_DB_PATH", str(CHRONICLER_ROOT / "chronicler.db")))
SCHEMA_PATH = PIPELINE_DIR / "schema.sql"

def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """The one read/write connection factory for the pipeline.

    WAL + busy_timeout + foreign_keys, always, via the shared pragma helper --
    so no pipeline stage can open the vault with weaker settings by forgetting.
    """
    conn = sqlite3.connect(str(db_path), timeout=BUSY_TIMEOUT_MS / 1000)
    apply_pragmas(conn)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path = DB_PATH, schema_path: Path = SCHEMA_PATH) -> None:
    conn = get_connection(db_path)
    with open(schema_path, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    print(f"Schema applied to {db_path}")


if __name__ == "__main__":
    init_db()
