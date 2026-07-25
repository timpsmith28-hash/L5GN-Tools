"""tester_governance_scope -- scope-honesty summary the report is filtered on
(COWORK_BRIEF_governance_scanners.md Task A / D1).

The data must group projects per scope and mark a root that yielded zero projects
this run as *empty* -- distinct from a scanned, non-empty root. The work run's bug
was labelling both the same, letting a reader conclude L5GN had no projects.
"""
from __future__ import annotations

from l5gntools.report import scope_summary


def run() -> list[str]:
    v: list[str] = []
    estate = {
        "roots": [{"path": "/e/L5GN", "scope": "l5gn"},
                  {"path": "/e/MCF", "scope": "mcf"}],
        "projects": [{"name": "A", "scope": "l5gn"},
                     {"name": "B", "scope": "l5gn"}],
    }
    summ = {r["scope"]: r for r in scope_summary(estate)}

    if "l5gn" not in summ or summ["l5gn"]["projects"] != 2:
        v.append(f"scope_summary: l5gn should show 2 scanned projects -> {summ.get('l5gn')}")
    if summ.get("l5gn", {}).get("state") != "scanned":
        v.append("scope_summary: a populated root must read 'scanned'")
    if summ.get("mcf", {}).get("state") != "empty":
        v.append("scope_summary: a root with zero projects must read 'empty' "
                 "(not the same as 'zero projects exist')")
    if summ.get("mcf", {}).get("projects") != 0:
        v.append("scope_summary: empty root should report 0 projects")
    return v
