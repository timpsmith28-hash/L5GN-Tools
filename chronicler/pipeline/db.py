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
import re
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


def resolve_registry_path() -> Path:
    """The one place the pipeline decides where ``project_registry.json`` lives
    (relink_scoring Task F; reconciliation report Task G).

    Order, most-explicit first:
      1. ``CHRONICLER_REGISTRY_PATH`` env -- the knob to set on a deploy target so
         the writer (build_registry) and every reader point at one file
         deterministically, independent of where the checkout happens to sit.
      2. else the per-host derived location
         ``<github_root>/L5GN/.intel_sync/project_registry.json`` where
         ``<github_root> = CHRONICLER_ROOT.parent.parent`` -- the historical
         layout, now computed in ONE place instead of a literal duplicated across
         build_registry / build_inventory / build_activity / build_vocabulary /
         relink / xref_filenames.

    This returns a *location*, never checks existence: writer and readers must
    agree on the same path whether or not the file is there yet. A reader that
    finds nothing at the resolved path fails loud on its own (each consumer already
    does an ``is_file()`` guard) -- the defect F removes is the *silent* fallback
    to a different literal, so this resolver deliberately has none.
    """
    env = os.environ.get("CHRONICLER_REGISTRY_PATH")
    if env:
        return Path(env)
    return CHRONICLER_ROOT.parent.parent / "L5GN" / ".intel_sync" / "project_registry.json"


# ---------------------------------------------------------------------------
# Co-origin identity (relink_scoring Task A)
# ---------------------------------------------------------------------------
# Evidence signals that name the SAME file/token are one piece of evidence, not
# several -- a filename_xref on `world_graph.json`, a path_mention on the
# `L5GN-Crystal-Spire` folder and an inline name_alias on `world_graph` must not
# compound as if independently corroborated. These helpers give every producer
# AND the consumer (relink) one canonical key for "what this signal is about", so
# co-origin duplicates collapse identically whether the key was stamped at
# produce time (the `link_evidence.origin` column) or derived on read.
_ORIGIN_EXT_RE = re.compile(r"\.[A-Za-z0-9]{1,8}$")   # one trailing file extension
_ORIGIN_STRIP_RE = re.compile(r"[-_\s./\\]+")          # separators that name-variants differ by


def normalize_origin(raw: str) -> str:
    """Lower-case, drop one trailing extension, strip separators, so that
    `world_graph.json`, `world-graph` and `World Graph` all collapse to
    `worldgraph`, and the folder token `L5GN_Armory_v4` / alias `l5gn armory v4`
    both collapse to `l5gnarmoryv4`."""
    if not raw:
        return ""
    s = raw.strip().lower()
    s = _ORIGIN_EXT_RE.sub("", s)
    s = _ORIGIN_STRIP_RE.sub("", s)
    return s


def origin_for(signal: str, detail: str) -> str:
    """Canonical co-origin key for one evidence row. name_alias details carry a
    `token@placement` shape (`world_graph@title`) -- the token before `@` is the
    origin. Every other signal's detail is already the file/token itself
    (filename_xref basename, path_mention source label)."""
    if not detail:
        return ""
    token = detail.split("@", 1)[0] if signal == "name_alias" else detail
    return normalize_origin(token)


def ensure_origin_column(conn) -> bool:
    """Idempotently add `link_evidence.origin` to an existing DB. A fresh build
    already has it (the producers' CREATE TABLE carries the column); this migrates
    a DB created before Task A. Returns True if the column is present afterwards,
    False if the table doesn't exist yet (nothing to migrate)."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(link_evidence)")}
    if not cols:
        return False
    if "origin" not in cols:
        conn.execute("ALTER TABLE link_evidence ADD COLUMN origin TEXT")
    return True


def iter_folder_backed_entries(registry: dict):
    """Yield every folder-backed registry entry: each project, then each of its
    repos, in that order.

    DECISIONS 0012 split a concept project's files across its repos -- a
    project like `crystal-spire` may carry no deposit of its own at all, while
    its repo `L5GN-Crystal-Spire` is the thing a deposit actually names. Before
    round 3's repo-tier fix, every producer that joins deposit facts against
    the registry did ``for entry in registry["projects"]`` and matched only the
    project's own `canonical_name` -- so a concept project whose files live in a
    differently-named repo got nothing, and neither did the repo, because the
    repo tier was never visited.

    One shared iteration order, used by build_inventory, build_activity,
    xref_filenames and extract_path_mentions, so "walk projects and repos"
    cannot drift into four subtly different shapes. A project entry with no
    `repos` key (the flat, pre-0012 shape some fixtures and a bare concept
    project still use) yields itself only -- backward compatible by
    construction, not by a special case.
    """
    for project in registry.get("projects", []):
        yield project
        for repo in project.get("repos") or []:
            yield repo


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
