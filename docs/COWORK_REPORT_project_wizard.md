# Cowork report — Project Wizard

**Brief:** `docs/COWORK_BRIEF_project_wizard.md`. **Ratification:** DECISIONS
0042 (accepted, precondition satisfied) and 0043. **Status:** Tasks 1–4 built
and hermetically verified on `LucasGoonPC` (the gaming rig, no MCF corpus on
this machine). Task 5's dev-rig fixture is built and wired into the
allowlist. **The three named pilots (`sf-data-service`, `PricingModel`,
`SolConfig`) are NOT wired** — this session has no access to those repos'
checkouts on the work rig (`10280L`), so Task 5's discovery step (identify
each project's real generator script, confirm it is safely re-runnable, hand-
author its manifest only after reading it) could not be done from here. That
is recorded plainly below rather than guessed at from the brief's own
worked example.

## What was built

- **`chronicler/review/project_wizard.py`** — the whole module: manifest
  parsing/validation (Task 1), the per-host allowlist loader (Task 2),
  `board()` (Task 3), execution through a reused pid+heartbeat lock and
  `curator_control.classify_outcome`'s four states (Task 3), and the
  `WizardPlanSpec`/`WizardPlanStep` seam (Task 4). One `router()` factory,
  registered as a `STATUS_REGISTRY` module.
- **`config/project_wizard.allow.json`** — committed, per-host repo
  allowlist (0042 clause 2). See "The allowlist as committed" below.
- **`wizforge.manifest.json`** — the dev-rig fixture manifest, committed at
  this repo's own root, declaring two real, already-existing, read-only-or-
  idempotent stages: `verify.py` (kind `other`) and `run.py build` (kind
  `report_build`, `output_glob: data/estate.json`).
- **`chronicler/review/modules.py`** — one new `ModuleDescriptor`
  (`id="project_wizard"`, order 55, between Docs board and UAT sidebar),
  `STATUS_REGISTRY`, `requires=()` on the `repo_docs`/`board` precedent: the
  allowlist and every manifest are read from this checkout the same
  structural way `docs/` is, so an empty allowlist is an honest empty board,
  not a degraded tab.
