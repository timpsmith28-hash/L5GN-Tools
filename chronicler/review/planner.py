"""planner.py -- Task 4', COWORK_BRIEF_conductor_governor.md.

The conductor's planner: turns a priority policy, a budget (or none), and a
list of candidate projects into a validated, serialisable plan -- never an
in-memory list, never free-text authored by a caller. Re-derives the pattern
`L5GN_Armory_v4/core/services/chain_registry.py` already proved for exactly
this shape of problem (closed vocabularies as frozensets, accumulate-then-
raise validation, a dataclass-derived field table so a later field addition
round-trips without a serialiser edit, a schema version from day one).
**Imports nothing from that repo** -- 0034 clause 3, and this codebase's own
working rule for this brief ("re-derive these patterns; import nothing").

Lives in the app tier (`chronicler.review`), not the pipeline tier, because
it needs `curator_control.STAGE_TABLE` -- the one declaration point for
stage keys -- and the dependency direction only runs app -> pipeline, never
back (DECISIONS 0034 clause 3's direction, the same one `governor.py`'s own
docstring already applies to itself).

**The line this module must not cross** (the addendum's own words): a plan
is *generated* from policy inputs and *approved* -- never authored. There is
no "paste your own plan JSON" path here, unlike CID's `chain_builder.py` /
`chain_authoring.save_chain_text()`, which is exactly the affordance 0037
clause (1) forbids for this brief (a caller supplies a plan identifier or
policy inputs, never a parameter that reaches a subprocess).

**What this module does NOT do.** It ranks caller-supplied
:class:`ProjectCandidate` objects and fills a budget -- it does not read
`knowledge_index.json`/`claims.json` itself to produce those candidates
(that adapter, and the real per-project time estimates Task 2's calibration
ledger would supply, are not built yet). A budgeted plan REFUSES to
fabricate an estimate for a candidate that doesn't carry one -- "an estimate
is produced with no measurement behind it" is one of the brief's own stop
conditions, not a detail to work around with a guess.
"""
from __future__ import annotations

import dataclasses
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from .curator_data import CURATOR_DATA_DIR

_PLANS_DIR = CURATOR_DATA_DIR / "plans"
_PLAN_SCHEMA = "l5gn.plan.v1"
_SLUG_OK = re.compile(r"^[a-z0-9_]+$")

#: Named, chosen, never inferred -- the brief's own words. Each policy is a
#: different, defensible ordering; the operator sees which one produced a
#: given plan (`PlanSpec.policy`), never a silent default.
VALID_POLICIES: frozenset[str] = frozenset({"coverage", "freshness", "breadth"})


class PlanValidationError(ValueError):
    """Raised with EVERY violation found, never just the first -- the
    improvement `chain_registry.py`'s own validator already made over
    fix-one-hit-the-next."""


# ---------------------------------------------------------------------------
# ProjectCandidate -- the planner's input. Deliberately NOT the plan itself;
# a candidate is a fact about a project ("N claims, last touched when, this
# many messages"), a PlanStep is a DECISION (this project, this stage, in
# this order). Keeping them separate is what lets `rank_candidates` be a
# pure function a tester can feed anything to, with no file I/O at all.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ProjectCandidate:
    project_id: str
    claim_count: int = 0           # coverage policy: fewer claims ranks first
    changed_conversations: int = 0  # freshness policy: more changed ranks first
    message_count: int = 0          # breadth policy: fewer messages ranks first
    #: Seconds this project is expected to take, or `None` if genuinely
    #: unmeasured (Task 2's ledger, not built, is the natural future
    #: source). `None` is a fact, never coerced to 0 or guessed.
    estimated_seconds: float | None = None


def rank_candidates(candidates: list[ProjectCandidate], policy: str) -> list[ProjectCandidate]:
    """Pure ordering -- no I/O, no budget, no plan. Ties break on
    `project_id` so the result is deterministic (a tester can assert an
    exact order, and two runs against identical input never disagree)."""
    if policy not in VALID_POLICIES:
        raise PlanValidationError(
            f"policy {policy!r} not in the closed vocabulary {sorted(VALID_POLICIES)}.")
    if policy == "coverage":
        key = lambda c: (c.claim_count, c.project_id)
    elif policy == "freshness":
        key = lambda c: (-c.changed_conversations, c.project_id)
    else:  # "breadth"
        key = lambda c: (c.message_count, c.project_id)
    return sorted(candidates, key=key)


