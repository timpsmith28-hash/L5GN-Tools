"""tester_curator_control: Task 3's control strip -- the execution allowlist,
the real lock, per-stage model selection, and cache-invalidation counts.

Hermetic. Never touches the real ``config/local.json`` (model selections are
written to a temp path in every test here) and never spawns the real
pipeline scripts (``run_stage``'s ``runner`` is injected).
"""
from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

from chronicler.review import curator_control as ctl


@dataclass
class _FakeProc:
    returncode: int
    stdout: str = ""
    stderr: str = ""


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
                                runner=lambda *a, **k: _FakeProc(0, "unused", ""))
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
        # runner, never a real subprocess (hermetic).
        outcome = ctl.execute_with_lock(
            "K3", lock_path=lock_path, host="isolated-test-host",
            runner=lambda *a, **k: _FakeProc(0, "ok", ""))
        if outcome.state != "success":
            v.append(f"curator_control: injected-success run must classify success, got {outcome.state}")
        if ctl.lock_status(lock_path=lock_path)["locked"]:
            v.append("curator_control: execute_with_lock left the lock held after completing")

    return v
