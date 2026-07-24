"""S4 step 1 (shared with S2) - per-project file inventory.

Adds a `file_inventory` block to each folder-backed registry entry:

    "file_inventory": {
      "built_at":   "2026-07-16T...Z",
      "source":     "deposit" | "local_disk",
      "source_commit":    "abc1234",   # git projects: HEAD short SHA
      "source_signature": "md5...",    # non-git: size/mtime signature
      "file_count": 1234,
      "paths": ["core/event_bus.py", "README.md", ...],  # repo-relative, /-sep
      "extra_basenames": ["late_file.py", ...],          # see "Truncation"
      "truncated": false
    }

Basenames are the last segment of each relative path, so "basenames + relative
paths" (spec S4.1) are both available from `paths`.

Where the facts come from
-------------------------
**The deposited estate, not a folder walk.** This module previously resolved
each project as ``GITHUB_ROOT_FS / <scope-root> / <canonical_name>`` -- a layout
that exists on no machine in the estate. Every project therefore resolved
missing, `file_inventory` was never populated on the knight, and S4 -- the
strongest automatic link signal in the system -- had nothing to join against
from the day it was written. That is the same folder-walk defect round 3 fixed
in `build_registry.py` and found blocking `build_activity.py`; this is the third
instance of the one bug.

The replacement is the file census carried inside each deposited
``estate.json``, which already reports exactly what `file_inventory` wants:
the working-set file list, the true file count, and git facts. Project
resolution reuses `build_registry`'s own deposit discovery
(`resolve_estates_dir` / `find_estate_snapshots` / `read_estate_snapshot`)
rather than introducing a second discovery path.

A **local-disk fallback** remains for a producer running against its own working
tree, matching the `LOCAL_ESTATE_JSON` pattern `build_registry` already uses.
On the knight, deposits win: the fallback only fires for a project no deposit
mentions.

Truncation
----------
The census caps its per-file list at ``file_cap`` (2000) and sets ``truncated``.
`L5GN-Castle` exceeds it. A truncated inventory would mean S4 silently could not
match the missing files, so the census now also carries
``basenames_beyond_cap``: the basenames -- and only the basenames -- of the
working-set files that did not fit. S4 matches on basename alone, so this closes
the blind spot for a few KB rather than raising the cap and inflating every
deposit with full path/size/mtime records nothing reads.

Those basenames land in `extra_basenames`. Consumers wanting the project's
complete basename set take the basenames of `paths` **union** `extra_basenames`;
`basename_set()` does this. `file_count` is always the true count, so
``file_count > len(paths)`` is the honest signal that `paths` is a subset.

Skip-if-unchanged: a project whose git HEAD (or non-git signature) matches the
stored value is left untouched, mirroring the change-detection the nightly
Intent task already does via state.json.

Standing rules honoured: UTF-8, UTC ISO-8601, whole-file atomic write, loud
failure, no half-updates.

Usage:
    python3 pipeline/build_inventory.py            # refresh changed projects
    python3 pipeline/build_inventory.py --force    # rebuild all inventories
    python3 pipeline/build_inventory.py --dry-run  # report, write nothing
    python3 pipeline/build_inventory.py --estates-dir /home/l5gn/vault/estates
"""
import argparse
import hashlib
import json
import os
import posixpath
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from db import CHRONICLER_ROOT

# Deposit discovery is build_registry's, reused rather than re-implemented: one
# estate-resolution path for the whole pipeline (round 3, Task C).
from build_registry import (
    REGISTRY_PATH,
    find_estate_snapshots,
    read_estate_snapshot,
    resolve_estates_dir,
)

GITHUB_ROOT_FS = CHRONICLER_ROOT.parent.parent

# Directory names never descended into (editor/build/vendor noise, not project
# content). Applies to the local-disk fallback only -- the census does its own,
# richer vendored/ignored classification before it ever reaches us.
NOISE_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules",
              ".obsidian", ".idea", ".pytest_cache", ".mypy_cache", "dist",
              "build", ".ipynb_checkpoints"}

NONGIT_MAX_DEPTH = 3   # spec S2.1: non-git recursive listing capped at depth 3
PRODUCER_VERSION = "build_inventory/2.0"


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


# --- the consumer-facing accessor ------------------------------------------
def basename_set(inv: dict) -> set:
    """The project's complete basename set, cap or no cap.

    S4 must use this rather than reading `paths` directly: on a truncated
    project `paths` is a deterministic prefix and the rest of the basenames are
    in `extra_basenames`. Reading `paths` alone silently loses them.
    """
    if not inv:
        return set()
    names = {posixpath.basename(p) for p in inv.get("paths") or []}
    names.update(inv.get("extra_basenames") or [])
    names.discard("")
    return names


