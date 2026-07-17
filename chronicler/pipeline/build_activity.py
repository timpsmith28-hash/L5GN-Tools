"""
S3 - Activity Windows (registry aux-data producer + scoring helper).

Per project, the date ranges when it was actually being worked on. Two uses:

  1. A `time_plausibility(thread_date, activity)` multiplier that relink.py (S6)
     folds into every candidate score, so a thread dated well outside a project's
     active life is discounted, and two projects that share vocabulary/aliases
     but were worked on in different eras (the classic Citadel-lineage case:
     legacy `v1 proto` vs current `L5GN_Armory_v4`) can be separated by DATE.
  2. Human-readable provenance in the registry.

Storage (spec S3): an `"activity"` block per registry entry:

    "activity": {
      "first_commit": "2026-05-02",
      "last_commit":  "2026-07-12",
      "bursts": [ {"from": "2026-05-02", "to": "2026-05-19"},
                  {"from": "2026-06-28", "to": "2026-07-12"} ],
      "precision":  "commit" | "mtime",   # mtime = coarse non-git fallback
      "source_commit":    "abc1234",      # git HEAD short SHA (skip-if-unchanged)
      "source_signature": "md5...",       # non-git mtime/size signature
      "built_at": "2026-07-16T...Z"
    }

Signal derivation:
  * git projects  -> `git log --format=%aI` author dates (ISO), date part only,
    clustered into bursts (a gap > BURST_GAP_DAYS days splits a burst).
  * non-git projects (e.g. `v1 proto`) -> file mtimes as a coarse fallback,
    flagged `"precision": "mtime"`.

Skip-if-unchanged: a project whose git HEAD (git) or mtime/size signature
(non-git) matches the stored value is left untouched - same change-detection
build_inventory.py uses.

Standing rules: UTF-8, UTC ISO-8601, whole-file atomic write, loud failure,
no half-updates.

Usage:
    python3 pipeline/build_activity.py            # refresh changed projects
    python3 pipeline/build_activity.py --force    # rebuild all activity blocks
    python3 pipeline/build_activity.py --dry-run  # report only, write nothing
"""
import argparse
import json
import math
import os
import subprocess
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from db import CHRONICLER_ROOT
# Reuse the single harvest walk (never re-walk what build_inventory already does).
from build_inventory import (
    walk_paths, NONGIT_MAX_DEPTH, git_head, nongit_signature,
    read_json, write_json_atomic, utc_now,
)

GITHUB_ROOT_FS = CHRONICLER_ROOT.parent.parent
REGISTRY_PATH = GITHUB_ROOT_FS / "L5GN" / ".intel_sync" / "project_registry.json"
SCOPE_TO_ROOT = {"l5gn": "L5GN", "mcf": "MCF"}

PRODUCER_VERSION = "build_activity/1.0"
BURST_GAP_DAYS = 7          # spec S3: a gap > 7 days splits a burst

# ---------------------------------------------------------------------------
# time_plausibility tunables - imported/used by relink.py (S6). ONE knob block.
# ---------------------------------------------------------------------------
TP_IN_BURST = 1.0            # thread date lands inside an active burst
TP_FLOOR = 0.1               # asymptote for dates far outside every burst
TP_NEUTRAL_NO_WINDOW = 1.0   # project has no usable activity window -> don't distort
TP_NEUTRAL_UNDATED = 0.7     # thread has no usable date -> mild discount, never 1.0
TP_DECAY_TAU_DAYS = 30.0     # exponential decay scale outside a burst
TP_HARD_ZERO_LEAD_DAYS = 14  # a thread > 14 days BEFORE first_commit -> hard 0.0


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------
def parse_iso_date(s):
    """First 10 chars of an ISO-8601 string -> date, or None if unparseable."""
    if not s:
        return None
    try:
        return date.fromisoformat(str(s)[:10])
    except (ValueError, TypeError):
        return None


# Public alias: relink.py imports this to normalise thread created_at.
parse_thread_date = parse_iso_date


def git_author_dates(fs_path: Path):
    """Sorted unique list of author dates (date objects) from git history."""
    o = subprocess.run(["git", "log", "--format=%aI"], cwd=str(fs_path),
                       capture_output=True, text=True, timeout=120)
    if o.returncode != 0:
        raise SystemExit(f"[build_activity] git log failed in {fs_path}: "
                         f"{o.stderr.strip()}")
    dates = {d for d in (parse_iso_date(line) for line in o.stdout.splitlines()) if d}
    return sorted(dates)


def mtime_dates(fs_path: Path):
    """Sorted unique file-mtime dates for a non-git project (coarse fallback)."""
    dates = set()
    for rel in walk_paths(fs_path, NONGIT_MAX_DEPTH):
        try:
            ts = (fs_path / rel).stat().st_mtime
        except OSError:
            continue
        dates.add(datetime.fromtimestamp(ts, tz=timezone.utc).date())
    return sorted(dates)


def cluster_bursts(dates, gap_days=BURST_GAP_DAYS):
    """Cluster a sorted list of dates into bursts; a gap > gap_days splits one.
    Returns a list of {"from": iso, "to": iso}."""
    if not dates:
        return []
    bursts = []
    start = prev = dates[0]
    for d in dates[1:]:
        if (d - prev).days > gap_days:
            bursts.append({"from": start.isoformat(), "to": prev.isoformat()})
            start = d
        prev = d
    bursts.append({"from": start.isoformat(), "to": prev.isoformat()})
    return bursts


