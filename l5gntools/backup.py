"""backup -- off-box VACUUM INTO snapshots of the live vault.

The knight holds the only live vault; its one off-box copy had drifted since the
knight became primary (DECISIONS 0005/0006), so everything ingested since the
move had no off-box copy at all -- a live loss risk, not hardening. This is the
standing fix (ARCHITECTURE §7):

  * an **atomic, consistent** snapshot taken with SQLite's ``VACUUM INTO`` -- safe
    to run while the DB is live, unlike a raw file copy that can catch a
    half-written page,
  * retained **keep-last-N** so a bad snapshot never overwrites the only good one,
  * pushed **off the knight** over the existing transport to the configured
    ``backup_target`` (the L5GN-Castle ``Chronicler_Backup`` area), refreshing the
    stale copy.

A *writer* (it creates snapshot files and shells out to push), deliberately
outside the read-only scanner contract and never registered as a scanner. The
source DB is opened read-only (``mode=ro``) so this can never mutate the vault,
and every path is resolved from ``CHRONICLER_HOME`` / config, never hardcoded
(DECISIONS 0007 consequence a: hardcoding re-creates the fork-path problem).
"""
from __future__ import annotations

import os
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .deposit import default_transport

SNAPSHOT_PREFIX = "chronicler-"
DEFAULT_KEEP = 7


def resolve_db_path(machine: dict | None = None) -> Path:
    """The live vault path. Order: ``CHRONICLER_DB_PATH`` env, then this machine's
    ``vault``, then ``CHRONICLER_HOME/chronicler.db``. Never hardcoded."""
    if machine is None:
        machine = config.machine()
    env = os.environ.get("CHRONICLER_DB_PATH")
    if env:
        return Path(env)
    if machine.get("vault"):
        return Path(machine["vault"])
    home = os.environ.get("CHRONICLER_HOME") or machine.get("chronicler_home")
    if home:
        return Path(home) / "chronicler.db"
    raise FileNotFoundError(
        "cannot resolve the vault DB path -- set CHRONICLER_DB_PATH, or 'vault' / "
        "'chronicler_home' for this machine in config/local.json.")


def resolve_backup_dir(machine: dict | None = None) -> Path:
    """Local staging dir for snapshots, under ``CHRONICLER_HOME`` (never in the
    repo). Falls back to a ``backups/`` sibling of the DB if HOME is unset."""
    if machine is None:
        machine = config.machine()
    home = os.environ.get("CHRONICLER_HOME") or machine.get("chronicler_home")
    if home:
        return Path(home) / "backups"
    return resolve_db_path(machine).parent / "backups"


def snapshot_name(now: datetime | None = None) -> str:
    """Dated, lexically-sortable filename: ``chronicler-YYYYMMDDTHHMMSSZ.db``."""
    now = now or datetime.now(timezone.utc)
    return f"{SNAPSHOT_PREFIX}{now.strftime('%Y%m%dT%H%M%SZ')}.db"


def _unique_dest(backup_dir: Path, name: str) -> Path:
    """VACUUM INTO refuses an existing target; disambiguate a same-second name."""
    dest = backup_dir / name
    if not dest.exists():
        return dest
    stem = name[:-3]  # strip ".db"
    i = 1
    while (backup_dir / f"{stem}-{i}.db").exists():
        i += 1
    return backup_dir / f"{stem}-{i}.db"


def vacuum_into(src_db: Path, dest: Path) -> Path:
    """Atomic consistent snapshot of ``src_db`` into ``dest`` via ``VACUUM INTO``.

    Opens the source ``mode=ro`` so the vault is never mutated. ``VACUUM INTO``
    takes only a read lock on the source, so this is safe while the single writer
    is live. Raises loudly (never silent-fails) if the source is missing or the
    target already exists.
    """
    src_db = Path(src_db)
    dest = Path(dest)
    if not src_db.exists():
        raise FileNotFoundError(f"vault DB not found: {src_db}")
    if dest.exists():
        raise FileExistsError(f"snapshot target already exists: {dest}")
    uri = f"file:{src_db.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        conn.execute("VACUUM INTO ?", (str(dest),))
    finally:
        conn.close()
    return dest


def list_snapshots(backup_dir: Path) -> list[Path]:
    backup_dir = Path(backup_dir)
    if not backup_dir.exists():
        return []
    return sorted(backup_dir.glob(f"{SNAPSHOT_PREFIX}*.db"))


def prune_snapshots(backup_dir: Path, keep: int = DEFAULT_KEEP) -> list[Path]:
    """Keep the newest ``keep`` snapshots; delete and return the rest. Dated names
    sort chronologically, so a lexical sort is a time order. ``keep`` is floored at
    1 so this never deletes the only generation."""
    keep = max(1, keep)
    snaps = list_snapshots(backup_dir)
    doomed = snaps[:-keep] if len(snaps) > keep else []
    for p in doomed:
        p.unlink()
    return doomed


def push_command(local: Path, target: str, transport: str = "rsync") -> list[str]:
    """Command to copy one snapshot file off-box. ``target`` may be an ssh alias
    (e.g. ``l5gn-castle:vault/Chronicler_Backup``) resolved via ``~/.ssh/config``."""
    t = target.rstrip("/")
    if transport == "scp":
        return ["scp", str(local), t + "/"]
    return ["rsync", "-az", str(local), t + "/"]


def make_backup(keep: int = DEFAULT_KEEP, push: bool = True,
                machine: dict | None = None, now: datetime | None = None) -> dict:
    """Take one snapshot, prune to keep-last-N, and (default) push it off-box.

    Snapshot failure raises (fatal). Push failure is captured in
    ``result['push_error']`` and reported loudly by the caller, but does not lose
    the local snapshot -- an off-box hiccup must not cost the local copy.
    """
    if machine is None:
        machine = config.machine()
    src = resolve_db_path(machine)
    backup_dir = resolve_backup_dir(machine)
    backup_dir.mkdir(parents=True, exist_ok=True)

    dest = _unique_dest(backup_dir, snapshot_name(now))
    vacuum_into(src, dest)
    pruned = prune_snapshots(backup_dir, keep)

    target = machine.get("backup_target")
    transport = machine.get("backup_transport") or default_transport()
    result = {
        "db": str(src),
        "snapshot": str(dest),
        "kept": [p.name for p in list_snapshots(backup_dir)],
        "pruned": [p.name for p in pruned],
        "backup_target": target,
        "transport": transport,
        "push_command": None,
        "pushed": False,
        "push_error": None,
    }
    if target:
        cmd = push_command(dest, target, transport)
        result["push_command"] = " ".join(cmd)
        if push:
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                result["pushed"] = proc.returncode == 0
                if proc.returncode != 0:
                    result["push_error"] = (proc.stderr.strip()[-500:]
                                            or f"exit {proc.returncode}")
            except (OSError, subprocess.SubprocessError) as exc:
                result["push_error"] = str(exc)
    return result
