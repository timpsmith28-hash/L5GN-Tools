"""drift: exercise the join logic across all three alert types with crafted
project_trail + estate_diff inputs (IO-free, via drift._compute)."""
from __future__ import annotations

from l5gntools.scanners import drift


def run() -> list[str]:
    v: list[str] = []

    project_trail = {
        "status": "ok",
        "projects": [
            # recent chat, present, no commits -> talked_not_built
            {"estate_project": "AppA", "estate": "L5GN", "thread_count": 3,
             "substantive_count": 2, "latest_activity": "2026-07-15", "present_in_estate": True},
            # chat but code not visible -> discussed_not_present
            {"estate_project": "AppB", "estate": "L5GN", "thread_count": 2,
             "substantive_count": 1, "latest_activity": "2026-07-14", "present_in_estate": False},
            # old chat + fresh commits -> built_not_discussed
            {"estate_project": "AppC", "estate": "MCF", "thread_count": 5,
             "substantive_count": 3, "latest_activity": "2026-05-01", "present_in_estate": True},
        ],
    }
    estate_diff = {
        "status": "ok",
        "to_generated_at": "2026-07-16",
        "changed": [
            {"project": "AppC", "git": {"new_commit_count": 4,
             "new_commits": [{"subject": "fix x"}, {"subject": "add y"}]}},
            # built but never discussed at all (absent from project_trail)
            {"project": "AppD", "git": {"new_commit_count": 2,
             "new_commits": [{"subject": "init"}]}},
        ],
    }

    out = drift._compute(project_trail, estate_diff)
    if out.get("status") != "ok":
        return [f"drift: expected ok, got {out.get('status')!r}"]
    if out["reference_date"] != "2026-07-16":
        v.append(f"drift: reference_date wrong {out['reference_date']!r}")

    al = out["alerts"]
    tnb = {x["project"] for x in al["talked_not_built"]}
    dnp = {x["project"] for x in al["discussed_not_present"]}
    bnd = {x["project"] for x in al["built_not_discussed"]}
    if tnb != {"AppA"}:
        v.append(f"drift: talked_not_built wrong {tnb}")
    if dnp != {"AppB"}:
        v.append(f"drift: discussed_not_present wrong {dnp}")
    if bnd != {"AppC", "AppD"}:
        v.append(f"drift: built_not_discussed wrong {bnd}")

    rec = {r["project"]: r for r in out["projects"]}
    if rec["AppD"]["discussed"] or rec["AppD"]["thread_count"] != 0:
        v.append("drift: built-only AppD should be undiscussed with 0 threads")
    if not rec["AppD"]["built_recently"]:
        v.append("drift: AppD should be built_recently")

    # Without estate_diff, only the presence gap should still fire.
    out2 = drift._compute(project_trail, None)
    if out2["inputs"]["estate_diff"] != "absent":
        v.append("drift: estate_diff should report absent when None")
    if {x["project"] for x in out2["alerts"]["discussed_not_present"]} != {"AppB"}:
        v.append("drift: discussed_not_present should still fire without estate_diff")
    if out2["alerts"]["built_not_discussed"]:
        v.append("drift: no build alerts expected without estate_diff")

    return v
