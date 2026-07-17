"""
S4 step 1 (shared with S2) - per-project file inventory.

Adds a `file_inventory` block to each folder-backed registry entry:

    "file_inventory": {
      "built_at":   "2026-07-16T...Z",
      "source_commit":    "abc1234",   # git projects: HEAD short SHA
      "source_signature": "md5...",    # non-git: mtime/size signature
      "file_count": 1234,
      "paths": ["core/event_bus.py", "README.md", ...]   # repo-relative, /-sep
    }

Basenames are the last segment of each relative path, so "basenames + relative
paths" (spec S4.1) are both available from `paths`.

ONE harvest pass, reused by S2 (vocabulary) and S4 (filename xref) so the
`git ls-files` walk is never run twice. `harvest_project()` is the importable
entry point for S2.

Skip-if-unchanged: a project whose git HEAD (or non-git signature) matches the
stored value is left untouched, mirroring the change-detection the nightly
Intent task already does via state.json.

Standing rules honoured: UTF-8, UTC ISO-8601, whole-file atomic write, loud
failure, no half-updates.

Usage:
    python3 pipeline/build_inventory.py            # refresh changed projects
    python3 pipeline/build_inventory.py --force    # rebuild all inventories
    python3 pipeline/build_inventory.py --dry-run  # report, write nothing
"""
import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from db import CHRONICLER_ROOT

GITHUB_ROOT_FS = CHRONICLER_ROOT.parent.parent
REGISTRY_PATH = GITHUB_ROOT_FS / "L5GN" / ".intel_sync" / "project_registry.json"
SCOPE_TO_ROOT = {"l5gn": "L5GN", "mcf": "MCF"}

# Directory names never descended into (editor/build/vendor noise, not project
# content). Applies to both git and non-git harvests.
NOISE_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules",
              ".obsidian", ".idea", ".pytest_cache", ".mypy_cache", "dist",
              "build", ".ipynb_checkpoints"}

NONGIT_MAX_DEPTH = 3   # spec S2.1: non-git recursive listing capped at depth 3
PRODUCER_VERSION = "build_inventory/1.0"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json_atomic(path: Path, obj) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def _rel(fs_root: Path, p: str) -> str:
    return os.path.relpath(p, str(fs_root)).replace(os.sep, "/")


def _noise(rel_path: str) -> bool:
    return any(seg in NOISE_DIRS for seg in rel_path.split("/"))


def git_head(fs_path: Path):
    try:
        o = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                           cwd=str(fs_path), capture_output=True, text=True, timeout=30)
        if o.returncode == 0 and o.stdout.strip():
            return o.stdout.strip()
    except Exception:
        pass
    return None


def git_paths(fs_path: Path):
    o = subprocess.run(["git", "ls-files"], cwd=str(fs_path),
                       capture_output=True, text=True, timeout=60)
    if o.returncode != 0:
        raise SystemExit(f"[build_inventory] git ls-files failed in {fs_path}: {o.stderr.strip()}")
    return [p for p in o.stdout.splitlines() if p and not _noise(p)]


def walk_paths(fs_path: Path, max_depth: int):
    """Depth-capped recursive listing for non-git projects."""
    paths = []
    root_depth = str(fs_path).rstrip(os.sep).count(os.sep)
    for root, dirs, files in os.walk(fs_path):
        dirs[:] = [d for d in dirs if d not in NOISE_DIRS]
        depth = root.rstrip(os.sep).count(os.sep) - root_depth
        if depth >= max_depth:
            dirs[:] = []  # stop descending past the cap
        for fn in files:
            rel = _rel(fs_path, os.path.join(root, fn))
            if not _noise(rel):
                paths.append(rel)
    return sorted(paths)


def nongit_signature(fs_path: Path, paths) -> str:
    """md5 over sorted 'relpath|size|mtime' lines (same shape state.json uses)."""
    lines = []
    for rel in paths:
        full = fs_path / rel
        try:
            st = full.stat()
            lines.append(f"{rel}|{st.st_size}|{int(st.st_mtime)}")
        except OSError:
            continue
    return hashlib.md5("\n".join(sorted(lines)).encode("utf-8")).hexdigest()


def harvest_project(fs_path: Path, is_git: bool) -> dict:
    """Importable single-project harvest (reused by S2). Returns a
    file_inventory dict. Does NOT do skip-if-unchanged — caller decides."""
    if is_git:
        paths = sorted(git_paths(fs_path))
        return {
            "built_at": utc_now(),
            "source_commit": git_head(fs_path),
            "source_signature": None,
            "file_count": len(paths),
            "paths": paths,
        }
    paths = walk_paths(fs_path, NONGIT_MAX_DEPTH)
    return {
        "built_at": utc_now(),
        "source_commit": None,
        "source_signature": nongit_signature(fs_path, paths),
        "file_count": len(paths),
        "paths": paths,
    }


def current_signature(fs_path: Path, is_git: bool):
    """Cheap signature for skip-if-unchanged (no full path list)."""
    if is_git:
        return ("git", git_head(fs_path))
    paths = walk_paths(fs_path, NONGIT_MAX_DEPTH)
    return ("sig", nongit_signature(fs_path, paths))


def unchanged(entry: dict, sig) -> bool:
    inv = entry.get("file_inventory")
    if not inv:
        return False
    kind, val = sig
    if val is None:
        return False
    if kind == "git":
        return inv.get("source_commit") == val
    return inv.get("source_signature") == val


def resolve_fs(entry: dict) -> Path:
    root = SCOPE_TO_ROOT.get(entry["scope"])
    if root is None:
        raise SystemExit(f"[build_inventory] unknown scope {entry['scope']} "
                         f"on {entry['canonical_name']}")
    return GITHUB_ROOT_FS / root / entry["canonical_name"]


def run(force: bool, dry_run: bool):
    if not REGISTRY_PATH.is_file():
        raise SystemExit(f"[build_inventory] registry missing: {REGISTRY_PATH} "
                         "(run build_registry.py first)")
    registry = read_json(REGISTRY_PATH)

    built, skipped, missing = [], [], []
    for entry in registry["projects"]:
        if entry.get("_orphaned"):
            missing.append(entry["canonical_name"])
            continue
        fs_path = resolve_fs(entry)
        if not fs_path.is_dir():
            missing.append(entry["canonical_name"])
            continue
        is_git = entry["vcs"] == "git"
        sig = current_signature(fs_path, is_git)
        if not force and unchanged(entry, sig):
            skipped.append(entry["canonical_name"])
            continue
        inv = harvest_project(fs_path, is_git)
        if not dry_run:
            entry["file_inventory"] = inv
            entry["registry_updated"] = utc_now()
        built.append((entry["canonical_name"], inv["file_count"]))

    if not dry_run:
        registry["generated_at"] = utc_now()
        write_json_atomic(REGISTRY_PATH, registry)

    print("=" * 60)
    print("build_inventory" + (" (dry-run)" if dry_run else ""))
    print("=" * 60)
    for name, n in built:
        print(f"  built   {name:28} {n:5} files")
    for name in skipped:
        print(f"  skip    {name:28} (unchanged)")
    for name in missing:
        print(f"  MISSING {name:28} (no folder / orphaned)")
    print("-" * 60)
    print(f"{len(built)} built, {len(skipped)} unchanged, {len(missing)} missing.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Harvest per-project file inventories (S4.1).")
    ap.add_argument("--force", action="store_true", help="Rebuild all, ignore skip-if-unchanged.")
    ap.add_argument("--dry-run", action="store_true", help="Report only, write nothing.")
    args = ap.parse_args()
    run(args.force, args.dry_run)
