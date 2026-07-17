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

    # ---- present_names overrides project_trail's own present_in_estate flag ----
    pt_flags = {
        "status": "ok",
        "projects": [
            # flag says present, but the knight's union says it isn't -> DNP fires.
            {"estate_project": "FlagTrue", "estate": "L5GN", "thread_count": 1,
             "substantive_count": 1, "latest_activity": "2026-07-16", "present_in_estate": True},
            # flag says absent, but the union DOES hold it -> DNP must NOT fire.
            {"estate_project": "FlagFalse", "estate": "L5GN", "thread_count": 1,
             "substantive_count": 1, "latest_activity": "2026-07-16", "present_in_estate": False},
        ],
    }
    ov = drift._compute(pt_flags, None, present_names={"FlagFalse"})
    dnp = {x["project"] for x in ov["alerts"]["discussed_not_present"]}
    if dnp != {"FlagTrue"}:
        v.append(f"drift: present_names should override the flag both ways, got DNP {dnp}")
    # FlagFalse is now present + recent + unbuilt -> surfaces as talked_not_built instead.
    if {x["project"] for x in ov["alerts"]["talked_not_built"]} != {"FlagFalse"}:
        v.append("drift: an overridden-present project should become talked_not_built")

    # ---- recency edge: exactly WINDOW_DAYS is still 'recent', one more day isn't ----
    w = drift.WINDOW_DAYS  # 30
    pt_edge = {
        "status": "ok",
        "projects": [
            {"estate_project": "Ref", "estate": "L5GN", "thread_count": 1,
             "substantive_count": 1, "latest_activity": "2026-07-31", "present_in_estate": True},
            {"estate_project": "Edge30", "estate": "L5GN", "thread_count": 1,
             "substantive_count": 1, "latest_activity": "2026-07-01", "present_in_estate": True},
            {"estate_project": "Edge31", "estate": "L5GN", "thread_count": 1,
             "substantive_count": 1, "latest_activity": "2026-06-30", "present_in_estate": True},
        ],
    }
    oe = drift._compute(pt_edge, None)
    if oe["reference_date"] != "2026-07-31":
        v.append(f"drift: reference_date should be the max signal date, got {oe['reference_date']!r}")
    if oe["window_days"] != w:
        v.append("drift: window_days should be reported")
    rec = {r["project"]: r for r in oe["projects"]}
    if not rec["Edge30"]["discussed_recently"]:
        v.append(f"drift: exactly WINDOW_DAYS ({w}) old should count as recent")
    if rec["Edge31"]["discussed_recently"]:
        v.append(f"drift: WINDOW_DAYS+1 old should NOT count as recent")
    tnb2 = {x["project"] for x in oe["alerts"]["talked_not_built"]}
    if "Edge31" in tnb2:
        v.append("drift: a stale-discussion project should not fire talked_not_built")
    if {"Ref", "Edge30"} - tnb2:
        v.append("drift: recent-discussion present projects should fire talked_not_built")

    # ---- estate_diff insufficient/absent degrades gracefully (no build alerts) ----
    insuff = drift._compute(pt_edge, {"status": "insufficient_history"})
    if insuff["inputs"]["estate_diff"] != "insufficient_history":
        v.append(f"drift: should carry estate_diff status through, got {insuff['inputs']['estate_diff']!r}")
    if insuff["alerts"]["built_not_discussed"]:
        v.append("drift: insufficient estate_diff must yield no built_not_discussed alerts")
    if insuff["reference_date"] != "2026-07-31":
        v.append("drift: reference should fall back to discussion dates when estate_diff has no 'to' date")

    return v
