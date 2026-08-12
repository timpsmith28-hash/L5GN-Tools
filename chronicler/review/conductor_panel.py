"""conductor_panel.py -- Task 6, COWORK_BRIEF_conductor_governor.md.

Assembles the JSON a conductor panel in the curator tab needs: LM Studio
reachability + the calibration state (Task 2's ledger), a plan preview
(Task 4's planner), and current run state (Task 5's lock). Pure data-
shaping over `curator_control`/`ledger`/`planner` -- no new I/O beyond what
those modules already do, and this module runs no stage itself.

**A panel over the curator tab, not a new tab** -- the brief's own words.
This file is the data layer a route (wired into `app.py`, alongside the
existing `/api/curator/control/*` family) would serve; the frontend
rendering of that data into the curator tab's HTML/JS is a separate,
not-yet-built piece (see the module's report entry for what's deliberately
deferred).

**Honest about what doesn't exist yet.** There is no execution loop —
Task 4' (the planner) and Task 5' (the streaming executor, the lock,
cancellation) were built as separate primitives; nothing currently walks a
`PlanSpec`'s steps through `execute_with_lock`. `run_state` reports the
real lock status and says so plainly rather than fabricating a "run in
progress" view. This is the same discipline `curator_data.py`'s own
`blocked_reason` fields already apply to every other stage output.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

from chronicler.pipeline import ledger as led

from . import curator_control as ctl
from . import planner as pl

#: The two stages the calibration ledger currently has anything to say
#: about (K2/K4 are the only model-calling stages -- see
#: `curator_control.MODEL_SELECTABLE_STAGES`, the single declaration point
#: this mirrors rather than redeclares a copy of).
_LEDGER_STAGES: tuple[str, ...] = ctl.MODEL_SELECTABLE_STAGES


def preconditions(curator, *, endpoint: str | None = None) -> dict:
    """Everything the panel needs probed before a plan is even offered --
    LM Studio reachability, the model list, the map/stage-output state
    (`curator_control.preflight`, unchanged, reused rather than
    reimplemented) plus whether the calibration ledger has anything in it
    at all. A read: changes nothing, safe on every page load."""
    pf = ctl.preflight(curator, endpoint=endpoint or ctl.DEFAULT_ENDPOINT)
    entries = led.load_entries()
    return {**pf, "calibration_available": bool(entries)}


def _summary_dict(summary) -> dict | None:
    return dataclasses.asdict(summary) if summary is not None else None


def calibration_state(*, ledger_path: Path | None = None,
                       model_ids: list[str] | None = None) -> dict:
    """Per-model, per-stage, per-cool-down-partition summaries -- the
    ledger's own `summarize` untouched, just fanned out over every model
    the ledger has ever seen (or a caller-supplied subset) and both
    stages that call a model. A model/stage/partition with nothing
    recorded reports `None`, exactly as `summarize` itself does -- this
    function adds no estimate `summarize` didn't already produce."""
    entries = led.load_entries(ledger_path)
    models = model_ids if model_ids is not None else led.known_models(entries)
    report: dict[str, dict] = {}
    for model_id in models:
        report[model_id] = {}
        for stage in _LEDGER_STAGES:
            report[model_id][stage] = {
                "clean": _summary_dict(led.summarize(
                    entries, model_id=model_id, stage=stage, cool_down_preceded=False)),
                "post_cool_down": _summary_dict(led.summarize(
                    entries, model_id=model_id, stage=stage, cool_down_preceded=True)),
            }
    return {"available": bool(models), "models": report}


def plan_preview(spec: pl.PlanSpec) -> dict:
    """A `PlanSpec` flattened into the shape a panel renders directly --
    steps, remainder, budget, and whether it's approved yet. Does not
    validate or mutate `spec`; a caller that wants a guaranteed-valid
    preview calls `spec.validate()` (or lets `PlanRegistry.save` do it)
    first, same as everywhere else in this codebase that separates
    building from validating."""
    return {
        "plan_id": spec.plan_id,
        "policy": spec.policy,
        "profile_name": spec.profile_name,
        "steps": [
            {"project_id": s.project_id, "stage": s.stage, "estimated_seconds": s.estimated_seconds}
            for s in spec.steps
        ],
        "step_count": len(spec.steps),
        "remainder": list(spec.remainder),
        "remainder_count": len(spec.remainder),
        "budget_seconds": spec.budget_seconds,
        "estimated_total_seconds": spec.estimated_total_seconds,
        "approved": spec.approved,
        "approved_at": spec.approved_at,
    }


def run_state(*, lock_path: Path | None = None) -> dict:
    """The real lock state, and an explicit statement that there is no live
    governor reading to show alongside it -- **never** a fabricated
    "in progress" view. `note` names exactly why: no execution loop exists
    yet to produce one. Stage-count/throughput/pause fields the eventual
    live panel will carry are deliberately absent here rather than stubbed
    with placeholder values a caller could mistake for real data."""
    return {
        "lock": ctl.lock_status(lock_path=lock_path),
        "governor": None,
        "note": ("No execution loop exists yet -- Task 4' (the planner) and Task 5' "
                 "(the streaming executor, the lock, cancellation) were built as "
                 "separate primitives; nothing currently walks a plan's steps through "
                 "them. This reports the real lock state and nothing else."),
    }
