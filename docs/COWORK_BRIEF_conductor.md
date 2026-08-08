# Cowork brief — the conductor: a budget becomes a plan, and the hardware gets to breathe

**Origin:** design thread, 2026-08-08, after real K2 runs on the work rig.
**Depends on:** DECISIONS **0032** (recency is the truth order), **0033**
(propose, ratify, execute), and the curator tab as built
(`COWORK_BRIEF_curator_tab.md` / `COWORK_REPORT_curator_tab.md`) — specifically
`curator_control.STAGE_TABLE`, its execution allowlist, and its run lock.
**Deliverable:** a conductor that turns *"you have an hour"* or *"run overnight"*
into an ordered, approved plan of scoped stage invocations, paced so the hardware
survives it.

The problem is not correctness. K2 and K4 work. The problem is that pushing many
prompts consecutively drives the GPU into thermal throttling, so the current
practice is to run K2 one project at a time and babysit it, reloading the model
by hand between projects to keep memory fresh. **That practice is a working
schedule executed by a human, and it should be a working schedule executed by
code.**

---

## The finding that should be tried before anything is built

**LM Studio already does the model-freshness half.** JIT loading loads a model on
demand; **idle TTL** unloads it after a set idle period (60 minutes by default for
JIT-loaded models); **auto-evict** unloads the previous model before loading a
new one. The `ttl` field is accepted in the request payload on the
OpenAI-compatible endpoint that `extract_claims.call_lmstudio` already POSTs to.

So *"force a model reload between projects"* may reduce entirely to **set a short
TTL and let the cool-down gap expire it** — no load/unload controller, no `lms`
CLI dependency, no new subprocess, one new field in a payload that already exists.

**Task 1 tries that first and reports whether it was sufficient.** Build the
explicit lifecycle controller only if TTL demonstrably is not enough, and say
what the evidence was. A feature deleted by reading the vendor's documentation is
the cheapest feature in the round.

