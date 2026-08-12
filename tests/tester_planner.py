"""tester_planner: Task 4's planner -- ranking policies, the budget-as-
strict-prefix fill, the validated PlanSpec artefact (closed vocabularies,
accumulate-then-raise, dataclass round-trip), approval, and the
validate-at-load-and-before-execution discipline.

Hermetic. `PlanRegistry` writes to a temp directory in every test here.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from chronicler.review import planner as pl


def run() -> list[str]:
    v: list[str] = []

    A = pl.ProjectCandidate("proj-a", claim_count=5, changed_conversations=1,
                              message_count=300, estimated_seconds=100.0)
    B = pl.ProjectCandidate("proj-b", claim_count=1, changed_conversations=9,
                              message_count=50, estimated_seconds=30.0)
    C = pl.ProjectCandidate("proj-c", claim_count=9, changed_conversations=3,
                              message_count=10, estimated_seconds=10.0)

    # --- ranking: each policy produces a DIFFERENT, deterministic order ----
    cov = pl.rank_candidates([A, B, C], "coverage")       # fewer claims first
    if [c.project_id for c in cov] != ["proj-b", "proj-a", "proj-c"]:
        v.append(f"coverage policy should rank by ascending claim_count: "
                 f"{[c.project_id for c in cov]}")

    fresh = pl.rank_candidates([A, B, C], "freshness")    # more changed first
    if [c.project_id for c in fresh] != ["proj-b", "proj-c", "proj-a"]:
        v.append(f"freshness policy should rank by descending changed_conversations: "
                 f"{[c.project_id for c in fresh]}")

    breadth = pl.rank_candidates([A, B, C], "breadth")    # fewer messages first
    if [c.project_id for c in breadth] != ["proj-c", "proj-b", "proj-a"]:
        v.append(f"breadth policy should rank by ascending message_count: "
                 f"{[c.project_id for c in breadth]}")

    # ties break on project_id -- deterministic, not insertion-order-dependent
    tie1 = pl.ProjectCandidate("z-proj", claim_count=5)
    tie2 = pl.ProjectCandidate("a-proj", claim_count=5)
    tied = pl.rank_candidates([tie1, tie2], "coverage")
    if [c.project_id for c in tied] != ["a-proj", "z-proj"]:
        v.append(f"a tie should break on project_id, deterministically: "
                 f"{[c.project_id for c in tied]}")

    try:
        pl.rank_candidates([A], "not-a-real-policy")
        v.append("rank_candidates accepted a policy outside the closed vocabulary")
    except pl.PlanValidationError:
        pass

    # --- unbudgeted plan: every candidate, policy order, no time claim -----
    unbudgeted = pl.build_plan([A, B, C], policy="coverage", profile_name="default")
    if [s.project_id for s in unbudgeted.steps] != ["proj-b", "proj-a", "proj-c"]:
        v.append(f"unbudgeted plan should include every candidate in policy order: "
                 f"{[s.project_id for s in unbudgeted.steps]}")
    if unbudgeted.remainder != ():
        v.append(f"an unbudgeted plan should have an empty remainder: {unbudgeted.remainder}")
    if unbudgeted.estimated_total_seconds is not None:
        v.append("an unbudgeted plan must not claim a total estimate -- nothing was budgeted")

    # --- budgeted plan: a STRICT prefix, never skipping ahead to a smaller
    #     later candidate that would individually fit ------------------------
    # coverage order: b(30) a(100) c(10). Budget 140 with cool_down=5 between
    # steps: b costs 30 (first, no cool-down), a costs 100+5=105 -> running
    # total 135, fits (<=140). c would cost 10+5=15 -> 150 > 140, so c is cut
    # even though 10 alone would easily fit -- the ordering is not corrupted
    # by skipping ahead to grab it.
    budgeted = pl.build_plan([A, B, C], policy="coverage", profile_name="default",
                               budget_seconds=140.0, cool_down_seconds=5.0)
    if [s.project_id for s in budgeted.steps] != ["proj-b", "proj-a"]:
        v.append(f"budgeted plan should be a strict prefix (b, a), never skipping "
                 f"ahead to grab c: {[s.project_id for s in budgeted.steps]}")
    if budgeted.remainder != ("proj-c",):
        v.append(f"the cut candidate should land in remainder: {budgeted.remainder}")
    if budgeted.estimated_total_seconds is None or abs(budgeted.estimated_total_seconds - 135.0) > 1e-9:
        v.append(f"estimated_total_seconds should be 30 + (100+5) = 135: "
                 f"{budgeted.estimated_total_seconds}")

    # a budget too small even for the FIRST candidate offers nothing, not a
    # cherry-picked smaller one further down the order
    tiny = pl.build_plan([A, B, C], policy="coverage", profile_name="default",
                           budget_seconds=5.0)
    if tiny.steps != ():
        v.append(f"a budget too small for even the first candidate should offer "
                 f"an empty plan, not skip ahead: {tiny.steps}")
    if set(tiny.remainder) != {"proj-a", "proj-b", "proj-c"}:
        v.append(f"everything should land in remainder when nothing fits: {tiny.remainder}")

    # --- an estimate is never fabricated: a budgeted plan REFUSES when a
    #     candidate carries no estimated_seconds (the brief's own stop
    #     condition, Task 2's ledger not being built yet) --------------------
    no_estimate = pl.ProjectCandidate("proj-d", claim_count=1)  # estimated_seconds=None
    try:
        pl.build_plan([A, no_estimate], policy="coverage", profile_name="default",
                        budget_seconds=1000.0)
        v.append("build_plan with budget_seconds should refuse a candidate with no "
                 "estimated_seconds, not silently treat it as free")
    except pl.PlanValidationError:
        pass
    # the SAME candidates are fine for an unbudgeted plan -- nothing is being
    # estimated there, so a missing estimate is not a problem
    ok_unbudgeted = pl.build_plan([A, no_estimate], policy="coverage", profile_name="default")
    if len(ok_unbudgeted.steps) != 2:
        v.append("an unbudgeted plan should accept candidates with no estimate at all")

    # --- PlanSpec.validate: closed vocabularies, accumulate-then-raise -----
    good = pl.build_plan([A, B], policy="coverage", profile_name="default", plan_id="p1")
    good.validate(known_stage_keys=frozenset({"K2"}))  # should not raise

    bad_policy = pl.dataclasses.replace(good, policy="not-real")
    try:
        bad_policy.validate(known_stage_keys=frozenset({"K2"}))
        v.append("PlanSpec.validate accepted a policy outside the closed vocabulary")
    except pl.PlanValidationError as exc:
        if "not-real" not in str(exc):
            v.append(f"validation error should name the bad policy: {exc}")

    bad_stage_step = pl.PlanStep("proj-x", "K9-not-real", 10.0)
    multi_bad = pl.dataclasses.replace(good, policy="not-real", steps=(bad_stage_step,))
    try:
        multi_bad.validate(known_stage_keys=frozenset({"K2"}))
        v.append("PlanSpec.validate accepted an unknown stage key")
    except pl.PlanValidationError as exc:
        msg = str(exc)
        if "not-real" not in msg or "K9-not-real" not in msg:
            v.append(f"validate should report EVERY violation together (accumulate-"
                     f"then-raise), not just the first: {msg}")

    dupe = pl.PlanSpec(plan_id="p2", policy="coverage", profile_name="default",
                         steps=(pl.PlanStep("proj-a", "K2"), pl.PlanStep("proj-a", "K2")),
                         remainder=(), budget_seconds=None, estimated_total_seconds=None)
    try:
        dupe.validate(known_stage_keys=frozenset({"K2"}))
        v.append("PlanSpec.validate accepted the same project appearing twice in steps")
    except pl.PlanValidationError:
        pass

    overlap = pl.PlanSpec(plan_id="p3", policy="coverage", profile_name="default",
                            steps=(pl.PlanStep("proj-a", "K2"),), remainder=("proj-a",),
                            budget_seconds=None, estimated_total_seconds=None)
    try:
        overlap.validate(known_stage_keys=frozenset({"K2"}))
        v.append("PlanSpec.validate accepted a project in BOTH steps and remainder")
    except pl.PlanValidationError:
        pass

    over_budget = pl.PlanSpec(plan_id="p4", policy="coverage", profile_name="default",
                                steps=(pl.PlanStep("proj-a", "K2", 200.0),), remainder=(),
                                budget_seconds=100.0, estimated_total_seconds=200.0)
    try:
        over_budget.validate(known_stage_keys=frozenset({"K2"}))
        v.append("PlanSpec.validate accepted an estimated_total_seconds exceeding its "
                 "own budget_seconds")
    except pl.PlanValidationError:
        pass

    # --- round-trip: dataclass-derived field table means to_dict/from_dict
    #     never silently drop a field ---------------------------------------
    round_tripped = pl.PlanSpec.from_dict(good.to_dict())
    if round_tripped != good:
        v.append(f"PlanSpec did not round-trip through JSON byte-for-field:\n"
                 f"  before: {good}\n  after:  {round_tripped}")

    # --- approval: explicit, per-plan, produces a NEW object ----------------
    if good.approved:
        v.append("a freshly built plan must not already be approved")
    approved = pl.approve(good, now="2026-08-13T00:00:00Z")
    if not approved.approved or approved.approved_at != "2026-08-13T00:00:00Z":
        v.append(f"approve() should set approved=True and stamp approved_at: {approved}")
    if good.approved:
        v.append("approve() must not mutate the original PlanSpec (frozen dataclass, "
                 "returns a new one)")

    # --- validate_for_execution: refuses an unapproved plan, refuses a plan
    #     whose profile is no longer known, re-checks structural validity ----
    try:
        pl.validate_for_execution(good, known_stage_keys=frozenset({"K2"}))
        v.append("validate_for_execution accepted a plan that was never approved")
    except ValueError as exc:
        if isinstance(exc, pl.PlanValidationError):
            v.append(f"an UNAPPROVED plan should raise plain ValueError, not "
                     f"PlanValidationError (that's for structural problems): {exc}")

    pl.validate_for_execution(approved, known_stage_keys=frozenset({"K2"}))  # should not raise

    try:
        pl.validate_for_execution(approved, known_stage_keys=frozenset({"K2"}),
                                    known_profiles=frozenset({"some-other-profile"}))
        v.append("validate_for_execution accepted a profile_name not in known_profiles")
    except pl.PlanValidationError:
        pass

    stale_stage = pl.approve(
        pl.PlanSpec(plan_id="p5", policy="coverage", profile_name="default",
                     steps=(pl.PlanStep("proj-a", "K9-not-real"),), remainder=(),
                     budget_seconds=None, estimated_total_seconds=None))
    try:
        pl.validate_for_execution(stale_stage, known_stage_keys=frozenset({"K2"}))
        v.append("validate_for_execution accepted a step whose stage is no longer known")
    except pl.PlanValidationError:
        pass

    # validate() with NO known_stage_keys given falls back to the real
    # curator_control.STAGE_TABLE -- proves the module actually wires to
    # the single declaration point rather than a hardcoded copy.
    from chronicler.review import curator_control as ctl
    real_stage_plan = pl.PlanSpec(plan_id="p6", policy="coverage", profile_name="default",
                                    steps=(pl.PlanStep("proj-a", next(iter(ctl.STAGE_TABLE))),),
                                    remainder=(), budget_seconds=None, estimated_total_seconds=None)
    real_stage_plan.validate()  # should not raise -- default known_stage_keys covers it

    # --- PlanRegistry: atomic persistence, malformed files skipped not
    #     crashing, isolated from the real data/knowledge_curator/plans/ ----
    with tempfile.TemporaryDirectory() as td:
        reg = pl.PlanRegistry(root=Path(td) / "plans")
        reg.save(pl.dataclasses.replace(good, steps=(pl.PlanStep("proj-a", "K2"),)))
        loaded = reg.load_all()
        if reg.errors:
            v.append(f"PlanRegistry.load_all reported errors on a clean save: {reg.errors}")
        if loaded.get(good.plan_id) is None:
            v.append("PlanRegistry did not round-trip a saved plan through load_all")

        # a malformed file is recorded and skipped, never crashes the registry
        (Path(td) / "plans" / "garbage.json").write_text("not json at all", encoding="utf-8")
        reg2 = pl.PlanRegistry(root=Path(td) / "plans")
        reg2.load_all()
        if not reg2.errors:
            v.append("PlanRegistry.load_all should have recorded the malformed file as an error")
        if good.plan_id not in reg2.list_ids():
            v.append("a malformed sibling file should not prevent loading the valid ones")

    return v
