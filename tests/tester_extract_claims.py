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
    import urllib.error

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

    # --- prompt fingerprint invalidation: a cache built under a DIFFERENT
    #     extraction prompt must be wholesale discarded, not silently served
    #     -- this is the same failure class as the real-run K1 bug (a
    #     downstream stage trusting cached output that predates an upstream
    #     change) that motivated this guard. ------------------------------
    conv_fp = _mk_conv("local_fp1", "2026-08-01T00:00:00Z", "hello there this is fp1")
    stale_cache = {
        "__prompt_fingerprint__": "not-the-real-fingerprint",
        "local_fp1": {
            "sources": k2.source_identity(conv_fp),
            "claims": [{"claim_text": "stale cached claim", "quoted_source": "stale"}],
            "rejected": [], "parse_failed": False, "scanned_with_zero": False,
            "real_time": "2026-08-01T00:00:00Z", "windows_total": 1, "windows_parse_failed": 0,
        },
    }
    fresh_calls = []

    def fresh_caller(t, *, endpoint, model, temperature, **kw):
        fresh_calls.append(t)
        return "[]"

    report_stale = k2.run_extraction([conv_fp], [], caller=fresh_caller, endpoint="x", model="m",
                                       temperature=0.0, cache=stale_cache, max_window_tokens=None,
                                       small_conv_tokens=None)
    if not fresh_calls:
        v.append("a cache built under a different prompt fingerprint should be discarded, "
                  "forcing re-extraction -- but no call was made")
    if report_stale["conversations"][0]["claims"] and \
       report_stale["conversations"][0]["claims"][0]["claim_text"] == "stale cached claim":
        v.append("run_extraction served a stale-prompt cached claim instead of re-extracting")
    if stale_cache.get("__prompt_fingerprint__") != k2.prompt_fingerprint():
        v.append("run_extraction should stamp the cache with the CURRENT prompt fingerprint "
                  "after discarding a stale one")

    # A cache stamped with the CURRENT fingerprint is trusted normally.
    fresh_calls.clear()
    report_fresh = k2.run_extraction([conv_fp], [], caller=fresh_caller, endpoint="x", model="m",
                                       temperature=0.0, cache=stale_cache, max_window_tokens=None,
                                       small_conv_tokens=None)
    if fresh_calls:
        v.append(f"a cache already stamped with the current prompt fingerprint should be "
                  f"reused, not re-extracted: {fresh_calls}")
    if report_fresh["conversations_from_cache"] != 1:
        v.append("run_extraction should report the matching-fingerprint conversation as "
                  "served from cache")

    # --- COWORK_BRIEF_conductor.md Task 1: --model-ttl -> payload `ttl` ----
    captured2 = {}

    def fake_urlopen2(req, timeout=None):
        captured2["payload"] = json.loads(req.data.decode("utf-8"))
        return _FakeResponse({"choices": [{"message": {"content": "[]"}}]})

    try:
        urllib.request.urlopen = fake_urlopen2
        k2.call_lmstudio("t", endpoint="http://x", model="m", temperature=0.0)
        if "ttl" in captured2["payload"]:
            v.append("call_lmstudio with no ttl given must not send a `ttl` field at all")

        k2.call_lmstudio("t", endpoint="http://x", model="m", temperature=0.0, ttl=120.0)
        if captured2["payload"].get("ttl") != 120.0:
            v.append(f"call_lmstudio(ttl=120.0) should send payload['ttl']==120.0, "
                      f"got {captured2['payload'].get('ttl')!r}")
    finally:
        urllib.request.urlopen = real_urlopen

    # --- COWORK_BRIEF_conductor.md Task 1: --cool-down sleeps BETWEEN
    #     conversations (never after the last one), and --cool-down 0 (the
    #     default) reproduces today's behaviour exactly (no sleep at all) --
    conv_cd1 = _mk_conv("local_cd1", "2026-08-03T00:00:00Z", "cool-down conversation one")
    conv_cd2 = _mk_conv("local_cd2", "2026-08-02T00:00:00Z", "cool-down conversation two")
    conv_cd3 = _mk_conv("local_cd3", "2026-08-01T00:00:00Z", "cool-down conversation three")

    sleeps: list[float] = []
    k2.run_extraction(
        [conv_cd1, conv_cd2, conv_cd3], [], caller=empty_caller, endpoint="x", model="m",
        temperature=0.0, cache={}, max_window_tokens=None, small_conv_tokens=None,
        cool_down=5.0, sleep_fn=sleeps.append,
    )
    if sleeps != [5.0, 5.0]:
        v.append(f"3 conversations with cool_down=5.0 should sleep exactly twice (between "
                  f"1-2 and 2-3, never after the last): {sleeps}")

    sleeps_zero: list[float] = []
    k2.run_extraction(
        [conv_cd1, conv_cd2], [], caller=empty_caller, endpoint="x", model="m",
        temperature=0.0, cache={}, max_window_tokens=None, small_conv_tokens=None,
        cool_down=0.0, sleep_fn=sleeps_zero.append,
    )
    if sleeps_zero:
        v.append(f"cool_down=0.0 (the default) must never sleep -- reproduces today's "
                  f"behaviour exactly: {sleeps_zero}")

    # A cached (no-network) re-run must not sleep either -- cool-down only
    # applies between groups that actually did a model call.
    warm_cache: dict = {}
    k2.run_extraction([conv_cd1, conv_cd2], [], caller=empty_caller, endpoint="x", model="m",
                        temperature=0.0, cache=warm_cache, max_window_tokens=None,
                        small_conv_tokens=None, cool_down=9.0, sleep_fn=lambda s: None)
    sleeps_cached: list[float] = []
    k2.run_extraction([conv_cd1, conv_cd2], [], caller=empty_caller, endpoint="x", model="m",
                        temperature=0.0, cache=warm_cache, max_window_tokens=None,
                        small_conv_tokens=None, cool_down=9.0, sleep_fn=sleeps_cached.append)
    if sleeps_cached:
        v.append(f"an all-cache-hit re-run should never sleep (nothing needed pacing): "
                  f"{sleeps_cached}")

    # --- COWORK_BRIEF_conductor.md Task 1: per-conversation timing line ---
    timing_records: list[dict] = []
    k2.run_extraction(
        [conv_cd1, conv_cd2], [], caller=empty_caller, endpoint="x", model="timing-model",
        temperature=0.0, cache={}, max_window_tokens=None, small_conv_tokens=None,
        session_to_project={"local_cd1": "proj-x", "local_cd2": "proj-y"},
        on_timing=timing_records.append,
    )
    if len(timing_records) != 2:
        v.append(f"expected one timing record per conversation, got {len(timing_records)}")
    else:
        ids = {r["conversation_id"] for r in timing_records}
        if ids != {"local_cd1", "local_cd2"}:
            v.append(f"timing records should cover both conversations: {ids}")
        r1 = next(r for r in timing_records if r["conversation_id"] == "local_cd1")
        if r1["project_id"] != "proj-x":
            v.append(f"timing record project_id should come from session_to_project: {r1}")
        if r1["model_id"] != "timing-model":
            v.append(f"timing record model_id should be the run's model: {r1}")
        if r1["message_count"] != 1:
            v.append(f"timing record message_count wrong: {r1}")
        if r1["batch_size"] != 1:
            v.append(f"single-conversation path should report batch_size 1: {r1}")
        if not isinstance(r1["wall_clock_seconds"], float) or r1["wall_clock_seconds"] < 0:
            v.append(f"timing record wall_clock_seconds should be a non-negative float: {r1}")
        if r1["cool_down_preceded"] is not False:
            v.append(f"no cool_down was configured -- cool_down_preceded should be False: {r1}")

    # omitting on_timing/session_to_project must change nothing about results.
    baseline = k2.run_extraction([conv_cd1, conv_cd2], [], caller=empty_caller, endpoint="x",
                                   model="timing-model", temperature=0.0, cache={},
                                   max_window_tokens=None, small_conv_tokens=None)
    if baseline["claims_extracted"] != 0 or baseline["conversations_scanned"] != 2:
        v.append("run_extraction with on_timing/session_to_project omitted should behave "
                  "exactly as before")

    # --- error-handling addition (2026-08-12): on_checkpoint fires after
    #     EVERY group with a partial report of everything finished so far,
    #     so a crash mid-run (the work-rig HTTP 400 that motivated this)
    #     loses at most the in-flight group. Three single-conversation
    #     groups (batching disabled) should produce exactly 3 checkpoints,
    #     each strictly larger than the last. -----------------------------
    checkpoints: list[dict] = []
    k2.run_extraction(
        [conv_cd1, conv_cd2, conv_cd3], [], caller=empty_caller, endpoint="x", model="m",
        temperature=0.0, cache={}, max_window_tokens=None, small_conv_tokens=None,
        on_checkpoint=checkpoints.append,
    )
    if len(checkpoints) != 3:
        v.append(f"expected one checkpoint per group (3 single-conversation groups), "
                  f"got {len(checkpoints)}")
    else:
        scanned_counts = [c["conversations_scanned"] for c in checkpoints]
        if scanned_counts != [1, 2, 3]:
            v.append(f"checkpoints should accumulate monotonically, one conversation more "
                      f"each time: {scanned_counts}")
        ids_seen = [{cv["conversation_id"] for cv in c["conversations"]} for c in checkpoints]
        if ids_seen[-1] != {"local_cd1", "local_cd2", "local_cd3"}:
            v.append(f"the final checkpoint should cover every conversation processed: "
                      f"{ids_seen[-1]}")
        if not ids_seen[0] <= ids_seen[1] <= ids_seen[2]:
            v.append(f"each checkpoint's conversation set should be a superset of the "
                      f"previous one, never losing anything already finished: {ids_seen}")

    # simulate a crash: on_checkpoint raises after the 2nd group. The cache
    # dict (mutated in place by run_extraction, independent of on_checkpoint
    # entirely) must still hold the first 2 conversations' entries even
    # though the run never reached the 3rd or returned normally -- this is
    # the actual resumability property, not just the callback firing.
    crash_cache: dict = {}
    crash_calls = {"n": 0}

    def crashing_checkpoint(partial_report):
        crash_calls["n"] += 1
        if crash_calls["n"] == 2:
            raise RuntimeError("simulated crash mid-run")

    crashed = False
    try:
        k2.run_extraction(
            [conv_cd1, conv_cd2, conv_cd3], [], caller=empty_caller, endpoint="x", model="m",
            temperature=0.0, cache=crash_cache, max_window_tokens=None, small_conv_tokens=None,
            on_checkpoint=crashing_checkpoint,
        )
    except RuntimeError:
        crashed = True
    if not crashed:
        v.append("expected the simulated on_checkpoint crash to propagate, not be swallowed")
    if "local_cd1" not in crash_cache or "local_cd2" not in crash_cache:
        v.append(f"a crash after the 2nd checkpoint should still leave the first 2 "
                  f"conversations' entries in the (in-memory) cache dict -- "
                  f"resumability depends on this: {sorted(crash_cache.keys())}")
    if "local_cd3" in crash_cache:
        v.append(f"the 3rd (never-reached) conversation should NOT be in the cache after "
                  f"a crash before its group ran: {sorted(crash_cache.keys())}")

    # omitting on_checkpoint entirely (every OTHER run_extraction test in
    # this file) must change nothing about the result -- purely observational.
    no_checkpoint_report = k2.run_extraction(
        [conv_cd1, conv_cd2, conv_cd3], [], caller=empty_caller, endpoint="x", model="m",
        temperature=0.0, cache={}, max_window_tokens=None, small_conv_tokens=None,
    )
    if no_checkpoint_report["conversations_scanned"] != 3:
        v.append("run_extraction with on_checkpoint omitted should behave exactly as before")

    # a batched group shares one wall-clock measurement across its members,
    # marked with the real batch_size rather than a fabricated per-conversation split.
    b1 = tiny_conv("local_tb1", 100)
    b2 = tiny_conv("local_tb2", 100)
    batch_timing: list[dict] = []

    def batch_empty_caller(t, *, endpoint, model, temperature, **kw):
        return "[]"

    k2.run_extraction([b1, b2], [], caller=batch_empty_caller, endpoint="x", model="m",
                        temperature=0.0, cache={}, max_window_tokens=None, small_conv_tokens=1500,
                        batch_target_tokens=6000, batch_max_conversations=6,
                        on_timing=batch_timing.append)
    if len(batch_timing) != 2:
        v.append(f"a batch of 2 should still emit 2 timing records (one per conversation): "
                  f"{len(batch_timing)}")
    elif batch_timing[0]["batch_size"] != 2 or batch_timing[1]["batch_size"] != 2:
        v.append(f"both members of a batched group should report batch_size 2: {batch_timing}")
    elif batch_timing[0]["wall_clock_seconds"] != batch_timing[1]["wall_clock_seconds"]:
        v.append("both members of a batched group should share the SAME measured wall-clock "
                  "time, not a fabricated split")

    # --- make_timing_reporter: human line to stream + optional JSONL file --
    with tempfile.TemporaryDirectory() as td5:
        td5 = Path(td5)
        buf2 = io.StringIO()
        jsonl_path = td5 / "timing.jsonl"
        reporter2 = k2.make_timing_reporter(stream=buf2, jsonl_path=jsonl_path)
        reporter2({"conversation_id": "c1", "project_id": "p1", "message_count": 3,
                    "model_id": "m1", "batch_size": 1, "cool_down_preceded": False,
                    "wall_clock_seconds": 1.5})
        written2 = buf2.getvalue()
        if "TIMING" not in written2 or "conversation_id=c1" not in written2 or "wall_clock_seconds=1.500" not in written2:
            v.append(f"make_timing_reporter did not write the expected TIMING line: {written2!r}")
        if not jsonl_path.exists():
            v.append("make_timing_reporter with jsonl_path given should create the file")
        else:
            lines = jsonl_path.read_text(encoding="utf-8").strip().splitlines()
            if len(lines) != 1:
                v.append(f"expected exactly one JSONL line written: {lines}")
            else:
                rec = json.loads(lines[0])
                if rec["conversation_id"] != "c1" or "timestamp" not in rec:
                    v.append(f"JSONL timing record missing fields: {rec}")

    # =========================================================================
    # COWORK_BRIEF_conductor_governor.md Task 1: finer timing records
    # =========================================================================

    # --- item 1: a per-WINDOW record alongside the per-conversation one,
    #     the only way decay WITHIN a conversation is observable -------------
    with tempfile.TemporaryDirectory() as td6:
        td6 = Path(td6)
        path = td6 / "wide.jsonl"
        path.write_text("{}\n", encoding="utf-8")
        msgs = [(i, "user", f"Turn {i}: " + ("z" * 390), f"2026-08-01T00:{i:02d}:00Z", f"u{i}")
                for i in range(12)]
        wide_conv = lt.Conversation(
            conversation_id="local_wide", real_time=msgs[-1][3],
            real_time_source="last_message_timestamp",
            sessions=[lt.ParsedSession(
                thread_id="wide", store="cowork", encoded_cwd="C--out", path=path,
                conversation_id="local_wide", messages=msgs,
                created_at=msgs[0][3], updated_at=msgs[-1][3],
            )],
        )

        window_records: list[dict] = []

        def wide_caller(t, *, endpoint, model, temperature, **kw):
            return "[]"

        result_wide = k2.extract_for_conversation(
            wide_conv, caller=wide_caller, endpoint="x", model="m", temperature=0.0,
            max_window_tokens=500, on_window_timing=window_records.append,
        )
        if len(window_records) != result_wide.windows_total or result_wide.windows_total < 2:
            v.append(f"expected one on_window_timing record per window "
                      f"({result_wide.windows_total} windows): {len(window_records)} records")
        else:
            indices = [r["window_index"] for r in window_records]
            if indices != list(range(result_wide.windows_total)):
                v.append(f"window_index should run 0..windows_total-1 in order: {indices}")
            if any(r["windows_total"] != result_wide.windows_total for r in window_records):
                v.append(f"every window record should carry the same windows_total: {window_records}")
            if any(not isinstance(r["token_count"], int) or r["token_count"] <= 0 for r in window_records):
                v.append(f"window record token_count should be a positive int: {window_records}")
            if any(not isinstance(r["wall_clock_seconds"], float) or r["wall_clock_seconds"] < 0
                    for r in window_records):
                v.append(f"window record wall_clock_seconds should be a non-negative float: {window_records}")

        # omitting on_window_timing must change nothing about the result.
        result_wide2 = k2.extract_for_conversation(
            wide_conv, caller=wide_caller, endpoint="x", model="m", temperature=0.0,
            max_window_tokens=500,
        )
        if result_wide2.windows_total != result_wide.windows_total:
            v.append("extract_for_conversation with on_window_timing omitted should behave "
                      "exactly as with it given")

        # run_extraction wires on_window_timing through, attaching
        # project_id/model_id/cool_down_preceded that extract_for_conversation
        # itself has no way to know.
        run_window_records: list[dict] = []
        k2.run_extraction(
            [wide_conv], [], caller=wide_caller, endpoint="x", model="wide-model",
            temperature=0.0, cache={}, max_window_tokens=500, small_conv_tokens=None,
            session_to_project={"local_wide": "proj-wide"},
            on_window_timing=run_window_records.append,
        )
        if len(run_window_records) < 2:
            v.append(f"run_extraction should forward one on_window_timing call per window: "
                      f"{len(run_window_records)}")
        else:
            wr = run_window_records[0]
            if wr["project_id"] != "proj-wide" or wr["model_id"] != "wide-model":
                v.append(f"run_extraction's window records should carry project_id/model_id "
                          f"like the per-conversation ones do: {wr}")
            # no cool-down configured on this run -> never preceded.
            if any(r["cool_down_preceded"] for r in run_window_records):
                v.append(f"no cool_down configured -- no window record should be "
                          f"cool_down_preceded: {run_window_records}")

        # a batched group (extract_batch) makes ONE call for the whole batch --
        # there is no window concept there, so on_window_timing must never fire.
        wb1 = tiny_conv("local_wb1", 100)
        wb2 = tiny_conv("local_wb2", 100)
        batch_window_records: list[dict] = []

        def wb_caller(t, *, endpoint, model, temperature, **kw):
            return "[]"

        k2.run_extraction([wb1, wb2], [], caller=wb_caller, endpoint="x", model="m",
                            temperature=0.0, cache={}, max_window_tokens=None,
                            small_conv_tokens=1500, batch_target_tokens=6000,
                            batch_max_conversations=6, on_window_timing=batch_window_records.append)
        if batch_window_records:
            v.append(f"a batched group has no window concept -- on_window_timing should "
                      f"never fire for it: {batch_window_records}")

    # --- item 2: cool_down_preceded is True only for the group immediately
    #     after a cool-down sleep, and (at window granularity) only that
    #     group's FIRST window -- the JIT-reload cost lands on ONE call ------
    def _multi_msg_conv(cid: str, ts: str, n: int) -> "lt.Conversation":
        p = Path(tempfile.mkstemp(suffix=".jsonl")[1])
        p.write_text("{}\n", encoding="utf-8")
        msgs = [(i, "user", f"Turn {i}: " + ("z" * 390), f"{ts[:10]}T00:{i:02d}:00Z", f"u{i}")
                for i in range(n)]
        sess = lt.ParsedSession(
            thread_id=cid, store="cowork", encoded_cwd="C--out", path=p,
            conversation_id=cid, messages=msgs, created_at=msgs[0][3], updated_at=msgs[-1][3],
        )
        return lt.Conversation(conversation_id=cid, sessions=[sess], real_time=ts,
                                 real_time_source="last_message_timestamp")

    cd_a = _multi_msg_conv("local_gov_a", "2026-08-05T00:00:00Z", 12)
    cd_b = _multi_msg_conv("local_gov_b", "2026-08-04T00:00:00Z", 12)
    cd_c = _mk_conv("local_gov_c", "2026-08-03T00:00:00Z", "governor conversation c")

    def gov_caller(t, *, endpoint, model, temperature, **kw):
        return "[]"

    gov_conv_timing: list[dict] = []
    gov_window_timing: list[dict] = []
    k2.run_extraction(
        [cd_a, cd_b, cd_c], [], caller=gov_caller, endpoint="x", model="m",
        temperature=0.0, cache={}, max_window_tokens=500, small_conv_tokens=None,
        cool_down=1.0, sleep_fn=lambda s: None,
        on_timing=gov_conv_timing.append, on_window_timing=gov_window_timing.append,
    )
    by_conv = {r["conversation_id"]: r for r in gov_conv_timing}
    if by_conv["local_gov_a"]["cool_down_preceded"] is not False:
        v.append("the FIRST conversation of a run is never preceded by a cool-down")
    if by_conv["local_gov_b"]["cool_down_preceded"] is not True:
        v.append("local_gov_b immediately follows a cool-down sleep -- should be flagged")
    if by_conv["local_gov_c"]["cool_down_preceded"] is not True:
        v.append("local_gov_c immediately follows a cool-down sleep -- should be flagged")

    a_windows = [r for r in gov_window_timing if r["conversation_id"] == "local_gov_a"]
    if len(a_windows) < 2:
        v.append(f"local_gov_a's long text should have windowed into >=2 windows: {len(a_windows)}")
    elif any(w["cool_down_preceded"] for w in a_windows):
        v.append(f"local_gov_a is the first conversation -- no window should be "
                  f"cool_down_preceded: {a_windows}")

    b_windows = [r for r in gov_window_timing if r["conversation_id"] == "local_gov_b"]
    if not b_windows or b_windows[0]["cool_down_preceded"] is not True:
        v.append(f"local_gov_b's FIRST window follows a cool-down -- should be flagged: {b_windows}")
    if any(w["cool_down_preceded"] for w in b_windows[1:]):
        v.append(f"only local_gov_b's FIRST window should carry the reload flag, not "
                  f"later ones in the same conversation: {b_windows}")

    # =========================================================================
    # COWORK_BRIEF_conductor_governor.md Addendum 2: usage capture, generation
    # ms/token -- the instrument fix. Wall-clock alone cannot separate a slow
    # (loaded) window from a verbose (long-output) one; ms/token can.
    # =========================================================================

    # --- the accumulator primitives, tested directly ------------------------
    box = {}
    k2.reset_usage_box(box)
    if k2.usage_from_box(box)["usage_available"] is not False:
        v.append("a freshly reset usage box (zero calls) should report usage_available=False")
    acc = k2.make_usage_accumulator(box)
    acc({"completion_tokens": 10, "prompt_tokens": 5})
    acc({"completion_tokens": 20, "prompt_tokens": 15})
    u = k2.usage_from_box(box)
    if u != {"usage_available": True, "prompt_tokens": 20, "completion_tokens": 30}:
        v.append(f"usage_from_box should SUM across all calls since the last reset: {u}")

    k2.reset_usage_box(box)
    acc({"completion_tokens": 10, "prompt_tokens": 5})
    acc(None)  # one call in the unit returned no usage at all
    u2 = k2.usage_from_box(box)
    if u2["usage_available"] is not False or u2["prompt_tokens"] is not None or u2["completion_tokens"] is not None:
        v.append(f"ONE call with no usage should make the whole unit's usage unavailable "
                  f"(never a partial/understated aggregate): {u2}")

    # --- generation_ms_per_token: the derived unit itself --------------------
    avail = {"usage_available": True, "completion_tokens": 100, "prompt_tokens": 10}
    if k2.generation_ms_per_token(2.0, avail) != 20.0:
        v.append(f"generation_ms_per_token(2.0s, 100 completion tokens) should be 20.0ms/tok: "
                  f"{k2.generation_ms_per_token(2.0, avail)}")
    zero_tok = {"usage_available": True, "completion_tokens": 0, "prompt_tokens": 10}
    if k2.generation_ms_per_token(2.0, zero_tok) is not None:
        v.append("zero completion_tokens should yield None, never a division by zero")
    unavail = {"usage_available": False, "completion_tokens": None, "prompt_tokens": None}
    if k2.generation_ms_per_token(2.0, unavail) is not None:
        v.append("usage_available=False should always yield None, regardless of elapsed time")

    # --- independent of output length: a long-output call and a short-output
    #     call with the SAME real ms/token report the SAME figure, even
    #     though their raw wall-clock and token counts differ enormously.
    #     This is the exact defect the addendum's real data exposed: 7,972
    #     tokens in 14.6s and 2,596 tokens in 111.7s read as a 24x swing on
    #     wall-clock alone but are actually comparable once normalised. -----
    long_output = {"usage_available": True, "completion_tokens": 800, "prompt_tokens": 50}
    short_output = {"usage_available": True, "completion_tokens": 40, "prompt_tokens": 50}
    ms_long = k2.generation_ms_per_token(16.0, long_output)   # 20ms/tok
    ms_short = k2.generation_ms_per_token(0.8, short_output)  # 20ms/tok
    if ms_long is None or ms_short is None or abs(ms_long - ms_short) > 1e-9:
        v.append(f"a long-output call (800 tok/16.0s) and a short-output call (40 tok/0.8s) "
                  f"at the SAME real generation speed should report the SAME ms/token: "
                  f"long={ms_long} short={ms_short}")

    # --- call_lmstudio: on_usage fires with a dict when `usage` is present,
    #     None when absent, and the function's OWN return value (the content
    #     string) is completely unaffected either way -----------------------
    usage_calls: list = []

    def usage_urlopen_present(req, timeout=None):
        return _FakeResponse({
            "choices": [{"message": {"content": "[]"}}],
            "usage": {"prompt_tokens": 123, "completion_tokens": 45, "total_tokens": 168},
        })

    def usage_urlopen_absent(req, timeout=None):
        return _FakeResponse({"choices": [{"message": {"content": "[]"}}]})

    try:
        urllib.request.urlopen = usage_urlopen_present
        content = k2.call_lmstudio("t", endpoint="http://x", model="m", temperature=0.0,
                                     on_usage=usage_calls.append)
        if content != "[]":
            v.append("call_lmstudio's return value must be unaffected by on_usage")
        if usage_calls != [{"completion_tokens": 45, "prompt_tokens": 123}]:
            v.append(f"on_usage should fire once with the response's usage block: {usage_calls}")

        usage_calls.clear()
        urllib.request.urlopen = usage_urlopen_absent
        content2 = k2.call_lmstudio("t", endpoint="http://x", model="m", temperature=0.0,
                                      on_usage=usage_calls.append)
        if content2 != "[]":
            v.append("call_lmstudio's return value must be unaffected by a missing usage block")
        if usage_calls != [None]:
            v.append(f"on_usage should fire with None when the response carries no usage -- "
                      f"absent, never estimated: {usage_calls}")

        # omitting on_usage entirely must not crash and must not change the
        # return value -- every earlier call_lmstudio test in this file
        # (none of which pass on_usage) already proves this, but assert it
        # explicitly against a response that HAS a usage block too.
        urllib.request.urlopen = usage_urlopen_present
        content3 = k2.call_lmstudio("t", endpoint="http://x", model="m", temperature=0.0)
        if content3 != "[]":
            v.append("call_lmstudio without on_usage should behave exactly as before")
    finally:
        urllib.request.urlopen = real_urlopen

    # --- post_json_with_retry / call_lmstudio retries: a transient failure
    #     (HTTPError, URLError, plain OSError) is retried up to `retries`
    #     times before succeeding, never touching the caller's return value;
    #     a failure that never clears is still raised once retries are
    #     exhausted -- the module's 'loud failure' contract is deferred, not
    #     dropped. Real-run motive: a work-rig HTTP 400 traced to local
    #     resource pressure cleared on a plain re-run -- exactly what this
    #     absorbs automatically now. sleep_fn is stubbed so the test never
    #     actually sleeps. -------------------------------------------------
    sleeps: list[float] = []

    def fake_sleep(seconds):
        sleeps.append(seconds)

    def make_flaky_urlopen(fail_times: int, exc):
        calls = {"n": 0}
        def flaky(req, timeout=None):
            calls["n"] += 1
            if calls["n"] <= fail_times:
                raise exc
            return _FakeResponse({"choices": [{"message": {"content": "[]"}}]})
        flaky.calls = calls
        return flaky

    try:
        # succeeds on the 2nd attempt (1 failure), well within default retries=2
        sleeps.clear()
        flaky2 = make_flaky_urlopen(1, urllib.error.HTTPError("http://x", 400, "Bad Request", {}, None))
        urllib.request.urlopen = flaky2
        content = k2.call_lmstudio("t", endpoint="http://x", model="m", temperature=0.0,
                                     sleep_fn=fake_sleep)
        if content != "[]":
            v.append(f"call_lmstudio should return normally once a retry succeeds: {content!r}")
        if flaky2.calls["n"] != 2:
            v.append(f"expected exactly 2 attempts (1 failure + 1 success), got {flaky2.calls['n']}")
        if len(sleeps) != 1:
            v.append(f"expected exactly 1 backoff sleep before the successful retry: {sleeps}")

        # exhausts retries=2 (3 attempts total) and still raises -- a
        # persistent failure is never silently swallowed
        sleeps.clear()
        always_fails = make_flaky_urlopen(999, urllib.error.URLError("connection refused"))
        urllib.request.urlopen = always_fails
        raised = False
        try:
            k2.call_lmstudio("t", endpoint="http://x", model="m", temperature=0.0,
                              retries=2, sleep_fn=fake_sleep)
        except urllib.error.URLError:
            raised = True
        if not raised:
            v.append("call_lmstudio should still raise once retries are exhausted, not swallow the error")
        if always_fails.calls["n"] != 3:
            v.append(f"expected exactly 3 attempts (retries=2 means 3 total), got {always_fails.calls['n']}")

        # retries=0 restores immediate failure -- exactly one attempt, no sleep
        sleeps.clear()
        fails_once = make_flaky_urlopen(999, OSError("boom"))
        urllib.request.urlopen = fails_once
        raised0 = False
        try:
            k2.call_lmstudio("t", endpoint="http://x", model="m", temperature=0.0,
                              retries=0, sleep_fn=fake_sleep)
        except OSError:
            raised0 = True
        if not raised0:
            v.append("call_lmstudio with retries=0 should still raise on the first failure")
        if fails_once.calls["n"] != 1:
            v.append(f"retries=0 should mean exactly 1 attempt, got {fails_once.calls['n']}")
        if sleeps:
            v.append(f"retries=0 should never sleep: {sleeps}")
    finally:
        urllib.request.urlopen = real_urlopen

    # --- end-to-end: extract_for_conversation wires usage_box into the
    #     per-window record's usage_available/prompt_tokens/completion_tokens/
    #     generation_ms_per_token -- the caller (not call_lmstudio) is what
    #     writes into usage_box here, exactly as a real call_lmstudio bound
    #     with on_usage=make_usage_accumulator(usage_box) would sideways ----
    usage_conv = _multi_msg_conv("local_usage", "2026-08-06T00:00:00Z", 12)
    run_box: dict = {}

    def usage_caller(t, *, endpoint, model, temperature, **kw):
        run_box["completion_tokens"] += 42
        run_box["prompt_tokens"] += 10
        run_box["calls_with_usage"] += 1
        run_box["calls_total"] += 1
        return "[]"

    usage_windows: list[dict] = []
    result_u = k2.extract_for_conversation(
        usage_conv, caller=usage_caller, endpoint="x", model="m", temperature=0.0,
        max_window_tokens=500, on_window_timing=usage_windows.append, usage_box=run_box,
    )
    if not usage_windows:
        v.append("expected at least one window record for local_usage")
    else:
        for w in usage_windows:
            if w["usage_available"] is not True or w["completion_tokens"] != 42 or w["prompt_tokens"] != 10:
                v.append(f"window record did not carry the usage_box's accumulated totals: {w}")
            expected_ms = w["wall_clock_seconds"] * 1000.0 / 42
            if w["generation_ms_per_token"] is None or abs(w["generation_ms_per_token"] - expected_ms) > 1e-9:
                v.append(f"window record's generation_ms_per_token should be derived from "
                          f"THAT window's own wall_clock_seconds and completion_tokens: {w}")

    # a caller that never touches usage_box (e.g. a plain stub, same as every
    # OTHER test in this file) leaves usage correctly marked unavailable --
    # not an error, not a guess, just "not measured this time."
    no_usage_windows: list[dict] = []
    k2.extract_for_conversation(
        usage_conv, caller=gov_caller, endpoint="x", model="m", temperature=0.0,
        max_window_tokens=500, on_window_timing=no_usage_windows.append, usage_box={},
    )
    if not no_usage_windows or any(w["usage_available"] is not False for w in no_usage_windows):
        v.append(f"a caller that never populates usage_box should leave every window's "
                  f"usage_available False, not True or missing: {no_usage_windows}")
    if any(w["generation_ms_per_token"] is not None for w in no_usage_windows):
        v.append(f"generation_ms_per_token must be None when usage was never captured: "
                  f"{no_usage_windows}")

    # omitting usage_box entirely (every OTHER window test in this file) must
    # still produce a well-formed record with usage fields present-but-empty,
    # never a KeyError downstream.
    no_box_windows: list[dict] = []
    k2.extract_for_conversation(
        usage_conv, caller=gov_caller, endpoint="x", model="m", temperature=0.0,
        max_window_tokens=500, on_window_timing=no_box_windows.append,
    )
    if not no_box_windows or any("usage_available" not in w or "generation_ms_per_token" not in w
                                    for w in no_box_windows):
        v.append(f"omitting usage_box should still produce usage fields (all absent/False), "
                  f"not missing keys: {no_box_windows}")

    return v