# --- deposit-driven harvest (the primary path) -----------------------------
def census_signature(census: dict) -> str:
    """Deterministic signature over a deposited census, for the non-git
    skip-if-unchanged path.

    Mirrors the shape the local-disk signature uses ('relpath|size|mtime'), so
    the two paths produce comparable -- though deliberately not identical --
    values. Includes the true file_count so that a change beyond the cap still
    moves the signature: without it, editing only truncated-away files would
    look like no change at all.
    """
    lines = [f"{f.get('path')}|{f.get('bytes')}|{f.get('mtime')}"
             for f in census.get("files") or []]
    lines.append(f"__count__|{census.get('file_count')}")
    lines.extend(f"__beyond__|{b}" for b in census.get("basenames_beyond_cap") or [])
    return hashlib.md5("\n".join(sorted(lines)).encode("utf-8")).hexdigest()


def inventory_from_census(census: dict, git_summary: dict) -> dict:
    """Build a file_inventory block from one deposited project's census.

    `source_commit` is preserved for git projects and `source_signature` for
    non-git ones -- the distinction is what makes the four repo-less projects
    work at all, so it is never collapsed into a single field.
    """
    paths = sorted(f["path"] for f in (census.get("files") or []) if f.get("path"))
    extra = sorted(census.get("basenames_beyond_cap") or [])
    is_git = bool(census.get("is_git"))
    head = (git_summary or {}).get("latest_hash") if is_git else None

    return {
        "built_at": utc_now(),
        "source": "deposit",
        # A git project whose deposit carries no hash still needs change
        # detection, so it falls back to the census signature rather than
        # silently rebuilding on every run.
        "source_commit": head,
        "source_signature": None if head else census_signature(census),
        "file_count": census.get("file_count", len(paths)),
        "paths": paths,
        "extra_basenames": extra,
        "truncated": bool(census.get("truncated")),
    }


# --- local-disk harvest (the producer fallback) ----------------------------
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


def resolve_fs(entry: dict) -> Path:
    """Local-disk path for a registry entry, from the deposit's recorded path.

    **This is the fallback, not the primary resolution.** It exists because
    `build_vocabulary` (S2) still imports it, and because a producer may run
    against its own working tree.

    It reads `path` as the deposit recorded it. It deliberately does NOT
    reconstruct ``<root>/<scope>/<canonical_name>`` -- that layout exists on no
    machine in the estate and is the folder-walk defect this module was
    refactored to remove. Callers must treat a non-existent path as "not
    available here", never as "project missing".
    """
    return Path(entry.get("path") or "")


def current_signature(fs_path: Path, is_git: bool):
    """Cheap ('git', head) | ('sig', md5) signature for skip-if-unchanged.

    Retained for `build_vocabulary`, which harvests from local disk. The
    deposit-driven path in this module uses `census_signature` instead.
    """
    if is_git:
        return ("git", git_head(fs_path))
    return ("sig", nongit_signature(fs_path, walk_paths(fs_path, NONGIT_MAX_DEPTH)))


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
    """Importable single-project harvest from local disk (reused by S2).

    The fallback path, kept for a producer running against its own working tree.
    Never truncates, so `extra_basenames` is always empty here.
    """
    if is_git:
        paths = sorted(git_paths(fs_path))
        return {
            "built_at": utc_now(),
            "source": "local_disk",
            "source_commit": git_head(fs_path),
            "source_signature": None,
            "file_count": len(paths),
            "paths": paths,
            "extra_basenames": [],
            "truncated": False,
        }
    paths = walk_paths(fs_path, NONGIT_MAX_DEPTH)
    return {
        "built_at": utc_now(),
        "source": "local_disk",
        "source_commit": None,
        "source_signature": nongit_signature(fs_path, paths),
        "file_count": len(paths),
        "paths": paths,
        "extra_basenames": [],
        "truncated": False,
    }


# --- change detection ------------------------------------------------------
def unchanged(entry: dict, commit, signature) -> bool:
    inv = entry.get("file_inventory")
    if not inv:
        return False
    if commit:
        return inv.get("source_commit") == commit
    if signature:
        return inv.get("source_signature") == signature
    return False


def index_deposits(snapshots: list) -> dict:
    """``{project_name: {"census":..., "git_summary":..., "estate":...}}``.

    First deposit mentioning a project wins, matching `build_registry`'s
    "same repo on two rigs is one project" rule. A project deposited without a
    census is indexed anyway so the caller can report it as a gap rather than
    mistake it for a project no producer has seen.
    """
    index: dict = {}
    for snap in snapshots:
        for project in snap.get("projects") or []:
            name = project.get("name")
            if not name or name in index:
                continue
            index[name] = {
                "census": project.get("file_census") or {},
                "git_summary": project.get("git_summary") or {},
                # Full commit list, for build_activity's burst clustering (S3).
                # Carried here so both consumers share one deposit index.
                "deep": project.get("git_deep_history") or {},
                "estate": snap.get("estate"),
                "path": project.get("path") or "",
            }
    return index


