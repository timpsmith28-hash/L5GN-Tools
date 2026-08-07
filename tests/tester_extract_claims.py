"""extract_claims (K2): newest-first claim extraction with literal-substring
quote verification, rejection counting, zero-claim recording, and a
source-identity cache.

Hermetic: builds synthetic Conversation objects directly (no real store
walk needed -- K1/K0 are exercised by their own testers) and drives
`run_extraction` / `extract_for_conversation` with a STUB caller that never
touches the network, so no LM Studio instance is required to run this gate.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


def run() -> list[str]:
    v: list[str] = []
    _PIPE = Path(__file__).resolve().parent.parent / "chronicler" / "pipeline"
    if str(_PIPE) not in sys.path:
        sys.path.insert(0, str(_PIPE))
    import extract_claims as k2
    import local_transcripts as lt

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

        conv_new = make_conv("local_new", "We decided to cap the free tier at 3 seats.", "2026-07-20T10:00:00Z")
        conv_old = make_conv("local_old", "We are still deciding on the seat cap.", "2026-07-01T10:00:00Z")
        conv_zero = make_conv("local_zero", "Just chit-chat, nothing to record.", "2026-07-05T10:00:00Z")

        # --- caller stub: literal quote for conv_new, a FABRICATED (non-
        #     literal) quote for conv_old, empty array for conv_zero -------
        calls = []

        def stub_caller(text, *, endpoint, model, temperature):
            calls.append(text)
            if "cap the free tier" in text:
                return json.dumps([
                    {"claim_text": "Free tier is capped at 3 seats",
                     "quoted_source": "We decided to cap the free tier at 3 seats."},
                ])
            if "still deciding" in text:
                return json.dumps([
                    {"claim_text": "Seat cap fabricated as decided",
                     "quoted_source": "We decided the seat cap is five."},  # NOT in transcript
                ])
            return "[]"

        # --- extract_for_conversation: accept + reject paths -----------------
        r_new = k2.extract_for_conversation(conv_new, caller=stub_caller, endpoint="x", model="m", temperature=0.0)
        if len(r_new.claims) != 1 or r_new.claims[0].quoted_source not in k2.full_transcript_text(conv_new):
            v.append(f"literal quote should be accepted: {r_new}")
        if r_new.rejected:
            v.append(f"conv_new should have zero rejections: {r_new.rejected}")
        if r_new.scanned_with_zero:
            v.append("conv_new produced a claim but was marked scanned_with_zero")

        r_old = k2.extract_for_conversation(conv_old, caller=stub_caller, endpoint="x", model="m", temperature=0.0)
        if r_old.claims:
            v.append(f"fabricated (non-literal) quote must be rejected, not accepted: {r_old.claims}")
        if len(r_old.rejected) != 1 or "literal substring" not in r_old.rejected[0]["reason"]:
            v.append(f"rejection reason should name the literal-substring rule: {r_old.rejected}")
        if not r_old.scanned_with_zero:
            v.append("conv_old with zero ACCEPTED claims should be scanned_with_zero")

        r_zero = k2.extract_for_conversation(conv_zero, caller=stub_caller, endpoint="x", model="m", temperature=0.0)
        if not r_zero.scanned_with_zero or r_zero.claims or r_zero.rejected:
            v.append(f"conv_zero (model returned []) should be scanned-with-zero, "
                      f"never omitted: {r_zero}")

        # --- malformed JSON from the model: parse_failed, not a crash --------
        def broken_caller(text, **kw):
            return "not json at all, sorry"
        r_broken = k2.extract_for_conversation(conv_new, caller=broken_caller, endpoint="x", model="m", temperature=0.0)
        if not r_broken.parse_failed or not r_broken.scanned_with_zero:
            v.append(f"unparseable model output should set parse_failed + scanned_with_zero: {r_broken}")

        # --- run_extraction: newest-first ordering, excluded named, cache ----
        included, excluded = lt.order_newest_first([conv_new, conv_old, conv_zero])
        cache: dict = {}
        report = k2.run_extraction(
            included, excluded, caller=stub_caller, endpoint="x", model="test-model",
            temperature=0.0, cache=cache,
        )
        order = [c["conversation_id"] for c in report["conversations"]]
        if order != ["local_new", "local_zero", "local_old"]:
            v.append(f"run_extraction did not process/report newest-first: {order}")
        if report["model_id"] != "test-model" or "run_timestamp" not in report:
            v.append("provenance (model_id/run_timestamp) missing from report")
        if report["claims_extracted"] != 1 or report["claims_rejected"] != 1:
            v.append(f"aggregate claim/rejection counts wrong: "
                      f"{report['claims_extracted']=} {report['claims_rejected']=}")
        expected_rate = 1 / 2
        if abs(report["quote_rejection_rate"] - expected_rate) > 1e-9:
            v.append(f"quote_rejection_rate wrong: {report['quote_rejection_rate']}")
        if report["conversations_reextracted"] != 3 or report["conversations_from_cache"] != 0:
            v.append(f"first run should re-extract all 3, cache 0: {report}")

        # --- an excluded (unresolvable-timestamp) conversation is named, never
        #     silently dropped -----------------------------------------------
        ghost = lt.Conversation(conversation_id="local_ghost", sessions=[],
                                 real_time=None, real_time_source=None,
                                 excluded=True, exclude_reason="no resolvable timestamp: test")
        report2 = k2.run_extraction([], [ghost], caller=stub_caller, endpoint="x",
                                      model="test-model", temperature=0.0, cache={})
        named = report2["conversations_excluded_no_timestamp"]
        if len(named) != 1 or named[0]["conversation_id"] != "local_ghost":
            v.append(f"excluded conversation not named in the report: {named}")

        # --- cache: re-run with nothing changed re-extracts ZERO -------------
        report3 = k2.run_extraction(
            included, excluded, caller=stub_caller, endpoint="x", model="test-model",
            temperature=0.0, cache=cache,  # same cache dict, mutated by the first run
        )
        if report3["conversations_reextracted"] != 0 or report3["conversations_from_cache"] != 3:
            v.append(f"re-run with nothing changed should re-extract 0: {report3}")
        if report3["claims_extracted"] != 1 or report3["claims_rejected"] != 1:
            v.append("cached re-run produced different aggregate counts than the live run")
        # conv_new's text was already called twice before this point (the
        # direct extract_for_conversation call, then run_extraction's first
        # pass) -- the cached re-run (report3) must add no THIRD call.
        calls_before_cached_rerun = calls.count(k2.full_transcript_text(conv_new))
        k2.run_extraction(included, excluded, caller=stub_caller, endpoint="x",
                           model="test-model", temperature=0.0, cache=cache)
        if calls.count(k2.full_transcript_text(conv_new)) != calls_before_cached_rerun:
            v.append("the stub model was called again for a conversation the cache should "
                      "have served -- caching is not actually skipping the call")

        # --- cache invalidates when a source file's mtime changes ------------
        import os
        import time
        target_path = conv_new.sessions[0].path
        time.sleep(0.01)
        target_path.write_text("{}\nchanged\n", encoding="utf-8")
        report4 = k2.run_extraction(
            [conv_new], [], caller=stub_caller, endpoint="x", model="test-model",
            temperature=0.0, cache=cache,
        )
        if report4["conversations_reextracted"] != 1:
            v.append("a changed source file's mtime should invalidate the cache entry")

        # --- save_cache / load_cache round-trip, read-only on sources --------
        cache_path = td / "cache.json"
        k2.save_cache(cache, cache_path)
        reloaded = k2.load_cache(cache_path)
        if reloaded.keys() != cache.keys():
            v.append("cache did not round-trip through save_cache/load_cache")

    return v