# ---------------------------------------------------------------------------
# PlanStep / PlanSpec -- the validated, serialisable artefact.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PlanStep:
    """One scoped invocation: run `stage` against `project_id` alone (the
    same `--project` scoping K2/K4 already support). A step is ALWAYS a
    whole project at this granularity -- 0037 clause 3's "unit of work is a
    project" is therefore structurally enforced by this shape, not merely
    checked afterward: there is no field here that could name a partial
    project. (A "newest-first prefix of a project" -- clause 3's other
    permitted unit -- would need per-conversation steps; not built this
    round.)"""
    project_id: str
    stage: str
    estimated_seconds: float | None = None


_STEP_FIELDS = MappingProxyType({f.name: f for f in dataclasses.fields(PlanStep)})


def _step_to_dict(step: PlanStep) -> dict[str, Any]:
    return {name: getattr(step, name) for name in _STEP_FIELDS}


def _step_from_dict(data: Any) -> PlanStep:
    if not isinstance(data, dict):
        raise PlanValidationError(f"each step must be a JSON object, got {type(data).__name__}.")
    kwargs: dict[str, Any] = {}
    for name, f in _STEP_FIELDS.items():
        if name in data:
            kwargs[name] = data[name]
        elif f.default is not dataclasses.MISSING:
            kwargs[name] = f.default
        else:
            raise PlanValidationError(f"step missing required field '{name}'.")
    return PlanStep(**kwargs)


@dataclass(frozen=True)
class PlanSpec:
    """A named, ordered, budget-aware plan -- the serialisable unit
    `PlanRegistry` persists. Approval is a field on the artefact itself
    (`approved`/`approved_at`), not a side channel, so "was this plan ever
    approved" is answerable from the file alone."""
    plan_id: str
    policy: str
    profile_name: str
    steps: tuple  # tuple[PlanStep, ...]
    remainder: tuple  # tuple[str, ...] -- project_ids that did not fit
    budget_seconds: float | None
    estimated_total_seconds: float | None
    approved: bool = False
    approved_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": _PLAN_SCHEMA,
            "plan_id": self.plan_id,
            "policy": self.policy,
            "profile_name": self.profile_name,
            "steps": [_step_to_dict(s) for s in self.steps],
            "remainder": list(self.remainder),
            "budget_seconds": self.budget_seconds,
            "estimated_total_seconds": self.estimated_total_seconds,
            "approved": self.approved,
            "approved_at": self.approved_at,
        }

    @classmethod
    def from_dict(cls, data: Any) -> "PlanSpec":
        if not isinstance(data, dict):
            raise PlanValidationError("plan spec must be a JSON object.")
        raw_steps = data.get("steps")
        if not isinstance(raw_steps, list):
            raise PlanValidationError("plan spec 'steps' must be a list.")
        return cls(
            plan_id=str(data.get("plan_id", "")).strip(),
            policy=str(data.get("policy", "")),
            profile_name=str(data.get("profile_name", "")),
            steps=tuple(_step_from_dict(s) for s in raw_steps),
            remainder=tuple(data.get("remainder") or ()),
            budget_seconds=data.get("budget_seconds"),
            estimated_total_seconds=data.get("estimated_total_seconds"),
            approved=bool(data.get("approved", False)),
            approved_at=data.get("approved_at"),
        )

    def validate(self, *, known_stage_keys: frozenset[str] | None = None,
                 known_policies: frozenset[str] = VALID_POLICIES) -> bool:
        """Raise :class:`PlanValidationError` (naming EVERY problem found)
        if invalid; return True otherwise. ``known_stage_keys`` defaults to
        `curator_control.STAGE_TABLE`'s keys, imported lazily so this module
        has no hard dependency on the app being fully wired at import time
        (mirrors `chain_registry.py`'s own posture toward `document_service`)."""
        errors: list[str] = []
        if not self.plan_id:
            errors.append("plan_id is empty.")
        elif not _SLUG_OK.match(self.plan_id):
            errors.append(f"plan_id '{self.plan_id}' must be lowercase a-z, 0-9, underscore only.")
        if self.policy not in known_policies:
            errors.append(f"policy '{self.policy}' not in {sorted(known_policies)}.")

        if known_stage_keys is None:
            from . import curator_control
            known_stage_keys = frozenset(curator_control.STAGE_TABLE)

        seen_projects: set[str] = set()
        for step in self.steps:
            if not step.project_id:
                errors.append("a step has an empty project_id.")
            if step.stage not in known_stage_keys:
                errors.append(f"step stage '{step.stage}' not in {sorted(known_stage_keys)}.")
            # 0037 clause 3, checked directly rather than trusted: a project
            # appearing twice in `steps` means something interleaved or
            # reordered around it -- this shape should be structurally
            # impossible given how build_plan constructs steps, but the
            # validator checks it explicitly rather than assuming the
            # constructor was the only path that ever produces a PlanSpec.
            if step.project_id in seen_projects:
                errors.append(f"project '{step.project_id}' appears more than once in "
                               "steps -- a project must be a single contiguous unit "
                               "(0037 clause 3).")
            seen_projects.add(step.project_id)

        overlap = seen_projects & set(self.remainder)
        if overlap:
            errors.append(f"project(s) {sorted(overlap)} appear in BOTH steps and "
                           "remainder -- a project is either scheduled or it isn't.")

        if self.budget_seconds is not None and self.estimated_total_seconds is not None:
            if self.estimated_total_seconds > self.budget_seconds + 1e-9:
                errors.append(f"estimated_total_seconds ({self.estimated_total_seconds}) "
                               f"exceeds budget_seconds ({self.budget_seconds}) -- a plan "
                               "must never claim to fit a budget it doesn't.")

        if errors:
            raise PlanValidationError(f"plan '{self.plan_id}' invalid: " + " ".join(errors))
        return True