def run(force: bool, dry_run: bool, estates_dir: str | None = None):
    if not REGISTRY_PATH.is_file():
        raise SystemExit(f"[build_inventory] registry missing: {REGISTRY_PATH} "
                         "(run build_registry.py first)")
    registry = read_json(REGISTRY_PATH)

    resolved = resolve_estates_dir(estates_dir)
    snapshots = [read_estate_snapshot(e) for e in find_estate_snapshots(resolved)]
    deposits = index_deposits(snapshots)
    if not deposits:
        where = str(resolved) if resolved else "(no estates_dir configured)"
        raise SystemExit(
            f"[build_inventory] no estate deposits found under {where} and no "
            "local build output. Run `run.py build` on a producer and "
            "`run.py deposit --push`, or pass --estates-dir.")

    built, skipped, missing, no_census = [], [], [], []

    for entry in registry["projects"]:
        name = entry["canonical_name"]
        if entry.get("_orphaned"):
            missing.append(name)
            continue

        dep = deposits.get(name)

        if dep and dep["census"].get("files") is not None:
            census, gs = dep["census"], dep["git_summary"]
            commit = gs.get("latest_hash") if census.get("is_git") else None
            signature = None if commit else census_signature(census)
            if not force and unchanged(entry, commit, signature):
                skipped.append(name)
                continue
            inv = inventory_from_census(census, gs)
        else:
            # Fallback: a producer running against its own working tree, for a
            # project no deposit describes. Deposits win wherever both exist.
            fs_path = Path(dep["path"]) if dep and dep.get("path") else None
            if fs_path is None or not fs_path.is_dir():
                (no_census if dep else missing).append(name)
                continue
            is_git = entry["vcs"] == "git"
            commit = git_head(fs_path) if is_git else None
            signature = None if is_git else nongit_signature(
                fs_path, walk_paths(fs_path, NONGIT_MAX_DEPTH))
            if not force and unchanged(entry, commit, signature):
                skipped.append(name)
                continue
            inv = harvest_project(fs_path, is_git)

        if not dry_run:
            entry["file_inventory"] = inv
            entry["registry_updated"] = utc_now()
        built.append((name, inv["file_count"], len(inv["paths"]),
                      len(inv["extra_basenames"]), inv["source"]))

    if not dry_run:
        registry["generated_at"] = utc_now()
        write_json_atomic(REGISTRY_PATH, registry)

    print("=" * 72)
    print("build_inventory" + (" (dry-run)" if dry_run else ""))
    print("=" * 72)
    print(f"  deposits read: {len(deposits)} project(s) from "
          f"{len(snapshots)} snapshot(s)")
    print("-" * 72)
    print(f"  {'project':32} {'files':>6} {'listed':>7} {'+names':>7}  source")
    for name, count, listed, extra, source in built:
        # SHORT means "files exist that we hold no basename for" -- the blind
        # spot S4 would suffer silently. It is NOT `count != listed + extra`:
        # `extra_basenames` is a deduplicated set of names, so two capped files
        # sharing a basename contribute one entry, and the arithmetic under-runs
        # by exactly the number of duplicates. A truncated project that carries
        # its beyond-cap basenames has no blind spot regardless of that gap.
        short = (count > listed) and not extra
        flag = "  <- SHORT (no basenames past the cap)" if short else ""
        print(f"  {name:32} {count:6} {listed:7} {extra:7}  {source}{flag}")
    for name in skipped:
        print(f"  {name:32} (unchanged)")
    for name in no_census:
        print(f"  {name:32} DEPOSITED BUT NO CENSUS -- re-run `run.py census`")
    for name in missing:
        print(f"  {name:32} MISSING (no deposit, no folder / orphaned)")
    print("-" * 72)
    print(f"{len(built)} built, {len(skipped)} unchanged, "
          f"{len(no_census)} without census, {len(missing)} missing.")
    if any(e for _, _, _, e, _ in built):
        print("'+names' = basenames carried past the census file cap. "
              "S4 must read them via basename_set().")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--force", action="store_true",
                    help="rebuild every inventory, ignoring skip-if-unchanged")
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would be built; write nothing")
    ap.add_argument("--estates-dir", default=None,
                    help="where deposited estate bundles live; defaults to this "
                         "machine's configured estates_dir, else the local build "
                         "output")
    args = ap.parse_args()
    run(args.force, args.dry_run, args.estates_dir)


if __name__ == "__main__":
    main()
