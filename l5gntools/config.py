"""Per-machine configuration for a single toolkit repo synced across the mesh.

One committed ``config/machines.json`` (keyed by ``socket.gethostname()``) lets
the same repo behave correctly on every machine: gaming rig, work laptop, and the
headless knight each read only their own section. A gitignored
``config/local.json`` overlays machine-specific paths/secrets that must not sync
to GitHub.

Precedence (lowest -> highest):
    machines.json["default"]  <  machines.json[host]
    <  local.json["default"]  <  local.json[host]

``default`` is a **base layer under a matched host, never a fallback for an
unmatched one**. A host listed in neither file raises
:class:`UnknownHostError` -- see :func:`machine` for why that is loud.

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


class UnknownHostError(RuntimeError):
    """This machine is listed in neither ``machines.json`` nor ``local.json``.

    Raised rather than fallen back from. A ``default`` entry with no ``roots``
    resolves to a machine that owns nothing, and every scanner downstream then
    reports a confident, complete-looking picture of an empty estate -- the
    failure INTENT §5 refuses everywhere else. The case that forced this was a
    sandbox run: the sandbox's hostname matched nothing, `default` answered,
    and the run produced a snapshot of nothing with no indication that it had.

    The message names the hosts that *are* configured, so the fix (add a
    section, or run somewhere real) is legible from the failure alone.
    """


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


def configured_hosts() -> list[str]:
    """Every host key declared across both files, sorted. Keys beginning ``_``
    are comments and ``default`` is a base layer, so neither is a host."""
    names: set[str] = set()
    for data in (_load(_MACHINES), _load(_LOCAL)):
        names.update(k for k in data
                     if not str(k).startswith("_") and k != "default")
    return sorted(names)


def machine(host: str | None = None) -> dict:
    """Resolved config for ``host`` (defaults to this machine).

    **Raises** :class:`UnknownHostError` when ``host`` appears in neither
    ``machines.json`` nor ``local.json``. It does *not* fall back to
    ``default``: an unmatched host resolving to a rootless entry is how a run
    somewhere it was never meant to run -- a sandbox, a fresh box, a renamed
    machine -- produces a confident snapshot of nothing. ``default`` still
    layers underneath a host that *is* matched, which is the job it was added
    for.
    """
    host = host or hostname()
    machines = _load(_MACHINES)
    local = _load(_LOCAL)

    if host not in machines and host not in local:
        known = configured_hosts()
        raise UnknownHostError(
            f"host {host!r} is declared in neither config/machines.json nor "
            f"config/local.json, so this machine has no estate, no roots and "
            f"no role. Configured hosts: "
            f"{', '.join(known) if known else '(none)'}. Add a section keyed "
            f"on this hostname, or run this on a machine that has one -- the "
            f"'default' entry is a base layer under a matched host, not a "
            f"stand-in for a missing one.")

    entry: dict = {}
    entry.update(machines.get("default", {}))
    entry.update(machines.get(host, {}))
    entry.update(local.get("default", {}))
    entry.update(local.get(host, {}))

    entry["_hostname"] = host
    # Retained for vendored consumers that read it; now always True, because
    # the unmatched case raises above rather than returning. A field with one
    # possible value is the thing 0048 clause 4 warns trains the eye past it --
    # it is kept only so a consumer pinned to an older toolkit does not
    # KeyError, and should go the next time this module's shape is reviewed.
    entry["_matched"] = True
    return entry


def mesh_enabled(host: str | None = None) -> bool:
    """True iff this machine has opted into mesh mode.

    The cross-machine mesh (deposit / consume / intake's drop zone / deploy/)
    stood down as the default shape in COWORK_BRIEF_unified_app.md Task 6 --
    see DECISIONS 0036 and ARCHITECTURE §2. The code is not deleted; a machine
    that still wants the two-role split opts back in with a ``"mesh": true``
    entry in ``config/machines.json`` or ``config/local.json`` (same
    precedence as every other machine setting -- see :func:`machine`)."""
    return bool(machine(host).get("mesh"))


def _authored_paths(entry: dict) -> list[str]:
    """The ``authors`` list of a resolved machine entry, as posix strings."""
    declared = entry.get("authors")
    if not isinstance(declared, list):
        return []
    return [str(p).replace("\\", "/").strip("/") for p in declared if p]


def authored_artefacts(host: str | None = None) -> list[str]:
    """Repo-relative artefact paths ``host`` declares itself the author of.

    ``authors`` is a per-host, **per-artefact** declaration, not a role.
    Authorship could not be carried by ``role`` because the estate has two
    hosts that are both ``producer`` -- the gaming rig authors the
    conversation map and the work laptop consumes a hand-copied version of
    it, and no value of one shared field distinguishes those without saying
    which artefact is meant.
    """
    return _authored_paths(machine(host))


def authors_artefact(rel_path, host: str | None = None) -> bool:
    """True iff ``host`` declares itself the author of ``rel_path`` (a
    repo-relative path). Compared as posix strings after stripping separators,
    so a caller may pass either a ``Path`` or a string in either slash style.
    """
    wanted = str(rel_path).replace("\\", "/").strip("/")
    return wanted in authored_artefacts(host)


def authoring_hosts(rel_path) -> list[str]:
    """Every configured host that declares itself an author of ``rel_path``.

    Used to make a refusal informative -- "not authored here" is only half a
    message; the other half is where it *is* authored. Empty means no host
    declares it at all, which is a config gap and is reported as one rather
    than read as permission.
    """
    wanted = str(rel_path).replace("\\", "/").strip("/")
    out: list[str] = []
    for host in configured_hosts():
        try:
            if wanted in _authored_paths(machine(host)):
                out.append(host)
        except UnknownHostError:      # pragma: no cover -- host came from the files
            continue
    return out


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
    """Normalise the ``roots`` config into
    ``[{"path": Path, "scope": str|None, "is_project": bool}]``.

    Three accepted shapes, so old config keeps working:

        "roots": ["D:/Work/Github/MCF"]                       # bare, scope unknown
        "roots": [{"path": "D:/Work/Github/MCF", "scope": "mcf"}]
        "roots": [{"path": ".../L5GN-Tools", "scope": "l5gn", "is_project": true}]

    ``is_project`` says *this path is itself a project*, not a container whose
    children are projects. Without it a project that does not live under a
    container root is unscannable by config alone: naming its parent drags in
    every unrelated sibling, and naming the project drags in its own
    subdirectories as if each were a project. It is also the only way the
    toolkit's own repo can be scanned -- :func:`common.discover_projects` skips
    ``TOOLKIT_ROOT`` when walking a container, and an ``is_project`` entry is an
    explicit declaration rather than something stumbled into by a broad root.

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
            out.append({"path": Path(path), "scope": r.get("scope"),
                        "is_project": bool(r.get("is_project"))})
        else:
            out.append({"path": Path(r), "scope": None, "is_project": False})
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
