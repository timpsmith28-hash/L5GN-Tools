"""tester_relink_scoring: the S6 scoring fixes (relink_scoring brief A/B/C/E).

Hermetic: drives relink.combine / relink.decide / relink.load_registry with
synthetic signals and a temp registry -- no DB, no network, no live vault. Proves
the co-origin collapse (A), the corroboration gate on auto-link (B), the
distinct-origin count cap (C), and the no-synthetic-repo_folder_path rule (E).
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

_PIPE = Path(__file__).resolve().parent.parent / "chronicler" / "pipeline"


def _sig(signal, weight, detail, origin=None):
    return {"id": None, "signal": signal, "weight": weight,
            "detail": detail, "origin": origin}


def _cand(project, adjusted, origins, second_score=None):
    return {"project": project, "adjusted": adjusted, "score": adjusted,
            "origins": origins, "used": [], "evidence_ids": [],
            "summary": f"{project} adj={adjusted} origins={origins}"}


def run() -> list[str]:
    v: list[str] = []
    if str(_PIPE) not in sys.path:
        sys.path.insert(0, str(_PIPE))
    import relink

    # --- Task A: three signals naming the SAME origin collapse to one -------
    s = [_sig("filename_xref", 0.97, "world_graph.json"),
         _sig("path_mention", 0.90, "world_graph.json"),
         _sig("name_alias", 0.80, "world_graph@title")]
    score, used, n = relink.combine(s)
    if n != 1:
        v.append(f"A: co-origin signals should be 1 origin, got {n}")
    if not (0.965 <= score <= 0.975):
        v.append(f"A: co-origin score should be ~0.97 (single capped signal), got {score:.4f}")
    if len(used) != 1:
        v.append(f"A: co-origin should leave 1 used signal, got {len(used)}")

    # name_alias + path_mention on the same repo-name token also collapse
    s = [_sig("name_alias", 0.60, "l5gn_armory_v4@body"),
         _sig("path_mention", 0.90, "L5GN_Armory_v4")]
    score, used, n = relink.combine(s)
    if n != 1 or not (0.895 <= score <= 0.905):
        v.append(f"A: repo-name co-origin should be 1 origin ~0.90, got n={n} score={score:.4f}")

    # --- Task A (negative): three DISTINCT origins stay independent --------
    s = [_sig("filename_xref", 0.97, "alpha.py"),
         _sig("filename_xref", 0.97, "beta.py"),
         _sig("filename_xref", 0.97, "gamma.py")]
    score, used, n = relink.combine(s)
    if n != 3:
        v.append(f"A: three distinct files should be 3 origins, got {n}")
    if score < 0.99:
        v.append(f"A: three distinct owned files should still combine high, got {score:.4f}")

    # --- Task C: distinct-origin hits of one type are capped ---------------
    cap = relink.SIGNAL_COUNT_CAP.get("filename_xref")
    if not cap:
        v.append("C: filename_xref has no SIGNAL_COUNT_CAP entry")
    else:
        s = [_sig("filename_xref", 0.90 + i * 0.001, f"file{i}.py")
             for i in range(cap + 3)]
        score, used, n = relink.combine(s)
        if len(used) != cap:
            v.append(f"C: {cap + 3} distinct files should cap to {cap} used, got {len(used)}")
        # the strongest cap_n must be the ones kept
        kept = sorted(u["weight"] for u in used)
        if kept and min(kept) <= 0.90 + (2) * 0.001 - 1e-9:
            v.append("C: cap did not keep the strongest N by weight")

    # --- Task B: one origin -> suggest; >=2 origins -> auto_link ------------
    fake = {"thread_id": "t1", "title": "x", "created_at": None,
            "project_link": None, "project_confidence": None}

    d = relink.decide(fake, [_cand("p1", 0.97, 1)], None, {})
    if d["category"] != "suggest" or not d.get("single_origin"):
        v.append(f"B: single-origin 0.97 should be a single_origin suggest, got {d['category']}")

    d = relink.decide(fake, [_cand("p1", 0.95, 2), _cand("p2", 0.40, 1)], None, {})
    if d["category"] != "auto_link":
        v.append(f"B: two-origin clear winner should auto_link, got {d['category']}")

    # rivals still ambiguous (unchanged behaviour)
    d = relink.decide(fake, [_cand("p1", 0.95, 2), _cand("p2", 0.92, 2)], None, {})
    if d["category"] != "ambiguous":
        v.append(f"B: two close strong rivals should stay ambiguous, got {d['category']}")

    if relink.MIN_AUTOLINK_ORIGINS < 2:
        v.append("B: MIN_AUTOLINK_ORIGINS must be >= 2 (one sentence must not lock)")

    # --- Task E: no on-disk path -> repo_folder_path is NULL, not synthetic --
    reg = {"programs": [{"id": "prog", "name": "Prog", "scope": "l5gn"}],
           "projects": [{"id": "proj-x", "canonical_name": "ProjX",
                         "program": "prog", "scope": "l5gn", "aliases": []}]}
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "project_registry.json"
        p.write_text(json.dumps(reg), encoding="utf-8")
        orig = relink.REGISTRY_PATH
        try:
            relink.REGISTRY_PATH = p
            targets = relink.load_registry()
        finally:
            relink.REGISTRY_PATH = orig
        rfp = targets["proj-x"]["repo_folder_path"]
        if rfp is not None:
            v.append(f"E: project with no on-disk path must upsert repo_folder_path NULL, got {rfp!r}")
        if "L5GN/ProjX" in (str(rfp) or ""):
            v.append("E: synthetic <scope>/<canon> path must not be written")

    return v
