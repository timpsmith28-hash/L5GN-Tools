"""tester_conductor_run: the execution loop -- conductor_run.run_plan.

Hermetic: `execute_fn` is a fake that never spawns a subprocess (it calls
`on_timing_line` directly with synthetic TIMING_WINDOW-shaped lines and
returns a canned `StageOutcome`), `curator`/`ledger_path`/`profile_path`
all point at temp locations -- no real lock, no real LM Studio, no real
`config/local.json` or `data/knowledge_curator/` touched.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from chronicler.pipeline import ledger as led
from chronicler.review import conductor_run as cr
from chronicler.review import curator_control as ctl
from chronicler.review import curator_data
from chronicler.review import planner as pl


def _make_spec(plan_id: str, profile_name: str, n_steps: int = 2, approved: bool = True) -> pl.PlanSpec:
    steps = tuple(pl.PlanStep(f"proj-{chr(ord('a') + i)}", "K2") for i in range(n_steps))
    spec = pl.PlanSpec(plan_id=plan_id, policy="coverage", profile_name=profile_name,
                        steps=steps, remainder=(), budget_seconds=None,
                        estimated_total_seconds=None)
    return pl.approve(spec) if approved else spec


def _timing_line(ms: float, model_id: str = "test-model") -> str:
    return (f"TIMING_WINDOW window_index=0 model_id={model_id} "
            f"cool_down_preceded=False generation_ms_per_token={ms}")


class _FlipMembership:
    """A `known_profiles`-shaped container whose `__contains__` answers
    True for its first `good_calls` checks, then False forever after --
    simulates a profile going stale partway through a real multi-step run
    (e.g. renamed on this machine) without needing wall-clock time to pass."""

    def __init__(self, good_calls: int):
        self.good_calls = good_calls
        self.calls = 0

    def __contains__(self, item) -> bool:
        self.calls += 1
        return self.calls <= self.good_calls

    def __iter__(self):
        # only exercised by the error-message formatter (`sorted(...)`) on
        # the failing call -- content doesn't matter to this test.
        return iter(["tester_conductor_run_profile"])


def run() -> list[str]:
    v: list[str] = []

    # --- an unapproved plan is refused before anything runs at all -------
    with tempfile.TemporaryDirectory() as td:
        spec = _make_spec("unapproved", "tester_conductor_run_profile", approved=False)
        calls = [0]

        def _never(*a, **kw):
            calls[0] += 1
            raise AssertionError("execute_fn must never be called for an unapproved plan")

        try:
            cr.run_plan(spec, execute_fn=_never, ledger_path=Path(td) / "ledger.jsonl",
                        curator=curator_data.Curator(data_dir=Path(td) / "curator",
                                                       ratified_map_path=Path(td) / "map.tsv"))
            v.append("run_plan should raise for an unapproved plan, not run it")
        except ValueError as exc:
            if "approved" not in str(exc):
                v.append(f"the refusal for an unapproved plan should say so: {exc}")
        if calls[0] != 0:
            v.append("execute_fn must never be called before the first validation passes")

    # --- the full happy path: two steps, a governor pause on step 0, the
    #     ledger fed from the same stream, real (temp) post-step state ----
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        ledger_path = td / "ledger.jsonl"
        curator = curator_data.Curator(data_dir=td / "curator", ratified_map_path=td / "map.tsv")
        spec = _make_spec("happy", "tester_conductor_run_profile")

        seen_steps: list[str] = []

        def fake_execute(stage, *, lock_path=None, host=None, project_id=None,
                          cancel_token=None, on_timing_line=None):
            seen_steps.append(f"{project_id}/{stage}")
            if project_id == "proj-a":
                # 4 to establish baseline at 100ms/token, then 4 more at
                # 50ms/token (ratio 0.5 < pause_threshold 0.75) -- the LAST
                # of these should come back as a "pause" action.
                for ms in (100.0, 100.0, 100.0, 100.0, 50.0, 50.0, 50.0, 50.0):
                    on_timing_line("window", ms, _timing_line(ms))
            else:
                # recovers back toward baseline -- ratio 0.9 >= 0.90 resumes.
                for ms in (90.0, 90.0, 90.0, 90.0):
                    on_timing_line("window", ms, _timing_line(ms))
            return ctl.StageOutcome(stage=stage, state="success", detail="completed",
                                     returncode=0)

        sleeps: list[float] = []
        # Live-progress callbacks -- the whole point of these (COWORK_REPORT_
        # conductor_governor.md's real-rig gremlin: a run with LM Studio
        # visibly working and the CLI showing nothing) is that they fire
        # DURING the run, not reconstructed from the return value afterward.
        step_starts: list[tuple] = []
        timing_calls: list[tuple] = []
        step_ends: list = []
        summary = cr.run_plan(spec, curator=curator, ledger_path=ledger_path,
                               execute_fn=fake_execute, sleep_fn=sleeps.append,
                               known_profiles=frozenset({"tester_conductor_run_profile"}),
                               on_step_start=lambda i, step: step_starts.append((i, step.project_id)),
                               on_timing_line=lambda kind, ms, line, action:
                                   timing_calls.append((kind, ms, action.action)),
                               on_step_end=lambda result: step_ends.append(result.project_id))

        if step_starts != [(0, "proj-a"), (1, "proj-b")]:
            v.append(f"on_step_start should fire once per step, in order, BEFORE that "
                     f"step's execute_fn: {step_starts}")
        if len(timing_calls) != 12:  # 8 from proj-a + 4 from proj-b
            v.append(f"on_timing_line should fire for every timing line across both "
                     f"steps, live, not just the last action per step: {len(timing_calls)}")
        if timing_calls[7][2] != "pause":
            v.append(f"on_timing_line's 4th argument is the REAL GovernorAction for that "
                     f"exact line, not just the step's final action: {timing_calls[7]}")
        if step_ends != ["proj-a", "proj-b"]:
            v.append(f"on_step_end should fire once per step, in order, right after "
                     f"that step's result is recorded: {step_ends}")

        if summary["stopped_early"]:
            v.append(f"the happy path should not stop early: {summary['stop_reason']}")
        if seen_steps != ["proj-a/K2", "proj-b/K2"]:
            v.append(f"both steps should run, in plan order, never reordered: {seen_steps}")
        if len(summary["results"]) != 2:
            v.append(f"expected 2 StepResults: {summary['results']}")
        r0, r1 = summary["results"]
        if r0.paused_after != 60.0:
            v.append(f"step 0's synthetic throughput drop should trigger the governor's "
                     f"default pause_seconds (60.0): {r0.paused_after}")
        if sleeps != [60.0]:
            v.append(f"sleep_fn should have been called exactly once, with 60.0: {sleeps}")
        if r1.paused_after is not None:
            v.append(f"the LAST step must never sleep after itself -- nothing follows it: "
                     f"{r1.paused_after}")
        if "stage" not in r0.post_state or r0.post_state.get("stage") != "K2":
            v.append(f"post_state should be a REAL post-step artefact read (never inferred "
                     f"from outcome alone): {r0.post_state}")

        entries = led.load_entries(ledger_path)
        if len(entries) != 12:  # 8 from proj-a + 4 from proj-b
            v.append(f"every valid timing line across both steps should have reached the "
                     f"ledger via the same on_timing_line stream: {len(entries)} entries")
        if any(e.get("model_id") != "test-model" for e in entries):
            v.append("ledger entries should carry the model_id parsed out of the timing line")

    # --- queued cancellation (stop_after_step already set before the loop
    #     even starts) -- the loop must not call execute_fn at all --------
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        spec = _make_spec("queued_cancel", "tester_conductor_run_profile")
        control = cr.RunControl()
        control.request_stop_after_step()
        calls = [0]

        def _fake(*a, **kw):
            calls[0] += 1
            return ctl.StageOutcome(stage="K2", state="success", detail="ok")

        summary = cr.run_plan(spec, control=control, execute_fn=_fake,
                               ledger_path=td / "ledger.jsonl",
                               curator=curator_data.Curator(data_dir=td / "curator",
                                                              ratified_map_path=td / "map.tsv"))
        if not summary["stopped_early"] or calls[0] != 0:
            v.append(f"a pre-set stop_after_step must stop the run before step 0 ever "
                     f"executes: stopped_early={summary['stopped_early']} calls={calls[0]}")
        if summary["results"]:
            v.append("no results should be recorded when the run stops before step 0")

    # --- in-flight cancellation: a step reports cancelled=True -> the loop
    #     stops, keeping the ALREADY-collected result, never runs step 1 --
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        spec = _make_spec("inflight_cancel", "tester_conductor_run_profile")
        seen = []

        def _cancelling_execute(stage, *, lock_path=None, host=None, project_id=None,
                                 cancel_token=None, on_timing_line=None):
            seen.append(project_id)
            return ctl.StageOutcome(stage=stage, state="failed",
                                     detail="cancelled by operator request (in-flight)",
                                     cancelled=True)

        summary = cr.run_plan(spec, execute_fn=_cancelling_execute,
                               ledger_path=td / "ledger.jsonl",
                               curator=curator_data.Curator(data_dir=td / "curator",
                                                              ratified_map_path=td / "map.tsv"))
        if not summary["stopped_early"]:
            v.append("a cancelled step must stop the run")
        if seen != ["proj-a"]:
            v.append(f"the run must stop AFTER the cancelled step, never start the next one: "
                     f"{seen}")
        if len(summary["results"]) != 1:
            v.append(f"the cancelled step's own result should still be recorded -- the run "
                     f"never trusts the plan's step list as what actually happened: "
                     f"{summary['results']}")

    # --- mid-run re-validation: a plan valid at the start goes stale
    #     exactly before step 1 -- the run stops there, but step 0's
    #     result is preserved, never discarded by a raised exception ------
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        spec = _make_spec("goes_stale", "tester_conductor_run_profile")
        flip = _FlipMembership(good_calls=2)  # pre-loop check + step-0's own check pass

        def _fake_ok(stage, *, lock_path=None, host=None, project_id=None,
                     cancel_token=None, on_timing_line=None):
            return ctl.StageOutcome(stage=stage, state="success", detail="ok")

        summary = cr.run_plan(spec, execute_fn=_fake_ok, ledger_path=td / "ledger.jsonl",
                               known_profiles=flip,
                               curator=curator_data.Curator(data_dir=td / "curator",
                                                              ratified_map_path=td / "map.tsv"))
        if not summary["stopped_early"]:
            v.append("a plan that goes stale mid-run must stop, not run past it silently")
        if len(summary["results"]) != 1:
            v.append(f"step 0's result must survive a step-1 validation failure -- a mid-run "
                     f"refusal is a stop condition like any other, not data loss: "
                     f"{summary['results']}")
        if summary["stop_reason"] is None or "no longer valid" not in summary["stop_reason"]:
            v.append(f"the stop reason should say the plan went stale, plainly: "
                     f"{summary['stop_reason']}")

    return v
