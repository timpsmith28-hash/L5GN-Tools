# Cowork brief — Project Wizard: one control surface over every repo's scripts and reports

**Origin:** design thread, 2026-08-13, off a live PowerShell transcript of
`sf-data-service estate status`/`estate refresh` working end to end, the first
Knowledge Curator report landing in L5GN-Tools, and two screenshots (Chronicler
Command Deck's Knowledge Curator tab; the Conductor's plan-builder/calibration
panel) plus two live SPA report examples (`Pricing_Model_Explorer.html`,
`solconfig_asset_dashboard.html`). Reviewed against the toolkit 2026-08-13.

**Precondition — satisfied.** DECISIONS **0042** (a consumer repo declares its
own runnable stages; the toolkit executes them under a committed repo allowlist
and never widens what they can do) is **accepted**. This brief may not be built
without it, because it is the ruling that authorises a second declaration site
outside `verify.py`'s reach. Read it before Task 2.

**Depends on — this repo's rulings:** **0023** (work-estate visibility is
auth-gated even to view — the gate itself remains unbuilt), **0025** (visibility
is scoped by *surface*, not by estate — a loopback-bound, single-estate surface
is not gated), **0031** (a non-gating check surface reports findings, never a
verdict), **0036** (the cross-machine mesh stands down by default — this is a
single-machine, single-operator surface, not a mesh service), **0037**
(execution parameters are generated from a ratified plan, never supplied by a
caller), **0042** (above), **0043** (another repo's rulings are cited with their
repo, at every mention).

**Depends on — other repos' rulings, named per 0043:** `sf-data-service` **0029**
(object read-scope allowlist — widening scope is a reviewed, committed edit,
never a side effect of what an operator typed) and `sf-data-service` **0032**
(the estate view is local-only status plus delegate-only refresh — no second
freshness engine, no scheduler yet). Also `WizForgeAnalytics` **ROADMAP R9**
(the refresh orchestrator — "one adaptive process with estate purview").

**Also builds on, in code:** `chronicler/review/docs_board.py`'s containment
anchor and derive-never-store discipline; `chronicler/review/curator_control.py`'s
hard execution allowlist, pid+heartbeat lock, and streaming `Popen` runner.

**Deliverable:** a new module inside L5GN-Tools, **Project Wizard**, that reads a
declared, committed manifest of runnable stages from each of a small, allowlisted
set of project repos (data-refresh and report-build stages alike), shows what
exists and whether it looks fresh, and lets Tim trigger one stage at a time by
hand. Nothing chains automatically in v1. The manifest and the stage-invocation
contract are built as validated, versioned artefacts specifically so a future
orchestrator (`WizForgeAnalytics` ROADMAP R9) can drive the same seam later
without a rewrite.

---

## Why this, why now

`sf-data-service` just proved the first half of the loop live: `estate
status`/`estate refresh` give one place to see staleness and trigger a pull
across ~20+ registered requirements, all local-only until a refresh is asked
for. Most other projects in the estate end their own pipeline the same shape — a
script chain that lands a SPA report (`Pricing_Model_Explorer.html`,
`solconfig_asset_dashboard.html` are two concrete, already-built examples).
Refreshing the data naturally raises the next question: who rebuilds the report
that consumes it? Today that's "run the script by hand, if you remember which
one." Project Wizard is the elevation of the existing docs-board pattern — read a
repo's declared shape, render it, offer an action — extended from *documents* to
*scripts*, and widened from *L5GN-Tools itself* to a small, named set of other
repos.

That widening is the one genuinely new thing here. Every existing surface in this
codebase — `docs_board.py`'s `REPO_ROOT` anchor, `estate_data.resolve_contained`
— has treated "stay inside this one repo" as structural, not configurable.
Project Wizard is the first surface asked to reach outside it on purpose. That is
why 0042 exists, and why Task 2 below is the load-bearing task in this brief
rather than a formality ahead of the UI work.