- **`chronicler/review/static/views/project_wizard.js`** — the pane: one
  card per repo, one row per stage, a single "Run" button per stage (no
  action offers to chain into another stage, per the brief's working rule),
  a freshness line, the last-run outcome, and the lock state including
  staleness.

No route in `app.py` was touched — the `STATUS_REGISTRY` wiring
(`modules.registered()` → `app.include_router(descriptor.router(ctx), ...)`)
picks the new module up automatically; that indirection is exactly what
Task 1/`unified_app` built the registry for.

## The manifest contract, as implemented

`schema_version` (int, currently `1`), `repo_name`, and `stages` — each with
`key` (unique within the manifest), `label`, `kind` (`data_refresh` |
`report_build` | `other`), `command` (a non-empty list of non-empty strings —
**there is no parameter field anywhere in this schema**, 0042 clause 4),
`cwd` (relative to the manifest's own location), optional `output_glob`,
optional `freshness_source` (`"self"`, the default, or
`{"type": "delegated", "command": [...]}`), and optional `depends_on`
(recorded, read by nothing — Task 4's seam).

**Validation accumulates, then refuses**, verified directly rather than
trusted from the code: a manifest with ten independent problems (a bad
`schema_version`, a missing `repo_name`, a duplicate stage key, and one stage
missing every required field) raised `ManifestValidationError` naming **all
ten** in one exception, not the first. A manifest that fails to parse or
fails validation is isolated to that repo's card — `load_manifests()`
returns a `RepoLoadResult` per repo, and one repo's failure never touches
another's.

## The allowlist as committed, and which host entries it carries

`config/project_wizard.allow.json` carries three sections:

- `"default"` — empty (`{"repos": {}}`), so an unrecognised host gets nothing
  rather than a fallback repo it never declared.
- `"LucasGoonPC"` (gaming rig) — `l5gn-tools-fixture` → this repo's own root.
  The dev-rig fixture, and only the fixture; commented in the file as not a
  pilot and not a precedent for widening.
- `"10280L"` (work rig) — present, `"repos": {}`, with a comment explaining
  why it is empty: the three pilots' manifests have not been authored, and
  this session has no access to those checkouts to author them from.

`load_allowlist()` layers `"default"` → the resolved host's entry, the same
precedence `l5gntools.config.machine()` uses for `machines.json`.

## The containment tests against manifest-declared paths

Run directly against the module (not just read from the code):

- A manifest declaring `cwd: "../../etc"` resolves through
  `resolve_stage_cwd()` → `estate_data.resolve_contained()` and is refused
  with reason `cwd_escapes_repo_root` — the same gate `docs_board.py` uses
  for a symlink escaping `docs/`, given a new anchor set (0042 clause 5),
  never a second implementation.
- `board()` against the fixture manifest resolves both stages' `cwd`
  correctly, reads `data/estate.json`'s real mtime for the `build` stage's
  self-freshness, and reports `verify`'s stage as having no output to check
  (no `output_glob` declared) rather than guessing one.

## Where the lock primitives ended up, and why

**Imported directly from `curator_control`** —
`acquire_lock`/`release_lock`/`heartbeat`/`lock_status`/`break_lock` plus
`classify_outcome` and the `StageOutcome`/`ExecutionRefused` types — not
lifted into a shared module. Task 3 left "import or lift, decide at build
time" open; importing is correct here because nothing about those functions
is Curator-specific: every one of them already takes `lock_path` as a
parameter, so Project Wizard hands it a per-`(repo_key, stage_key)` lock
file (`data/project_wizard/locks/<repo_key>__<stage_key>.lock`) and the
Curator's own lock at `data/knowledge_curator/.curator_run.lock` is
untouched. Lifting would have meant moving working code out of a module
`verify.py` already audits, for no behavioural gain.

Verified directly: acquiring the lock manually and then calling
`execute_with_lock` for the same `(repo_key, stage_key)` raises
`ExecutionRefused(reason="already_running")` — never queued, never silently
dropped. `break_stage_lock()` clears it and nothing else does; there is no
code path in this module that reclaims a stale lock automatically.

## Execution, run markers, and outcome — exercised end to end

Because `python verify.py`'s full auditor+tester suite runs longer than this
session's remote-shell timeout allows in one call, the **live walk of the
`verify` stage through Project Wizard's own execute path was not performed
in this session** — that is a tooling constraint of how this build was
produced, not a limitation of the code, and it is UAT item `[H]` below,
unwalked. What *was* run end to end, against a synthetic fixture repo with a
trivial (`echo`) stage, using the same `execute_with_lock()` code path the
real stages use:

- a full run: `state == "success"`, `returncode == 0`, the streamed
  `stdout_tail` captured correctly, and a run marker written with a
  UTC ISO-8601 `finished_at`;
- the lock refusal above;
- the explicit break-lock path.

Also run directly against `verify.py`'s own auditors (not the full slow
suite, but every auditor whose job is exactly this kind of change):
`auditor_module_contract`, `auditor_dependency_direction`, `auditor_stdlib`,
`auditor_readonly`, `auditor_tool_contract`, `auditor_doc_claims`,
`auditor_uat_stamp`, and `tests.tester_module_registry`,
`tests.tester_file_census`, `tests.tester_census`, `tests.tester_project_root`,
`tests.tester_docs_board`, `tests.tester_review_preflight` — all green.
**A full `python verify.py` has not been run in this session** and should be
run on the gaming rig before this lands, per the working convention.

## The PricingModel and SolConfig discovery findings

**Not done.** Task 5 requires identifying the real generator script behind
`Pricing_Model_Explorer.html` and `solconfig_asset_dashboard.html`, confirming
each is safely re-runnable, and only then hand-authoring that repo's
`wizforge.manifest.json` — from inside that repo, having read its scripts.
This session ran on the gaming rig with no access to `PricingModel`'s or
`SolConfig`'s checkouts (they exist only on the work rig, per the brief's own
"The board is per-machine" section), so nothing was guessed at and no
manifest was authored blind for either repo. Nothing was found *not* safe to
re-run, because nothing was inspected — that is the honest state, not a
result of "nothing was found."

`sf-data-service`'s manifest is also not authored, for the same reason —
its `estate refresh` command and `estate status` delegated-freshness
behaviour are described precisely in the brief, but authoring the manifest
from a description rather than the repo itself would be exactly the
"honour-system contract" 0042/the brief's own words rule out.

## Whether the dev fixture carried the build

**Yes, for Tasks 1–4's own logic** — manifest parsing/validation, allowlist
layering, containment resolution, freshness (both `self` and the refusal
path), the board render, the lock, and the streaming execute/outcome/marker
path were all exercised against this fixture, hermetically, on the machine
with no MCF repo. What it could **not** exercise: a `"delegated"`
freshness source (the fixture uses `"self"` for both stages — there was no
safe, already-proven "print a status string" command in this repo to point
one at without inventing one), and running a stage whose own subprocess
takes long enough to prove the streaming really shows progress before exit
(the fixture's `verify`/`build` stages were declared but not walked through
the UI in this session, per above). Both are named as open items for the
UAT walk on whichever rig runs it next, not silently assumed to work.

## Explicitly not done here (scope, not a cut)

- No route or file in `app.py` needed changing (see above) — noted so a
  reviewer does not go looking for one.
- `REQUIREMENTS`/`module_contract.py`'s closed vocabulary was **not**
  extended with a new requirement key for Project Wizard; `requires=()`
  was used instead, on the `repo_docs`/Docs-board precedent. If a future
  round wants the tab to visibly grey out on a host with an empty
  allowlist (rather than open onto an honest "no repos configured" pane),
  that is a small, separate addition to `REQUIREMENTS` and
  `module_contract.capabilities()` — not done here because the board's own
  empty-state message already states the fact plainly, the same way
  `docs_board`'s empty columns do.
- The Conductor/planner's `ProjectCandidate`/`build_plan` machinery was not
  touched or reused for Task 4's `WizardPlanSpec` — it is a much smaller,
  deliberately inert shape (no ranking, no budget, no builder function),
  because nothing in this brief populates one yet.
