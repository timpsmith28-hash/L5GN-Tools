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
    import extract_claims as k2

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

    # --- similarity() must not penalize a long candidate that genuinely
    #     contains the answer, against a short irrelevant stub -- this is
    #     the exact real-run failure mode (a 51-char heading outscoring an
    #     8,000-char section that actually held the content) that motivated
    #     switching away from SequenceMatcher.ratio()'s symmetric formula --
    claim = "The free tier seat cap is 3 seats per workspace"
    short_stub = "3. How it actually works (the corrected model)"
    long_real = (
        "Lorem ipsum dolor sit amet consectetur adipiscing elit sed do eiusmod "
        "tempor incididunt ut labore et dolore magna aliqua. " * 20
        + "The free tier seat cap is 3 seats per workspace, agreed in the pricing "
          "review. " + "Ut enim ad minim veniam quis nostrud exercitation. " * 20
    )
    sim_stub = k4.similarity(claim, short_stub)
    sim_real = k4.similarity(claim, long_real)
    if sim_real <= sim_stub:
        v.append(f"similarity() still penalizes a long chunk that actually contains the "
                  f"claim: real={sim_real:.4f} vs irrelevant short stub={sim_stub:.4f} "
                  f"(real should score higher)")
    ranked = k4.shortlist(claim, [
        {"file": "f.md", "heading": "stub", "text": short_stub},
        {"file": "f.md", "heading": "real", "text": long_real},
    ], k=2)
    if not ranked or ranked[0]["heading"] != "real":
        v.append(f"shortlist() should rank the chunk that actually contains the claim "
                  f"above an irrelevant short stub, regardless of chunk length: {ranked}")

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

    # --- real transport: response_format schema selection by system prompt --
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
        return _FakeResponse({"choices": [{"message": {"content": "{}"}}]})

    real_urlopen = urllib.request.urlopen
    try:
        urllib.request.urlopen = fake_urlopen

        if k4.DEFAULT_TIMEOUT != 900.0:
            v.append(f"match_claims DEFAULT_TIMEOUT should be 900s: {k4.DEFAULT_TIMEOUT!r}")

        k4.call_lmstudio_generic("p", system=k4.CONFIRM_CHUNK_SYSTEM, endpoint="http://x",
                                   model="m", temperature=0.0)
        if captured["timeout"] != k4.DEFAULT_TIMEOUT:
            v.append("call_lmstudio_generic did not default to DEFAULT_TIMEOUT")
        rf = captured["payload"].get("response_format")
        if rf is None or rf["json_schema"]["schema"] != k4.CONFIRM_CHUNK_SCHEMA:
            v.append("call_lmstudio_generic did not select CONFIRM_CHUNK_SCHEMA for "
                      "CONFIRM_CHUNK_SYSTEM")

        captured.clear()
        k4.call_lmstudio_generic("p", system=k4.CONFIRM_SUPERSEDE_SYSTEM, endpoint="http://x",
                                   model="m", temperature=0.0)
        rf = captured["payload"].get("response_format")
        if rf is None or rf["json_schema"]["schema"] != k4.CONFIRM_SUPERSEDE_SCHEMA:
            v.append("call_lmstudio_generic did not select CONFIRM_SUPERSEDE_SCHEMA for "
                      "CONFIRM_SUPERSEDE_SYSTEM")

        captured.clear()
        k4.call_lmstudio_generic("p", system=k4.CONFIRM_CHUNK_SYSTEM, endpoint="http://x",
                                   model="m", temperature=0.0, json_mode=False)
        if "response_format" in captured["payload"]:
            v.append("call_lmstudio_generic with json_mode=False must not send response_format")
    finally:
        urllib.request.urlopen = real_urlopen

    # --- merge_matches: a --project-scoped re-run replaces that project's
    #     claims wholesale, leaves every other project's claims untouched ----
    old_matches = {
        "model_id": "old-model", "claims": [
            {"project_id": "proj-a", "conversation_id": "c1", "claim_text": "old a", "outcome": "gap"},
            {"project_id": "proj-b", "conversation_id": "c2", "claim_text": "b claim", "outcome": "captured"},
        ],
    }
    new_matches = {
        "model_id": "new-model", "claims": [
            {"project_id": "proj-a", "conversation_id": "c1", "claim_text": "refreshed a", "outcome": "captured"},
        ],
    }
    merged_m = k4.merge_matches(old_matches, new_matches, touched_projects={"proj-a"})
    by_proj = {(c["project_id"], c["conversation_id"]): c for c in merged_m["claims"]}
    if by_proj[("proj-a", "c1")]["claim_text"] != "refreshed a":
        v.append("merge_matches should replace the touched project's claims with this run's")
    if ("proj-b", "c2") not in by_proj:
        v.append("merge_matches dropped an untouched project's claims")
    if merged_m["model_id"] != "new-model":
        v.append("merge_matches should keep the new run's own provenance")
    if merged_m["partial_run_projects"] != ["proj-a"]:
        v.append(f"merge_matches should record which projects were scoped: {merged_m.get('partial_run_projects')}")

    merged_m_none = k4.merge_matches(None, new_matches, touched_projects={"proj-a"})
    if merged_m_none is not new_matches:
        v.append("merge_matches with old=None should return the new report unchanged")

    # --- progress callback: fires once per claim, ends at (n, n); a run
    #     with no callback (every match_claims() call above) is unaffected --
    progress_calls = []
    k4.match_claims(claims, corpus_index, caller=stub_caller, endpoint="x", model="test-model",
                      temperature=0.0, progress=lambda done, total: progress_calls.append((done, total)))
    if not progress_calls or progress_calls[-1] != (len(claims), len(claims)):
        v.append(f"match_claims's progress callback should end at (n, n): {progress_calls}")
    if len(progress_calls) != len(claims):
        v.append(f"match_claims's progress callback should fire exactly once per claim: "
                  f"{len(progress_calls)} calls for {len(claims)} claims")

    # --- resumable cache: a second run against the SAME claims + corpus
    #     should reuse every decision from the cache and make ZERO network
    #     calls, while producing byte-identical outcomes (including the
    #     supersession chain, which depends on established-list state) -----
    call_count = {"n": 0}

    def counting_caller(prompt, *, system, endpoint, model, temperature):
        call_count["n"] += 1
        return stub_caller(prompt, system=system, endpoint=endpoint, model=model, temperature=temperature)

    cache: dict = {}
    first = k4.match_claims(claims, corpus_index, caller=counting_caller, endpoint="x",
                              model="test-model", temperature=0.0, cache=cache)
    first_calls = call_count["n"]
    if first_calls == 0:
        v.append("first cached run should still have made network calls (cache was empty)")
    if "results" not in cache or len(cache["results"]) != len(claims):
        v.append(f"cache should hold one entry per claim after a full run: {cache.get('results')}")

    call_count["n"] = 0
    second = k4.match_claims(claims, corpus_index, caller=counting_caller, endpoint="x",
                               model="test-model", temperature=0.0, cache=cache)
    if call_count["n"] != 0:
        v.append(f"a second run against an unchanged corpus should reuse the cache entirely "
                  f"and make zero network calls, made {call_count['n']}")
    if [c["outcome"] for c in second["claims"]] != [c["outcome"] for c in first["claims"]]:
        v.append("a fully cached re-run should reproduce the same outcomes as the original "
                  "(supersession chain must survive being replayed from cache)")
    by_conv2 = {c["conversation_id"]: c for c in second["claims"]}
    if by_conv2["c-old"]["outcome"] != "superseded" or \
       (by_conv2["c-old"]["supersedes"] or {}).get("newer_conversation_id") != "c-new2":
        v.append(f"cached re-run lost the supersession chain: {by_conv2['c-old']}")

    # A claim NOT in the cache (e.g. from a newly re-extracted conversation)
    # is still computed fresh even though the cache is otherwise fully
    # populated -- new claims are never blocked by an unrelated cache.
    call_count["n"] = 0
    extra_claim = {"project_id": "proj-b", "conversation_id": "c-brand-new",
                     "real_time": "2026-08-05T00:00:00Z", "claim_text": "Renewal notices fire 30 days ahead",
                     "quoted_source": "renewal reminder at 30 days"}
    third = k4.match_claims(claims + [extra_claim], corpus_index, caller=counting_caller, endpoint="x",
                              model="test-model", temperature=0.0, cache=cache)
    if call_count["n"] == 0:
        v.append("a brand-new claim not in the cache should still trigger network calls")
    if len(third["claims"]) != len(claims) + 1:
        v.append("a new claim alongside cached ones should appear in the result")

    # Corpus change invalidates the ENTIRE cache (coarse, deliberately) --
    # confirm the fingerprint mismatch clears prior entries rather than
    # silently reusing stale decisions against a different corpus.
    changed_corpus = json.loads(json.dumps(corpus_index))
    changed_corpus["projects"][0]["files"][0]["chunks"][0]["text"] += " -- edited"
    call_count["n"] = 0
    k4.match_claims(claims, changed_corpus, caller=counting_caller, endpoint="x",
                      model="test-model", temperature=0.0, cache=cache)
    if call_count["n"] == 0:
        v.append("a changed corpus should invalidate the cache and trigger fresh network calls")

    # --- on_checkpoint: fires every `checkpoint_every` claims and once more
    #     at the end, receiving a result-shaped dict each time ---------------
    checkpoints = []
    fresh_cache: dict = {}
    k4.match_claims(claims, corpus_index, caller=stub_caller, endpoint="x", model="test-model",
                      temperature=0.0, cache=fresh_cache, on_checkpoint=checkpoints.append,
                      checkpoint_every=2)
    if len(checkpoints) < 2:
        v.append(f"on_checkpoint should fire more than once for 5 claims at checkpoint_every=2: "
                  f"{len(checkpoints)} checkpoints")
    if "claims" not in checkpoints[0]:
        v.append("on_checkpoint should receive a result-shaped dict (with a 'claims' key)")
    if len(checkpoints[-1]["claims"]) != len(claims):
        v.append("the final on_checkpoint call should carry the complete result")
    # on_checkpoint must never fire when no cache is supplied (nothing to
    # checkpoint, and no caller should be required to handle it).
    def _boom(_):
        raise AssertionError("on_checkpoint must not be called without a cache")
    k4.match_claims(claims, corpus_index, caller=stub_caller, endpoint="x", model="test-model",
                      temperature=0.0, cache=None, on_checkpoint=_boom)

    # --- COWORK_BRIEF_conductor.md Task 1: --model-ttl -> payload `ttl` ----
    captured3 = {}

    def fake_urlopen3(req, timeout=None):
        captured3["payload"] = json.loads(req.data.decode("utf-8"))
        return _FakeResponse({"choices": [{"message": {"content": "{}"}}]})

    try:
        urllib.request.urlopen = fake_urlopen3
        k4.call_lmstudio_generic("p", system=k4.CONFIRM_CHUNK_SYSTEM, endpoint="http://x",
                                   model="m", temperature=0.0)
        if "ttl" in captured3["payload"]:
            v.append("call_lmstudio_generic with no ttl given must not send a `ttl` field")

        k4.call_lmstudio_generic("p", system=k4.CONFIRM_CHUNK_SYSTEM, endpoint="http://x",
                                   model="m", temperature=0.0, ttl=90.0)
        if captured3["payload"].get("ttl") != 90.0:
            v.append(f"call_lmstudio_generic(ttl=90.0) should send payload['ttl']==90.0, "
                      f"got {captured3['payload'].get('ttl')!r}")
    finally:
        urllib.request.urlopen = real_urlopen

    # --- COWORK_BRIEF_conductor.md Task 1: cool-down sleeps BETWEEN
    #     conversations (never mid-conversation, never after the last one),
    #     and a per-conversation timing line carries claim_count (K4 has no
    #     message_count -- it never sees a Conversation object). Two claims
    #     share "c-tl1", one is alone in "c-tl2"; an empty corpus makes every
    #     claim a fast, deterministic "gap" so this stays about the pacing
    #     mechanics, not outcome correctness (already covered above). -------
    empty_corpus = {"projects": []}
    tl_claims = [
        {"project_id": "proj-a", "conversation_id": "c-tl1", "real_time": "2026-08-01T00:00:00Z",
         "claim_text": "claim 1a", "quoted_source": "q1a"},
        {"project_id": "proj-a", "conversation_id": "c-tl1", "real_time": "2026-08-01T00:00:00Z",
         "claim_text": "claim 1b", "quoted_source": "q1b"},
        {"project_id": "proj-a", "conversation_id": "c-tl2", "real_time": "2026-07-01T00:00:00Z",
         "claim_text": "claim 2a", "quoted_source": "q2a"},
    ]

    def gap_caller(prompt, *, system, endpoint, model, temperature):
        if system == k4.CONFIRM_CHUNK_SYSTEM:
            return json.dumps({"confirmed": False, "matched_span": ""})
        return json.dumps({"conflicts": False, "matched_span": ""})

    tl_sleeps: list[float] = []
    k4.match_claims(tl_claims, empty_corpus, caller=gap_caller, endpoint="x", model="test-model",
                      temperature=0.0, cool_down=7.0, sleep_fn=tl_sleeps.append)
    if tl_sleeps != [7.0]:
        v.append(f"2 conversations (c-tl1 x2 claims, c-tl2 x1) with cool_down=7.0 should "
                  f"sleep exactly once, between conversations, never mid-conversation and "
                  f"never after the last: {tl_sleeps}")

    tl_sleeps_zero: list[float] = []
    k4.match_claims(tl_claims, empty_corpus, caller=gap_caller, endpoint="x", model="test-model",
                      temperature=0.0, cool_down=0.0, sleep_fn=tl_sleeps_zero.append)
    if tl_sleeps_zero:
        v.append(f"cool_down=0.0 (the default) must never sleep: {tl_sleeps_zero}")

    tl_timing: list[dict] = []
    k4.match_claims(tl_claims, empty_corpus, caller=gap_caller, endpoint="x", model="timing-model",
                      temperature=0.0, on_timing=tl_timing.append)
    if len(tl_timing) != 2:
        v.append(f"expected one timing record per CONVERSATION (not per claim): {len(tl_timing)}")
    else:
        by_id = {r["conversation_id"]: r for r in tl_timing}
        if by_id["c-tl1"]["claim_count"] != 2:
            v.append(f"c-tl1 has 2 claims -- timing record claim_count should say so: {by_id['c-tl1']}")
        if by_id["c-tl2"]["claim_count"] != 1:
            v.append(f"c-tl2 has 1 claim -- timing record claim_count should say so: {by_id['c-tl2']}")
        if by_id["c-tl1"]["project_id"] != "proj-a" or by_id["c-tl1"]["model_id"] != "timing-model":
            v.append(f"timing record missing project_id/model_id: {by_id['c-tl1']}")
        if not isinstance(by_id["c-tl1"]["wall_clock_seconds"], float) or by_id["c-tl1"]["wall_clock_seconds"] < 0:
            v.append(f"timing record wall_clock_seconds should be a non-negative float: {by_id['c-tl1']}")

    # a conversation whose claims are ALL cache hits made no network call --
    # it should get neither a timing record nor a cool-down sleep.
    warm_cache: dict = {}
    k4.match_claims(tl_claims, empty_corpus, caller=gap_caller, endpoint="x", model="test-model",
                      temperature=0.0, cache=warm_cache)
    cached_sleeps: list[float] = []
    cached_timing: list[dict] = []
    k4.match_claims(tl_claims, empty_corpus, caller=gap_caller, endpoint="x", model="test-model",
                      temperature=0.0, cache=warm_cache, cool_down=3.0, sleep_fn=cached_sleeps.append,
                      on_timing=cached_timing.append)
    if cached_sleeps or cached_timing:
        v.append(f"an all-cache-hit re-run should emit no timing records and never sleep: "
                  f"sleeps={cached_sleeps} timing={cached_timing}")

    # omitting cool_down/on_timing entirely (every match_claims() call above
    # this point) must leave behaviour and results completely unchanged --
    # already implicitly proven by every earlier assertion in this file.

    # --- make_timing_reporter: human line to stream + optional JSONL file --
    import io
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        buf = io.StringIO()
        jsonl_path = td_path / "timing.jsonl"
        reporter = k4.make_timing_reporter(stream=buf, jsonl_path=jsonl_path)
        reporter({"conversation_id": "c1", "project_id": "p1", "claim_count": 2,
                   "model_id": "m1", "cool_down_preceded": False, "wall_clock_seconds": 2.25})
        written = buf.getvalue()
        if "TIMING" not in written or "conversation_id=c1" not in written or "claim_count=2" not in written:
            v.append(f"make_timing_reporter did not write the expected TIMING line: {written!r}")
        if not jsonl_path.exists():
            v.append("make_timing_reporter with jsonl_path given should create the file")
        else:
            lines = jsonl_path.read_text(encoding="utf-8").strip().splitlines()
            if len(lines) != 1 or "timestamp" not in json.loads(lines[0]):
                v.append(f"JSONL timing record missing fields: {lines}")

    # =========================================================================
    # COWORK_BRIEF_conductor_governor.md Task 1: finer timing records
    # =========================================================================

    # --- item 1: a per-CLAIM record, the finer unit K4 has (no window
    #     concept -- shortlist-plus-confirm per claim IS the unit) ----------
    gov_claim_timing: list[dict] = []
    k4.match_claims(tl_claims, empty_corpus, caller=gap_caller, endpoint="x", model="test-model",
                      temperature=0.0, on_claim_timing=gov_claim_timing.append)
    if len(gov_claim_timing) != len(tl_claims):
        v.append(f"expected one on_claim_timing record per claim that made a network call "
                  f"({len(tl_claims)} claims, none cached): {len(gov_claim_timing)}")
    else:
        c1a, c1b, c2a = gov_claim_timing
        if c1a["conversation_id"] != "c-tl1" or c2a["conversation_id"] != "c-tl2":
            v.append(f"claim timing records out of order or misattributed: {gov_claim_timing}")
        if c1a["project_id"] != "proj-a" or c1a["model_id"] != "test-model":
            v.append(f"claim timing record missing project_id/model_id: {c1a}")
        if not isinstance(c1a["wall_clock_seconds"], float) or c1a["wall_clock_seconds"] < 0:
            v.append(f"claim timing record wall_clock_seconds should be a non-negative float: {c1a}")

    # a claim served from cache made no network call -- no on_claim_timing
    # for it, same as the conversation-level on_timing behaviour.
    warm_cache2: dict = {}
    k4.match_claims(tl_claims, empty_corpus, caller=gap_caller, endpoint="x", model="test-model",
                      temperature=0.0, cache=warm_cache2)
    cached_claim_timing: list[dict] = []
    k4.match_claims(tl_claims, empty_corpus, caller=gap_caller, endpoint="x", model="test-model",
                      temperature=0.0, cache=warm_cache2, on_claim_timing=cached_claim_timing.append)
    if cached_claim_timing:
        v.append(f"an all-cache-hit re-run should emit no on_claim_timing records: "
                  f"{cached_claim_timing}")

    # --- item 2: cool_down_preceded at claim granularity -- True only for
    #     the FIRST network-making claim of a conversation immediately after
    #     a cool-down sleep, never for its later claims or the first run ----
    gov_conv_timing2: list[dict] = []
    gov_claim_timing2: list[dict] = []
    k4.match_claims(tl_claims, empty_corpus, caller=gap_caller, endpoint="x", model="test-model",
                      temperature=0.0, cool_down=2.0, sleep_fn=lambda s: None,
                      on_timing=gov_conv_timing2.append, on_claim_timing=gov_claim_timing2.append)
    conv_by_id = {r["conversation_id"]: r for r in gov_conv_timing2}
    if conv_by_id["c-tl1"]["cool_down_preceded"] is not False:
        v.append("c-tl1 is the FIRST conversation of the run -- never cool_down_preceded")
    if conv_by_id["c-tl2"]["cool_down_preceded"] is not True:
        v.append("c-tl2 immediately follows a cool-down sleep -- should be flagged")

    claims_for_c1 = [r for r in gov_claim_timing2 if r["conversation_id"] == "c-tl1"]
    if len(claims_for_c1) != 2 or any(r["cool_down_preceded"] for r in claims_for_c1):
        v.append(f"c-tl1's claims are the run's first -- neither should be cool_down_preceded: "
                  f"{claims_for_c1}")
    claims_for_c2 = [r for r in gov_claim_timing2 if r["conversation_id"] == "c-tl2"]
    if not claims_for_c2 or claims_for_c2[0]["cool_down_preceded"] is not True:
        v.append(f"c-tl2's only (and therefore first) claim follows a cool-down -- should be "
                  f"flagged: {claims_for_c2}")

    # --- item 3: the conversation-boundary assumption is ASSERTED -- a
    #     conversation_id reappearing after its run already closed out must
    #     fail loudly (ValueError), never silently double-count -------------
    non_contiguous_claims = [
        {"project_id": "proj-a", "conversation_id": "c-x", "real_time": "2026-08-01T00:00:00Z",
         "claim_text": "x1", "quoted_source": "qx1"},
        {"project_id": "proj-a", "conversation_id": "c-y", "real_time": "2026-07-25T00:00:00Z",
         "claim_text": "y1", "quoted_source": "qy1"},
        {"project_id": "proj-a", "conversation_id": "c-x", "real_time": "2026-08-01T00:00:00Z",
         "claim_text": "x2", "quoted_source": "qx2"},  # c-x reappears -- non-contiguous
    ]
    raised = False
    try:
        k4.match_claims(non_contiguous_claims, empty_corpus, caller=gap_caller, endpoint="x",
                          model="test-model", temperature=0.0)
    except ValueError as e:
        raised = True
        if "c-x" not in str(e):
            v.append(f"the ValueError should name the conversation that reappeared: {e}")
    if not raised:
        v.append("a non-contiguous conversation_id stream should raise ValueError loudly, "
                  "not silently double-count")

    # A genuinely contiguous stream (the normal case, exercised throughout
    # this file already) must never raise.
    k4.match_claims(tl_claims, empty_corpus, caller=gap_caller, endpoint="x", model="test-model",
                      temperature=0.0)  # no exception == pass

    # =========================================================================
    # COWORK_BRIEF_conductor_governor.md Addendum 2: usage capture, generation
    # ms/token in K4's per-claim records. K2's own tester covers the shared
    # primitives (reset_usage_box/make_usage_accumulator/usage_from_box/
    # generation_ms_per_token) exhaustively -- this file covers K4-specific
    # wiring: call_lmstudio_generic's on_usage, and accumulation across
    # SEVERAL confirm calls that can belong to one claim.
    # =========================================================================

    # --- call_lmstudio_generic: on_usage present/absent, return value
    #     unaffected either way -----------------------------------------------
    usage_calls: list = []

    def usage_urlopen_present(req, timeout=None):
        return _FakeResponse({
            "choices": [{"message": {"content": "{}"}}],
            "usage": {"prompt_tokens": 77, "completion_tokens": 33, "total_tokens": 110},
        })

    def usage_urlopen_absent(req, timeout=None):
        return _FakeResponse({"choices": [{"message": {"content": "{}"}}]})

    try:
        urllib.request.urlopen = usage_urlopen_present
        content = k4.call_lmstudio_generic("p", system=k4.CONFIRM_CHUNK_SYSTEM, endpoint="http://x",
                                             model="m", temperature=0.0, on_usage=usage_calls.append)
        if content != "{}":
            v.append("call_lmstudio_generic's return value must be unaffected by on_usage")
        if usage_calls != [{"completion_tokens": 33, "prompt_tokens": 77}]:
            v.append(f"on_usage should fire once with the response's usage block: {usage_calls}")

        usage_calls.clear()
        urllib.request.urlopen = usage_urlopen_absent
        k4.call_lmstudio_generic("p", system=k4.CONFIRM_CHUNK_SYSTEM, endpoint="http://x",
                                   model="m", temperature=0.0, on_usage=usage_calls.append)
        if usage_calls != [None]:
            v.append(f"on_usage should fire with None when usage is absent -- never estimated: "
                      f"{usage_calls}")
    finally:
        urllib.request.urlopen = real_urlopen

    # --- call_lmstudio_generic retries: shares extract_claims.
    #     post_json_with_retry with K2, so this just confirms K4's call site
    #     wires it through -- a transient failure clears within the retry
    #     budget without disturbing the return value, and a persistent one
    #     still raises once exhausted. Full retry-count/backoff/exhaustion
    #     coverage lives in tester_extract_claims.py against the shared
    #     primitive; not re-litigated here. ------------------------------
    sleeps: list[float] = []

    def fake_sleep(seconds):
        sleeps.append(seconds)

    def make_flaky_urlopen(fail_times: int, exc):
        calls = {"n": 0}
        def flaky(req, timeout=None):
            calls["n"] += 1
            if calls["n"] <= fail_times:
                raise exc
            return _FakeResponse({"choices": [{"message": {"content": "{}"}}]})
        flaky.calls = calls
        return flaky

    try:
        flaky = make_flaky_urlopen(1, urllib.error.HTTPError("http://x", 400, "Bad Request", {}, None))
        urllib.request.urlopen = flaky
        content = k4.call_lmstudio_generic("p", system=k4.CONFIRM_CHUNK_SYSTEM, endpoint="http://x",
                                             model="m", temperature=0.0, sleep_fn=fake_sleep)
        if content != "{}":
            v.append(f"call_lmstudio_generic should return normally once a retry succeeds: {content!r}")
        if flaky.calls["n"] != 2:
            v.append(f"expected exactly 2 attempts (1 failure + 1 success), got {flaky.calls['n']}")

        always_fails = make_flaky_urlopen(999, urllib.error.URLError("connection refused"))
        urllib.request.urlopen = always_fails
        raised = False
        try:
            k4.call_lmstudio_generic("p", system=k4.CONFIRM_CHUNK_SYSTEM, endpoint="http://x",
                                       model="m", temperature=0.0, retries=2, sleep_fn=fake_sleep)
        except urllib.error.URLError:
            raised = True
        if not raised:
            v.append("call_lmstudio_generic should still raise once retries are exhausted")
        if always_fails.calls["n"] != 3:
            v.append(f"expected exactly 3 attempts (retries=2), got {always_fails.calls['n']}")
    finally:
        urllib.request.urlopen = real_urlopen

    # --- accumulation across SEVERAL confirm_chunk calls belonging to ONE
    #     match_against_corpus call -- a claim can cost more than one
    #     underlying network call (up to SHORTLIST_SIZE candidates), and the
    #     box must SUM across all of them, not keep only the last -----------
    multi_calls: list = []
    multi_box: dict = {}
    k2.reset_usage_box(multi_box)

    def multi_confirm_caller(prompt, *, system, endpoint, model, temperature):
        multi_calls.append(prompt)
        multi_box["completion_tokens"] += 7
        multi_box["prompt_tokens"] += 3
        multi_box["calls_with_usage"] += 1
        multi_box["calls_total"] += 1
        return json.dumps({"confirmed": False, "matched_span": ""})

    multi_chunks = [
        {"file": "f.md", "heading": f"h{i}", "text": "the quick brown fox jumps over the lazy dog"}
        for i in range(3)
    ]
    k4.match_against_corpus("the quick brown fox jumps", multi_chunks, caller=multi_confirm_caller,
                              endpoint="x", model="m", temperature=0.0)
    if len(multi_calls) < 2:
        v.append(f"expected several confirm_chunk calls across multiple shortlisted "
                  f"candidates (none confirmed): {len(multi_calls)}")
    multi_usage = k2.usage_from_box(multi_box)
    if (multi_usage["usage_available"] is not True
            or multi_usage["completion_tokens"] != 7 * len(multi_calls)
            or multi_usage["prompt_tokens"] != 3 * len(multi_calls)):
        v.append(f"usage_box should SUM across every confirm_chunk call for the match, not "
                  f"just the last one: {multi_usage} over {len(multi_calls)} calls")

    # --- end-to-end: match_claims wires usage_box into on_claim_timing's
    #     usage_available/prompt_tokens/completion_tokens/
    #     generation_ms_per_token. One chunk that matches all three claims'
    #     text confirms immediately (one call per claim, clean 1:1). --------
    usage_corpus = {
        "projects": [{
            "project_id": "proj-a",
            "files": [{"file": "f.md", "chunks": [
                {"heading": "h", "text": "claim 1a claim 1b claim 2a shared keywords for matching"},
            ]}],
        }],
    }

    def confirm_always(prompt, *, system, endpoint, model, temperature):
        run_box["completion_tokens"] += 42
        run_box["prompt_tokens"] += 10
        run_box["calls_with_usage"] += 1
        run_box["calls_total"] += 1
        return json.dumps({"confirmed": True, "matched_span": "claim"})

    run_box: dict = {}
    claim_usage_records: list[dict] = []
    k4.match_claims(tl_claims, usage_corpus, caller=confirm_always, endpoint="x",
                      model="usage-model", on_claim_timing=claim_usage_records.append,
                      usage_box=run_box, temperature=0.0)
    if len(claim_usage_records) != len(tl_claims):
        v.append(f"expected one on_claim_timing record per claim: {len(claim_usage_records)}")
    else:
        for rec in claim_usage_records:
            if rec["usage_available"] is not True or rec["completion_tokens"] != 42 or rec["prompt_tokens"] != 10:
                v.append(f"claim record did not carry usage_box's per-claim totals "
                          f"(reset before each claim, not accumulated across claims): {rec}")
            expected_ms = rec["wall_clock_seconds"] * 1000.0 / 42
            if rec["generation_ms_per_token"] is None or abs(rec["generation_ms_per_token"] - expected_ms) > 1e-9:
                v.append(f"claim record's generation_ms_per_token should derive from THAT "
                          f"claim's own wall_clock_seconds and completion_tokens: {rec}")

    # a claim served from cache makes no network call and gets no on_claim_timing
    # record at all (already covered above) -- confirms usage_box is never even
    # touched for it, consistent with "absent, never estimated."

    # omitting usage_box entirely must still produce well-formed usage fields
    # (present but empty), never a KeyError, and must not change outcomes.
    no_box_records: list[dict] = []
    result_no_box = k4.match_claims(tl_claims, usage_corpus, caller=confirm_always, endpoint="x",
                                      model="usage-model", on_claim_timing=no_box_records.append,
                                      temperature=0.0)
    if not no_box_records or any(
        "usage_available" not in r or "generation_ms_per_token" not in r for r in no_box_records
    ):
        v.append(f"omitting usage_box should still produce usage fields (all absent/False), "
                  f"not missing keys: {no_box_records}")
    if any(r["usage_available"] is not False for r in no_box_records):
        v.append(f"omitting usage_box should leave usage_available False for every claim: "
                  f"{no_box_records}")
    if not result_no_box["claims"] or any(c["outcome"] != "captured" for c in result_no_box["claims"]):
        v.append("omitting usage_box must not change match outcomes")

    return v