---

## What already exists — verified against the code, 2026-08-13

Build on these; do not reimplement them.

- **`curator_control`'s lock is already pid + heartbeat**, reports stale via
  `_pid_alive` and `STALE_HEARTBEAT_SECONDS`, and is **never auto-reclaimed**.
- **`curator_control.run_stage` already streams**, via `subprocess.Popen` read
  line by line — not `subprocess.run(capture_output=True)`.
- **`classify_outcome` already returns four states** — `success` / `failed` /
  `skipped` / `blocked`. `blocked` is exactly the state wanted for a precondition
  that stopped the subprocess starting; **nothing new is needed, and a fifth
  state is a stop condition.**
- **`docs_board`'s `_ANCHORS` is already a tuple**, so "a new anchor set" is the
  designed extension point for `resolve_contained`, not a modification to it.
- **`l5gntools.config.machine()`** already resolves per-host with a `default`
  fallback, layered `machines.json` → `local.json`.

---

## Working rules

- **The manifest is data, never code.** A repo declares its runnable stages in a
  committed JSON file at its own root. Project Wizard never imports another
  repo's Python — most pilot repos have no reason to expose a Python API to an
  outside caller, and a manifest is the same language-agnostic contract
  `sf-data-service`'s own `.request.json` already is. **0042 clause (1).**
- **One execution allowlist, built from validated manifests**, exactly like
  `curator_control.STAGE_TABLE`/`EXECUTION_ALLOWLIST`. The execute route accepts
  a `(repo_key, stage_key)` pair and nothing else — no argv, no path, no flag
  reaches a subprocess from outside the manifest that declared it. **0042 clause
  (3); 0037 clause (1) applied one repo further out.**
- **One repo allowlist, committed, reviewed-to-widen** — the posture of
  `sf-data-service` 0029. Project Wizard looks only where it has been told to
  look, and adding a fourth repo is a one-line committed diff, never a path typed
  into the UI. **0042 clause (2).**
- **Derived, never stored**, the rule `docs_board.py` states for itself: no
  board-state file, no cached column assignment. Every render walks the
  allowlisted repos' manifests and their declared output paths fresh.
- **No second freshness engine.** Where a repo already answers "is this fresh"
  itself — `sf-data-service`'s registry, reached via `estate status` — Project
  Wizard calls that and shows its answer. It does not re-derive staleness a
  second, competing way. **0042 clause (7); `sf-data-service` 0032's precedent.**
- **Manual only, in v1.** No stage's completion ever triggers another stage.
  Every run is one explicit click on one card. (Tim's call, deliberately against
  this brief's own first-pass recommendation — see Task 4.)
- **Reuse the lock and the outcome contract.** `curator_control`'s pid+heartbeat
  lock and `classify_outcome`'s four states, not a second lock scheme and not a
  fifth state.
- **Read-only where the underlying repo's own tool is read-only.** Project Wizard
  does not widen what any pilot repo can do — `sf-data-service` stays a read-only
  Salesforce client regardless of who clicks the button. **0042 clause (6).**
- UTF-8 explicit, UTC ISO-8601, same as everywhere else in this estate.

---

## Task 1 ▸ the manifest contract — `wizforge.manifest.json`, one per repo

A committed file at each participating repo's root (not inside L5GN-Tools — the
repo declares its own shape, the same way `.request.json` lives inside
`sf-data-service` rather than being authored centrally).

- `schema_version` — an integer, so a later field addition is a documented bump,
  not a silent shape change (mirrors the Conductor's own plan versioning under
  0037).