# ---------------------------------------------------------------------------
# build_plan -- ranks candidates, fills the budget as a strict PREFIX (never
# skips ahead to a smaller later candidate that would individually fit --
# "filling the time with work that corrupts the ordering" is the brief's own
# phrase for exactly that shortcut).
# ---------------------------------------------------------------------------

def build_plan(candidates: list[ProjectCandidate], *, policy: str, profile_name: str,
                stage: str = "K2", budget_seconds: float | None = None,
                cool_down_seconds: float = 0.0, plan_id: str | None = None) -> PlanSpec:
    """No budget -> every candidate, policy-ordered, no truncation, no time
    claim (``estimated_total_seconds=None`` -- there is nothing to estimate
    against). A budget -> every candidate MUST carry ``estimated_seconds``;
    if any doesn't, this REFUSES (`PlanValidationError`) rather than
    fabricate one -- call it without ``budget_seconds`` for an unbudgeted
    ordering instead, exactly Task 2's own "no measurements -> no estimate,
    offer an unbudgeted ordering instead" rule, applied here to the same
    situation.

    The budget accounts for pause time: every step after the first pays
    ``cool_down_seconds`` before its own estimate. This is the brief's own
    correction to a wall-clock-only budget -- cool-downs and governor
    pauses are run time."""
    ordered = rank_candidates(list(candidates), policy)
    plan_id = plan_id or f"plan_{policy}_{int(time.time())}"

    if budget_seconds is None:
        steps = tuple(PlanStep(c.project_id, stage, c.estimated_seconds) for c in ordered)
        return PlanSpec(plan_id=plan_id, policy=policy, profile_name=profile_name,
                          steps=steps, remainder=(), budget_seconds=None,
                          estimated_total_seconds=None)

    missing = [c.project_id for c in ordered if c.estimated_seconds is None]
    if missing:
        raise PlanValidationError(
            f"budget_seconds was given but these candidates carry no estimate: {missing} -- "
            "an estimate needs a measurement behind it (Task 2's calibration ledger, not "
            "yet built). Call build_plan without budget_seconds for an unbudgeted ordering.")

    steps: list[PlanStep] = []
    total = 0.0
    cutoff = len(ordered)
    for i, c in enumerate(ordered):
        step_cost = c.estimated_seconds + (cool_down_seconds if i > 0 else 0.0)
        if total + step_cost > budget_seconds:
            cutoff = i
            break
        steps.append(PlanStep(c.project_id, stage, c.estimated_seconds))
        total += step_cost
    remainder = tuple(c.project_id for c in ordered[cutoff:])

    return PlanSpec(plan_id=plan_id, policy=policy, profile_name=profile_name,
                      steps=tuple(steps), remainder=remainder, budget_seconds=budget_seconds,
                      estimated_total_seconds=total)


