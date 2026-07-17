"""
Chronicler DB helper.

Thin wrapper around sqlite3 (stdlib — no CLI needed, no extra install).
Run standalone to (re)create the schema:

    python3 pipeline/db.py

Import from normalizers to get a connection:

    from db import get_connection
    conn = get_connection()
"""
import os
import sqlite3
from pathlib import Path

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
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON;")
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