- `repo_name` — a stable label, shown on the card.
- `stages`: an ordered list, each with:
  - `key` — stable handle, unique within the repo.
  - `label` — human-readable.
  - `kind` — `"data_refresh"` | `"report_build"` | `"other"`. Not enforced
    behaviourally in v1 (every kind runs the same way); recorded because Task 4's
    future planner needs to reason about "refresh, then build."
  - `command` — **a fixed, literal argv list**, e.g. `["python", "-m",
    "sf_service", "estate", "refresh"]` or `["python", "generate_report.py"]`.
    Fixed at declaration time. **There is no parameter slot in this schema at
    all, on purpose.** 0037 permitted schema-declared parameters because the
    Conductor needed pacing; **0042 clause (4)** declines that weakening here
    because this surface does not need it. Adding one later is its own entry with
    its own reason.
  - `cwd` — relative to the manifest's own location; resolved and verified
    contained within that repo's allowlisted root before every run (Task 2).
  - `output_glob` (optional) — a path glob whose newest mtime is shown as "last
    built"; absent for a stage with no single output artefact (e.g. one that only
    refreshes an upstream registry).
  - `freshness_source` (optional) — `"self"` (use `output_glob`'s mtime, the
    default) or `"delegated"` with a `command` of its own to run and read for a
    status string. This is how the `sf-data-service` stage reports its
    registry-derived staleness instead of Project Wizard guessing from file
    mtimes over data it does not understand.
  - `depends_on` (optional, list of stage keys) — recorded, never acted on in v1.
    Task 4's seam, not a live dependency graph yet.
- **Validation accumulates, then refuses.** Report *every* violation in a
  manifest at once, not the first — the `chain_registry._validate_stage` pattern
  the Conductor adopted, and the difference between fixing a manifest in one pass
  and one error per attempt.
- A manifest that fails to parse or fails validation blocks **that repo's card
  only**, with the validation error shown on the card — the same per-item
  isolation `estate refresh` already gives `sf-data-service`'s own requirement
  batch, and the same "findings, not a crash" posture `docs_board.py` takes
  toward a malformed archive stamp.

---

## Task 2 ▸ the repo allowlist — where Project Wizard is allowed to look

**This is the load-bearing task, and 0042 is the ruling that authorises it.**

- A new committed file, `config/project_wizard.allow.json`, keyed the same way
  `config/machines.json` already is (per-host, since MCF repos sit at different
  absolute paths per machine): `{"<host>": {"repos": {"<repo_key>": "<path>"}}}`,
  falling back to a `"default"` entry the same way `l5gntools.config.machine()`
  does.
- **0042 records that this being config rather than code is a step down from
  0033's posture**, taken knowingly because per-host paths are exactly what
  `machines.json` exists for. Do not "improve" it into a code constant listing
  absolute paths; that trade was already considered and refused.
- Do **not** repurpose `estate_roots()` for this. It already declares
  personal/work scope tags for a different purpose (document ingestion); folding
  execution permission into the same list would make "this directory is known to
  the estate" and "this directory's scripts may be run by a click" the same fact,
  which they must not be. A separate, smaller, explicitly execution-flavoured
  allowlist keeps `sf-data-service` 0029's discipline intact: *widening scope is
  its own reviewed diff*, never an inherited side effect of an unrelated list
  growing.
- Every repo path is resolved and re-verified through the **existing**
  `estate_data.resolve_contained` gate with a **new anchor set** (the allowlisted
  repo roots) — `_ANCHORS` is already a tuple, so this is the designed extension
  point, not a second implementation of containment checking. A manifest whose
  `cwd` or `output_glob` resolves outside its own declared repo root is refused
  the same way a symlink escaping `docs/` is refused today. **0042 clause (5).**

### The board is per-machine, and that is what makes it developable

All three pilot repos (Task 5) are MCF/work and exist **only on the work rig**.
The gaming rig — where development actually happens — cannot exercise any of them.

The allowlist is already per-host, so this resolves without a new mechanism:
**the gaming rig's entry points at personal-estate repos, the work rig's at the
MCF three.** L5GN-Tools itself has real runnable stages (`run.py build`,
`verify.py`) and makes a legitimate dev fixture; a second personal repo may be
added if one stage is too thin to exercise the board.

