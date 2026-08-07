"""match_claims (K4): two-stage match (shortlist by similarity, confirm via
a stub model call with the matched span quoted back), newest-first
supersession, and the four outcomes (captured / gap / superseded /
cross-project).

Hermetic: drives `match_claims()` directly against synthetic claims and a
synthetic corpus index, with a STUB caller -- no LM Studio instance
required.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def run() -> list[str]:
    v: list[str] = []
    _PIPE = Path(__file__).resolve().parent.parent / "chronicler" / "pipeline"
    if str(_PIPE) not in sys.path:
        sys.path.insert(0, str(_PIPE))
    import match_claims as k4

    corpus_index = {
        "projects": [
            {
                "project_id": "proj-a",
                "files": [{
                    "file": "A_KNOWLEDGE.md",
                    "chunks": [
                        {"heading": "Pricing tiers", "text":
                         "The free tier is capped at 3 seats per workspace."},
                    ],
                }],
            },
            {
                "project_id": "proj-b",
                "files": [{
                    "file": "B_KNOWLEDGE.md",
                    "chunks": [
                        {"heading": "Renewal", "text":
                         "Annual renewal notices go out 30 days before expiry."},
                    ],
                }],
            },
        ],
    }

    # --- claims, newest-first as K2 would already have ordered them --------
    claims = [
        # captured: matches proj-a's own corpus.
        {"project_id": "proj-a", "conversation_id": "c-newest", "real_time": "2026-08-01T00:00:00Z",
         "claim_text": "Free tier seat cap is 3", "quoted_source": "cap is three seats"},
        # establishes the NEWEST truth on churn threshold for proj-a.
        {"project_id": "proj-a", "conversation_id": "c-new2", "real_time": "2026-07-25T00:00:00Z",
         "claim_text": "Churn threshold is now set to 15 percent", "quoted_source": "we moved churn to 15%"},
        # older, conflicting claim on the SAME topic -> should supersede.
        {"project_id": "proj-a", "conversation_id": "c-old", "real_time": "2026-07-01T00:00:00Z",
         "claim_text": "Churn threshold is set to 10 percent", "quoted_source": "churn threshold is 10%"},
        # cross-project: not in proj-a's own corpus, but confirmed in proj-b's.
        {"project_id": "proj-a", "conversation_id": "c-cross", "real_time": "2026-07-20T00:00:00Z",
         "claim_text": "Renewal notices fire 30 days ahead", "quoted_source": "renewal reminder at 30 days"},
        # a genuine gap: nothing supports it anywhere, no established topic match.
        {"project_id": "proj-a", "conversation_id": "c-gap", "real_time": "2026-07-15T00:00:00Z",
         "claim_text": "Support SLA response time is 4 business hours", "quoted_source": "SLA is 4 hours"},
    ]

    def stub_caller(prompt: str, *, system: str, endpoint: str, model: str, temperature: float) -> str:
        if system == k4.CONFIRM_CHUNK_SYSTEM:
            # Only the two claims that are ACTUALLY about that candidate's
            # topic should confirm -- matching on the CLAIM half of the
            # prompt, never on the candidate passage alone (every proj-a
            # candidate mentions "cap"/"seats", so matching on the passage
            # would confirm every claim against it, which is exactly the
            # false-positive this stub must not produce).
            claim_part = prompt.split("CANDIDATE PASSAGE:")[0]
            if "Free tier seat cap is 3" in claim_part:
                return json.dumps({"confirmed": True,
                                     "matched_span": "capped at 3 seats per workspace"})
            if "Renewal notices fire 30 days ahead" in claim_part:
                return json.dumps({"confirmed": True,
                                     "matched_span": "renewal notices go out 30 days before expiry"})
            return json.dumps({"confirmed": False, "matched_span": ""})
        if system == k4.CONFIRM_SUPERSEDE_SYSTEM:
            if "10 percent" in prompt and "15 percent" in prompt:
                return json.dumps({"conflicts": True, "matched_span": "we moved churn to 15%"})
            return json.dumps({"conflicts": False, "matched_span": ""})
        return "{}"

    result = k4.match_claims(claims, corpus_index, caller=stub_caller, endpoint="x",
                               model="test-model", temperature=0.0)
    by_conv = {c["conversation_id"]: c for c in result["claims"]}

    # --- captured -----------------------------------------------------------
    if by_conv["c-newest"]["outcome"] != "captured":
        v.append(f"seat-cap claim should be captured: {by_conv['c-newest']}")
    if not by_conv["c-newest"]["confirm"] or not by_conv["c-newest"]["confirm"]["span_verified"]:
        v.append("captured claim's confirm result should carry a verified literal span")
    if not by_conv["c-newest"]["shortlist"]:
        v.append("captured claim should carry its shortlist (both score and verdict must be kept)")

    # --- newest churn claim: not in corpus, no newer established claim to
    #     conflict with (it IS the newest) -> gap, and becomes 'established'.
    if by_conv["c-new2"]["outcome"] != "gap":
        v.append(f"newest churn-threshold claim (nothing newer to conflict with) should be gap: "
                  f"{by_conv['c-new2']}")

    # --- superseded -----------------------------------------------------------
    old = by_conv["c-old"]
    if old["outcome"] != "superseded":
        v.append(f"older conflicting churn claim should be superseded: {old}")
    if not old["supersedes"] or old["supersedes"].get("newer_conversation_id") != "c-new2":
        v.append(f"superseded claim should name the newer conversation it was superseded by: {old}")
    if old["supersedes"] and "15%" not in old["supersedes"].get("matched_span", ""):
        v.append(f"superseded record should carry the newer claim's literal quoted span: {old}")

    # --- cross-project ----------------------------------------------------
    cross = by_conv["c-cross"]
    if cross["outcome"] != "cross-project":
        v.append(f"renewal claim should be cross-project (found in proj-b): {cross}")
    if cross["supersedes"] is None or cross["supersedes"].get("found_in_project") != "proj-b":
        v.append(f"cross-project record should name which project it was found in: {cross}")

    # --- gap ----------------------------------------------------------------
    gap = by_conv["c-gap"]
    if gap["outcome"] != "gap":
        v.append(f"SLA claim with no support anywhere should be gap: {gap}")

    # --- similarity() and shortlist() ---------------------------------------
    if k4.similarity("hello world", "hello world") != 1.0:
        v.append("similarity() of identical strings should be 1.0")
    if k4.similarity("completely different", "unrelated text entirely") > 0.6:
        v.append("similarity() of unrelated strings should be well below 0.6")

    chunks = [{"file": "f.md", "heading": "h1", "text": "the quick brown fox"},
              {"file": "f.md", "heading": "h2", "text": "totally unrelated content here"}]
    short = k4.shortlist("the quick brown fox jumps", chunks, k=1)
    if len(short) != 1 or short[0]["heading"] != "h1":
        v.append(f"shortlist() did not rank the closer chunk first: {short}")
    if "shortlist_score" not in short[0]:
        v.append("shortlist() must attach the score, not just the winning chunk")

    # --- span verification is never trusted from the model's own say-so ----
    def lying_caller(prompt, *, system, endpoint, model, temperature):
        # claims confirmed but the span is NOT actually in the candidate text.
        return json.dumps({"confirmed": True, "matched_span": "this text does not appear anywhere"})
    res = k4.confirm_chunk("some claim", "the actual candidate passage text",
                             caller=lying_caller, endpoint="x", model="m", temperature=0.0)
    if res["confirmed"] or res["span_verified"]:
        v.append("confirm_chunk trusted a 'confirmed: true' whose matched_span was not a "
                  "literal substring of the candidate -- span verification must never be "
                  "downgraded to trusting the model")

    # --- flatten_claims: attaches project via the ratified map -------------
    claims_report = {
        "conversations": [
            {"conversation_id": "local_x", "real_time": "2026-07-01T00:00:00Z",
             "claims": [{"claim_text": "t", "quoted_source": "q"}]},
            {"conversation_id": "local_unmapped", "real_time": "2026-07-02T00:00:00Z",
             "claims": [{"claim_text": "orphan", "quoted_source": "o"}]},
        ],
    }
    flat = k4.flatten_claims(claims_report, {"local_x": "proj-a"})
    if len(flat) != 1 or flat[0]["project_id"] != "proj-a":
        v.append(f"flatten_claims should drop conversations with no project mapping "
                  f"and attach project_id for the rest: {flat}")

    return v
