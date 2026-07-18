"""viewer -- the Datasette read surface (DECISIONS 0007 stage 1).

The DB had never been queryable, so the INTENT §2 falsification test could not be
run at all. Datasette makes the corpus visible for the first time. It is a *read*
surface only: opened ``--immutable``, it is **structurally incapable of writing**,
which is what preserves the single-writer doctrine -- not a convention, a mode.

Datasette is an OPTIONAL extra (``pip install -e .[viewer]``); it never enters the
stdlib-only core or the default install. The stage skips cleanly and loudly when
it is absent. The write endpoint (0007 stage 2) is deliberately NOT built here.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from .backup import resolve_db_path  # shared, config-driven path resolution

__all__ = ["resolve_db_path", "datasette_available", "datasette_argv",
           "DEFAULT_PORT", "DEFAULT_HOST"]

DEFAULT_PORT = 8001
DEFAULT_HOST = "0.0.0.0"  # answer on both the 100.x tailnet and 192.168.x LAN (0007)


def datasette_available() -> bool:
    """True iff the optional ``datasette`` CLI is importable/on PATH."""
    return shutil.which("datasette") is not None


def datasette_argv(db_path: Path | str, host: str = DEFAULT_HOST,
                   port: int = DEFAULT_PORT) -> list[str]:
    """The read-only Datasette invocation.

    ``--immutable PATH`` opens the DB in a mode that cannot write it (the point:
    it *cannot* violate single-writer, per 0007). Binding ``0.0.0.0`` lets the
    headless knight answer on both its Tailscale ``100.x`` address (phone on
    cellular) and its ``192.168.x`` LAN address (the work rig, not on the tailnet).
    """
    return ["datasette", "serve", "--immutable", str(db_path),
            "-h", host, "-p", str(port)]