Reference: [Idle TTL and Auto-Evict](https://lmstudio.ai/docs/developer/core/ttl-and-auto-evict),
[LM Studio REST API](https://lmstudio.ai/docs/developer/rest).

---

## Precondition ▸ DECISIONS 0037 must be ratified before any code

Two things here are rulings, not implementation choices.

The first is a **security boundary being widened**. `run_stage` today accepts a
stage key and nothing else — `STAGE_TABLE`'s docstring calls the allowlist "the
whole security story of this task", and the argv template is built server-side
from `config/local.json`. The conductor needs `--project` and a cool-down on
those invocations. That is caller-influenced argv arriving by a new route, and
pretending otherwise would be the quiet stretch this log exists to prevent.

The second is **what a partial run is allowed to be**, which is a genuine
extension of 0032 and the more important of the two.

> ## 0037 — Execution parameters are generated from a ratified plan, never supplied by a caller; and a budgeted run's unit of work is a project, or a newest-first prefix of one
>
> **Date:** 2026-08-08 · **Status:** proposed · **Builds on:** 0032 (recency is
> the truth order), 0033 (propose, ratify, execute), the curator tab's execution
> allowlist · **Source:** design thread, after real K2 runs on the work rig
>
> **Context.** The curator tab's execute route accepts a stage key and nothing
> else: no argv, no path, no flag. That rule made the surface's execution remit
> auditable at a glance. A conductor cannot hold to it literally — pacing a run
> means invoking K2 scoped to one project, with a cool-down, repeatedly.
>
> Separately: 0032 makes recency the truth order. Conversations are processed
> newest-first, and an older conflicting claim is *superseded* rather than a gap.
> That property is established **by the order of processing**. A budget planner
> free to pick any subset of work — "the twenty quickest conversations across the
> estate" — would silently destroy it, and the destruction would be invisible in
> the output, because a wrongly-ordered supersession looks exactly like a
> correctly-ordered one.
>
> **Decision.**
>
> 1. **A caller supplies a plan identifier, never a parameter.** Execution
>    parameters are derived server-side from a **ratified plan**, which is itself
>    generated server-side from a bounded set of policy inputs (budget, policy
>    name, thermal profile). `STAGE_TABLE` remains the single place a runnable
>    stage is declared, and gains a **declared parameter schema** per stage —
>    which parameters that stage accepts, and their permitted ranges. A
>    parameter outside its declared range is a refusal, not a clamp.
> 2. **A plan is proposed, shown, and approved before it runs**, in the same
>    posture as 0033's per-row ratification. An unapproved plan does not execute.
> 3. **The unit of work in any plan is a whole project, or a newest-first prefix
>    of one.** Never an arbitrary subset, never a cross-project interleaving,
>    never "the cheapest N conversations". Within a project, newest-first is
>    absolute and the planner may not reorder it.
> 4. **A plan states its own estimate's provenance**, and where there is no
>    measurement it says so and offers no estimate. A budget plan built on a
>    guessed throughput is a fabricated window.
>
> **Consequences.** (1) is a real weakening: parameters now reach a subprocess
> that previously took none. It is bounded by being schema-declared in code
> rather than config, by the caller never naming a parameter, and by (2) putting
> a human between the plan and the process. (3) costs granularity — an hour that
> cannot fit a whole project fits a prefix of it, and sometimes fits nothing,
> which the planner must say plainly rather than filling the time with work that
> corrupts the ordering. That cost is accepted: a shorter honest run beats a
> fuller one whose supersessions cannot be trusted.

---

## Working rules

- **The conductor is a scheduler over existing invocations. It runs no
  inference, computes no claim, and reimplements no stage.**
- **Stdlib only**, in the pipeline half. `nvidia-smi` is a subprocess to a vendor
  tool and is therefore a **capability**, never a dependency — probe it, use it
  if present, degrade loudly if not.
- Gate GREEN before commit. **Every check, the planner, the ledger and the
  governor are plain functions a tester calls with a temp directory** — the same
  rule `curator_control.py` already holds to, and for the same reason.
- **No new source of truth about progress.** K2 caches per conversation, K4 has a
  per-claim decision cache, and both do `--project` scoping with merge-on-write.
  The conductor re-derives remaining work from those caches on every pass and
  **never keeps its own record of what it ran**.
- Findings, never verdicts (0031). A plan is a proposal; a run is testimony.
- UTF-8 explicit, UTC ISO-8601.

---

## Grounding — what is already there

- `curator_control.STAGE_TABLE` — six stages, script + `deterministic` +
  `model_stage` + an `argv` lambda taking the resolved model config. **The lambda
  is the extension point**: give it a validated parameter object alongside `cfg`
  and the single-declaration-point property survives.
- `EXECUTION_ALLOWLIST`, `acquire_lock` / `release_lock` (`O_CREAT|O_EXCL`),
  `classify_outcome` (success / failed / skipped / blocked), `run_stage`,
  `execute_with_lock`, `probe_lm_studio` (already reads `/v1/models`).
- `extract_claims.py` — `--project` (append), `--batch-target-tokens`,
  `--max-window-tokens`, `--small-conv-tokens`, `--cache`, `--out`,
  `merge_report()` for scoped merge-on-write, terminal progress reporting.
- `match_claims.py` — `--project`, `--cache`, `--checkpoint-every`, resumable per
  claim.
- `curator_data.Curator.stage_states()` / `coverage()` — per-stage artefact state
  and per-project coverage, already the header's source.

**What does not exist anywhere:** any notion of a pause, a cool-down, a TTL, a
timing measurement, or a plan. `grep` for `sleep|cool|ttl|throttle` across K2 and
K4 returns nothing. All of it is new, and none of it needs to touch what is there.

---

## Task 1 ▸ the two stage changes, and the TTL question answered

The smallest possible change to K2 and K4, and the only stage edits in this round.

- **`--cool-down SECONDS`** (default 0, so existing behaviour is untouched): sleep
  between conversations — *between*, never mid-conversation, so a conversation's
  windows stay contiguous and the cache's unit is unchanged. The pause belongs
  inside the stage because only the stage knows where one conversation's model
  calls end.
- **`--model-ttl SECONDS`** (optional): pass `ttl` in the chat-completions
  payload. Then **measure whether that alone keeps memory healthy across a long
  run.** Report the answer. If TTL is sufficient, the explicit load/unload
  controller is dropped from this brief and said to be dropped. If it is not,
  report what actually degraded — that evidence is what would justify building
  one, and without it the controller is speculation.
- **Emit a per-conversation timing line**: conversation id, project, message
  count, model id, wall-clock seconds. This is Task 2's entire input and it costs
  one line of output per conversation.

Nothing else about K2 or K4 changes. No new default alters an existing run.

## Task 2 ▸ the calibration ledger — measurement before planning

An append-only ledger under `data/knowledge_curator/`, fed by Task 1's timing
lines: per conversation, per model, wall-clock seconds and message count.

- Derive throughput **per model**, because model choice changes it enormously and
  an estimate that averages across models is an estimate of nothing.
- Report the spread, not just a mean. A project whose conversations run 40s to
  900s has an estimate with an honest error bar, and the plan should carry it.
- **With no measurements for the selected model, there is no estimate.** The
  planner says so and refuses to plan a budget, per 0037 (4). It may still
  produce an *unbudgeted* plan — an order of work with no time claim attached —
  and it should, because that is exactly what a first measurement run is.
- **The first conductor runs are measurement runs.** Design for that state
  explicitly and label it on the surface; it is the normal condition on day one,
  not an error.

## Task 3 ▸ the thermal governor — say which loop you are in

- **Probe for `nvidia-smi`.** Present → closed loop: sample temperature, pause
  until it drops below a resume threshold, cap the wait. Absent → open loop:
  fixed cool-down from the profile.
- **The surface must state which loop is in force, always.** An open-loop pause
  assumes a cooling rate rather than observing one, and on an already-hot machine
  it may do nothing at all. That is an acceptable degradation and an unacceptable
  silence — the same shape as slice 1's FTS5 check and the curator tab's
  shortlist-capability display.
- **Two dials, not one.** Cool-down lowers *duty cycle*; `--batch-target-tokens`
  and `--max-window-tokens` lower *peak* load. A thermal profile sets both. Report
  which lever actually helped on the real rig — that measurement is worth more
  than the feature.
- Profiles are **named and machine-scoped**, in `config/local.json` beside
  `curator_models`, since they describe this rig's cooling and nothing else.
  Suggested: `sprint` (short budget, minimal pausing), `steady`, `overnight`
  (long cool-downs, conservative peaks). Names are a starting point, not a
  ruling.
- **Cooling is a conductor state, never a stage state.** `classify_outcome`'s four
  states stay exactly as they are. A paused conductor is not a skipped stage, and
  adding a fifth blended state to that function would undo the distinction the
  curator tab was built to preserve.

## Task 4 ▸ the planner — a budget becomes a plan you approve

Input: a **budget** (a duration, or none), a **priority policy**, and a **thermal
profile**. Output: an ordered list of scoped stage invocations with pauses, an
estimate with stated provenance, and — the part that earns the feature — **what
the budget does not reach**.

- **The unit of work is a project, or a newest-first prefix of one** (0037). The
  planner may not interleave projects within a stage, and may not reorder
  conversations inside a project.
- **The priority policy is named and chosen, never inferred.** At least:
  *coverage* (projects with no claims yet), *freshness* (projects whose
  transcripts changed since last extraction), *breadth* (smallest first, to touch
  the most projects). They give genuinely different plans and the operator must
  see which one produced this one.
- **Show the plan before it runs**, with per-step estimates, cumulative time, the
  cool-down policy, and a plain statement of the remainder: *"an hour reaches
  PricingModel and SolConfig; six projects and 31 conversations are not in this
  plan."*
- **A budget too small for a whole project offers a newest-first prefix, or
  nothing.** If nothing fits, say so. Filling the time with work that corrupts
  the ordering is the failure 0037 (3) exists to forbid.
- Approval is explicit and per-plan. An unapproved plan does not run.

## Task 5 ▸ the conductor — executing a ratified plan, and what the lock must become

- Execute the approved plan step by step through `execute_with_lock`, with the
  governor's pause between steps. Per-step outcome uses `classify_outcome`
  unchanged.
- **Stop on a failure, in the shape `run_pipeline` already established**: a clean
  skip for a missing input is not a failure; a real failure stops the plan and
  says which step, rather than ploughing on through a broken chain overnight.
- **Re-derive remaining work from the caches at every step**, never from the
  plan's own record of what it has done. A plan is a proposal about the future,
  not a ledger of the past.
- **The lock is now a multi-hour hold, and that breaks it.** Today it is a file
  created `O_CREAT|O_EXCL` whose unreadable state is treated as locked — correct
  for a five-minute stage, an operational trap for an overnight run that dies to
  a crash or a reboot and leaves a lock nothing in the UI can clear. It needs:
  - the **pid** and a **heartbeat** written into the lock;
  - a stale-lock determination based on both (a dead pid, or a heartbeat older
    than a stated threshold);
  - an explicit **break action that names what it is breaking** and what was
    running when it stopped — never an automatic silent reclaim.
- **Interruption must be safe by construction, not by promise.** Stopping
  mid-plan leaves K2's per-conversation cache and K4's per-claim cache
  consistent; prove it by walking it, not by asserting it.

## Task 6 ▸ the surface

A conductor panel in the curator tab, not a new tab.

- Preconditions first, as the control strip already does: LM Studio, the model
  selection, the governor's loop (closed or open, stated), the calibration
  state ("no measurements for this model yet").
- The plan, shown before approval, with the remainder stated.
- During a run: current step, stage-count progress, what is cooling and for how
  long, elapsed against budget. **Stage-count progress only — never a
  percentage** over a duration whose spread is a real error bar.
- After a run: per-step outcomes in the four existing states, the plan's estimate
  beside the actual, and the new measurements added to the ledger. **The estimate
  versus the actual is the most useful number on the page** — it is the only
  thing that says whether the planner can be trusted yet.

---

## Explicitly out of scope

- **Scheduling.** This is a *duration budget*, not a cadence. K6's re-run-cadence
  question stays parked, and "overnight" here means a long budget started by a
  human, not a timer. If the two blur, the round has failed.
- **An explicit model load/unload controller**, unless Task 1 produces evidence
  that TTL and auto-evict are insufficient. Report the evidence either way.
- **Conducting Chronicler's ingest chain.** `run_pipeline` has its own contract
  and no thermal problem; nothing here touches it.
- **Any change to what K2 or K4 compute.** Task 1's three flags add pacing,
  lifecycle and timing. They alter no claim, no verdict and no cache key.
- **Cross-machine anything.** 0036 stood the mesh down.
- **Estimating from anything other than measurement.** No model-size heuristics,
  no token-count arithmetic standing in for a timing.

---

## Stop conditions

- **A plan interleaves projects, reorders conversations within a project, or
  selects an arbitrary subset** → stop. That is 0032's ordering destroyed
  invisibly.
- **An estimate is produced with no measurement behind it** → stop.
- **A caller-supplied parameter reaches a subprocess** — anything not derived
  server-side from a ratified plan against a declared schema → stop.
- **A parameter outside its declared range is clamped rather than refused** →
  stop.
- **A plan executes without approval** → stop.
- **The conductor keeps its own record of completed work** and uses it in place of
  the caches → stop.
- **A stale lock is reclaimed automatically** → stop.
- **`classify_outcome` gains a fifth state**, or cooling is rendered as a stage
  outcome → stop.
- **A percentage progress bar appears** over an unmeasured duration → stop.
- **`nvidia-smi` becomes a hard requirement** rather than a probed capability →
  stop.

---

## UAT — acceptance checks (Tim walks these)

Mark each `[G]` / `[W]` / `[H]` per 0031.

- `[H]` **0037 is ratified and committed before any code lands.**
- `[G]` `--cool-down 0` and no `--model-ttl` reproduce today's behaviour exactly.
- `[G]` `--cool-down N` pauses **between** conversations, never inside one; a
  conversation's windows stay contiguous and the cache is unchanged.
- `[W]` **The TTL question is answered with evidence** — a long run with a short
  TTL, and a statement of whether memory stayed healthy without manual reloads.
- `[G]` Per-conversation timings are emitted and land in the ledger.
- `[G]` With no measurements for the selected model, the planner **offers no
  budgeted plan** and says why — and still offers an unbudgeted ordering.
- `[G]` The governor states closed or open loop on the surface; with `nvidia-smi`
  absent, the run still proceeds on fixed pauses **with the notice visible**.
- `[G]` A plan never interleaves projects and never reorders within one. Feed it
  a budget that fits 1.5 projects and confirm it offers a newest-first prefix,
  not a cherry-pick.
- `[G]` A budget too small for any useful work says so and plans nothing.
- `[G]` The plan states what it does not reach, by project and conversation count.
- `[G]` An unapproved plan cannot execute. A parameter outside its declared range
  is refused, not clamped. The execute route still accepts no argv.
- `[G]` **Kill the conductor mid-plan** (or pull the power): K2's and K4's caches
  are consistent, and re-planning re-derives the remaining work correctly from
  them rather than from the dead plan.
- `[G]` A lock left by a killed run is detected as stale via pid and heartbeat,
  and breaking it names what it is breaking. It is never reclaimed silently.
- `[G]` A failed step stops the plan and names the step; a skipped step does not.
- `[H]` **Walk a real hour-budget run on the work rig.** Did it stay within
  budget? Was the estimate close? Did the machine stay cool enough that you did
  not want to intervene?
- `[H]` **Walk a real overnight run.** The honest test: did you sleep through it,
  and was the morning state comprehensible without reading a log?
- `[H]` **Which lever actually helped** — cool-down, or reduced peak batch sizes?
  If the answer is "neither, it still throttled", that is the round's most
  important finding.
- `[H]` **Is the estimate-versus-actual close enough to trust a plan?** If not,
  say so; the planner is then a measurement tool, not a planner, and should be
  described as one.

Results log needs a uat stamp naming the commit; do not write a `gate=` field.

---

## Reporting

`docs/COWORK_REPORT_conductor.md`, walk-sheet `docs/UAT_conductor.md`, stamped
results after the walk.

Record: the 0037 ratification; **the TTL finding in full**, and whether the
load/unload controller was dropped; the parameter schema as declared, per stage,
with ranges; the measured throughput spread per model and how wide the error bar
really is; estimate-versus-actual for every plan run during the round; which
thermal lever measurably helped on the real hardware; and the stale-lock
behaviour as implemented, walked rather than asserted.
