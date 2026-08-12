"""tester_conductor_panel: Task 6's backend data layer -- preconditions +
calibration state, plan preview, and honest run state (no fabricated
"in progress" view when no execution loop exists).

Hermetic. Every ledger/lock path is a temp file; `curator_control.preflight`
is exercised against a `curator_data.Curator` pointed at a temp directory,
never the real machine's LM Studio or data/knowledge_curator/.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from chronicler.pipeline import ledger as led
from chronicler.review import conductor_panel as cp
from chronicler.review import curator_data
from chronicler.review import planner as pl


def run() -> list[str]:
    v: list[str] = []

    # --- preconditions: wraps curator_control.preflight, adds
    #     calibration_available honestly (empty ledger -> False) ------------
    with tempfile.TemporaryDirectory() as td:
        curator = curator_data.Curator(data_dir=Path(td) / "nonexistent")
        pf = cp.preconditions(curator, endpoint="http://localhost:1234")
        if "lm_studio" not in pf or "map_ratified" not in pf or "lock" not in pf:
            v.append(f"preconditions should carry everything curator_control.preflight "
                     f"already produces: {pf}")
        if pf.get("calibration_available") is not False:
            v.append(f"an untouched ledger (nothing recorded anywhere) should read "
                     f"calibration_available=False: {pf}")

    # --- calibration_state: fans summarize() out per model/stage/partition,
    #     never fabricates a number summarize() itself wouldn't produce ------
    with tempfile.TemporaryDirectory() as td:
        ledger_path = Path(td) / "ledger.jsonl"
        led.append_entry({"model_id": "m1", "stage": "K2", "cool_down_preceded": False,
                            "generation_ms_per_token": 40.0}, path=ledger_path)
        led.append_entry({"model_id": "m1", "stage": "K2", "cool_down_preceded": False,
                            "generation_ms_per_token": 60.0}, path=ledger_path)
        led.append_entry({"model_id": "m1", "stage": "K2", "cool_down_preceded": True,
                            "generation_ms_per_token": 150.0}, path=ledger_path)

        cal = cp.calibration_state(ledger_path=ledger_path)
        if not cal["available"] or "m1" not in cal["models"]:
            v.append(f"calibration_state should report m1 as available: {cal}")
        m1 = cal["models"].get("m1", {})
        if m1.get("K2", {}).get("clean") is None or m1["K2"]["clean"]["n"] != 2:
            v.append(f"calibration_state's K2/clean entry should reflect the 2 "
                     f"not-cool-down-preceded observations: {m1.get('K2')}")
        if m1.get("K2", {}).get("post_cool_down") is None or m1["K2"]["post_cool_down"]["n"] != 1:
            v.append(f"calibration_state's K2/post_cool_down entry should reflect the 1 "
                     f"preceded observation, kept SEPARATE from the clean one: {m1.get('K2')}")
        # K4 was never recorded for m1 -- both partitions must read None, not
        # borrow K2's figures or fabricate anything
        if m1.get("K4", {}).get("clean") is not None or m1.get("K4", {}).get("post_cool_down") is not None:
            v.append(f"a stage with no recorded observations must report None in both "
                     f"partitions, never borrow another stage's figures: {m1.get('K4')}")

        # an empty ledger -> available=False, models={}
        empty_cal = cp.calibration_state(ledger_path=Path(td) / "never_written.jsonl")
        if empty_cal["available"] or empty_cal["models"]:
            v.append(f"calibration_state over an empty/absent ledger should report "
                     f"available=False and no models: {empty_cal}")

        # model_ids filter restricts which models are reported, without
        # needing to already know what's in the ledger
        led.append_entry({"model_id": "m2", "stage": "K2", "cool_down_preceded": False,
                            "generation_ms_per_token": 10.0}, path=ledger_path)
        filtered = cp.calibration_state(ledger_path=ledger_path, model_ids=["m2"])
        if "m1" in filtered["models"] or "m2" not in filtered["models"]:
            v.append(f"an explicit model_ids filter should restrict the report to "
                     f"exactly those models: {list(filtered['models'])}")

    # --- plan_preview: flattens a PlanSpec into the panel's shape,
    #     including an unapproved plan's approved=False/approved_at=None ----
    candidate = pl.ProjectCandidate("proj-a", claim_count=1, estimated_seconds=42.0)
    spec = pl.build_plan([candidate], policy="coverage", profile_name="default",
                           plan_id="preview_test")
    preview = cp.plan_preview(spec)
    if preview["plan_id"] != "preview_test" or preview["step_count"] != 1:
        v.append(f"plan_preview did not carry the plan's own id/step count through: {preview}")
    if preview["steps"] != [{"project_id": "proj-a", "stage": "K2", "estimated_seconds": 42.0}]:
        v.append(f"plan_preview's steps should mirror the spec's steps exactly: {preview['steps']}")
    if preview["approved"] is not False or preview["approved_at"] is not None:
        v.append(f"an unapproved plan's preview should show approved=False, "
                 f"approved_at=None: {preview}")

    approved_spec = pl.approve(spec, now="2026-08-13T00:00:00Z")
    approved_preview = cp.plan_preview(approved_spec)
    if not approved_preview["approved"] or approved_preview["approved_at"] != "2026-08-13T00:00:00Z":
        v.append(f"plan_preview should reflect approval once it's happened: {approved_preview}")

    budgeted = pl.build_plan([candidate], policy="coverage", profile_name="default",
                               budget_seconds=100.0, plan_id="budgeted_preview")
    budgeted_preview = cp.plan_preview(budgeted)
    if budgeted_preview["remainder_count"] != len(budgeted.remainder):
        v.append(f"plan_preview's remainder_count should match the spec's remainder length: "
                 f"{budgeted_preview}")

    # --- run_state: real lock status, NO fabricated governor/progress view -
    with tempfile.TemporaryDirectory() as td:
        lock_path = Path(td) / "test.lock"
        idle = cp.run_state(lock_path=lock_path)
        if idle["lock"]["locked"] is not False:
            v.append(f"run_state over an unlocked path should report locked=False: {idle}")
        if idle["governor"] is not None:
            v.append(f"run_state must never fabricate a governor reading when no "
                     f"execution loop exists to produce one: {idle}")
        if "note" not in idle or not idle["note"]:
            v.append("run_state should explain plainly why there's no live governor "
                     "reading, not just leave the field empty with no context")

        from chronicler.review import curator_control as ctl
        ctl.acquire_lock("K2", lock_path=lock_path)
        held = cp.run_state(lock_path=lock_path)
        if held["lock"]["locked"] is not True or held["lock"]["stage"] != "K2":
            v.append(f"run_state should reflect a REAL held lock, not just report "
                     f"unlocked regardless: {held}")
        ctl.release_lock(lock_path=lock_path)

    return v
