"""tester_curator_control: Task 3's control strip -- the execution allowlist,
the real lock, per-stage model selection, and cache-invalidation counts.
Also Task 5' (COWORK_BRIEF_conductor_governor.md): the streaming executor,
the pid+heartbeat lock, and cancellation (queued vs in-flight).

Hermetic. Never touches the real ``config/local.json`` (model selections are
written to a temp path in every test here) and never spawns the real
pipeline scripts (``run_stage``'s ``popen_factory`` is injected).
"""
from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path

from chronicler.review import curator_control as ctl


class _FakePopen:
    """Stands in for `subprocess.Popen` -- `stdout` is an iterator of lines
    (as `_default_popen`'s merged, text-mode stream would yield), `wait()`
    returns the fixed returncode, `terminate()` just records that it was
    called (a fake process has nothing real to kill)."""

    def __init__(self, lines: list[str], returncode: int = 0):
        self._lines = lines
        self._returncode = returncode
        self.stdout = iter(lines)
        self.terminated = False

    def wait(self) -> int:
        return self._returncode

    def terminate(self) -> None:
        self.terminated = True


def run() -> list[str]:
    v: list[str] = []

    # --- the execution allowlist: a stage key is the ONLY thing accepted ---
    if ctl.EXECUTION_ALLOWLIST != frozenset(ctl.STAGE_TABLE):
        v.append("curator_control: EXECUTION_ALLOWLIST must be derived from "
                 "STAGE_TABLE, not maintained separately")
    try:
        ctl.run_stage("K9-not-real")
        v.append("curator_control: run_stage accepted a stage key not on the allowlist")
    except ctl.ExecutionRefused as exc:
        if exc.reason != "not_allowlisted":
            v.append(f"curator_control: wrong refusal reason for a bad stage key: {exc.reason}")

    # --- K2/K4 argv gets the full chat-completions URL, not the bare host:port
    # base (extract_claims.py / match_claims.py POST to --endpoint literally;
    # a bare base like "http://localhost:1234" hits "/" and LM Studio answers
    # "Unexpected endpoint or method") ---------------------------------------
    for stage in ("K2", "K4"):
        argv = ctl.STAGE_TABLE[stage]["argv"]({stage: "gemma-4"})
        if argv is None or "--endpoint" not in argv:
            v.append(f"curator_control: {stage} argv must pass --endpoint")
        else:
            ep = argv[argv.index("--endpoint") + 1]
            if not ep.endswith("/v1/chat/completions"):
                v.append(f"curator_control: {stage} --endpoint must be the full "
                          f"chat-completions URL, got {ep!r}")
    already_full = ctl.chat_completions_endpoint("http://localhost:1234/v1/chat/completions")
    if already_full != "http://localhost:1234/v1/chat/completions":
        v.append("curator_control: chat_completions_endpoint must not double-append "
                  f"the suffix, got {already_full!r}")

    # --- K0/K1/K3/K5 offer no model selector --------------------------------
    for stage in ("K0", "K1", "K3", "K5"):
        if stage in ctl.MODEL_SELECTABLE_STAGES:
            v.append(f"curator_control: {stage} must not be model-selectable (deterministic)")
    for stage in ("K2", "K4"):
        if stage not in ctl.MODEL_SELECTABLE_STAGES:
            v.append(f"curator_control: {stage} must be model-selectable")

    # --- K4's shortlist is a capability display, never a selector ----------
    cap = ctl.shortlist_capability()
    if cap["selectable"]:
        v.append("curator_control: K4's shortlist step must not be offered as a selector")
    if "difflib" not in cap["method"]:
        v.append("curator_control: shortlist capability must name the real "
                 "method in code today (difflib.SequenceMatcher), not an "
                 "aspirational embedding path")

    # --- model selection: config/local.json, keyed by hostname, isolated ---
    with tempfile.TemporaryDirectory() as tmp:
        local_json = Path(tmp) / "local.json"
        local_json.write_text(json.dumps({"other-host": {"estate": "personal"}}), encoding="utf-8")
        try:
            ctl.set_curator_model("K0", "some-model", host="rig-a", path=local_json)
            v.append("curator_control: set_curator_model accepted a non-selectable stage (K0)")
        except ValueError:
            pass
        result = ctl.set_curator_model("K2", "qwen-14b", host="rig-a", path=local_json)
        if result["model_id"] != "qwen-14b":
            v.append(f"curator_control: set_curator_model result wrong: {result}")
        data = json.loads(local_json.read_text(encoding="utf-8"))
        if "other-host" not in data:
            v.append("curator_control: writing one host's selection clobbered "
                     "another host's existing config/local.json entry")
        selections = ctl.get_curator_models(host="rig-a", path=local_json)
        if selections.get("K2") != "qwen-14b":
            v.append(f"curator_control: get_curator_models did not read back the "
                     f"selection: {selections}")
        # a second stage selection must not clobber the first
        ctl.set_curator_model("K4", "qwen-32b", host="rig-a", path=local_json)
        selections2 = ctl.get_curator_models(host="rig-a", path=local_json)
        if selections2.get("K2") != "qwen-14b" or selections2.get("K4") != "qwen-32b":
            v.append(f"curator_control: second selection clobbered the first: {selections2}")

    # --- cache-invalidation counts: real numbers from fixture cache files ---
    with tempfile.TemporaryDirectory() as tmp:
        cache_dir = Path(tmp)
        k2_cache = cache_dir / "claims_cache.json"
        k2_cache.write_text(json.dumps({
            "conv1": {"sources": [], "claims": []}, "conv2": {"sources": [], "claims": []},
            "conv3": {"sources": [], "claims": []},
        }), encoding="utf-8")
        impact = ctl.k2_model_change_impact(cache_path=k2_cache)
        if impact["cached_conversations"] != 3:
            v.append(f"curator_control: k2 impact miscounted cache entries: {impact}")
        if impact["claims_untouched"] != 0:
            v.append("curator_control: K2's cache carries no per-entry model "
                     "attribution -- a model change must not claim any claims "
                     "as provably untouched")

        k4_cache = cache_dir / "matches_cache.json"
        k4_cache.write_text(json.dumps({
            "corpus_fingerprint": "abc",
            "results": {"h1": {}, "h2": {}, "h3": {}, "h4": {}},
        }), encoding="utf-8")
        claims_json = cache_dir / "claims.json"
        claims_json.write_text(json.dumps({"claims_extracted": 312}), encoding="utf-8")
        impact4 = ctl.k4_model_change_impact(cache_path=k4_cache, claims_path=claims_json)
        if impact4["cached_verdicts"] != 4:
            v.append(f"curator_control: k4 impact miscounted verdict cache: {impact4}")
        if impact4["claims_untouched"] != 312:
            v.append(f"curator_control: k4 impact must leave claims untouched: {impact4}")
        if "312" not in impact4["detail"] or "4" not in impact4["detail"]:
            v.append(f"curator_control: k4 impact detail must state real numbers: {impact4}")

        # absent cache -> zero, never a crash
        empty_impact = ctl.k2_model_change_impact(cache_path=cache_dir / "nope.json")
        if empty_impact["cached_conversations"] != 0:
            v.append("curator_control: an absent cache must report 0, not raise")

    # --- three-state outcome classification ---------------------------------
    ok_state, _ = ctl.classify_outcome(0, "done", "")
    fail_state, _ = ctl.classify_outcome(1, "", "traceback")
    skip_state, _ = ctl.classify_outcome(0, "skipped (no input available)", "")
    if len({ok_state, fail_state, skip_state}) != 3:
        v.append(f"curator_control: success/failed/skipped must be three "
                 f"distinct states, got {ok_state}/{fail_state}/{skip_state}")

    # --- run_stage: a model stage with no selection is BLOCKED, never guessed
    with tempfile.TemporaryDirectory() as tmp:
        # point HOME/config/local.json at an empty file via a host with no
        # selections recorded -- run_stage must see argv_extra is None
        outcome = ctl.run_stage("K2", host="a-host-with-no-curator-config-at-all",
                                popen_factory=lambda *a, **k: _FakePopen(["unused"], 0))
        if outcome.state != "blocked":
            v.append(f"curator_control: K2 with no model selected must be "
                     f"blocked, not {outcome.state}")

    # --- the lock: real, refuses a second acquire, names what's running -----
    with tempfile.TemporaryDirectory() as tmp:
        lock_path = Path(tmp) / ".curator_run.lock"
        first = ctl.acquire_lock("K3", lock_path=lock_path)
        if not first["acquired"]:
            v.append("curator_control: first lock acquisition must succeed")
        second = ctl.acquire_lock("K5", lock_path=lock_path)
        if second["acquired"]:
            v.append("curator_control: a second acquire while one is held must be refused")
        if second.get("stage") != "K3" or not second.get("started_at"):
            v.append(f"curator_control: refusal must name what's running and "
                     f"when it started: {second}")
        ctl.release_lock(lock_path=lock_path)
        status = ctl.lock_status(lock_path=lock_path)
        if status["locked"]:
            v.append("curator_control: lock_status must read unlocked after release")
        third = ctl.acquire_lock("K3", lock_path=lock_path)
        if not third["acquired"]:
            v.append("curator_control: a lock must be re-acquirable after release")
        ctl.release_lock(lock_path=lock_path)

        # execute_with_lock: a bad stage key is refused before the lock is
        # ever touched (never against the real repo-relative LOCK_PATH).
        try:
            ctl.execute_with_lock("K9-not-real", lock_path=lock_path)
            v.append("curator_control: execute_with_lock accepted a stage not "
                     "on the allowlist")
        except ctl.ExecutionRefused as exc:
            if exc.reason != "not_allowlisted":
                v.append(f"curator_control: wrong refusal reason: {exc.reason}")
        if ctl.lock_status(lock_path=lock_path)["locked"]:
            v.append("curator_control: a refused execute must never leave a lock behind")

        # a real run releases the lock even on a real outcome -- injected
        # popen_factory, never a real subprocess (hermetic).
        outcome = ctl.execute_with_lock(
            "K3", lock_path=lock_path, host="isolated-test-host",
            popen_factory=lambda *a, **k: _FakePopen(["ok"], 0))
        if outcome.state != "success":
            v.append(f"curator_control: injected-success run must classify success, got {outcome.state}")
        if ctl.lock_status(lock_path=lock_path)["locked"]:
            v.append("curator_control: execute_with_lock left the lock held after completing")

    # --- Task 5': the lock carries a pid + heartbeat, and staleness is
    #     REPORTED, never acted on automatically ---------------------------
    with tempfile.TemporaryDirectory() as tmp:
        lock_path = Path(tmp) / ".curator_run.lock"
        ctl.acquire_lock("K2", lock_path=lock_path)
        status = ctl.lock_status(lock_path=lock_path)
        if status.get("pid") is None or status.get("heartbeat_at") is None:
            v.append(f"curator_control: a freshly acquired lock must carry a pid "
                     f"and an initial heartbeat_at: {status}")
        if status["stale"]:
            v.append(f"curator_control: a freshly acquired lock (heartbeat just set, "
                     f"pid is US, definitely alive) must not read stale: {status}")

        # heartbeat() updates heartbeat_at in place, touching nothing else
        before = json.loads(lock_path.read_text(encoding="utf-8"))
        ok = ctl.heartbeat(lock_path=lock_path, now=before["heartbeat_at"] + 5.0)
        if not ok:
            v.append("curator_control: heartbeat() on a held lock should return True")
        after = json.loads(lock_path.read_text(encoding="utf-8"))
        if after["heartbeat_at"] != before["heartbeat_at"] + 5.0:
            v.append(f"curator_control: heartbeat() did not update heartbeat_at: {after}")
        if after["stage"] != before["stage"] or after["pid"] != before["pid"]:
            v.append("curator_control: heartbeat() must preserve every other field "
                     "(read-modify-write, not a blind rewrite)")

        # heartbeat() on a lock nobody holds does nothing and never creates one
        ctl.release_lock(lock_path=lock_path)
        if ctl.heartbeat(lock_path=lock_path):
            v.append("curator_control: heartbeat() on a released lock should return "
                     "False, and must never resurrect a lock nobody holds")
        if lock_path.exists():
            v.append("curator_control: heartbeat() must never CREATE a lock file")

        # a lock with an old heartbeat reads stale; a fresh one does not --
        # `now` is injected so this needs no real sleep.
        ctl.acquire_lock("K4", lock_path=lock_path)
        old_status = ctl.lock_status(lock_path=lock_path, stale_after=10.0,
                                       now=time.time() + 999.0)
        if not old_status["stale"]:
            v.append(f"curator_control: a lock whose heartbeat is far in the past "
                     f"relative to `now` must read stale: {old_status}")
        fresh_status = ctl.lock_status(lock_path=lock_path, stale_after=10.0)
        if fresh_status["stale"]:
            v.append(f"curator_control: a lock heartbeated just now must not read "
                     f"stale: {fresh_status}")

        # break_lock: mandatory reason, names what it broke, never silent
        try:
            ctl.break_lock("", lock_path=lock_path)
            v.append("curator_control: break_lock must refuse an empty reason")
        except ValueError:
            pass
        broken = ctl.break_lock("stale after a killed overnight run", lock_path=lock_path)
        if not broken["broken"] or broken["reason"] != "stale after a killed overnight run":
            v.append(f"curator_control: break_lock did not record what/why: {broken}")
        if ctl.lock_status(lock_path=lock_path)["locked"]:
            v.append("curator_control: break_lock must actually clear the lock")
        # breaking an already-unlocked path is a no-op, not an error
        noop = ctl.break_lock("nothing to break", lock_path=lock_path)
        if noop["broken"]:
            v.append("curator_control: break_lock on an unlocked path should report broken=False")

        # acquire_lock itself NEVER auto-reclaims a stale lock, no matter how
        # stale lock_status would call it -- only break_lock ever clears one.
        ctl.acquire_lock("K2", lock_path=lock_path)
        still_held = ctl.acquire_lock("K4", lock_path=lock_path)
        if still_held["acquired"]:
            v.append("curator_control: acquire_lock must never silently reclaim a "
                     "lock it considers stale -- that is break_lock's job alone")
        ctl.break_lock("cleanup", lock_path=lock_path)

    # --- Task 5': streaming -- on_timing_line fires per TIMING* line, and
    #     the four-caller-site-style contract holds: a stage that emits no
    #     timing lines at all never fires it -------------------------------
    with tempfile.TemporaryDirectory() as tmp:
        lock_path = Path(tmp) / ".curator_run.lock"
        seen: list[tuple] = []
        fake_lines = [
            "extracting: 1/3 done",
            "TIMING_WINDOW conversation_id=c1 project_id=p window_index=0 windows_total=2 "
            "token_count=500 model_id=m cool_down_preceded=False usage_available=True "
            "prompt_tokens=100 completion_tokens=50 generation_ms_per_token=42.50 "
            "wall_clock_seconds=2.100",
            "TIMING_WINDOW conversation_id=c1 project_id=p window_index=1 windows_total=2 "
            "token_count=500 model_id=m cool_down_preceded=False usage_available=False "
            "prompt_tokens=None completion_tokens=None generation_ms_per_token=unavailable "
            "wall_clock_seconds=1.900",
            "extracting: 3/3 done",
        ]
        outcome = ctl.execute_with_lock(
            "K3", lock_path=lock_path, host="isolated-test-host",
            popen_factory=lambda *a, **k: _FakePopen(fake_lines, 0),
            on_timing_line=lambda kind, ms, line: seen.append((kind, ms)),
        )
        if outcome.state != "success":
            v.append(f"curator_control: streaming run should classify success, got {outcome.state}")
        if seen != [("window", 42.5), ("window", None)]:
            v.append(f"curator_control: on_timing_line should fire exactly for the 2 "
                     f"TIMING_WINDOW lines, with the parsed ms/token (or None when the "
                     f"line marks it unavailable), and for nothing else: {seen}")

        # omitting on_timing_line entirely must change nothing about the result
        baseline = ctl.execute_with_lock(
            "K3", lock_path=lock_path, host="isolated-test-host",
            popen_factory=lambda *a, **k: _FakePopen(fake_lines, 0))
        if baseline.state != "success":
            v.append("curator_control: streaming run with on_timing_line omitted "
                     "should behave exactly as before")

        # the lock heartbeats automatically during a streamed run -- by the
        # time it completes, heartbeat_at has moved past acquisition time
        # (execute_with_lock binds heartbeat_fn to THIS lock unless overridden)
        hb_calls: list[float] = []
        ctl.execute_with_lock(
            "K3", lock_path=lock_path, host="isolated-test-host",
            popen_factory=lambda *a, **k: _FakePopen(fake_lines, 0),
            heartbeat_fn=lambda: hb_calls.append(time.time()))
        if len(hb_calls) != len(fake_lines):
            v.append(f"curator_control: heartbeat_fn should fire once per streamed "
                     f"line ({len(fake_lines)} lines): got {len(hb_calls)} calls")

    # --- Task 5': cancellation -- queued (skipped, never started) vs
    #     in-flight (subprocess terminated mid-stream), the SAME token -----
    with tempfile.TemporaryDirectory() as tmp:
        lock_path = Path(tmp) / ".curator_run.lock"

        # queued: a token already set before the step starts skips it
        # entirely -- state=blocked, cancelled=True, and the fake process is
        # never even constructed (popen_factory raises if called).
        queued_token = ctl.CancelToken()
        queued_token.request()

        def _never_call(*a, **k):
            raise AssertionError("popen_factory must not be called for a queued cancellation")

        queued_outcome = ctl.execute_with_lock(
            "K3", lock_path=lock_path, host="isolated-test-host",
            popen_factory=_never_call, cancel_token=queued_token)
        if queued_outcome.state != "blocked" or not queued_outcome.cancelled:
            v.append(f"curator_control: a token cancelled before the step starts should "
                     f"produce state=blocked, cancelled=True: {queued_outcome}")
        if queued_token.is_set():
            v.append("curator_control: a consumed cancel token must not still read as set "
                     "-- one-shot, test-and-clear")
        if ctl.lock_status(lock_path=lock_path)["locked"]:
            v.append("curator_control: a queued-cancelled step must still release the lock")

        # in-flight: a token set WHILE the step is streaming terminates the
        # subprocess and marks cancelled=True, state="failed" (never a 5th
        # state) -- the process is stopped after the 2nd of many lines.
        inflight_token = ctl.CancelToken()
        long_lines = [f"line {i}" for i in range(50)]

        class _CancellingPopen(_FakePopen):
            """Requests cancellation itself partway through its own output --
            simulates an operator clicking cancel while this step streams."""
            def __init__(self):
                super().__init__(long_lines, 0)
                self._n = 0
                self._it = iter(long_lines)
            def __iter__(self):
                return self
            def __next__(self):
                self._n += 1
                if self._n == 3:
                    inflight_token.request()
                return next(self._it)

        fake_proc = _CancellingPopen()
        fake_proc.stdout = fake_proc  # iterate the wrapper itself, not the raw list

        inflight_outcome = ctl.execute_with_lock(
            "K3", lock_path=lock_path, host="isolated-test-host",
            popen_factory=lambda *a, **k: fake_proc, cancel_token=inflight_token)
        if not inflight_outcome.cancelled or inflight_outcome.state != "failed":
            v.append(f"curator_control: an in-flight cancellation should terminate the "
                     f"process and report cancelled=True, state=failed: {inflight_outcome}")
        if not fake_proc.terminated:
            v.append("curator_control: an in-flight cancellation must call terminate() "
                     "on the running process")
        if fake_proc._n >= len(long_lines):
            v.append(f"curator_control: an in-flight cancellation should stop reading "
                     f"well before the process's own output ends: consumed {fake_proc._n} "
                     f"of {len(long_lines)} lines")
        if ctl.lock_status(lock_path=lock_path)["locked"]:
            v.append("curator_control: an in-flight-cancelled step must still release the lock")

    return v
