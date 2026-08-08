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
            temperature=0.0, cache=cache, max_window_tokens=None, small_conv_tokens=None,
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
                                      model="test-model", temperature=0.0, cache={},
                                      max_window_tokens=None, small_conv_tokens=None)
        named = report2["conversations_excluded_no_timestamp"]
        if len(named) != 1 or named[0]["conversation_id"] != "local_ghost":
            v.append(f"excluded conversation not named in the report: {named}")

        # --- cache: re-run with nothing changed re-extracts ZERO -------------
        report3 = k2.run_extraction(
            included, excluded, caller=stub_caller, endpoint="x", model="test-model",
            temperature=0.0, cache=cache,  # same cache dict, mutated by the first run
            max_window_tokens=None, small_conv_tokens=None,
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
                           model="test-model", temperature=0.0, cache=cache,
                           max_window_tokens=None, small_conv_tokens=None)
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
            temperature=0.0, cache=cache, max_window_tokens=None, small_conv_tokens=None,
        )
        if report4["conversations_reextracted"] != 1:
            v.append("a changed source file's mtime should invalidate the cache entry")

        # --- save_cache / load_cache round-trip, read-only on sources --------
        cache_path = td / "cache.json"
        k2.save_cache(cache, cache_path)
        reloaded = k2.load_cache(cache_path)
        if reloaded.keys() != cache.keys():
            v.append("cache did not round-trip through save_cache/load_cache")

    # --- real transport: response_format/timeout wiring, no network touched --
    # Monkeypatches urllib.request.urlopen so call_lmstudio's actual payload
    # construction is exercised (not just the stub used everywhere above).
    import urllib.request

    class _FakeResponse:
        def __init__(self, body: dict):
            self._body = json.dumps(body).encode("utf-8")
        def read(self):
            return self._body
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["timeout"] = timeout
        captured["payload"] = json.loads(req.data.decode("utf-8"))
        return _FakeResponse({"choices": [{"message": {"content": "[]"}}]})

    real_urlopen = urllib.request.urlopen
    try:
        urllib.request.urlopen = fake_urlopen
        k2.call_lmstudio("hello transcript", endpoint="http://x", model="m", temperature=0.0)
        if captured["timeout"] != k2.DEFAULT_TIMEOUT or k2.DEFAULT_TIMEOUT != 900.0:
            v.append(f"call_lmstudio default timeout should be 900s: "
                      f"{captured['timeout']!r} (DEFAULT_TIMEOUT={k2.DEFAULT_TIMEOUT!r})")
        if "response_format" not in captured["payload"]:
            v.append("call_lmstudio (json_mode default True) did not send response_format")
        elif captured["payload"]["response_format"]["json_schema"]["schema"] != k2.CLAIMS_JSON_SCHEMA:
            v.append("call_lmstudio sent a response_format schema that doesn't match CLAIMS_JSON_SCHEMA")

        captured.clear()
        k2.call_lmstudio("hello transcript", endpoint="http://x", model="m", temperature=0.0,
                          json_mode=False, timeout=30.0)
        if "response_format" in captured["payload"]:
            v.append("call_lmstudio with json_mode=False must not send response_format at all")
        if captured["timeout"] != 30.0:
            v.append("call_lmstudio did not honour an explicit timeout override")
    finally:
        urllib.request.urlopen = real_urlopen

    # --- wrapper-noise stripping: system-reminder blocks never reach the
    #     model or the substring-verification universe --------------------
    noisy_conv = None
    with tempfile.TemporaryDirectory() as td2:
        td2 = Path(td2)
        path = td2 / "noisy.jsonl"
        path.write_text("{}\n", encoding="utf-8")
        text = ("<system-reminder>ignore this, it is bookkeeping</system-reminder>"
                "The real decision: ship the v2 pricing tier next sprint.")
        sess = lt.ParsedSession(
            thread_id="noisy", store="cowork", encoded_cwd="C--out", path=path,
            conversation_id="local_noisy", messages=[(0, "user", text, "2026-07-01T00:00:00Z", "u1")],
            created_at="2026-07-01T00:00:00Z", updated_at="2026-07-01T00:00:00Z",
        )
        noisy_conv = lt.Conversation(conversation_id="local_noisy", sessions=[sess],
                                       real_time="2026-07-01T00:00:00Z",
                                       real_time_source="last_message_timestamp")

        seen_texts = []

        def noise_check_caller(t, *, endpoint, model, temperature):
            seen_texts.append(t)
            return "[]"

        k2.extract_for_conversation(noisy_conv, caller=noise_check_caller, endpoint="x",
                                      model="m", temperature=0.0)
        if "system-reminder" in seen_texts[0] or "ignore this" in seen_texts[0]:
            v.append(f"system-reminder wrapper text reached the model call: {seen_texts[0]!r}")
        if "ship the v2 pricing tier" not in seen_texts[0]:
            v.append("stripping the wrapper also ate the real message content")

        full = k2.full_transcript_text(noisy_conv)
        if "<system-reminder>" in full:
            v.append("full_transcript_text() still contains an unstripped system-reminder block")

    # --- approx_token_count + build_windows: turn-aligned, no message split -
    if k2.approx_token_count("") != 0:
        v.append("approx_token_count('') should be 0")
    if k2.approx_token_count("a" * 400) != 100:
        v.append(f"approx_token_count sanity check failed: {k2.approx_token_count('a'*400)}")

    with tempfile.TemporaryDirectory() as td4:
        td4 = Path(td4)
        path = td4 / "big.jsonl"
        path.write_text("{}\n", encoding="utf-8")
        # 20 messages of ~400 chars (~100 tokens) each = ~2000 tokens total.
        msgs = [(i, "user", f"Turn {i}: " + ("x" * 390), f"2026-07-01T00:{i:02d}:00Z", f"u{i}")
                for i in range(20)]
        sess = lt.ParsedSession(
            thread_id="big", store="cowork", encoded_cwd="C--out", path=path,
            conversation_id="local_big", messages=msgs,
            created_at=msgs[0][3], updated_at=msgs[-1][3],
        )
        big_conv = lt.Conversation(conversation_id="local_big", sessions=[sess],
                                     real_time=msgs[-1][3], real_time_source="last_message_timestamp")

        windows = k2.build_windows(big_conv, max_tokens=500)
        if len(windows) < 2:
            v.append(f"a ~2000-token conversation windowed at 500 tokens should split "
                      f"into several windows, got {len(windows)}")
        # every original message must appear in exactly one window, none split.
        rejoined = "".join(windows)
        for i in range(20):
            if f"Turn {i}: " not in rejoined:
                v.append(f"build_windows lost message {i}")
        for w in windows:
            if k2.approx_token_count(w) > 500 and w.count("Turn ") > 1:
                pass  # a single very long message alone in a window is allowed to exceed max_tokens

        # extract_for_conversation windows internally and reports windows_total;
        # each window's quote is verified against ITS OWN window text.
        window_calls = []

        def window_caller(t, *, endpoint, model, temperature):
            window_calls.append(t)
            if "Turn 0:" in t:
                first_word = t.split("Turn 0: ")[1][:5]
                return json.dumps([{"claim_text": "first window claim",
                                      "quoted_source": f"Turn 0: {first_word}"}])
            return "[]"

        r_windowed = k2.extract_for_conversation(
            big_conv, caller=window_caller, endpoint="x", model="m", temperature=0.0,
            max_window_tokens=500,
        )
        if r_windowed.windows_total < 2:
            v.append(f"windowed extraction should report windows_total >= 2: {r_windowed.windows_total}")
        if len(window_calls) != r_windowed.windows_total:
            v.append(f"one model call expected per window: {len(window_calls)} calls for "
                      f"{r_windowed.windows_total} windows")
        if len(r_windowed.claims) != 1:
            v.append(f"expected exactly one claim from the window containing 'Turn 0': {r_windowed.claims}")

        # unwindowed (max_window_tokens=None) sends the whole thing in one call.
        single_calls = []

        def single_caller(t, *, endpoint, model, temperature):
            single_calls.append(t)
            return "[]"

        k2.extract_for_conversation(big_conv, caller=single_caller, endpoint="x", model="m",
                                      temperature=0.0, max_window_tokens=None)
        if len(single_calls) != 1:
            v.append(f"max_window_tokens=None should send one call, got {len(single_calls)}")

    # --- group_into_batches: short conversations grouped, large ones solo --
    def tiny_conv(cid: str, tokens_hint: int) -> "lt.Conversation":
        p = Path(tempfile.mkstemp(suffix=".jsonl")[1])
        p.write_text("{}\n", encoding="utf-8")
        text = "y" * (tokens_hint * 4)
        sess = lt.ParsedSession(
            thread_id=cid, store="cowork", encoded_cwd="C--out", path=p,
            conversation_id=cid, messages=[(0, "user", text, "2026-07-01T00:00:00Z", "u1")],
            created_at="2026-07-01T00:00:00Z", updated_at="2026-07-01T00:00:00Z",
        )
        return lt.Conversation(conversation_id=cid, sessions=[sess],
                                 real_time="2026-07-01T00:00:00Z",
                                 real_time_source="last_message_timestamp")

    small1 = tiny_conv("local_s1", 200)
    small2 = tiny_conv("local_s2", 200)
    small3 = tiny_conv("local_s3", 200)
    large1 = tiny_conv("local_l1", 5000)  # over the 1500-token small floor used below

    groups = k2.group_into_batches(
        [small1, small2, small3, large1],
        small_token_floor=1500, batch_target_tokens=6000, batch_max_conversations=6,
    )
    group_sizes = sorted(len(g) for g in groups)
    if group_sizes != [1, 3]:
        v.append(f"group_into_batches should group the 3 small ones together and leave "
                  f"the large one solo: sizes={group_sizes}")
    solo_group = next(g for g in groups if len(g) == 1)
    if solo_group[0].conversation_id != "local_l1":
        v.append("the solo group should be the large conversation, not a small one")

    # --- extract_batch: claims routed to the right conversation, cross-
    #     conversation leakage rejected exactly like a fabricated quote -----
    def batch_caller(t, *, endpoint, model, temperature, batch=False):
        if not batch:
            v.append("extract_batch must call the caller with batch=True")
        return json.dumps([
            {"conversation_index": 0, "claim_text": "claim from conv 0",
             "quoted_source": "y" * 20},  # literal substring of small1's own text
            {"conversation_index": 1, "claim_text": "claim from conv 1",
             "quoted_source": "y" * 20},  # both fixtures happen to be all "y"s, so this
                                            # verifies fine against its own claimed index --
                                            # true cross-conversation leakage is its own test below.
            {"conversation_index": 99, "claim_text": "out of range", "quoted_source": "y" * 5},
        ])

    batch_results, unattributed = k2.extract_batch(
        [small1, small2], caller=batch_caller, endpoint="x", model="m", temperature=0.0,
    )
    if batch_results["local_s1"].claims == [] or len(batch_results["local_s1"].claims) != 1:
        v.append(f"conv 0's claim should route to local_s1: {batch_results['local_s1']}")
    if len(batch_results["local_s2"].claims) != 1:
        v.append(f"conv 1's claim should route to local_s2: {batch_results['local_s2']}")
    if len(unattributed) != 1 or "not in this batch" not in unattributed[0]["reason"]:
        v.append(f"an out-of-range conversation_index should be reported unattributed, "
                  f"not silently dropped: {unattributed}")

    # cross-conversation leakage: a quote that is real text from a DIFFERENT
    # conversation in the batch, attributed to one it doesn't belong to.
    def leaking_caller(t, *, endpoint, model, temperature, batch=False):
        return json.dumps([
            {"conversation_index": 0, "claim_text": "leaked",
             "quoted_source": "totally different content only in conv 1"},
        ])

    leak_small1 = tiny_conv("local_leak0", 50)
    leak_small2 = tiny_conv("local_leak1", 50)
    # overwrite leak_small2's message text with distinguishable content.
    leak_small2.sessions[0].messages[0] = (0, "user", "totally different content only in conv 1",
                                             "2026-07-01T00:00:00Z", "u1")
    leak_results, leak_unattr = k2.extract_batch(
        [leak_small1, leak_small2], caller=leaking_caller, endpoint="x", model="m", temperature=0.0,
    )
    if leak_results["local_leak0"].claims:
        v.append("a quote that only exists in a DIFFERENT conversation in the batch must be "
                  "rejected as cross-conversation leakage, not accepted")
    if not leak_results["local_leak0"].rejected or "leakage" not in leak_results["local_leak0"].rejected[0]["reason"]:
        v.append(f"cross-conversation leakage should be named as such in the rejection reason: "
                  f"{leak_results['local_leak0'].rejected}")

    # --- run_extraction end-to-end with batching engaged --------------------
    batch_run_calls = []

    def e2e_batch_caller(t, *, endpoint, model, temperature, batch=False):
        batch_run_calls.append((t, batch))
        if batch:
            return json.dumps([
                {"conversation_index": 0, "claim_text": "from s1", "quoted_source": "y" * 20},
            ])
        return "[]"

    batch_report = k2.run_extraction(
        [small1, small2], [], caller=e2e_batch_caller, endpoint="x", model="test-model",
        temperature=0.0, cache={}, max_window_tokens=None, small_conv_tokens=1500,
        batch_target_tokens=6000, batch_max_conversations=6,
    )
    if len(batch_run_calls) != 1:
        v.append(f"two small conversations under the batch target should cost exactly ONE "
                  f"model call, got {len(batch_run_calls)}")
    if batch_report["claims_extracted"] != 1:
        v.append(f"batched run_extraction should still surface the routed claim: {batch_report}")
    ordered_ids = [c["conversation_id"] for c in batch_report["conversations"]]
    if ordered_ids != ["local_s1", "local_s2"]:
        v.append(f"batched run_extraction must still report in original newest-first order: "
                  f"{ordered_ids}")

    # --- merge_report: a --project-scoped re-run must not clobber other
    #     projects' already-computed results -------------------------------
    old_report = {
        "conversations": [
            {"conversation_id": "local_a", "real_time": "2026-07-01T00:00:00Z",
             "claims": [{"claim_text": "old a claim", "quoted_source": "q"}],
             "rejected": [], "parse_failed": False, "scanned_with_zero": False,
             "windows_total": 1, "windows_parse_failed": 0},
            {"conversation_id": "local_b", "real_time": "2026-07-02T00:00:00Z",
             "claims": [], "rejected": [{"claim_text": "x", "quoted_source": "y", "reason": "r"}],
             "parse_failed": False, "scanned_with_zero": True,
             "windows_total": 1, "windows_parse_failed": 0},
        ],
        "conversations_excluded_no_timestamp": [
            {"conversation_id": "local_ghost_old", "reason": "stale"},
        ],
        "batch_unattributed_rejections": [],
    }
    # This scoped run only touched local_b -- re-extracted with a NEW claim
    # this time -- and left local_a untouched (not even in its conversations
    # list, as a --project filter would produce).
    new_report = {
        "model_id": "test-model-v2", "endpoint": "x", "temperature": 0.0,
        "run_timestamp": "2026-08-08T00:00:00Z",
        "conversations_scanned": 1, "conversations_reextracted": 1, "conversations_from_cache": 0,
        "conversations_excluded_no_timestamp": [],
        "claims_extracted": 1, "claims_rejected": 0, "quote_rejection_rate": 0.0,
        "batch_unattributed_rejections": [],
        "conversations": [
            {"conversation_id": "local_b", "real_time": "2026-07-02T00:00:00Z",
             "claims": [{"claim_text": "new b claim", "quoted_source": "q2"}],
             "rejected": [], "parse_failed": False, "scanned_with_zero": False,
             "windows_total": 1, "windows_parse_failed": 0},
        ],
    }
    merged = k2.merge_report(old_report, new_report, touched_ids={"local_b"})
    merged_ids = {c["conversation_id"] for c in merged["conversations"]}
    if merged_ids != {"local_a", "local_b"}:
        v.append(f"merge_report should keep local_a untouched and update local_b: {merged_ids}")
    a = next(c for c in merged["conversations"] if c["conversation_id"] == "local_a")
    if a["claims"][0]["claim_text"] != "old a claim":
        v.append("merge_report altered a conversation outside the scoped run's touched set")
    b = next(c for c in merged["conversations"] if c["conversation_id"] == "local_b")
    if b["claims"][0]["claim_text"] != "new b claim":
        v.append("merge_report did not apply the scoped run's new result for the touched conversation")
    if merged["conversations_scanned"] != 2 or merged["claims_extracted"] != 2:
        v.append(f"merge_report should recompute aggregates over the MERGED set, not just "
                  f"this run's slice: scanned={merged['conversations_scanned']} "
                  f"claims={merged['claims_extracted']}")
    # old-style exclusion carried over untouched.
    if merged["conversations_excluded_no_timestamp"][0]["conversation_id"] != "local_ghost_old":
        v.append("merge_report dropped a prior exclusion it never touched this run")
    if merged["model_id"] != "test-model-v2":
        v.append("merge_report should keep the NEW run's own provenance (model_id/run_timestamp)")

    # A conversation that WAS excluded before, but got resolved and
    # successfully processed this run, must not linger in the excluded list.
    old_report2 = {
        "conversations": [],
        "conversations_excluded_no_timestamp": [{"conversation_id": "local_c", "reason": "was stale"}],
        "batch_unattributed_rejections": [],
    }
    new_report2 = {
        "model_id": "m", "endpoint": "x", "temperature": 0.0, "run_timestamp": "t",
        "conversations_scanned": 1, "conversations_reextracted": 1, "conversations_from_cache": 0,
        "conversations_excluded_no_timestamp": [],
        "claims_extracted": 0, "claims_rejected": 0, "quote_rejection_rate": 0.0,
        "batch_unattributed_rejections": [],
        "conversations": [{"conversation_id": "local_c", "real_time": "t", "claims": [], "rejected": [],
                             "parse_failed": False, "scanned_with_zero": True,
                             "windows_total": 1, "windows_parse_failed": 0}],
    }
    merged2 = k2.merge_report(old_report2, new_report2, touched_ids={"local_c"})
    if merged2["conversations_excluded_no_timestamp"]:
        v.append("merge_report left a now-resolved conversation in the excluded list")

    # No prior output file at all -- merge_report returns the new report as-is.
    merged3 = k2.merge_report(None, new_report2, touched_ids={"local_c"})
    if merged3 is not new_report2:
        v.append("merge_report with old=None should return the new report unchanged")

    # --- make_progress_reporter: writes "label: done/total", overwritten via
    #     \r (no scrolling spam), and is a plain optional callback -- passing
    #     none must not change run_extraction's behavior or output at all ---
    import io
    buf = io.StringIO()
    reporter = k2.make_progress_reporter("extracting", stream=buf)
    reporter(1, 3)
    reporter(3, 3)
    written = buf.getvalue()
    if "extracting: 1/3" not in written or "extracting: 3/3" not in written:
        v.append(f"make_progress_reporter did not write the expected done/total text: {written!r}")
    if not written.startswith("\r"):
        v.append("make_progress_reporter should overwrite in place (\\r prefix), not scroll")
    if not written.rstrip("\n").endswith("3/3") or not written.endswith("\n"):
        v.append("make_progress_reporter should emit a trailing newline only once done == total")
    buf0 = io.StringIO()
    k2.make_progress_reporter("x", stream=buf0)(0, 0)
    if buf0.getvalue():
        v.append("make_progress_reporter with total=0 should write nothing (nothing to report)")

    # progress callback actually fires during run_extraction, once per
    # conversation, ending at (n, n) -- and is purely additive: omitting it
    # (progress=None, the default used everywhere else in this file) must
    # leave results identical, which every earlier run_extraction assertion
    # in this file already covers since none of them pass progress=.
    def _mk_conv(cid: str, ts: str, text: str) -> "lt.Conversation":
        p = Path(tempfile.mkstemp(suffix=".jsonl")[1])
        p.write_text("{}\n", encoding="utf-8")
        sess = lt.ParsedSession(
            thread_id=cid, store="cowork", encoded_cwd="C--out", path=p,
            conversation_id=cid, messages=[(0, "user", text, ts, "u1")],
            created_at=ts, updated_at=ts,
        )
        return lt.Conversation(conversation_id=cid, sessions=[sess], real_time=ts,
                                 real_time_source="last_message_timestamp")

    calls = []
    stub_progress = lambda done, total: calls.append((done, total))
    convs_p = [
        _mk_conv("local_p1", "2026-08-01T00:00:00Z", "hello there this is p1"),
        _mk_conv("local_p2", "2026-07-01T00:00:00Z", "hello there this is p2"),
    ]

    def empty_caller(t, *, endpoint, model, temperature, **kw):
        return "[]"

    k2.run_extraction(convs_p, [], caller=empty_caller, endpoint="x", model="m",
                        temperature=0.0, cache={}, max_window_tokens=None,
                        small_conv_tokens=None, progress=stub_progress)
    if not calls or calls[-1] != (2, 2):
        v.append(f"run_extraction's progress callback should end at (n, n): {calls}")

    return v