# ---------------------------------------------------------------------------
# Approval -- explicit, per-plan (0037 clause 2). A plan is generated and
# approved; it is never authored, and there is no route that accepts
# caller-supplied plan JSON to save (the line CID's chain_builder.py crosses
# that this module must not -- see the module docstring).
# ---------------------------------------------------------------------------

def approve(spec: PlanSpec, *, now: str | None = None) -> PlanSpec:
    """Returns a NEW, approved `PlanSpec` -- frozen dataclasses don't mutate
    in place, and approval producing a new object (rather than flipping a
    flag on the caller's live reference) means an already-approved plan
    handed elsewhere can't be silently un-approved by someone else's edit."""
    stamp = now or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    return dataclasses.replace(spec, approved=True, approved_at=stamp)


def validate_for_execution(spec: PlanSpec, *, known_stage_keys: frozenset[str] | None = None,
                            known_profiles: frozenset[str] | None = None) -> bool:
    """Re-validated immediately before execution, not just at build time --
    a plan approved an hour ago against a model since unloaded (or a
    profile since renamed) is refused HERE, not silently run anyway. Raises
    `PlanValidationError` (structural problems, via `PlanSpec.validate`, or
    an unknown profile) or a plain `ValueError` (never approved) --
    distinguished so a caller can tell "this plan is malformed" from "this
    plan is fine but nobody signed off on it" apart."""
    spec.validate(known_stage_keys=known_stage_keys)
    if not spec.approved:
        raise ValueError(f"plan '{spec.plan_id}' has not been approved -- refused "
                          "(0037 clause 2: approval is explicit and per-plan).")
    if known_profiles is not None and spec.profile_name not in known_profiles:
        raise PlanValidationError(
            f"plan '{spec.plan_id}' invalid: profile '{spec.profile_name}' is no longer "
            f"known on this machine (known: {sorted(known_profiles)}) -- refused rather "
            "than run against a profile that may have changed meaning since approval.")
    return True


# ---------------------------------------------------------------------------
# PlanRegistry -- file-backed persistence, ChainRegistry's own shape
# (atomic tmp-swap, malformed files recorded and skipped rather than
# crashing the registry).
# ---------------------------------------------------------------------------

class PlanRegistry:
    def __init__(self, root: Path | None = None) -> None:
        self.root: Path = Path(root) if root is not None else _PLANS_DIR
        self._specs: dict[str, PlanSpec] = {}
        self.errors: list[str] = []

    def _path_for(self, plan_id: str) -> Path:
        return self.root / f"{plan_id}.json"

    def save(self, spec: PlanSpec) -> Path:
        """Validate then atomically persist (`.tmp` + `os.replace`, the
        same last-write-wins posture `ChainRegistry.save` uses)."""
        spec.validate()
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path_for(spec.plan_id)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(spec.to_dict(), indent=2), encoding="utf-8")
        os.replace(tmp, path)
        self._specs[spec.plan_id] = spec
        return path

    def load_all(self) -> dict[str, PlanSpec]:
        self._specs = {}
        self.errors = []
        if not self.root.exists():
            return {}
        for path in sorted(self.root.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                spec = PlanSpec.from_dict(data)
                spec.validate()
            except (OSError, json.JSONDecodeError, PlanValidationError, ValueError) as exc:
                self.errors.append(f"{path.name}: {exc}")
                continue
            self._specs[spec.plan_id] = spec
        return dict(self._specs)

    def get(self, plan_id: str) -> PlanSpec | None:
        return self._specs.get(plan_id)

    def list_ids(self) -> list[str]:
        return sorted(self._specs)