This is not a co-rendering: each machine renders only its own estate's repos,
which is 0025 satisfied by construction and the same shape 0039 gives the
Curator. **A single allowlist file containing both hosts' entries is fine** — the
file is a config that ships manually, and only the running host's entry is ever
resolved.

**This is a work-estate surface on the work rig.** Project Wizard inherits 0025's
discipline as it stands: bound to loopback, rendering only the machine's own
estate, never co-rendered alongside personal-estate material. If it is ever asked
to become reachable beyond the machine it runs on, it falls under 0023's
still-unbuilt TOTP gate exactly as the knight's work column would. This brief
does not build that gate and ships nothing that needs it.

---

## Task 3 ▸ the module — `chronicler/review/project_wizard.py` + surface

- `project_wizard.board(allowlist=None)` — derives the whole board fresh on every
  call, the same shape as `docs_board.board()`: one card per `(repo_key,
  stage_key)`, grouped by repo. No stored board state, no cache.
- Each card shows: label, kind, last-run outcome (from Project Wizard's own small
  per-stage run-marker — timestamp, exit state — written after each run, never
  inferred), and a freshness line resolved per the stage's `freshness_source`
  (self mtime, or the delegated command's own answer).
- Execution: one hard allowlist built from every validated manifest at
  board-build time — `frozenset((repo_key, stage_key) for ...)` — mirroring
  `curator_control.EXECUTION_ALLOWLIST` exactly. The execute route takes only
  this pair.
- Lock: one real file lock per `(repo_key, stage_key)`, **reusing
  `curator_control`'s existing pid+heartbeat primitives** — they are built,
  report stale, and never auto-reclaim. Import them, or lift the same small set
  of functions into a shared location if importing directly couples the two
  modules more than is wanted; decide at build time, not in this brief.
- Streaming, not buffered to exit: spawn via `Popen`, read merged stdout/stderr
  line by line, **exactly as `curator_control.run_stage` already does**, so a
  multi-minute report build shows it is alive rather than hanging silently until
  it exits.
- Outcome: `classify_outcome`'s **existing four states** —
  success/failed/skipped/blocked. `blocked` already covers a precondition that
  never let the subprocess start (missing script, bad `cwd`, not on the
  allowlist). **No fifth state.**
- The UI surface sits in the existing app shell (`chronicler/review/app.py`), as
  a new tab/panel beside the Knowledge Curator and Docs Board, not a second
  application.

---

## Task 4 ▸ the seam for the future orchestrator — design now, don't wire yet

Tim's own call: v1 stays fully manual, every stage triggered by an explicit
click, no automatic chaining of "data refreshed" into "now rebuild the report" —
deliberately the more conservative of the two options put to him. That does not
mean the future chain goes undesigned:

- `depends_on` (Task 1) is recorded on every stage now, read by nothing yet.
- A `project_wizard.plan` shape — schema-versioned, validated, serialisable, in
  the same spirit as the Conductor's `PlanSpec`/`PlanRegistry` (0037) — is
  sketched as a dataclass or equivalent even if no planner populates it in this
  brief. An ordered list of `(repo_key, stage_key)` steps, each still requiring
  explicit approval before it runs, is the shape a future scheduler would emit;
  this brief just makes sure that shape already exists and is exercised (even
  trivially, one manual step at a time) before anything is asked to plan across
  it.
- This is explicitly **not** `WizForgeAnalytics` ROADMAP R9. R9 is "one adaptive
  process with estate purview" across the whole estate's refresh cadence, and
  stays a Horizon 3 build. This brief's job is narrower: don't build anything
  here that R9 would have to tear out later. If Task 4 turns out to need more
  than a stub to hold that promise, **that is a finding to report, not a licence
  to quietly build R9 early.**

---

## Task 5 ▸ pilot wiring — exactly 3 repos on the work rig

Per Tim's answer: the narrowest pilot, not the widest plausible one.

- **`sf-data-service`** (already inside WizForgeAnalytics) — one manifest, one
  stage: `data_refresh`, command `["python", "-m", "sf_service", "estate",
  "refresh"]`, `freshness_source: delegated` reading `estate status`'s own
  output. No new capability is added to `sf-data-service` by this brief —
  Project Wizard's card is a thin, honest shell over a command that already
  exists and already works, per the transcript that prompted this brief.
- **PricingModel** and **SolConfig** — before either gets a manifest, this task
  includes a discovery step: **identify the actual script(s)** behind
  `Pricing_Model_Explorer.html` and `solconfig_asset_dashboard.html`, confirm
  each is safely re-runnable (idempotent, no destructive side effect on rerun, no
  hidden interactive prompt), and only then hand-author that repo's
  `wizforge.manifest.json`. Do not guess a script name and wire it blind — a
  manifest entered from outside the repo without having read the repo's own
  scripts is exactly the "honour-system contract" `sf-data-service` moved away
  from at Capture (`SF_DATA_SERVICE.md` §"Capturing a requirement").
- Each of the 3 manifests is committed inside its own repo and reviewed before
  Project Wizard's allowlist (Task 2) is pointed at it — the review is part of
  "done", not a follow-up. **0042's honesty clause depends on this**: the
  manifest is the declaration site `verify.py` cannot see, so the human review of
  it is the only gate it gets.

### Dev-rig fixture — a fourth manifest that never ships to the work rig

So the build can be exercised where it is written: **one manifest in L5GN-Tools
itself**, declaring a genuinely runnable stage or two (`verify.py`, `run.py
build`), listed only under the gaming rig's host entry in the allowlist. It
proves the board, the lock, the streaming runner and the containment gate on a
machine that has no MCF repo on it at all.

It is a fixture, not a pilot: it does not count toward the three, and it is not a
precedent for widening. Report whether it was sufficient to develop against, or
whether the MCF stages differed enough that work-rig-only testing was still
needed.

---

## Explicitly out of scope

- Any automatic chaining of one stage into another — Tim's decision, this brief's
  whole v1 posture.
- Any parameter slot in the manifest schema — 0042 clause (4).
- Scheduling or cron of any kind. Belongs to `WizForgeAnalytics` ROADMAP R9, not
  this brief (the same boundary `sf-data-service` 0032 already draws for `estate
  refresh`).
- Any repo beyond the 3 named above, plus the dev fixture. Widening is a reviewed
  allowlist edit — a small, separate, later ask.
- A cross-object/cross-repo "true SQL" interface, or any resolution of the
  export-model fork question in `WizForgeAnalytics` ROADMAP.md — unrelated
  question, not gated by or gating this brief.
- Any write path to Salesforce or any other org. `sf-data-service` stays
  read-only; Project Wizard only ever shells to a command a repo already declared
  for itself.
- A mesh-wide or multi-machine version of this board. 0036 stood the mesh down as
  the default shape; this is a single-machine, single-operator surface.
- Building the TOTP/work-estate gate (0023). This brief inherits its discipline
  (loopback-bound, single-estate rendering); it does not build the gate.
- Re-deriving or second-guessing any pilot repo's own freshness logic. Delegate,
  per `sf-data-service` 0032's precedent.

---

## Stop conditions

- A manifest's `command` is anything other than a fixed, literal argv list — a
  caller-supplied flag, path, or parameter reaching a subprocess — → stop (0037
  clause 1, 0042 clause 4).
- Any repo outside the committed `project_wizard.allow.json` is read, listed, or
  executed → stop (0042 clause 2).
- A path resolved from a manifest (`cwd`, `output_glob`) escapes its own declared
  repo root → stop; this must fail through the shared `resolve_contained` gate,
  never a bespoke check (0042 clause 5).
- One stage's completion automatically triggers another stage without an explicit,
  separate click → stop (Tim's decision, non-negotiable for v1).
- Project Wizard keeps its own record of a pilot repo's data freshness instead of
  delegating to that repo's own freshness engine where one exists → stop (0042
  clause 7).
- A stale lock is reclaimed automatically, without an explicit, named "break"
  action → stop.
- `classify_outcome` gains a fifth state → stop.
- Validation raises on the first error rather than reporting all of them → stop.
- Project Wizard becomes reachable beyond loopback, or co-renders alongside
  personal-estate material, without the TOTP gate existing → stop (0023/0025).
- A manifest is authored for PricingModel or SolConfig without first having read
  and confirmed the actual generator script it points at → stop (Task 5's
  discovery step is not optional).
- Another repo's ruling is cited by bare number → stop (0043).

---

## UAT — acceptance checks (Tim walks these)

Mark each `[G]` / `[H]` per 0031.

- `[G]` A malformed manifest (bad JSON, missing `command`, unknown
  `schema_version`) blocks only that repo's card, with **every** validation error
  shown at once — the rest of the board renders normally.
- `[G]` The execute route refuses any `(repo_key, stage_key)` pair not present in
  the allowlist built from validated manifests, with no argv, path, or flag
  accepted alongside it.
- `[G]` A repo path not present in `project_wizard.allow.json` is never read,
  described, or executed, **even if a manifest file physically exists there**.
- `[G]` A `cwd`/`output_glob` that resolves outside its own repo's root (crafted
  relative path, or a symlink) is refused by `resolve_contained`, not by a
  bespoke check.
