"""compile_report (K5): assembles data/knowledge_curator/report_<date>.md
from K1/K2/K4's outputs. Never writes under docs/ (0030). Checks the five
sections appear in order, the header carries provenance so a thin run reads
as thin, recurrence ranking for no-knowledge-file projects, and that the
superseded section says so plainly when it never fired.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path


def run() -> list[str]:
    v: list[str] = []
    _PIPE = Path(__file__).resolve().parent.parent / "chronicler" / "pipeline"
    if str(_PIPE) not in sys.path:
        sys.path.insert(0, str(_PIPE))
    import compile_report as k5

    claims_report = {
        "run_timestamp": "2026-08-07T12:00:00+00:00",
        "model_id": "test-model", "endpoint": "http://x",
        "conversations_scanned": 5,
        "conversations_excluded_no_timestamp": [{"conversation_id": "local_ghost", "reason": "x"}],
        "claims_extracted": 6, "claims_rejected": 1, "quote_rejection_rate": 1 / 7,
    }
    knowledge_index = {
        "projects": [
            {"project_id": "proj-with-kf", "local_folder": "MCF/A", "knowledge_files": ["A_KNOWLEDGE.md"]},
            {"project_id": "proj-no-kf", "local_folder": "MCF/B", "knowledge_files": []},
        ],
        "unresolved": [{"project_id": "proj-ghost", "state": "mapped but folder absent on this machine",
                          "detail": "x"}],
    }
    matches_report = {
        "run_timestamp": "2026-08-07T12:00:00+00:00", "model_id": "test-model", "endpoint": "http://x",
        "claims": [
            {"project_id": "proj-with-kf", "conversation_id": "c1", "real_time": "2026-08-01T00:00:00Z",
             "claim_text": "Formalized claim", "quoted_source": "q1", "outcome": "captured",
             "shortlist": [], "confirm": {}, "supersedes": None},
            {"project_id": "proj-with-kf", "conversation_id": "c2", "real_time": "2026-08-02T00:00:00Z",
             "claim_text": "Gap claim about deploy cadence", "quoted_source": "q2", "outcome": "gap",
             "shortlist": [], "confirm": None, "supersedes": None},
            {"project_id": "proj-no-kf", "conversation_id": "c3", "real_time": "2026-07-01T00:00:00Z",
             "claim_text": "We use blue-green deploys for the B service", "quoted_source": "q3",
             "outcome": "gap", "shortlist": [], "confirm": None, "supersedes": None},
            {"project_id": "proj-no-kf", "conversation_id": "c4", "real_time": "2026-07-15T00:00:00Z",
             "claim_text": "We use blue-green deploys for the B service always", "quoted_source": "q4",
             "outcome": "gap", "shortlist": [], "confirm": None, "supersedes": None},
            {"project_id": "proj-no-kf", "conversation_id": "c5", "real_time": "2026-07-20T00:00:00Z",
             "claim_text": "Totally unrelated one-off remark about lunch", "quoted_source": "q5",
             "outcome": "gap", "shortlist": [], "confirm": None, "supersedes": None},
            {"project_id": "proj-with-kf", "conversation_id": "c6", "real_time": "2026-07-05T00:00:00Z",
             "claim_text": "Renewal window is thirty days", "quoted_source": "q6", "outcome": "cross-project",
             "shortlist": [], "confirm": {}, "supersedes": {"found_in_project": "proj-no-kf", "chunk": "x#y"}},
        ],
    }

    report_md = k5.compile_report(claims_report, matches_report, knowledge_index)

    # --- header carries provenance ------------------------------------------
    for expected in ["run timestamp:", "model id: test-model", "conversations scanned: 5",
                       "claims extracted: 6", "claims rejected", "projects covered: 2",
                       "projects unresolved: 1"]:
        if expected not in report_md:
            v.append(f"header missing {expected!r}")

    # --- section order ----------------------------------------------------
    section_titles = ["## 1. Not yet formalized", "## 2. No knowledge file yet",
                        "## 3. Cross-project relevance", "## 4. Superseded",
                        "## 5. Confirmed captured"]
    positions = [report_md.find(t) for t in section_titles]
    if any(p == -1 for p in positions):
        v.append(f"a required section header is missing: {list(zip(section_titles, positions))}")
    if positions != sorted(positions):
        v.append("sections are not in the brief's required order")

    # --- section 1: gaps only for projects that already have a knowledge file
    sec1 = report_md[positions[0]:positions[1]]
    if "Gap claim about deploy cadence" not in sec1:
        v.append("section 1 should include a gap for a project that HAS a knowledge file")
    if "blue-green deploys" in sec1:
        v.append("section 1 must not include gaps for a project with NO knowledge file "
                  "(that belongs in section 2's starter list, not a raw gap dump)")

    # --- section 2: recurrence-ranked starter list, not a raw dump -----------
    sec2 = report_md[positions[1]:positions[2]]
    if "recurred across 2 conversation" not in sec2:
        v.append(f"the two similar blue-green-deploy claims should cluster and show "
                  f"recurrence across 2 conversations: {sec2!r}")
    if "proj-no-kf" not in sec2:
        v.append("section 2 should be scoped to the no-knowledge-file project")

    # --- section 3: cross-project --------------------------------------------
    sec3 = report_md[positions[2]:positions[3]]
    if "Renewal window is thirty days" not in sec3 or "proj-no-kf" not in sec3:
        v.append(f"section 3 should show the cross-project claim and where it was found: {sec3!r}")

    # --- section 4: superseded never fired this run -> says so plainly -------
    sec4 = report_md[positions[3]:positions[4]]
    if "did not fire" not in sec4:
        v.append("section 4 should say plainly that the superseded path did not fire, "
                  "not just render an empty section")

    # --- section 5: confirmed captured ---------------------------------------
    sec5 = report_md[positions[4]:]
    if "Formalized claim" not in sec5 or "proj-with-kf" not in sec5:
        v.append(f"section 5 should list the captured claim under its project: {sec5!r}")

    # --- cluster_claims: recurrence grouping in isolation ---------------------
    clusters = k5.cluster_claims([
        {"claim_text": "The API rate limit is 100 requests per minute", "quoted_source": "q",
         "conversation_id": "x1", "real_time": "2026-07-01T00:00:00Z"},
        {"claim_text": "API rate limit is 100 requests per minute now", "quoted_source": "q",
         "conversation_id": "x2", "real_time": "2026-07-05T00:00:00Z"},
        {"claim_text": "Totally different topic about billing cycles", "quoted_source": "q",
         "conversation_id": "x3", "real_time": "2026-07-10T00:00:00Z"},
    ])
    if clusters[0]["conversation_count"] != 2:
        v.append(f"cluster_claims should group the two similar claims (2 conversations): {clusters}")
    if len(clusters) != 2:
        v.append(f"cluster_claims should keep the unrelated claim as its own cluster: {clusters}")

    # --- out_path_for uses the run date, never docs/ --------------------------
    out_path = k5.out_path_for("2026-08-07T12:00:00+00:00")
    if "docs" in out_path.parts:
        v.append(f"report path must never live under docs/ (0030): {out_path}")
    if out_path.name != "report_2026-08-07.md":
        v.append(f"out_path_for did not derive the date from run_timestamp: {out_path}")

    # --- main() writes the file, read-only on inputs --------------------------
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        out = td / "report_2026-08-07.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report_md, encoding="utf-8")
        if not out.exists() or "## 1. Not yet formalized" not in out.read_text(encoding="utf-8"):
            v.append("report file did not round-trip correctly")

    return v
