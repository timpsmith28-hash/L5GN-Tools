"""tester_build_activity: the activity generator reads deposited git facts.

Fourth and last instance of the folder-walk defect round 3 fixed in
`build_registry` and this session fixed in `build_inventory`: `build_activity`
resolved every project as ``GITHUB_ROOT/<L5GN|MCF>/<canonical_name>``, a layout
that exists on no machine, so every project resolved missing and the S3 activity
window -- which `relink`'s `time_plausibility` multiplies every score by -- was
never built anywhere.

Hermetic: synthetic deposit + synthetic registry in a temp dir. No real estate,
no vault, no git.

Assertions:

  * activity blocks come from the deposit, not from folders on this machine
  * burst clustering uses the FULL commit list in `git_deep_history`, not just
    the first/last pair -- a project with two clusters must report two bursts
  * a thin deposit (no deep history) degrades to a coarse window from
    `git_summary`, rather than to nothing
  * a non-git project gets an mtime-precision window from the census
  * a truncated commit list is FLAGGED, because git log is newest-first so the
    dates lost are the earliest ones and the window silently narrows
  * skip-if-unchanged holds; `--force` overrides
  * no deposits at all is loud, never a silently empty activity set
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

_PIPELINE = Path(__file__).resolve().parent.parent / "chronicler" / "pipeline"


def _load_module():
    added = str(_PIPELINE) not in sys.path
    if added:
        sys.path.insert(0, str(_PIPELINE))
    try:
        import importlib
        return importlib.import_module("build_activity")
    finally:
        if added and str(_PIPELINE) in sys.path:
            sys.path.remove(str(_PIPELINE))


def _project(name, *, is_git, commits=None, head=None, mtimes=None,
             first=None, last=None, truncated=False):
    gs = {"project": name, "is_git": is_git}
    if head:
        gs["latest_hash"] = head
    if first:
        gs["first_commit_date"] = first
    if last:
        gs["latest_date"] = last
    deep = {"project": name, "is_git": is_git, "truncated": truncated}
    if commits is not None:
        deep["commits"] = [{"hash": f"h{i}", "date": d, "author": "t",
                            "subject": "s"} for i, d in enumerate(commits)]
        deep["total_commits"] = len(commits)
    census = {
        "project": name, "is_git": is_git, "file_count": len(mtimes or []),
        "truncated": False, "file_cap": 2000,
        "files": [{"path": f"f{i}.txt", "bytes": 1, "mtime": m, "git": None}
                  for i, m in enumerate(mtimes or [])],
        "basenames_beyond_cap": [], "summary": {}, "directories": [],
        "mass": [], "outliers": [], "at_risk": [], "at_risk_note": None,
    }
    return {"name": name, "path": f"/nonexistent/{name}", "scope": "l5gn",
            "file_census": census, "git_summary": gs, "git_deep_history": deep}


def run() -> list[str]:
    v: list[str] = []
    ba = _load_module()

    # Two clusters 30 days apart -> must produce TWO bursts (gap > 7 days).
    TWO_BURSTS = ["2026-05-01T10:00:00+01:00", "2026-05-02T10:00:00+01:00",
                  "2026-05-03T10:00:00+01:00",
                  "2026-06-10T10:00:00+01:00", "2026-06-11T10:00:00+01:00"]

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        estates = td / "estates" / "personal"
        estates.mkdir(parents=True)
        registry_path = td / "project_registry.json"

        projects = [
            _project("Bursty", is_git=True, commits=TWO_BURSTS, head="aaa1111"),
            _project("ThinDeposit", is_git=True, head="bbb2222",
                     first="2026-04-01T09:00:00+01:00",
                     last="2026-04-09T09:00:00+01:00"),
            _project("NoGit", is_git=False,
                     mtimes=["2026-03-01T09:00:00+01:00",
                             "2026-03-02T09:00:00+01:00"]),
            _project("Truncated", is_git=True, commits=TWO_BURSTS[:2],
                     head="ccc3333", truncated=True),
        ]
        (estates / "estate.json").write_text(json.dumps({
            "generated_at": "2026-07-21T09:00:00+01:00", "estate_name": "personal",
            "roots": [], "projects": projects}), encoding="utf-8")

        registry_path.write_text(json.dumps({"schema_version": 1, "projects": [
            {"canonical_name": p["name"], "scope": "l5gn",
             "vcs": "git" if p["git_summary"]["is_git"] else "none",
             "path": p["path"], "aliases": [], "status": "active"}
            for p in projects]}), encoding="utf-8")

        ba.REGISTRY_PATH = registry_path
        ba.resolve_estates_dir = lambda explicit=None: estates.parent

        def built():
            return {p["canonical_name"]: p for p in
                    json.loads(registry_path.read_text(encoding="utf-8"))["projects"]}

        ba.run(force=False, dry_run=False)
        e = built()

        bursty = e["Bursty"].get("activity")
        if not bursty:
            v.append("build_activity: no activity block for a deposited git "
                     "project -- the folder-walk defect has regressed")
        else:
            if len(bursty.get("bursts") or []) != 2:
                v.append(f"build_activity: expected 2 bursts from the deposited "
                         f"commit list, got {len(bursty.get('bursts') or [])} -- "
                         "the full commit list is not being read")
            if bursty.get("first_commit") != "2026-05-01":
                v.append(f"build_activity: first_commit is "
                         f"{bursty.get('first_commit')}, expected 2026-05-01")
            if bursty.get("precision") != "commit":
                v.append("build_activity: git project not at commit precision")
            if bursty.get("source_commit") != "aaa1111":
                v.append("build_activity: git project did not preserve the "
                         "deposit's HEAD as source_commit")

        thin = e["ThinDeposit"].get("activity")
        if not thin or not thin.get("first_commit"):
            v.append("build_activity: a deposit with no deep history degraded to "
                     "nothing; it must fall back to git_summary's date pair")
        elif thin.get("first_commit") != "2026-04-01":
            v.append(f"build_activity: thin-deposit fallback gave "
                     f"{thin.get('first_commit')}, expected 2026-04-01")

        nogit = e["NoGit"].get("activity")
        if not nogit:
            v.append("build_activity: no activity block for the non-git project")
        else:
            if nogit.get("precision") != "mtime":
                v.append("build_activity: non-git project not at mtime precision")
            if not nogit.get("source_signature"):
                v.append("build_activity: non-git project has no signature, so "
                         "skip-if-unchanged cannot work")

        trunc = e["Truncated"].get("activity")
        if trunc and not trunc.get("truncated_source"):
            v.append("build_activity: a truncated commit list was not flagged -- "
                     "git log is newest-first, so the EARLIEST dates are the ones "
                     "missing and first_commit is silently too late")

        # skip-if-unchanged, then --force
        before = {n: (x.get("activity") or {}).get("built_at")
                  for n, x in e.items() if x.get("activity")}
        ba.run(force=False, dry_run=False)
        after = {n: (x.get("activity") or {}).get("built_at")
                 for n, x in built().items() if x.get("activity")}
        if before != after:
            v.append("build_activity: a second run rebuilt unchanged projects")
        ba.run(force=True, dry_run=False)
        if not built()["Bursty"].get("activity"):
            v.append("build_activity: --force lost an activity block")

        # dry-run writes nothing
        snap = registry_path.read_text(encoding="utf-8")
        ba.run(force=True, dry_run=True)
        if registry_path.read_text(encoding="utf-8") != snap:
            v.append("build_activity: --dry-run wrote to the registry")

        # no deposits at all is loud
        ba.find_estate_snapshots = lambda *a, **k: []
        try:
            ba.run(force=True, dry_run=True)
            v.append("build_activity: finding no deposits produced no error")
        except SystemExit:
            pass

    return v
