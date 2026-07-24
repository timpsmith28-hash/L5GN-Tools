"""tester_build_inventory: the inventory generator reads deposited census facts.

The load-bearing defect this gate protects against is the third instance of the
folder-walk bug round 3 fixed in `build_registry` and found blocking
`build_activity`: `build_inventory` resolved every project as
``GITHUB_ROOT/<L5GN|MCF>/<canonical_name>``, a layout that exists on no machine
in the estate. Every project resolved missing, `file_inventory` stayed empty on
the knight, and S4 -- described in the spec as "the strongest automatic link
signal available" -- had nothing to join against from the day it was written.

Hermetic: writes a synthetic estate deposit and a synthetic registry into a temp
dir and reads them back. No real estate, no vault DB, no network, no git.

The assertions are about the contract with the deposit:

  * inventories come from the deposited census, not from folders on this machine
  * a git project preserves `source_commit` (the deposit's HEAD)
  * a NON-GIT project preserves `source_signature` instead -- the distinction
    that makes the four repo-less projects work at all, never collapsed
  * a TRUNCATED project still exposes every basename, via `extra_basenames`,
    because a silently short inventory means S4 silently cannot match
  * `basename_set()` unions both, so a consumer cannot accidentally read only
    the capped prefix
  * `file_count` is always the true count, so `count > len(paths)` stays the
    honest signal that `paths` is a subset
  * skip-if-unchanged holds on a second run, and `--force` overrides it
  * a changed deposit is NOT skipped -- including a change only beyond the cap
  * a project in the registry but in no deposit is reported, never invented
  * no deposits at all is a loud failure, never a silently empty inventory
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

_PIPELINE = Path(__file__).resolve().parent.parent / "chronicler" / "pipeline"


def _load_module():
    """Import build_inventory the way the pipeline does (flat `from db import ...`),
    without leaving the path hack behind for other testers."""
    added = str(_PIPELINE) not in sys.path
    if added:
        sys.path.insert(0, str(_PIPELINE))
    try:
        import importlib
        return importlib.import_module("build_inventory")
    finally:
        if added and str(_PIPELINE) in sys.path:
            sys.path.remove(str(_PIPELINE))


def _census(name: str, paths: list[str], *, is_git: bool,
            beyond: list[str] | None = None, file_count: int | None = None) -> dict:
    beyond = beyond or []
    return {
        "project": name,
        "is_git": is_git,
        "summary": {"total_files": len(paths), "total_bytes": 100},
        "file_count": file_count if file_count is not None else len(paths),
        "truncated": bool(beyond),
        "file_cap": len(paths),
        "directories": [],
        "files": [{"path": p, "bytes": 10, "mtime": "2026-07-01T00:00:00+01:00",
                   "git": "tracked" if is_git else None} for p in paths],
        "basenames_beyond_cap": sorted(beyond),
        "mass": [], "outliers": [], "at_risk": [], "at_risk_note": None,
    }


def _project(name: str, census: dict, *, head: str | None) -> dict:
    gs = {"project": name, "is_git": census["is_git"]}
    if head:
        gs["latest_hash"] = head
    return {"name": name, "path": f"/nonexistent/{name}", "scope": "l5gn",
            "file_census": census, "git_summary": gs}


def _write_deposit(estates: Path, estate: str, projects: list[dict]) -> None:
    d = estates / estate
    d.mkdir(parents=True, exist_ok=True)
    (d / "estate.json").write_text(json.dumps({
        "generated_at": "2026-07-21T09:00:00+01:00",
        "estate_name": estate,
        "roots": [{"path": "/nonexistent", "scope": "l5gn"}],
        "projects": projects,
    }), encoding="utf-8")


def _registry(names: list[str]) -> dict:
    return {"schema_version": 1, "generated_at": "2026-07-21T09:00:00+01:00",
            "projects": [{"canonical_name": n, "scope": "l5gn",
                          "vcs": "git", "aliases": [], "status": "active"}
                         for n in names]}


def run() -> list[str]:
    v: list[str] = []
    bi = _load_module()

    GIT_PATHS = ["README.md", "core/event_bus.py", "core/handover_schema.py"]
    NONGIT_PATHS = ["notes.md", "raw_history_txt/L5GN_SAGA_STITCHED_VOLUME01.txt"]
    CAPPED_PATHS = [f"a/file_{i:03}.py" for i in range(5)]
    BEYOND = ["late_one.py", "late_two.json"]

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        estates = td / "estates"
        registry_path = td / "project_registry.json"

        _write_deposit(estates, "personal", [
            _project("L5GN-Castle",
                     _census("L5GN-Castle", GIT_PATHS, is_git=True), head="96d099a"),
            _project("L5GN-Archive",
                     _census("L5GN-Archive", NONGIT_PATHS, is_git=False), head=None),
            _project("L5GN-Truncated",
                     _census("L5GN-Truncated", CAPPED_PATHS, is_git=True,
                             beyond=BEYOND,
                             file_count=len(CAPPED_PATHS) + len(BEYOND)),
                     head="abc1234"),
        ])
        registry_path.write_text(json.dumps(_registry(
            ["L5GN-Castle", "L5GN-Archive", "L5GN-Truncated", "L5GN-Nowhere"])),
            encoding="utf-8")

        # Point the module at the synthetic estate + registry.
        bi.REGISTRY_PATH = registry_path
        bi.resolve_estates_dir = lambda explicit=None: estates

        def _built() -> dict:
            data = json.loads(registry_path.read_text(encoding="utf-8"))
            return {p["canonical_name"]: p for p in data["projects"]}

        # --- run 1: everything builds from the deposit --------------------
        bi.run(force=False, dry_run=False)
        entries = _built()

        castle = entries["L5GN-Castle"].get("file_inventory")
        if not castle:
            v.append("build_inventory: no file_inventory built for a deposited "
                     "git project -- the folder-walk defect has regressed")
        else:
            if castle.get("source") != "deposit":
                v.append(f"build_inventory: git project sourced from "
                         f"{castle.get('source')!r}, expected 'deposit'")
            if castle.get("source_commit") != "96d099a":
                v.append("build_inventory: git project did not preserve "
                         "source_commit from the deposit")
            if castle.get("source_signature") is not None:
                v.append("build_inventory: git project carries a signature as "
                         "well as a commit; the two paths have blurred")
            if sorted(castle.get("paths") or []) != sorted(GIT_PATHS):
                v.append("build_inventory: git project paths do not match the "
                         "deposited census")

        # --- the non-git project: signature, not an empty block -----------
        arch = entries["L5GN-Archive"].get("file_inventory")
        if not arch:
            v.append("build_inventory: no file_inventory for the non-git project")
        else:
            if not arch.get("source_signature"):
                v.append("build_inventory: non-git project has no "
                         "source_signature -- skip-if-unchanged cannot work and "
                         "the four repo-less projects lose change detection")
            if arch.get("source_commit") is not None:
                v.append("build_inventory: non-git project invented a "
                         "source_commit")

        # --- the truncated project: no silent blind spot ------------------
        trunc = entries["L5GN-Truncated"].get("file_inventory")
        if not trunc:
            v.append("build_inventory: no file_inventory for the truncated project")
        else:
            if not trunc.get("truncated"):
                v.append("build_inventory: truncated project did not carry the "
                         "truncated flag -- the blind spot would be silent")
            if sorted(trunc.get("extra_basenames") or []) != sorted(BEYOND):
                v.append("build_inventory: truncated project lost the basenames "
                         "beyond the cap; S4 cannot match those files")
            if trunc.get("file_count") != len(CAPPED_PATHS) + len(BEYOND):
                v.append("build_inventory: truncated project's file_count is not "
                         "the true count")
            if trunc["file_count"] <= len(trunc.get("paths") or []):
                v.append("build_inventory: truncated project lost the "
                         "count>len(paths) signal that paths is a subset")

            names = bi.basename_set(trunc)
            expected = {Path(p).name for p in CAPPED_PATHS} | set(BEYOND)
            if names != expected:
                v.append(f"build_inventory: basename_set() returned {len(names)} "
                         f"names, expected {len(expected)} -- a consumer reading "
                         "it would silently miss capped files")

        # basename_set on an empty/absent inventory must not explode
        if bi.basename_set(None) or bi.basename_set({}):
            v.append("build_inventory: basename_set() on an empty inventory is "
                     "not empty")

        # --- a project in the registry but in no deposit ------------------
        if entries["L5GN-Nowhere"].get("file_inventory"):
            v.append("build_inventory: invented an inventory for a project no "
                     "deposit describes")

        # --- run 2: skip-if-unchanged holds -------------------------------
        before = {n: (e.get("file_inventory") or {}).get("built_at")
                  for n, e in entries.items() if e.get("file_inventory")}
        bi.run(force=False, dry_run=False)
        after = {n: (e.get("file_inventory") or {}).get("built_at")
                 for n, e in _built().items() if e.get("file_inventory")}
        if before != after:
            v.append("build_inventory: a second run rebuilt unchanged projects "
                     "-- skip-if-unchanged does not hold")

        # --- --force overrides the skip -----------------------------------
        bi.run(force=True, dry_run=False)
        if not _built()["L5GN-Castle"].get("file_inventory"):
            v.append("build_inventory: --force lost an inventory")

        # --- a change ONLY beyond the cap must still rebuild ---------------
        stale = (_built()["L5GN-Archive"]["file_inventory"] or {}).get("source_signature")
        _write_deposit(estates, "personal", [
            _project("L5GN-Castle",
                     _census("L5GN-Castle", GIT_PATHS, is_git=True), head="96d099a"),
            _project("L5GN-Archive",
                     _census("L5GN-Archive", NONGIT_PATHS, is_git=False,
                             beyond=["appeared_beyond_the_cap.txt"],
                             file_count=len(NONGIT_PATHS) + 1), head=None),
            _project("L5GN-Truncated",
                     _census("L5GN-Truncated", CAPPED_PATHS, is_git=True,
                             beyond=BEYOND,
                             file_count=len(CAPPED_PATHS) + len(BEYOND)),
                     head="abc1234"),
        ])
        bi.run(force=False, dry_run=False)
        fresh = _built()["L5GN-Archive"]["file_inventory"]
        if fresh.get("source_signature") == stale:
            v.append("build_inventory: a deposit change confined to files beyond "
                     "the cap did not move the signature -- those edits would be "
                     "invisible to change detection forever")
        if "appeared_beyond_the_cap.txt" not in bi.basename_set(fresh):
            v.append("build_inventory: a newly-capped basename did not reach "
                     "basename_set()")

        # --- dry-run writes nothing ---------------------------------------
        snapshot = registry_path.read_text(encoding="utf-8")
        bi.run(force=True, dry_run=True)
        if registry_path.read_text(encoding="utf-8") != snapshot:
            v.append("build_inventory: --dry-run wrote to the registry")

        # --- no deposits at all is loud, never silently empty --------------
        # Note the local-estate fallback is deliberately neutralised here.
        # `find_estate_snapshots` falls back to this repo's own data/estate.json
        # when the landing area is empty -- correct behaviour on a producer rig,
        # and the reason an "empty estates dir" alone is NOT the no-deposits
        # case. What must be loud is genuinely finding nothing.
        bi.find_estate_snapshots = lambda *a, **k: []
        try:
            bi.run(force=True, dry_run=True)
            v.append("build_inventory: finding no deposits at all produced no "
                     "error -- an empty inventory would look like a clean run")
        except SystemExit:
            pass

    return v
