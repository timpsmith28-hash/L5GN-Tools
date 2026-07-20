"""tester_build_registry: the registry generator reads deposited estate facts.

The load-bearing change this gate protects (round-3 Task C / DECISIONS 0012):
build_registry used to walk `GITHUB_ROOT/L5GN/` and `GITHUB_ROOT/MCF/`, a layout
that exists on neither machine, so it had never run anywhere. It now reads the
deposited estate snapshots instead -- the consumer reads facts producers left, and
never reaches back to a producer's disk.

Hermetic: writes fake estate deposits into a temp dir and reads them. No real
estate, no vault DB, no network. The assertions are about the *contract with the
deposit*, which is the thing that must not silently regress:

  * projects come from the deposit, not from folders on this machine
  * `scope` comes from the deposit's config tag (a flat estate is classifiable)
  * an untagged project is filed 'other' AND reported as a gap, never guessed
  * git dates ride along for the S3 activity signal; their absence is reported
  * the same repo deposited by two estates is one entry, not two
  * a missing estate is a loud failure, never an empty registry
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

_PIPELINE = Path(__file__).resolve().parent.parent / "chronicler" / "pipeline"


def _load_module():
    """Import build_registry the way the pipeline does (flat `from db import ...`),
    without leaving the path hack behind for other testers."""
    added = str(_PIPELINE) not in sys.path
    if added:
        sys.path.insert(0, str(_PIPELINE))
    try:
        import importlib
        return importlib.import_module("build_registry")
    finally:
        if added and str(_PIPELINE) in sys.path:
            sys.path.remove(str(_PIPELINE))


def _deposit(estates: Path, estate: str, projects: list[dict],
             generated: str = "2026-07-20T09:00:00+01:00") -> None:
    d = estates / estate
    d.mkdir(parents=True, exist_ok=True)
    (d / "estate.json").write_text(json.dumps({
        "generated_at": generated,
        "estate_name": estate,
        "projects": projects,
    }), encoding="utf-8")


def _project(name: str, scope=None, is_git: bool = True,
             first: str | None = "2026-01-15T10:00:00+00:00",
             last: str | None = "2026-06-01T10:00:00+00:00") -> dict:
    gs: dict = {"project": name, "is_git": is_git}
    if is_git:
        gs.update({"first_commit_date": first, "latest_date": last,
                   "commit_count": 42})
    return {"name": name, "path": f"C:/Repos/{name}", "scope": scope,
            "git_summary": gs}


def run() -> list[str]:
    v: list[str] = []
    try:
        br = _load_module()
    except Exception as exc:  # noqa: BLE001 -- an unimportable generator is a red gate
        return [f"build_registry: could not import ({type(exc).__name__}: {exc})"]

    # --- it must no longer depend on a folder walk at all ---
    if hasattr(br, "discover_folders"):
        v.append("build_registry: discover_folders still present -- the folder walk "
                 "was the thing that could never run on either machine")
    if not hasattr(br, "discover_from_estates"):
        v.append("build_registry: no discover_from_estates -- discovery must read "
                 "deposited estate facts")
        return v

    with tempfile.TemporaryDirectory() as td:
        estates = Path(td) / "estates"

        _deposit(estates, "personal", [
            _project("L5GN-Crystal-Spire", scope="l5gn"),
            _project("L5GN_Armory_v4", scope="l5gn"),
            _project("untagged-thing", scope=None),
            _project("no-git-here", scope="l5gn", is_git=False, first=None, last=None),
        ])
        _deposit(estates, "work", [
            _project("ActivityStatements", scope="mcf"),
            _project("L5GN_Armory_v4", scope="l5gn"),  # same repo, two rigs
        ])

        found = br.find_estate_snapshots(estates)
        if {f["estate"] for f in found} != {"personal", "work"}:
            v.append(f"build_registry: find_estate_snapshots saw "
                     f"{sorted(f['estate'] for f in found)}, expected both deposits")

        snapshots = [br.read_estate_snapshot(f) for f in found]
        entries, gaps = br.discover_from_estates(snapshots)
        by_name = {e["canonical_name"]: e for e in entries}

        # projects come from the deposit
        for expected in ("L5GN-Crystal-Spire", "ActivityStatements"):
            if expected not in by_name:
                v.append(f"build_registry: '{expected}' missing -- it was in a "
                         "deposit and must appear without any local folder")

        # scope is the deposited config tag, both sides of the wall
        if by_name.get("ActivityStatements", {}).get("scope") != "mcf":
            v.append("build_registry: work-estate project did not carry scope 'mcf' "
                     "from its deposit")
        if by_name.get("L5GN-Crystal-Spire", {}).get("scope") != "l5gn":
            v.append("build_registry: personal-estate project did not carry scope "
                     "'l5gn' from its deposit")

        # untagged is filed 'other' and REPORTED -- never quietly guessed
        if by_name.get("untagged-thing", {}).get("scope") != "other":
            v.append("build_registry: an untagged project must fall back to scope "
                     "'other', not to a guess")
        if not any("untagged-thing" in g and "scope" in g for g in gaps):
            v.append("build_registry: an untagged project must be reported as a "
                     "deposit gap -- a silently wrong scope mis-files a project")

        # git dates ride along; their absence is reported, not invented
        spire = by_name.get("L5GN-Crystal-Spire", {})
        if spire.get("first_seen") != "2026-01-15":
            v.append(f"build_registry: first_seen={spire.get('first_seen')!r}, "
                     "expected the deposited first-commit date (the S3 signal)")
        if spire.get("last_activity") != "2026-06-01":
            v.append("build_registry: last_activity not carried from the deposit")
        if by_name.get("no-git-here", {}).get("first_seen") != "unknown":
            v.append("build_registry: a project with no git dates must read "
                     "'unknown', never a fabricated date")
        if not any("no-git-here" in g and "git dates" in g for g in gaps):
            v.append("build_registry: missing git dates must be reported as a gap")

        # one repo on two rigs is ONE project, tagged with both estates
        dupes = [e for e in entries if e["canonical_name"] == "L5GN_Armory_v4"]
        if len(dupes) != 1:
            v.append(f"build_registry: {len(dupes)} entries for a repo deposited by "
                     "two estates, expected one")
        elif sorted(dupes[0].get("estates", [])) != ["personal", "work"]:
            v.append(f"build_registry: cross-estate repo records estates "
                     f"{dupes[0].get('estates')}, expected both")

        # alias seeding still works off the deposited name
        if "Crystal Spire" not in spire.get("aliases", []):
            v.append("build_registry: short-name alias seeding regressed")

        # --- loud failure, never an empty registry ---
        empty = Path(td) / "nothing"
        empty.mkdir()
        if br.find_estate_snapshots(empty, only_estate="work"):
            v.append("build_registry: found deposits in an empty landing area")

        # --- a single-estate run is legitimate and says so ---
        personal_only = br.find_estate_snapshots(estates, only_estate="personal")
        if len(personal_only) != 1 or personal_only[0]["estate"] != "personal":
            v.append("build_registry: --estate could not restrict to one deposit "
                     "(needed while the work rig has not deployed yet)")

    return v