# ---------------------------------------------------------------------------
# The scoring helper used by relink.py (S6). Replaces the old 1.0 stub.
# ---------------------------------------------------------------------------
def time_plausibility(thread_date, activity):
    """Multiplier in [0, 1] applied to a candidate's combined score.

    thread_date : a `date` (from parse_thread_date) or None.
    activity    : a project's activity block (dict) or None.

    Rules (spec S3):
      * thread has no usable date        -> TP_NEUTRAL_UNDATED (0.7). Never 1.0:
        we must not silently treat an undated thread as perfectly plausible.
      * project has no usable window      -> TP_NEUTRAL_NO_WINDOW (1.0): we can't
        assess time, so we don't distort the score either way.
      * thread date inside any burst      -> TP_IN_BURST (1.0).
      * thread > 14 days BEFORE first_commit -> 0.0 (design talk may slightly
        predate code, but not by a month).
      * otherwise -> decay from 1.0 toward TP_FLOOR (0.1) with the thread's
        distance in days to the nearest burst edge.
    """
    if thread_date is None:
        return TP_NEUTRAL_UNDATED
    if not activity:
        return TP_NEUTRAL_NO_WINDOW

    bursts = []
    for b in activity.get("bursts", []):
        f = parse_iso_date(b.get("from"))
        t = parse_iso_date(b.get("to"))
        if f and t:
            bursts.append((f, t))
    first = parse_iso_date(activity.get("first_commit"))
    if not bursts and not first:
        return TP_NEUTRAL_NO_WINDOW

    # Hard floor: a thread well before the project ever started is implausible.
    if first and thread_date < first - timedelta(days=TP_HARD_ZERO_LEAD_DAYS):
        return 0.0

    if not bursts:
        # Have a first_commit but no bursts (shouldn't happen) - treat neutrally.
        return TP_NEUTRAL_NO_WINDOW

    # Distance (days) to the nearest burst; 0 means inside a burst.
    dist = None
    for f, t in bursts:
        if thread_date < f:
            d = (f - thread_date).days
        elif thread_date > t:
            d = (thread_date - t).days
        else:
            d = 0
        dist = d if dist is None else min(dist, d)

    if dist == 0:
        return TP_IN_BURST
    return TP_FLOOR + (TP_IN_BURST - TP_FLOOR) * math.exp(-dist / TP_DECAY_TAU_DAYS)


# ---------------------------------------------------------------------------
# Per-project build
# ---------------------------------------------------------------------------
def build_activity_block(fs_path: Path, is_git: bool) -> dict:
    """Return an activity block for one project. Does NOT skip-if-unchanged -
    the caller decides that."""
    if is_git:
        dates = git_author_dates(fs_path)
        precision, commit, signature = "commit", git_head(fs_path), None
    else:
        dates = mtime_dates(fs_path)
        precision, commit = "mtime", None
        signature = nongit_signature(fs_path, walk_paths(fs_path, NONGIT_MAX_DEPTH))
    bursts = cluster_bursts(dates)
    return {
        "first_commit": dates[0].isoformat() if dates else None,
        "last_commit": dates[-1].isoformat() if dates else None,
        "bursts": bursts,
        "precision": precision,
        "source_commit": commit,
        "source_signature": signature,
        "built_at": utc_now(),
    }


def current_signature(fs_path: Path, is_git: bool):
    """Cheap change-detection signature (no full harvest)."""
    if is_git:
        return ("git", git_head(fs_path))
    return ("sig", nongit_signature(fs_path, walk_paths(fs_path, NONGIT_MAX_DEPTH)))


def unchanged(entry: dict, sig) -> bool:
    act = entry.get("activity")
    if not act:
        return False
    kind, val = sig
    if val is None:
        return False
    if kind == "git":
        return act.get("source_commit") == val
    return act.get("source_signature") == val


def resolve_fs(entry: dict) -> Path:
    root = SCOPE_TO_ROOT.get(entry["scope"])
    if root is None:
        raise SystemExit(f"[build_activity] unknown scope {entry['scope']} "
                         f"on {entry['canonical_name']}")
    return GITHUB_ROOT_FS / root / entry["canonical_name"]


def run(force: bool, dry_run: bool):
    if not REGISTRY_PATH.is_file():
        raise SystemExit(f"[build_activity] registry missing: {REGISTRY_PATH} "
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
        is_git = entry.get("vcs") == "git"
        sig = current_signature(fs_path, is_git)
        if not force and unchanged(entry, sig):
            skipped.append(entry["canonical_name"])
            continue
        act = build_activity_block(fs_path, is_git)
        if not dry_run:
            entry["activity"] = act
            entry["registry_updated"] = utc_now()
        built.append((entry["canonical_name"], act))

    if not dry_run:
        registry["generated_at"] = utc_now()
        write_json_atomic(REGISTRY_PATH, registry)

    print("=" * 68)
    print("build_activity" + (" (dry-run)" if dry_run else ""))
    print("=" * 68)
    for name, act in built:
        nb = len(act["bursts"])
        span = f"{act['first_commit']}..{act['last_commit']}"
        print(f"  built   {name:26} {act['precision']:6} {nb:2} burst(s)  {span}")
    for name in skipped:
        print(f"  skip    {name:26} (unchanged)")
    for name in missing:
        print(f"  MISSING {name:26} (no folder / orphaned)")
    print("-" * 68)
    print(f"{len(built)} built, {len(skipped)} unchanged, {len(missing)} missing.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Per-project activity windows (S3).")
    ap.add_argument("--force", action="store_true",
                    help="Rebuild all activity blocks, ignore skip-if-unchanged.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Report only, write nothing.")
    args = ap.parse_args()
    run(args.force, args.dry_run)
