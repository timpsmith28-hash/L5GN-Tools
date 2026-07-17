"""drift -- reconcile what was BUILT against what was DISCUSSED (S8).

Joins two existing feeds by project name:
  * ``data/project_trail.json`` -- chat discussion per project (from project_trail)
  * ``data/estate_diff.json``   -- new commits per project since last snapshot

and raises three drift signals:
  * ``discussed_not_present`` -- chat references a project the estate can't see
    (``present_in_estate: False``). The estate-completeness gap the knight exists
    to close; available from project_trail alone.
  * ``talked_not_built``      -- recent discussion, but the code hasn't moved.
  * ``built_not_discussed``   -- new commits, but no recent linked conversation.

Recency is measured against the newest signal in the data (newest discussion or
the estate_diff "to" snapshot), NOT wall-clock now -- the knight may process a
bridged export that is itself days old, so self-relative is the honest frame.

Read-only consumer of other tools' JSON output; needs neither the vault nor the
live repos. Estate tool, excluded from build (SKIP_IN_BUILD).
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from ..common import DATA_DIR
from ..contract import SAFE

NAME = "drift"
DESCRIPTION = "Drift alerts (S8): talked-not-built / built-not-discussed / discussed-not-present."
ESTATE_LEVEL = True
SAFETY = SAFE
SKIP_IN_BUILD = True

WINDOW_DAYS = 30


def _load(name: str):
    p = DATA_DIR / name
    if p.exists() and p.stat().st_size > 0:
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return None
    return None


def _pdate(s):
    if not s:
        return None
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def _days_between(latest, ref):
    d = _pdate(latest)
    return (ref - d).days if (d is not None and ref is not None) else None


def scan_estate(projects: list) -> dict:
    pt = _load("project_trail.json")
    if not pt or pt.get("status") != "ok":
        return {"status": "needs_inputs",
                "note": "Run project_trail first (data/project_trail.json missing or not ok).",
                "project_trail_status": pt.get("status") if pt else "absent"}
    ed = _load("estate_diff.json")
    return _compute(pt, ed)


def _compute(pt: dict, ed: dict | None, present_names: set | None = None) -> dict:
    # present_names: the set of project names actually present in the estate(s).
    # On the knight there are no live repos, so presence is judged from the
    # deposited estate.json project lists rather than project_trail's own flag.
    ed_status = ed.get("status") if ed else "absent"

    built: dict = {}
    if ed and ed.get("status") == "ok":
        for c in ed.get("changed", []):
            git = c.get("git")
            if git and git.get("new_commit_count", 0) > 0:
                built[c["project"]] = git

    discussed = {p["estate_project"]: p for p in pt.get("projects", [])}

    dates = [p["latest_activity"][:10] for p in pt.get("projects", [])
             if p.get("latest_activity")]
    if ed and ed.get("to_generated_at"):
        dates.append(ed["to_generated_at"][:10])
    ref_str = max(dates) if dates else None
    ref = _pdate(ref_str)

    a_dnp: list = []
    a_tnb: list = []
    a_bnd: list = []
    records: list = []

    for name in sorted(set(discussed) | set(built)):
        d = discussed.get(name)
        thread_count = d["thread_count"] if d else 0
        substantive = d.get("substantive_count", 0) if d else 0
        latest = d.get("latest_activity") if d else None
        if present_names is not None:
            present = name in present_names
        else:
            present = d.get("present_in_estate") if d else None
        is_discussed = thread_count > 0
        days_since = _days_between(latest, ref)
        recent = days_since is not None and days_since <= WINDOW_DAYS
        is_built = name in built
        new_commits = built[name]["new_commit_count"] if is_built else 0

        alerts: list = []
        if is_discussed and present is False:
            alerts.append("discussed_not_present")
            a_dnp.append({"project": name, "estate": d.get("estate"),
                          "latest_discussion": latest, "thread_count": thread_count,
                          "substantive_count": substantive})
        if recent and present is not False and not is_built:
            alerts.append("talked_not_built")
            a_tnb.append({"project": name, "latest_discussion": latest,
                          "thread_count": thread_count, "days_since_discussion": days_since})
        if is_built and (not is_discussed or not recent):
            alerts.append("built_not_discussed")
            a_bnd.append({"project": name, "new_commit_count": new_commits,
                          "sample_subjects": [c.get("subject") for c in
                                              built[name].get("new_commits", [])[:3]],
                          "latest_discussion": latest})

        records.append({
            "project": name, "estate": d.get("estate") if d else None,
            "discussed": is_discussed, "thread_count": thread_count,
            "substantive_count": substantive, "latest_discussion": latest,
            "discussed_recently": recent, "built_recently": is_built,
            "new_commit_count": new_commits, "present_in_estate": present,
            "alerts": alerts,
        })

    return {
        "status": "ok",
        "inputs": {"project_trail": "ok", "estate_diff": ed_status},
        "window_days": WINDOW_DAYS,
        "reference_date": ref_str,
        "summary": {"discussed_not_present": len(a_dnp),
                    "talked_not_built": len(a_tnb),
                    "built_not_discussed": len(a_bnd)},
        "alerts": {"discussed_not_present": a_dnp,
                   "talked_not_built": a_tnb,
                   "built_not_discussed": a_bnd},
        "projects": records,
    }
