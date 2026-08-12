"""tester_candidates: the real-data adapter -- candidates_from_curator
turning ratified-map + claims.json + knowledge_index.json + K2's cache +
real conversations + the calibration ledger into ProjectCandidate objects.

Hermetic: builds synthetic Conversation objects directly (same technique
tester_extract_claims.py uses) so no real store walk or LM Studio is needed.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from chronicler.pipeline import extract_claims as k2
from chronicler.pipeline import local_transcripts as lt
from chronicler.review import candidates as cd
from chronicler.review import planner as pl


def _row(session_id: str, project_id: str) -> dict:
    """`map_rows` entries are plain dicts, exactly `curator_data.
    ratified_map_rows()`'s own real shape -- not a bespoke object (a real
    bug this dict shape catches: an earlier draft read `row.session_id`
    attribute-style, which silently worked against a fabricated test
    object but would have broken the first time this ran against the
    real ratified map's actual dict rows)."""
    return {"session_id": session_id, "project_id": project_id}


def run() -> list[str]:
    v: list[str] = []

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)

        def make_conv(conv_id: str, text: str, ts: str) -> lt.Conversation:
            path = td / f"{conv_id}.jsonl"
            path.write_text("{}\n", encoding="utf-8")
            sess = lt.ParsedSession(
                thread_id=conv_id, store="cowork", encoded_cwd="C--out", path=path,
                conversation_id=conv_id, messages=[(0, "user", text, ts, "u1")],
                created_at=ts, updated_at=ts,
            )
            return lt.Conversation(conversation_id=conv_id, sessions=[sess],
                                     real_time=ts, real_time_source="last_message_timestamp")

        conv_a1 = make_conv("local_a1", "Project A conversation one, some real content here.",
                              "2026-07-20T10:00:00Z")
        conv_a2 = make_conv("local_a2", "Project A conversation two, more content for sizing.",
                              "2026-07-19T10:00:00Z")
        conv_b1 = make_conv("local_b1", "Project B's only conversation, short.", "2026-07-18T10:00:00Z")

        map_rows = [_row("local_a1", "proj-a"), _row("local_a2", "proj-a"), _row("local_b1", "proj-b")]

        claims_report = {
            "conversations": [
                {"conversation_id": "local_a1", "claims": [{"claim_text": "x"}, {"claim_text": "y"}]},
                {"conversation_id": "local_a2", "claims": []},
                {"conversation_id": "local_b1", "claims": [{"claim_text": "z"}]},
            ]
        }

        knowledge_index = {
            "projects": [
                {"project_id": "proj-a", "conversations": ["local_a1", "local_a2"]},
                {"project_id": "proj-b", "conversations": ["local_b1"]},
            ]
        }

        # --- minimal call: only map_rows + claims_report + knowledge_index.
        #     changed_conversations and estimated_seconds stay at their
        #     honest defaults (0, None) -- no real conversations/cache/ledger
        #     were given to compute them from --------------------------------
        minimal = cd.candidates_from_curator(
            map_rows=map_rows, claims_report=claims_report, knowledge_index=knowledge_index)
        by_id = {c.project_id: c for c in minimal}
        if set(by_id) != {"proj-a", "proj-b"}:
            v.append(f"candidates_from_curator should produce one candidate per project "
                     f"in map_rows: {set(by_id)}")
        if by_id["proj-a"].claim_count != 2:
            v.append(f"proj-a's claim_count should sum claims.json's conversations "
                     f"(2 + 0 = 2): {by_id['proj-a'].claim_count}")
        if by_id["proj-b"].claim_count != 1:
            v.append(f"proj-b's claim_count should be 1: {by_id['proj-b'].claim_count}")
        if by_id["proj-a"].message_count != 2:
            v.append(f"proj-a's breadth proxy (conversation count via knowledge_index) "
                     f"should be 2: {by_id['proj-a'].message_count}")
        if by_id["proj-b"].message_count != 1:
            v.append(f"proj-b's breadth proxy should be 1: {by_id['proj-b'].message_count}")
        if by_id["proj-a"].changed_conversations != 0 or by_id["proj-a"].estimated_seconds is not None:
            v.append(f"omitting real conversations/cache should leave "
                     f"changed_conversations=0 and estimated_seconds=None, never guessed: "
                     f"{by_id['proj-a']}")

        # --- knowledge_index absent -> falls back to counting map_rows,
        #     never zero just because K1 hasn't run --------------------------
        no_k1 = cd.candidates_from_curator(map_rows=map_rows, claims_report=claims_report,
                                             knowledge_index=None)
        no_k1_by_id = {c.project_id: c for c in no_k1}
        if no_k1_by_id["proj-a"].message_count != 2 or no_k1_by_id["proj-b"].message_count != 1:
            v.append(f"with knowledge_index=None, breadth should fall back to counting "
                     f"map_rows per project: proj-a={no_k1_by_id['proj-a'].message_count} "
                     f"proj-b={no_k1_by_id['proj-b'].message_count}")

        # --- claims_report absent -> claim_count 0 everywhere, never crashes -
        no_claims = cd.candidates_from_curator(map_rows=map_rows, claims_report=None,
                                                 knowledge_index=knowledge_index)
        if any(c.claim_count != 0 for c in no_claims):
            v.append("with claims_report=None every claim_count should be 0, not guessed")

        # --- real conversations + cache: changed_conversations reflects
        #     K2's OWN cache-identity check (source_identity), reused not
        #     reimplemented -- an unchanged conversation (cache hit) does
        #     NOT count as changed ------------------------------------------
        cache = {
            "local_a1": {"sources": k2.source_identity(conv_a1)},  # unchanged
            # local_a2 not in cache at all -> changed
            # local_b1 in cache but with STALE sources -> changed
            "local_b1": {"sources": [["some/other/path.jsonl", 0.0]]},
        }
        with_conv = cd.candidates_from_curator(
            map_rows=map_rows, claims_report=claims_report, knowledge_index=knowledge_index,
            k2_cache=cache, conversations=[conv_a1, conv_a2, conv_b1])
        with_conv_by_id = {c.project_id: c for c in with_conv}
        if with_conv_by_id["proj-a"].changed_conversations != 1:
            v.append(f"proj-a should show exactly 1 changed conversation (a2, not cached "
                     f"at all -- a1 is a clean cache hit): "
                     f"{with_conv_by_id['proj-a'].changed_conversations}")
        if with_conv_by_id["proj-b"].changed_conversations != 1:
            v.append(f"proj-b's b1 has stale cached sources -> counts as changed: "
                     f"{with_conv_by_id['proj-b'].changed_conversations}")
        # still no ledger/model_id given -> still no estimate, even with real
        # conversations available (sizing needs BOTH pieces)
        if with_conv_by_id["proj-a"].estimated_seconds is not None:
            v.append("real conversations without ledger_entries/model_id should still "
                     "leave estimated_seconds=None -- both pieces are required together")

        # --- full pipeline: ledger + model_id -> a real estimate, scaled by
        #     the ACTUAL token count of the changed conversations only -------
        ledger_entries = [
            {"model_id": "m1", "stage": "K2", "cool_down_preceded": False,
             "generation_ms_per_token": 20.0},
            {"model_id": "m1", "stage": "K2", "cool_down_preceded": False,
             "generation_ms_per_token": 20.0},
        ]
        full = cd.candidates_from_curator(
            map_rows=map_rows, claims_report=claims_report, knowledge_index=knowledge_index,
            k2_cache=cache, conversations=[conv_a1, conv_a2, conv_b1],
            ledger_entries=ledger_entries, model_id="m1", stage="K2")
        full_by_id = {c.project_id: c for c in full}
        expected_tokens_a = k2.approx_token_count(k2.full_transcript_text(conv_a2))  # only a2 changed
        expected_seconds_a = 20.0 * expected_tokens_a / 1000.0
        if (full_by_id["proj-a"].estimated_seconds is None
                or abs(full_by_id["proj-a"].estimated_seconds - expected_seconds_a) > 1e-6):
            v.append(f"proj-a's estimated_seconds should be median ms/token (20.0) * "
                     f"a2's ACTUAL token count / 1000 = {expected_seconds_a}, got "
                     f"{full_by_id['proj-a'].estimated_seconds}")
        # proj-a's UNCHANGED conversation (a1) must not contribute to the
        # estimate -- a cache hit costs nothing on a re-run
        if full_by_id["proj-a"].estimated_seconds >= 20.0 * (
                k2.approx_token_count(k2.full_transcript_text(conv_a1))
                + expected_tokens_a) / 1000.0:
            v.append("estimated_seconds must only account for CHANGED conversations, "
                     "never the cache hit too")

        # --- no calibration for this model at all -> None, plainly ----------
        no_calibration = cd.candidates_from_curator(
            map_rows=map_rows, claims_report=claims_report, knowledge_index=knowledge_index,
            k2_cache=cache, conversations=[conv_a1, conv_a2, conv_b1],
            ledger_entries=[], model_id="m1", stage="K2")
        if any(c.estimated_seconds is not None for c in no_calibration):
            v.append("an empty ledger should leave every estimated_seconds at None, "
                     "never a fabricated number")

        # --- the resulting candidates are exactly what build_plan already
        #     expects -- an end-to-end sanity check, not a re-test of
        #     planner.py's own logic (covered exhaustively in tester_planner.py) -
        plan = pl.build_plan(full, policy="coverage", profile_name="default")
        if len(plan.steps) != 2:
            v.append(f"the adapter's output should build a valid unbudgeted plan over "
                     f"both projects: {plan.steps}")

    return v
