"""tester_governor: Task 3's throughput governor -- baseline, rolling-median
decay detection, pause/resume/cap, the honesty requirement (0031), and
named machine-scoped profiles.

Hermetic. Every profile test writes to a temp `config/local.json` path,
never the real one. No clock, no LM Studio, no subprocess -- `observe` is a
pure function of `(state, ms_per_token)`.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from chronicler.pipeline import governor as gov


def run() -> list[str]:
    v: list[str] = []

    # --- baseline establishment: the first `baseline_units` measured units,
    #     median, nothing else -- and it happens ONCE per state -----------
    profile = dict(gov.DEFAULT_PROFILE)
    profile["baseline_units"] = 4
    profile["rolling_window"] = 4
    state = gov.new_governor(profile)

    actions = [gov.observe(state, ms) for ms in [100.0, 110.0, 90.0, 100.0]]
    if [a.action for a in actions] != ["measuring", "measuring", "measuring", "baseline_set"]:
        v.append(f"expected 3 'measuring' then one 'baseline_set': {[a.action for a in actions]}")
    if state.baseline != 100.0:
        v.append(f"baseline should be the median of the first 4 units (100,110,90,100 -> 100): "
                  f"{state.baseline}")

    # a 5th unit at baseline should read 'observing' (rolling window not yet
    # full) then, once full, 'none' at ~100% -- never re-measuring the
    # baseline again.
    a5 = gov.observe(state, 100.0)
    if a5.action != "observing":
        v.append(f"expected 'observing' while the rolling window fills: {a5.action}")

    # --- None (usage unavailable) is skipped entirely -- does not touch
    #     baseline_samples, recent, or advance anything -------------------
    state2 = gov.new_governor(dict(profile))
    a_none = gov.observe(state2, None)
    if a_none.action != "none" or state2.baseline_samples:
        v.append(f"observe(None) must be skipped, not counted toward the baseline: "
                  f"action={a_none.action} baseline_samples={state2.baseline_samples}")

    # --- steady stream at baseline never pauses -------------------------
    state3 = gov.new_governor(dict(profile))
    steady_actions = [gov.observe(state3, 100.0) for _ in range(12)]
    if any(a.action in ("pause", "cap_reached") for a in steady_actions):
        v.append(f"a steady stream at baseline should never pause: "
                  f"{[a.action for a in steady_actions]}")

    # --- decay then recovery: baseline at 100, then 4 units at 40 (40% of
    #     baseline, below the 75% pause_threshold) should trigger exactly
    #     one 'pause' once the rolling window is full of degraded values;
    #     recovering back to baseline should trigger exactly one 'resume' --
    state4 = gov.new_governor(dict(profile))
    for ms in [100.0, 100.0, 100.0, 100.0]:            # establish baseline
        gov.observe(state4, ms)
    decay_actions = [gov.observe(state4, 40.0) for _ in range(4)]  # fill rolling window with decay
    pauses = [a for a in decay_actions if a.action == "pause"]
    if len(pauses) != 1:
        v.append(f"expected exactly 1 'pause' once the rolling window fills with degraded "
                  f"units: {[a.action for a in decay_actions]}")
    elif pauses[0].pause_seconds != profile["pause_seconds"]:
        v.append(f"a 'pause' action should carry the profile's pause_seconds: {pauses[0]}")
    if not state4.paused:
        v.append("governor state should be 'paused' after a pause action")

    recovery_actions = [gov.observe(state4, 100.0) for _ in range(4)]  # recover back to baseline
    resumes = [a for a in recovery_actions if a.action == "resume"]
    if len(resumes) != 1:
        v.append(f"expected exactly 1 'resume' once the rolling window recovers to baseline: "
                  f"{[a.action for a in recovery_actions]}")
    if state4.paused:
        v.append("governor state should no longer be 'paused' after a resume action")

    # --- never recovers: hits the cap, records it ONCE, then proceeds
    #     without pausing forever (a governor that waits forever is a hang,
    #     Addendum 2's own 10 August evidence for why the cap is load-bearing) -
    state5 = gov.new_governor(dict(profile))
    for ms in [100.0, 100.0, 100.0, 100.0]:
        gov.observe(state5, ms)
    never_recovers = [gov.observe(state5, 40.0) for _ in range(20)]  # stays degraded throughout
    cap_actions = [a for a in never_recovers if a.action == "cap_reached"]
    if len(cap_actions) != 1:
        v.append(f"expected the cap to be reached and recorded EXACTLY ONCE, not repeated on "
                  f"every subsequent still-degraded unit: {[a.action for a in never_recovers]}")
    pause_count_before_cap = sum(1 for a in never_recovers if a.action == "pause")
    if pause_count_before_cap != profile["pause_cap"]:
        v.append(f"expected exactly pause_cap ({profile['pause_cap']}) 'pause' actions before "
                  f"the cap fires: got {pause_count_before_cap}")
    # after the cap, the stream must proceed (action 'none'), never hang
    # waiting -- and never pause again while still capped
    after_cap = never_recovers[never_recovers.index(cap_actions[0]) + 1:]
    if any(a.action == "pause" for a in after_cap):
        v.append(f"once the cap is reached, the governor must not pause again until it "
                  f"actually recovers: {[a.action for a in after_cap]}")
    if not all(a.action == "none" for a in after_cap):
        v.append(f"after the cap, every further still-degraded unit should read 'none' "
                  f"(proceeding), not silently do nothing else: {[a.action for a in after_cap]}")

    # a cap that has been hit and then genuinely recovers should still
    # resume normally, and cap_reached should reset for any FUTURE decay.
    # 4 more units at baseline is enough to fully flush the degraded
    # readings out of a rolling_window=4 detector -- no internal state is
    # touched directly here, only observe() is called, same as every other
    # scenario above.
    recover_after_cap = [gov.observe(state5, 100.0) for _ in range(4)]
    if not any(a.action == "resume" for a in recover_after_cap):
        v.append(f"a capped-and-still-degraded stream should still be able to resume once "
                  f"it genuinely recovers: {[a.action for a in recover_after_cap]}")
    if state5.cap_reached:
        v.append("cap_reached should reset to False once the governor actually resumes")

    # --- the honesty requirement (0031): read every message produced across
    #     every scenario above -- none may name a cause. This is 0031
    #     applied to a control loop, mechanically checked rather than
    #     reviewed by eye. -----------------------------------------------
    all_actions = (actions + [a5] + [a_none] + steady_actions + decay_actions
                   + recovery_actions + never_recovers + recover_after_cap)
    for a in all_actions:
        low = a.message.lower()
        for bad in gov._FORBIDDEN_WORDS:
            if bad in low:
                v.append(f"governor message names a cause ('{bad}' in {a.message!r}) -- "
                          f"0031 violation: report the observation, never the diagnosis")

    # --- profiles: named, machine-scoped, config/local.json, layered over
    #     DEFAULT_PROFILE so a partial stored profile still has every key --
    with tempfile.TemporaryDirectory() as td:
        cfg_path = Path(td) / "local.json"

        # no profile ever stored -> DEFAULT_PROFILE exactly
        default_read = gov.get_profile("nope", host="test-host", path=cfg_path)
        if default_read != gov.DEFAULT_PROFILE:
            v.append(f"a never-stored profile name should return DEFAULT_PROFILE exactly: "
                      f"{default_read}")

        gov.set_profile("aggressive", {"pause_threshold": 0.9, "pause_cap": 1},
                          host="test-host", path=cfg_path)
        merged = gov.get_profile("aggressive", host="test-host", path=cfg_path)
        if merged["pause_threshold"] != 0.9 or merged["pause_cap"] != 1:
            v.append(f"set_profile's stored keys should override the default on read: {merged}")
        if merged["max_window_tokens"] != gov.DEFAULT_PROFILE["max_window_tokens"]:
            v.append(f"a partially-specified stored profile should still carry every OTHER "
                      f"key from DEFAULT_PROFILE unchanged: {merged}")

        # writing one host/profile must not disturb another host's section,
        # or a second profile under the same host -- read-modify-write, not
        # a blind overwrite.
        gov.set_profile("default", {"pause_cap": 5}, host="other-host", path=cfg_path)
        still_there = gov.get_profile("aggressive", host="test-host", path=cfg_path)
        if still_there["pause_threshold"] != 0.9:
            v.append("writing a second host's profile must not disturb the first host's "
                      "already-stored profile")

    return v
