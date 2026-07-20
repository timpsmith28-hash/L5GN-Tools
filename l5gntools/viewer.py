"""viewer -- the Datasette read surface (DECISIONS 0007 stage 1).

The DB had never been queryable, so the INTENT §2 falsification test could not be
run at all. Datasette makes the corpus visible for the first time. It is a *read*
surface only: opened ``--immutable``, it is **structurally incapable of writing**,
which is what preserves the single-writer doctrine -- not a convention, a mode.

Datasette is an OPTIONAL extra (``pip install -e .[viewer]``); it never enters the
stdlib-only core or the default install. The stage skips cleanly and loudly when
it is absent. The write endpoint (0007 stage 2) is deliberately NOT built here.

**It serves a snapshot, never the live vault (DECISIONS 0013).** ``--immutable`` is
a *promise to SQLite that the file will not change*; it lets Datasette skip locking
and cache the page map. Pointed at the live DB while the pipeline or the review
endpoint writes, that promise is broken and Datasette serves from a stale page map
-- which surfaces as a false ``database disk image is malformed`` on a perfectly
sound database (the live incident that produced 0013). Pointed at a fresh
``VACUUM INTO`` snapshot, the promise is honestly true: the file genuinely cannot
change under it, and a reader against a copy cannot collide with the writer at all.

The trade is staleness, and the honest answer is to say so out loud rather than
hide it -- ``serve`` prints the snapshot time and the UI carries it in the banner,
so a ruling made in the review endpoint after the snapshot reads as "re-launch to
refresh", never as a lost ruling.
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from . import backup
from .backup import resolve_db_path  # shared, config-driven path resolution

__all__ = ["resolve_db_path", "datasette_available", "datasette_argv",
           "resolve_snapshot_dir", "make_serve_snapshot", "write_metadata",
           "staleness_note", "SNAPSHOT_DIRNAME", "SNAPSHOT_FILENAME",
           "DEFAULT_PORT", "DEFAULT_HOST"]

DEFAULT_PORT = 8001
DEFAULT_HOST = "0.0.0.0"  # answer on both the 100.x tailnet and 192.168.x LAN (0007)

# Read-only-consumer scratch, overwritten every launch. Deliberately NOT the
# backup directory: these are disposable serving copies and must never enter the
# keep-last-N rotation, where they would age out a real off-box generation.
SNAPSHOT_DIRNAME = "serve-snapshot"
SNAPSHOT_FILENAME = "chronicler-serve.db"
METADATA_FILENAME = "serve-metadata.json"


def datasette_available() -> bool:
    """True iff the optional ``datasette`` CLI is importable/on PATH."""
    return shutil.which("datasette") is not None


def datasette_argv(db_path: Path | str, host: str = DEFAULT_HOST,
                   port: int = DEFAULT_PORT,
                   metadata: Path | str | None = None) -> list[str]:
    """The read-only Datasette invocation.

    ``--immutable PATH`` opens the DB in a mode that cannot write it (the point:
    it *cannot* violate single-writer, per 0007). Binding ``0.0.0.0`` lets the
    headless knight answer on both its Tailscale ``100.x`` address (phone on
    cellular) and its ``192.168.x`` LAN address (the work rig, not on the tailnet).

    ``db_path`` is expected to be a **snapshot**, not the live vault (0013) -- the
    caller (`run.py serve`) takes it. ``metadata`` points at the generated
    metadata file carrying the staleness banner.
    """
    argv = ["datasette", "serve", "--immutable", str(db_path),
            "-h", host, "-p", str(port)]
    if metadata is not None:
        argv += ["--metadata", str(metadata)]
    return argv


# ---------------------------------------------------------------------------
# Snapshot (DECISIONS 0013) -- serve reads a frozen copy, never the live vault
# ---------------------------------------------------------------------------
def resolve_snapshot_dir(machine: dict | None = None) -> Path:
    """Transient location for the serving copy.

    A ``serve-snapshot/`` sibling of the real backup directory: same
    ``CHRONICLER_HOME``-derived, config-driven resolution (never hardcoded), but a
    separate folder so ``backup``'s keep-last-N rotation never sees these files.
    """
    return backup.resolve_backup_dir(machine).parent / SNAPSHOT_DIRNAME


def _clear_snapshot(dest: Path) -> None:
    """Remove a previous serving copy and its WAL sidecars.

    ``VACUUM INTO`` refuses an existing target, so the overwrite has to be an
    explicit unlink. The ``-wal``/``-shm`` sidecars go too: leaving a stale sidecar
    beside a fresh snapshot is precisely the kind of mismatched-page-map state
    0013 was about.
    """
    for p in (dest, Path(str(dest) + "-wal"), Path(str(dest) + "-shm")):
        if p.exists():
            p.unlink()


def make_serve_snapshot(machine: dict | None = None,
                        now: datetime | None = None) -> dict:
    """Take a fresh ``VACUUM INTO`` snapshot of the live vault for serving.

    Reuses ``backup.vacuum_into`` rather than duplicating the snapshot logic --
    one implementation of "consistent copy of the vault", used by both the off-box
    backup and the read surface. The target is overwritten every launch, so the
    serving copy is always this launch's view and never accumulates.

    Returns the snapshot path, the source, and the snapshot time (the staleness
    the caller must surface).
    """
    src = resolve_db_path(machine)
    if not Path(src).exists():
        raise FileNotFoundError(f"vault DB not found: {src}")
    snap_dir = resolve_snapshot_dir(machine)
    snap_dir.mkdir(parents=True, exist_ok=True)
    dest = snap_dir / SNAPSHOT_FILENAME
    _clear_snapshot(dest)
    backup.vacuum_into(Path(src), dest)
    taken = now or datetime.now(timezone.utc)
    return {"db": str(src), "snapshot": str(dest), "dir": str(snap_dir),
            "taken_at": taken.strftime("%Y-%m-%dT%H:%M:%SZ")}


def staleness_note(taken_at: str) -> str:
    """The one-line honesty note 0013 asks for, used by both the console line and
    the UI banner so the two can never drift apart."""
    return (f"showing vault as of {taken_at} (snapshot) -- re-launch `run.py serve` "
            "to refresh. A ruling made in `run.py review` after that time is saved "
            "in the live vault but not yet in this copy.")


def write_metadata(snapshot_dir: Path | str, taken_at: str) -> Path:
    """Write the Datasette metadata file carrying the staleness banner.

    Datasette renders ``description_html`` on the index page, so the note is
    visible in the UI itself and not only in the launching terminal -- which
    matters because the usual reader is a phone on the tailnet, nowhere near the
    console output.
    """
    snapshot_dir = Path(snapshot_dir)
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    note = staleness_note(taken_at)
    meta = {
        "title": "Chronicler vault (snapshot)",
        "description_html": (
            f"<strong>Snapshot, not live.</strong> {note}"),
    }
    path = snapshot_dir / METADATA_FILENAME
    path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return path
