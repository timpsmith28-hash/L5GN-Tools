"""Per-machine configuration for a single toolkit repo synced across the mesh.

One committed ``config/machines.json`` (keyed by ``socket.gethostname()``) lets
the same repo behave correctly on every machine: gaming rig, work laptop, and the
headless knight each read only their own section. A gitignored
``config/local.json`` overlays machine-specific paths/secrets that must not sync
to GitHub.

Precedence (lowest -> highest):
    machines.json["default"]  <  machines.json[host]
    <  local.json["default"]  <  local.json[host]

This module imports stdlib only and does NOT import :mod:`l5gntools.common`,
so ``common`` can depend on it without an import cycle.
"""
from __future__ import annotations

import json
import socket
from pathlib import Path

# config.py lives at L5GN-Tools/l5gntools/config.py
_PKG_DIR: Path = Path(__file__).resolve().parent
TOOLKIT_ROOT: Path = _PKG_DIR.parent
CONFIG_DIR: Path = TOOLKIT_ROOT / "config"
_MACHINES: Path = CONFIG_DIR / "machines.json"
_LOCAL: Path = CONFIG_DIR / "local.json"
_AUTHORS: Path = CONFIG_DIR / "authors.json"


def _load(path: Path) -> dict:
    """Read a JSON object file; return {} on missing/empty/malformed (never raise)."""
    if path.exists() and path.stat().st_size > 0:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (ValueError, OSError):
            return {}
    return {}


def hostname() -> str:
    return socket.gethostname()


def machine(host: str | None = None) -> dict:
    """Resolved config for ``host`` (defaults to this machine).

    Falls back to the ``default`` entry when the host is not listed, so an
    un-configured machine still gets a sane, non-crashing config.
    """
    host = host or hostname()
    machines = _load(_MACHINES)
    local = _load(_LOCAL)

    entry: dict = {}
    entry.update(machines.get("default", {}))
    entry.update(machines.get(host, {}))
    entry.update(local.get("default", {}))
    entry.update(local.get(host, {}))

    entry["_hostname"] = host
    entry["_matched"] = host in machines or host in local
    return entry


def author_aliases() -> dict:
    """Map of ``alias_name_lowercased -> canonical_name`` for folding git author
    identities. Built from ``config/authors.json`` (canonical -> [aliases]); the
    canonical also maps to itself. Empty dict when the file is absent."""
    data = _load(_AUTHORS)
    out: dict = {}
    for canonical, aliases in data.items():
        if str(canonical).startswith("_"):
            continue
        out.setdefault(str(canonical).lower(), canonical)
        if isinstance(aliases, list):
            for alias in aliases:
                out[str(alias).lower()] = canonical
    return out


def estate_roots(host: str | None = None) -> list[Path] | None:
    """Configured estate roots for ``host`` as ``Path``s, or ``None`` when none
    are declared -- ``None`` signals callers to use legacy sibling discovery."""
    roots = machine(host).get("roots")
    if not roots:
        return None
    return [Path(r) for r in roots]
