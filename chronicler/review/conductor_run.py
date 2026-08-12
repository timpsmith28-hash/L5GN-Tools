"""conductor_run.py -- the execution loop, COWORK_BRIEF_conductor_governor.md's
final built piece. Takes an APPROVED :class:`planner.PlanSpec` and actually
runs it, step by step: one `curator_control.execute_with_lock` call per
step, exactly as Task 5' left it, with the governor (pacing) and the
calibration ledger (measurement) wired into the SAME `on_timing_line`
stream a step already emits -- a run now measures itself and paces itself
off nothing new.

**0037 clause 2, applied per step, not once.** `planner.validate_for_
execution` is re-run before EVERY step, not just once at the top of the
loop. An overnight run spans hours; a plan approved at the start could be
stale by step three (a profile renamed on this machine, a stage's model
unselected). Re-validating per step means a run degrades to a clean
refusal on the step it actually goes stale on, never a crash three steps
later and never a silent continuation past a plan that is no longer the
one that was approved.

**"Never trusts the plan as a record of what ran" (0037/0031).** A
`StageOutcome.state == "success"` is a subprocess's return code, not proof
of what changed on disk. After every step this loop re-reads the REAL
post-step artefact state via `curator_data.Curator.stage_states()` and
attaches it to the result -- an honest observation of what the caches
actually show now, never an inference drawn from the plan's own static
step list.

**The governor paces BETWEEN steps, never mid-stream.**
`COWORK_REPORT_conductor_governor.md`'s Task 5' section says plainly that
"governor pausing between steps... needs a *sequence* of steps to pause
between" and that this was Task 4's/the execution loop's job -- this is
that sequence. One `GovernorState` lives for the WHOLE run (the baseline
is per-run, `governor.py`'s own rule, established from this run's own
opening units); `observe()` is fed off the same `on_timing_line` calls the
ledger feeder already consumes. If the LAST action a step produced was
`"pause"`, the loop sleeps `pause_seconds` before the NEXT step starts --
never mid-step (a step's own subprocess is never paused while it's
running; nothing in this codebase can do that safely), and never for the
step after the last one (there is nothing left to pause before).

**Two-stage cancellation, matching a real overnight run's two intents.**
`RunControl` wraps a `curator_control.CancelToken` (Task 5's in-flight/
queued primitive) with one more flag, `stop_after_step` -- the CLI wires a
SIGINT handler so a FIRST Ctrl-C requests only `stop_after_step` (the
current step is left alone to finish; the loop declines to start another);
a SECOND Ctrl-C also fires the `CancelToken`, which `execute_with_lock`/
`run_stage` already terminate an in-flight subprocess on. One gesture for
"let this one finish, then stop"; a second for "stop it now" -- exactly
the two intents `CancelToken`'s own docstring names, given a second signal
to tell them apart by.

Lives in the app tier (`chronicler.review`), same layer as `planner.py`/
`conductor_panel.py`/`candidates.py` -- it orchestrates `curator_control`
(app tier) and `governor`/`ledger` (pipeline tier), the same direction
every other module in this brief already runs (DECISIONS 0034 clause 3).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from chronicler.pipeline import governor as gov
from chronicler.pipeline import ledger as led

from . import curator_control as ctl
from . import curator_data
from . import planner as pl


@dataclass
class RunControl:
    """Two independent stop intents layered over one `CancelToken`.
    `stop_after_step` is a plain flag this loop peeks (non-consuming,
    never cleared by peeking) before scheduling the NEXT step; the wrapped
    `cancel_token` is handed straight through to `execute_with_lock` for
    the in-flight/queued half Task 5' already built -- requesting
    `stop_now` sets BOTH, since there is no step left to "let finish" once
    the current one has been asked to stop immediately."""
    cancel_token: "ctl.CancelToken" = field(default_factory=ctl.CancelToken)
    stop_after_step: bool = False

    def request_stop_after_step(self) -> None:
        self.stop_after_step = True

    def request_stop_now(self) -> None:
        self.stop_after_step = True
        self.cancel_token.request()


@dataclass
class StepResult:
    step_index: int
    project_id: str
    stage: str
    outcome: "ctl.StageOutcome"
    #: The REAL post-step artefact state for this step's stage, read fresh
    #: from disk right after the step ends -- never inferred from
    #: `outcome` alone (see module docstring, "never trusts the plan").
    post_state: dict
    #: Seconds actually slept (via `sleep_fn`) before the NEXT step, or
    #: `None` if the governor's last action for this step wasn't `"pause"`
    #: (or this was the last step, with nothing left to pause before).
    paused_after: float | None = None


def run_plan(spec: "pl.PlanSpec", *, host: str | None = None, lock_path: Path | None = None,
             ledger_path: Path | None = None, profile_path: Path | None = None,
             curator: "curator_data.Curator | None" = None,
             control: RunControl | None = None,
             known_stage_keys: frozenset | None = None,
             known_profiles: frozenset | None = None,
             execute_fn=None, sleep_fn=None,
             on_step_start=None, on_timing_line=None, on_step_end=None) -> dict:
    """Run every step of an APPROVED `spec`, in the order `spec.steps`
    already carries -- this loop reorders nothing (0037 clause 3). Returns
    a summary dict: ``{"plan_id", "results": [StepResult, ...],
    "stopped_early": bool, "stop_reason": str | None}`` once the WHOLE run
    is over -- a caller that only reads the return value sees nothing
    until then, which is wrong for anything multi-hour. The three
    optional callbacks below are how a caller (`run.py conductor`) gets
    LIVE progress instead, firing in real time as the loop actually
    reaches each point, not reconstructed afterward from the final
    summary:

    - ``on_step_start(step_index, step)`` -- right before a step's
      `execute_fn` is called.
    - ``on_timing_line(kind, ms_per_token, line, action)`` -- for every
      TIMING* line a step emits, AFTER the governor has already observed
      it and the ledger has already recorded it (`action` is that
      `GovernorAction`) -- this callback changes nothing about the run
      itself, purely observational, same posture `curator_control.
      run_stage`'s own `on_timing_line` already has.
    - ``on_step_end(step_result)`` -- right after a step's `StepResult` is
      recorded, before the next step (or a governor pause) starts.

    Raises immediately, before touching anything, if `spec` does not pass
    `planner.validate_for_execution` right now -- and re-checks it again
    before every subsequent step, for the reason the module docstring
    gives (a plan can go stale mid-run)."""
    control = control or RunControl()
    execute_fn = execute_fn or ctl.execute_with_lock
    sleep_fn = sleep_fn or time.sleep
    curator = curator or curator_data.Curator()

    pl.validate_for_execution(spec, known_stage_keys=known_stage_keys,
                               known_profiles=known_profiles)

    profile = gov.get_profile(spec.profile_name, host=host, path=profile_path)
    state = gov.new_governor(profile)
    results: list[StepResult] = []
    stopped_early = False
    stop_reason: str | None = None

    for i, step in enumerate(spec.steps):
        # 0037 clause 2: re-validated before EVERY step, not just once. A
        # failure HERE (mid-run) is a stop condition like any other -- it
        # preserves every result already collected rather than discarding
        # them by letting the exception propagate out of this function
        # (the one exception is the FIRST validation, above the loop,
        # which fails fast before anything has run at all).
        try:
            pl.validate_for_execution(spec, known_stage_keys=known_stage_keys,
                                       known_profiles=known_profiles)
        except (pl.PlanValidationError, ValueError) as exc:
            stopped_early = True
            stop_reason = (f"plan no longer valid before step {i} "
                            f"({step.project_id}/{step.stage}): {exc}")
            break

        if control.stop_after_step:
            stopped_early = True
            stop_reason = (f"stopped by operator request before step {i} "
                            f"({step.project_id}/{step.stage}) started")
            break

        last_action: list = [None]

        def _on_timing_line(kind, ms_per_token, line, _stage=step.stage):
            action = gov.observe(state, ms_per_token)
            last_action[0] = action
            led.make_ledger_feeder(ledger_path, stage=_stage)(kind, ms_per_token, line)
            if on_timing_line is not None:
                on_timing_line(kind, ms_per_token, line, action)

        if on_step_start is not None:
            on_step_start(i, step)

        try:
            outcome = execute_fn(step.stage, lock_path=lock_path, host=host,
                                  project_id=step.project_id,
                                  cancel_token=control.cancel_token,
                                  on_timing_line=_on_timing_line)
        except ctl.ExecutionRefused as exc:
            stopped_early = True
            stop_reason = f"step {i} ({step.project_id}/{step.stage}) refused: {exc}"
            break

        # 0037/0031: re-derive what actually happened from the caches --
        # never trust `outcome` alone as the record of what ran.
        post = curator.stage_states().get(step.stage)
        post_state = post.summary() if post is not None else {}

        paused_after = None
        action = last_action[0]
        if action is not None and action.action == "pause" and i + 1 < len(spec.steps):
            paused_after = action.pause_seconds
            sleep_fn(paused_after)

        result = StepResult(step_index=i, project_id=step.project_id, stage=step.stage,
                             outcome=outcome, post_state=post_state, paused_after=paused_after)
        results.append(result)
        if on_step_end is not None:
            on_step_end(result)

        if outcome.cancelled:
            stopped_early = True
            stop_reason = f"step {i} ({step.project_id}/{step.stage}) was cancelled"
            break

    return {"plan_id": spec.plan_id, "results": results,
            "stopped_early": stopped_early, "stop_reason": stop_reason}