- `[G]` Triggering `sf-data-service`'s stage runs `estate refresh` exactly,
  streams its output live, and reflects `estate status`'s own freshness answer on
  the card — never a second, Project-Wizard-derived staleness number.
- `[G]` Kill a running stage's process: the lock is left held, reported stale via
  pid+heartbeat on the next board render, and is never auto-reclaimed — only an
  explicit break action clears it.
- `[G]` Two clicks on the same stage in quick succession: the second is refused
  as "already running", never queued, never silently dropped.
- `[G]` No card offers an action that chains into another stage; there is no
  "refresh then rebuild" button anywhere in this slice.
- `[G]` On the gaming rig, the board renders the dev fixture and **no MCF repo is
  reachable, described, or listed** — the host entry is the only thing consulted.
- `[H]` **Walk the sf-data-service card for real** — trigger it, watch it stream,
  confirm the freshness shown afterward matches what `estate status` reports
  directly from the command line.
- `[H]` **Walk the PricingModel and SolConfig discovery findings** — did Task 5
  correctly identify the real generator script for each, and is each confirmed
  safe to re-run before its manifest went live?
- `[H]` **Does the board tell you what you actually want to know at a glance** —
  which repos are stale, which just ran, which failed — or does it need another
  pass at the layout before it earns a spot next to the Knowledge Curator tab?
- `[H]` **Is the manifest shape something you'd want to hand-author for a fourth
  repo later**, or does Task 1's schema already feel like it's missing something
  obvious once you've lived with three real examples?
- `[H]` **Was the dev fixture enough to build against?** If the MCF stages
  differed enough that you still had to develop on the work rig, that is a
  finding about the fixture, not a failure of the round.

Results log needs a `uat` stamp naming the commit; do not write a `gate=` field.

---

## Reporting

`docs/COWORK_REPORT_project_wizard.md`, walk-sheet
`docs/UAT_project_wizard.md`, stamped results after the walk.

Record: the manifest schema as implemented, with its validation errors shown
accumulated rather than first-only; the allowlist as committed and which host
entries it carries; the containment tests against manifest-declared paths; where
the lock primitives ended up (imported or lifted) and why; the PricingModel and
SolConfig discovery findings in full, including anything found *not* safe to
re-run; and whether the dev fixture carried the build.
