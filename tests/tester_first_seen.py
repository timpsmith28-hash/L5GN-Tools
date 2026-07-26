"""tester_first_seen: curated first_seen anchors time_plausibility (apply brief precond 4).

Hermetic: a re-created repo's git window starts late, so its earlier chat threads
would be hard-zeroed by time_plausibility. A curated first_seen (the operator's
known real start) must widen the window earlier -- never later -- so the era
scores in-window. No DB, no network.
"""
from __future__ import annotations

import json
import sys
import tempfile
from datetime import date
from pathlib import Path

_PIPE = Path(__file__).resolve().parent.parent / "chronicler" / "pipeline"


def run() -> list[str]:
    v: list[str] = []
    if str(_PIPE) not in sys.path:
        sys.path.insert(0, str(_PIPE))
    import build_activity as ba

    # a re-created repo: git window is a late two-day sliver
    git_act = {"first_commit": "2026-07-21", "last_commit": "2026-07-21",
               "bursts": [{"from": "2026-07-21", "to": "2026-07-21"}]}
    early = date(2026, 5, 16)

    # WITHOUT a curated anchor: a 2026-05-16 thread is >14d before 07-21 -> hard 0.0
    tp = ba.time_plausibility(early, dict(git_act, bursts=[dict(b) for b in git_act["bursts"]]))
    if tp != 0.0:
        v.append(f"first_seen: baseline should hard-zero the early thread, got {tp}")

    # WITH the curated anchor folded in: window widens to 2026-05-16, thread in-burst
    widened = ba.apply_first_seen(dict(git_act, bursts=[dict(b) for b in git_act["bursts"]]),
                                  "2026-05-16")
    if widened.get("first_seen") != "2026-05-16":
        v.append(f"first_seen: apply_first_seen should record 2026-05-16, got {widened.get('first_seen')}")
    if widened.get("first_commit") != "2026-07-21":
        v.append("first_seen: git first_commit must be preserved for provenance")
    if widened["bursts"][0]["from"] != "2026-05-16":
        v.append(f"first_seen: earliest burst should widen to 2026-05-16, got {widened['bursts'][0]['from']}")
    tp2 = ba.time_plausibility(early, widened)
    if tp2 <= 0.0:
        v.append(f"first_seen: early thread should NOT be zeroed after widening, got {tp2}")

    # a curated anchor LATER than git changes nothing (min semantics, never narrows)
    later = ba.apply_first_seen(dict(git_act, bursts=[dict(b) for b in git_act["bursts"]]),
                               "2026-09-01")
    if later.get("first_seen") != "2026-07-21":
        v.append(f"first_seen: a later anchor must not narrow the window, got {later.get('first_seen')}")

    # curated first_seen cascades from a project to its repos
    reg = {"projects": [{"id": "proj-x", "canonical_name": "X", "first_seen": "2026-05-16",
                         "repos": [{"id": "repo-x", "canonical_name": "Xr"}]}]}
    with tempfile.TemporaryDirectory() as td:
        gp = Path(td) / "groups.json"
        gp.write_text(json.dumps(reg), encoding="utf-8")
        m = ba.load_curated_first_seen(gp)
        if m.get("proj-x") != "2026-05-16" or m.get("repo-x") != "2026-05-16":
            v.append(f"first_seen: project anchor must cascade to repos, got {m}")

    return v
