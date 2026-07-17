"""Shared, read-only helpers for every L5GN tool.

Design rules enforced by the auditors:
* Tools NEVER write into a scanned target. The only writer lives here
  (:func:`write_json`) and only ever writes under ``DATA_DIR``.
* Tools use stdlib only, so they run against any sibling regardless of that
  project's virtual-env.
"""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# --- Anchors -----------------------------------------------------------------
# common.py lives at  L5GN-Tools/l5gntools/common.py
TOOLKIT_ROOT: Path = Path(__file__).resolve().parent.parent          # L5GN-Tools
ESTATE_ROOT: Path = TOOLKIT_ROOT.parent                              # GitHub/
DATA_DIR: Path = TOOLKIT_ROOT / "data"

# Directories that are never project code and are skipped on every walk.
IGNORE_DIRS: frozenset[str] = frozenset({
    ".git", "__pycache__", "node_modules", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", "dist", "build", ".idea", ".vscode", ".eggs", ".tox",
    "site-packages",
})

# Folders that are third-party clones rather than L5GN projects. Still scannable
# on request, but excluded from default estate sweeps.
THIRD_PARTY: frozenset[str] = frozenset({"all-MiniLM-L6-v2", "godot-demo-projects"})


def is_ignored_dir(name: str) -> bool:
    """True for directory names that are never project code and are pruned on
    every walk: exact ignores, any venv variant (.venv, .venv_inference, venv3),
    and bundled model-weight folders."""
    return (name in IGNORE_DIRS
            or name.startswith((".venv", "venv"))
            or name == "models")


# --- Project discovery -------------------------------------------------------
def _projects_under(root: Path, include_third_party: bool) -> list[Path]:
    """Direct child project folders of ``root`` (read-only listing)."""
    out: list[Path] = []
    if not root.exists():
        return out
    for child in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if not child.is_dir():
            continue
        if child.resolve() == TOOLKIT_ROOT.resolve():
            continue
        if child.name.startswith("."):
            continue
        if not include_third_party and child.name in THIRD_PARTY:
            continue
        out.append(child)
    return out


def discover_projects(include_third_party: bool = False) -> list[Path]:
    """Project folders to scan.

    When this machine declares ``roots`` in ``config/machines.json``, the
    projects are the child folders of every configured estate root. Otherwise
    fall back to the legacy behaviour: sibling folders of the toolkit itself.
    """
    from . import config  # local import keeps common <- config one-directional

    roots = config.estate_roots()
    if roots:
        out: list[Path] = []
        seen: set[Path] = set()
        for root in roots:
            for p in _projects_under(root, include_third_party):
                rp = p.resolve()
                if rp not in seen:
                    seen.add(rp)
                    out.append(p)
        return sorted(out, key=lambda p: p.name.lower())
    return _projects_under(ESTATE_ROOT, include_third_party)


def resolve_targets(target: str | None, do_all: bool,
                    include_third_party: bool = False) -> list[Path]:
    """Turn CLI flags into a concrete list of target folders."""
    if target:
        p = Path(target)
        if p.is_absolute():
            return [p.resolve()]
        from . import config
        # A bare name is resolved against configured roots first, then the
        # legacy sibling location, then the current working directory.
        for root in (config.estate_roots() or []):
            cand = root / target
            if cand.exists():
                return [cand.resolve()]
        sibling = ESTATE_ROOT / target
        p = sibling if sibling.exists() else Path.cwd() / target
        return [p.resolve()]
    return discover_projects(include_third_party=include_third_party)


# --- Filesystem walking (read-only) -----------------------------------------
def iter_files(target: Path, suffixes: tuple[str, ...] | None = None):
    """Yield files under ``target`` skipping ignored dirs. Read-only.

    Uses os.walk with in-place dir pruning so we never descend into vendored
    trees (site-packages, venv, models) -- essential for speed on repos that
    bundle their dependencies.
    """
    for dirpath, dirnames, filenames in os.walk(target):
        dirnames[:] = [d for d in dirnames if not is_ignored_dir(d)]
        for fn in filenames:
            if suffixes and os.path.splitext(fn)[1].lower() not in suffixes:
                continue
            yield Path(dirpath) / fn


def is_vendored(path: Path) -> bool:
    """True for files that belong to a bundled dependency or model, not code."""
    return any(is_ignored_dir(part) for part in path.parts)


def rel(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


# --- Git (subprocess; never imports a project) ------------------------------
def is_git_repo(path: Path) -> bool:
    return (path / ".git").exists()


def run_git(path: Path, *args: str) -> str:
    """Run ``git -C path <args>`` and return stripped stdout ('' on failure)."""
    try:
        res = subprocess.run(
            ["git", "-C", str(path), *args],
            capture_output=True, text=True, timeout=60,
        )
        return res.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return ""


def toolkit_git_info() -> dict:
    """The toolkit's own git state, so a report reveals which build produced it
    (cross-machine version parity). ``commit`` is None if git is unavailable."""
    commit = run_git(TOOLKIT_ROOT, "rev-parse", "--short", "HEAD")
    dirty = bool(run_git(TOOLKIT_ROOT, "status", "--porcelain"))
    return {"commit": commit or None, "dirty": dirty}


# --- Output (the ONLY writer -- always under DATA_DIR) -----------------------
def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def write_json(relative_name: str, payload: object) -> Path:
    """Serialise ``payload`` to ``DATA_DIR/relative_name``. Refuses to escape."""
    dest = (DATA_DIR / relative_name).resolve()
    if DATA_DIR.resolve() not in dest.parents and dest != DATA_DIR.resolve():
        raise ValueError(f"refusing to write outside data dir: {dest}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return dest
