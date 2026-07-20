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


def _root_entries(host: str | None = None) -> list[dict]:
    """Normalise the ``roots`` config into ``[{"path": Path, "scope": str|None}]``.

    Two accepted shapes, so old config keeps working:

        "roots": ["D:/Work/Github/MCF"]                       # bare, scope unknown
        "roots": [{"path": "D:/Work/Github/MCF", "scope": "mcf"}]

    The tagged shape is the **config-tag resolution** for scope (DECISIONS 0012 /
    round-3 Task C.3): a project's ``scope`` is whichever configured root it was
    scanned under on its producer, declared in that producer's config -- *not*
    inferred from folder nesting. That matters because the layout differs per
    machine: the knight has an ``L5GN`` folder, the gaming rig is flat with no
    ``MCF`` at all, and the work rig has both. Deriving scope from nesting would
    demand a folder reorg on the gaming rig to satisfy a naming convention;
    tagging the root in config gets the same answer with no files moved.
    """
    roots = machine(host).get("roots")
    if not roots:
        return []
    out: list[dict] = []
    for r in roots:
        if isinstance(r, dict):
            path = r.get("path")
            if not path:
                continue
            out.append({"path": Path(path), "scope": r.get("scope")})
        else:
            out.append({"path": Path(r), "scope": None})
    return out


def estate_roots(host: str | None = None) -> list[Path] | None:
    """Configured estate roots for ``host`` as ``Path``s, or ``None`` when none
    are declared -- ``None`` signals callers to use legacy sibling discovery."""
    entries = _root_entries(host)
    if not entries:
        return None
    return [e["path"] for e in entries]


def estate_roots_tagged(host: str | None = None) -> list[dict]:
    """Configured roots with their scope tags: ``[{"path": Path, "scope": str}]``.

    Empty list when none are declared. Callers that need the scope of a project
    use :func:`scope_for_path` rather than reading this directly.
    """
    return _root_entries(host)


def scope_for_path(path, host: str | None = None) -> str | None:
    """The configured scope tag of the root ``path`` sits under, else ``None``.

    Longest-match wins, so a nested tagged root (``.../Github/MCF`` inside a
    tagged ``.../Github``) takes precedence over its parent. ``None`` means the
    producer has not tagged that root yet -- reported honestly rather than
    guessed at, because a wrong scope silently mis-files a project.
    """
    try:
        target = Path(path).resolve()
    except (OSError, ValueError):
        return None
    best: tuple[int, str | None] = (-1, None)
    for entry in _root_entries(host):
        if not entry.get("scope"):
            continue
        try:
            root = entry["path"].resolve()
        except (OSError, ValueError):
            continue
        try:
            target.relative_to(root)
        except ValueError:
            continue
        depth = len(root.parts)
        if depth > best[0]:
            best = (depth, entry["scope"])
    return best[1]
