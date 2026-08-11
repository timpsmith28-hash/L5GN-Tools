# Cowork brief — the conductor, part 2: the governor closes on throughput, not temperature

**Origin:** design thread, 2026-08-10, after the sensor survey on the work rig.
**Supersedes:** **Tasks 2–6 of `COWORK_BRIEF_conductor.md`**, which are unbuilt.
That brief stays frozen and untouched — its Task 1 is built, reported
(`COWORK_REPORT_conductor.md`, commit `0873d02`) and was executed against the
request as written. This is the successor, not a correction.
**Depends on:** DECISIONS **0037** (already accepted at `8687d25`), **0031**
(a check surface reports findings, never a verdict), **0032**.
**Deliverable:** a conductor that paces itself by measuring its own throughput,
because the machine it must run on exposes no temperature at all.

---

## The finding that forced this brief

The original Task 3 said: *probe for `nvidia-smi`; present → closed loop on
temperature, absent → open loop on fixed pauses with a visible notice.* On
`10280L` — the only machine the Curator runs on (0032) — **every temperature
route is closed.** Measured 2026-08-10:

| Route | Result |
|---|---|
| `MSAcpi_ThermalZoneTemperature` (`root\wmi`) | not supported — firmware does not populate the ACPI zone |
| `Get-Counter "\Thermal Zone Information(*)\Temperature"` | object not found — same gap, different path |
| LibreHardwareMonitor / HWiNFO / Open Hardware Monitor | blocked: they load WinRing0 (CVE-2020-14979), on Microsoft's vulnerable-driver blocklist. `Win32_DeviceGuard.SecurityServicesRunning` = `2, 3, 4, 7` — Memory Integrity is enforcing |
| Dell Command \| Monitor (`root\dcim\sysman`) | namespace present but holds only `__*`/`CIM_*` system classes. Provider not installed |
| `nvidia-smi` | no NVIDIA adapter. The GPU is an **Intel Arc 140V (16GB shared)** |

So the brief's "present → closed loop" branch is unreachable on the one machine
that matters, and its "absent" branch — fixed pauses — is the weaker design being
made permanent by accident.

**The replacement is better, not merely available.** Throttling *is* throughput
decay: the same work taking longer as the run proceeds. K2 and K4 already emit
timings. So the governor can close its loop on **throughput**, which:

- needs no driver, no admin, no vendor tool, and survives Memory Integrity;
- behaves identically on any hardware, so the design does not fork by GPU vendor;
- measures the thing actually worth protecting — *are we losing performance* —
  rather than a proxy. A machine that runs hot without throttling needs no pause,
  and a temperature-gated governor would pause it anyway.

**No new DECISIONS entry is required.** 0037 governs plans and parameters and is
unchanged. 0031 already governs the line this brief draws in Task 3 between an
observation and a diagnosis. Say so in the report rather than opening a ruling
that nothing needs.

---

## Working rules

- **The conductor is a scheduler over existing invocations.** It runs no
  inference, computes no claim, reimplements no stage.
- **Stdlib only** in the pipeline half. There is no sensor dependency left to
  probe for, which is one fewer capability check than the original design.
- Gate GREEN before commit. The ledger, the decay detector, the planner and the
  lock are **plain functions a tester calls with a temp directory** — as
  `curator_control.py` already does.
- **No new source of truth about progress.** K2 caches per conversation, K4 per
  claim; both do `--project` scoping with merge-on-write. The conductor
  re-derives remaining work from those caches every pass and **never keeps its
  own record of what it ran.**
- **The governor observes; it never diagnoses** (0031). See Task 3.
- UTF-8 explicit, UTC ISO-8601.

---

## Task 1 ▸ make the timing record fit for purpose

Four changes, all small, all prerequisites for the ledger. Three are findings
from the Task 1 review; the fourth is what the trial needs.

1. **A finer unit.** K2 emits one record per conversation, but calls the model
   once per **window**; K4 makes shortlist-plus-confirm calls per **claim**. Emit
   a record per window (K2) and per claim (K4) alongside the existing
   per-conversation one. This is the only way decay *within* a conversation is
   observable — and Run 2 of `RUNBOOK_conductor_thermal_trial.md`, the decisive
   experiment, is unreadable without it. The window loop already exists in
   `extract_for_conversation`; this is an emission, not a restructure.
2. **Record whether a cool-down preceded the measurement.** With
   `--model-ttl` shorter than `--cool-down` — the configuration the trial
   recommends — the model is evicted in the gap and JIT-reloads on the next call.
   That reload lands inside `wall_clock_seconds` for the first unit after every
   gap. The ledger derives throughput from this field and reports spread; without
   a flag it will attribute a bimodal distribution to the conversations rather
   than to the pacing policy. A bool, or the observed gap in seconds. **Do this
   before Task 2 reads the field**, not after.
3. **Assert K4's conversation-boundary assumption.** `_flush_conv` treats "the
   `conversation_id` changed" as a boundary, reasoning that runs are contiguous
   within a project. If that ever stops holding, K4 emits two records for one
   conversation and inserts an extra cool-down, and the ledger double-counts
   silently. A seen-set check turns it into a loud finding.
4. **Document what `--cool-down` does not do.** `group_idx < len(groups) - 1`
   means a single-group run — one conversation, or one batch — never sleeps. The
   conductor drives K2 per project, so the inter-project gap must come entirely
   from the conductor. That is the right division of labour and it is currently
   written down nowhere.

Defaults must continue to reproduce today's behaviour exactly.

## Task 2 ▸ the calibration ledger

Append-only, under `data/knowledge_curator/`, fed by Task 1's records.

- Throughput **per model**, in the finest unit available (seconds per window,
  seconds per claim). A figure averaged across models is a figure about nothing.
- **Normalise by size.** K2 already computes `approx_token_count`; seconds per
  token is comparable across conversations where seconds per conversation is not.
- **Partition on the cool-down flag.** Post-gap units are a different population;
  merging them inflates the spread and hides the reload cost that is worth
  knowing separately.
- Report the **spread**, not a mean alone. A wide error bar is a fact about the
  estimate, and Task 4 has to carry it.
- **No measurements for the selected model → no estimate.** Say so; offer an
  unbudgeted ordering instead. The first runs are measurement runs and the
  surface should label them as such — that is day one's normal state, not an
  error.

## Task 3 ▸ the governor — closed on throughput

- **Baseline from the run's own opening units**, not from the ledger. Absolute
  throughput varies with model, machine load and conversation size; what matters
  is decay *relative to how this run started*.
- **Detect on a rolling median over recent units**, never a single reading. One
  slow window is noise; four consecutive slow windows is a trend.
- **Act:** pause until throughput recovers to within a stated fraction of
  baseline, or until a cap is reached — then proceed anyway and record that the
  cap was hit. A governor that can wait forever is a hang.
- **The honesty requirement, and it is the point of this task.** Throughput
  decays for reasons other than heat: a longer window, a larger corpus, another
  process competing, a model swap. **The governor must never claim it detected
  thermal throttling.** It reports *"throughput fell to 61% of this run's
  baseline over the last four windows; paused 90s; recovered to 94%"* — the
  observation and the action, never the diagnosis. This is 0031 applied to a
  control loop, and it is the difference between an instrument and a guess.
- **Two dials, and the trial says which leads.** Cool-down lowers duty cycle;
  `--batch-target-tokens` / `--max-window-tokens` lower peak. Profiles set both.
  **If the trial's Run 5 shows peak reduction preserves throughput better than
  pausing, the profile leads with the token dials** — the reverse of the original
  brief's framing, and a legitimate outcome.
- Profiles are **named and machine-scoped**, in `config/local.json` beside
  `curator_models`. They describe this rig and nothing else.
- **Cooling is a conductor state, never a stage state.** `classify_outcome`'s
  four states are unchanged. Adding a fifth would undo the distinction the
  curator tab was built to preserve.
- **If the trial's Run 2 shows decay within a single conversation**, this task
  needs an intra-conversation pause and that is a bigger change to K2. Raise it
  as a finding before building, rather than shipping a governor whose dial cannot
  reach the problem.

## Task 4 ▸ the planner

Input: a **budget** (or none), a **priority policy**, a **thermal profile**.
Output: an ordered list of scoped invocations, an estimate with stated
provenance, and **what the budget does not reach**.

- **Unit of work is a project, or a newest-first prefix of one** — 0037 clause
  (3), non-negotiable, and the planner may not reorder within a project.
- **The priority policy is named and chosen, never inferred:** *coverage*
  (projects with no claims), *freshness* (transcripts changed since last
  extraction), *breadth* (smallest first). They give different plans; the
  operator must see which produced this one.
- **Budget must account for pausing.** Cool-downs and governor pauses are run
  time. A plan that budgets only inference is wrong by however long it waits.
- **A budget too small for a whole project offers a newest-first prefix, or
  nothing** — and says "nothing" rather than filling the time with work that
  corrupts the ordering.
- Approval is explicit and per-plan (0037 clause 2).

## Task 5 ▸ execution, and two things that must change

- Execute the approved plan step by step, governor pausing between steps,
  `classify_outcome` unchanged, stop on a real failure in the shape
  `run_pipeline` already established (a clean skip is not a failure).
- **`subprocess.run(capture_output=True)` has to go.** It buffers everything and
  returns only on exit, so a multi-hour run shows nothing until it finishes — no
  timings, no progress, no "currently paused". The governor *needs* the timing
  lines while the process is alive, because that is its input. Stream from a
  `Popen`, parse the timing records as they arrive. **This is what makes the
  governor possible at all**, not a UI nicety.
- **The lock must survive a multi-hour hold.** Today it is `O_CREAT|O_EXCL` and
  an unreadable lock counts as locked — correct for a five-minute stage, a trap
  for an overnight run killed by a crash or reboot. It needs a **pid** and a
  **heartbeat**, a stale determination based on both, and an explicit **break
  action that names what it is breaking**. Never an automatic silent reclaim.
- **Re-derive remaining work from the caches at every step.** A plan is a
  proposal about the future, not a ledger of the past.

## Task 6 ▸ the surface

A conductor panel in the curator tab, not a new tab.

- Preconditions: LM Studio, the model selection, the calibration state, and —
  replacing the old loop indicator — **the governor's live throughput reading
  against this run's baseline.**
- The plan, before approval, with the remainder stated.
- During a run: current step, stage-count progress, current throughput versus
  baseline, and what is paused and why, in the governor's observational language.
  **Stage-count only — never a percentage** over a duration whose spread is a
  real error bar.
- After a run: per-step outcomes in the four existing states, **estimate beside
  actual**, and the new measurements added to the ledger. Estimate-versus-actual
  is the most useful number on the page — it is the only thing that says whether
  the planner can be trusted yet.

---

## Explicitly out of scope

- **Any hardware temperature reading.** Established as unavailable; do not
  re-attempt, do not add a driver, do not ask for admin. The survey table above
  is the record.
- **Scheduling.** A duration budget, not a cadence. K6's re-run question stays
  parked.
- **An explicit model load/unload controller**, unless the trial shows TTL
  insufficient. Report the evidence either way.
- **Conducting Chronicler's ingest chain.**
- **Any change to what K2 or K4 compute.** Task 1 adds emission and a flag; no
  claim, verdict or cache key changes.
- **Cross-machine anything** (0036).

---

## Stop conditions

- **The governor asserts a cause** — "thermal throttling detected" — rather than
  reporting the observation → stop (0031).
- **A plan interleaves projects, reorders within one, or selects an arbitrary
  subset** → stop (0037 clause 3).
- **An estimate is produced with no measurement behind it** → stop.
- **A caller-supplied parameter reaches a subprocess** → stop; **a parameter
  outside its declared range is clamped rather than refused** → stop.
- **A plan executes without approval** → stop.
- **The conductor keeps its own record of completed work** and uses it instead of
  the caches → stop.
- **A stale lock is reclaimed automatically** → stop.
- **The governor can pause without bound** → stop; a cap and a recorded
  cap-reached are required.
- **`classify_outcome` gains a fifth state** → stop.
- **A percentage progress bar appears** over an unmeasured duration → stop.

---

## UAT — acceptance checks (Tim walks these)

Mark each `[G]` / `[W]` / `[H]` per 0031.

- `[G]` Task 1's defaults reproduce today's behaviour; per-window and per-claim
  records appear alongside the per-conversation one.
- `[G]` A unit measured after a cool-down is flagged as such, and the ledger
  partitions on it rather than averaging it in.
- `[G]` K4's boundary assertion fires loudly on a synthetic non-contiguous
  claim stream instead of silently double-counting.
- `[G]` With no measurements for the selected model, the planner offers no
  budgeted plan, says why, and still offers an unbudgeted ordering.
- `[G]` The governor pauses on a synthetic decaying-throughput stream, resumes on
  recovery, and hits its cap on a stream that never recovers — recording that it
  did.
- `[G]` **The governor's output names no cause.** Read three of its messages: if
  any says "thermal", "overheating" or "throttling" as a claim about the
  hardware, that is a finding.
- `[G]` A plan never interleaves projects or reorders within one; a budget
  fitting 1.5 projects yields a newest-first prefix, not a cherry-pick.
- `[G]` The plan's budget includes pause time, not just inference time.
- `[G]` Timing records reach the governor **while the process is running** —
  streamed, not buffered to exit.
- `[G]` Kill the conductor mid-plan: both caches stay consistent and re-planning
  re-derives the remainder from them.
- `[G]` A lock left by a killed run is detected stale via pid and heartbeat;
  breaking it names what it breaks; it is never reclaimed silently.
- `[H]` **Walk a real hour-budget run.** Within budget? Estimate close? Did you
  want to intervene?
- `[H]` **Walk a real overnight run.** Did you sleep through it, and was the
  morning state comprehensible without reading a log?
- `[H]` **Did the governor actually help**, or did it pause for decay that had
  another cause? The false-positive rate is the honest weak point of closing on
  effect rather than cause.
- `[H]` **Is estimate-versus-actual close enough to trust a plan?** If not, the
  planner is a measurement tool and should be described as one.

Results log needs a uat stamp naming the commit; do not write a `gate=` field.

---

## Reporting

`docs/COWORK_REPORT_conductor_governor.md`, walk-sheet
`docs/UAT_conductor_governor.md`, stamped results after the walk.

Record: the sensor survey as the standing record of why there is no temperature
reading; the trial's four answers and what they changed; the decay detector's
parameters (window, threshold, cap) and how they were chosen; the measured
throughput spread per model and the size of the post-gap reload penalty; the
streaming executor and the lock's stale-detection, walked rather than asserted;
and the governor's false-positive rate over the round's real runs — because
closing the loop on an effect rather than a cause is this design's one honest
weakness and it should be quantified rather than argued about.

---

# Addendum — 2026-08-10 · Tasks 4 and 5 superseded, from the CID chain precedent

**Source:** design thread, after reading `L5GN_Armory_v4`'s forge and chain
registry. **Status of the rest:** Task 1 is built (`7709652`); Tasks 2, 3 and 6
are unchanged.

The Task 4 and Task 5 text above **stands as the record of what was asked** and
is not edited. The versions below replace them for build purposes, in the shape
`DECISIONS.md` uses — append and supersede, never correct in place
(`docs/README.md` §2).

## Why — the problem was already solved next door

0037 clause (1) requires a *"declared parameter schema per stage — which
parameters that stage accepts, and their permitted ranges. A parameter outside
its declared range is a refusal, not a clamp."* The original Task 4 described
that in prose. `L5GN_Armory_v4/core/services/chain_registry.py` **has it built**,
and better than the prose:

- **Closed vocabularies as module-level frozensets** (`_VALID_SKIP`,
  `_VALID_COMPOSE`, `_VALID_CHUNK`) — immutable globals, the same posture the
  toolkit's scanners already use.
- **Accumulate-then-raise validation.** `_validate_stage` returns a *list* of
  errors rather than raising on the first, so an operator sees every problem at
  once instead of fixing them one per attempt. This is strictly better than what
  the original Task 4 asked for.
- **One error type.** `ChainValidationError`, with `chain_authoring.parse_chain_text`
  funnelling malformed JSON *and* invalid content into it, so the caller handles
  exactly one failure.
- **Validate loudly at load, never fail silently at run** — the module's own
  stated rule, and already the toolkit's.
- **A dataclass-derived field table.** `_STAGE_FIELDS = MappingProxyType({f.name:
  f for f in dataclasses.fields(Stage)})` drives (de)serialisation generically,
  so adding a field later cannot silently drop it on round-trip. That is 0030 —
  shape is generated, not hand-maintained — applied to a config schema.
- **A schema version on the artefact**, `citadel.chain.v1`, present from the
  start rather than added after the first breaking change.

**Re-derive these patterns. Import nothing.** CID carries `customtkinter`,
`llama_cpp` and `numpy`; none of that comes near this repo (0034).

## Task 4′ ▸ the planner, and the plan as a validated artefact

Everything in the original Task 4 **carries forward unchanged** — unit of work is
a project or a newest-first prefix (0037 clause 3), the priority policy is named
and chosen rather than inferred, the budget must account for pause time, a budget
too small offers a prefix or says nothing, and approval is explicit and per-plan.

Added to it: **the plan is a validated, serialisable artefact, not an in-memory
list.**

- A `PlanSpec` / `PlanRegistry` pair in `chain_registry.py`'s mould, carrying
  schema `l5gn.plan.v1`.
- **Closed vocabularies as frozensets** for policy names, profile names and stage
  keys — the stage keys sourced from `curator_control.STAGE_TABLE`, which stays
  the single declaration point.
- **Accumulate-then-raise**, one `PlanValidationError`, every violation reported
  together.
- **The field table derived from the dataclass**, so a later field addition
  round-trips without a serialiser edit.
- **Validated at load *and* immediately before execution.** A plan approved an
  hour ago against a model that has since been unloaded is not still valid.

**The line CID crosses that this must not.** `plugs/chain_builder.py` and
`chain_authoring.save_chain_text()` let the operator **author arbitrary chain
JSON in a text editor and persist it.** That is the right affordance for CID and
it is precisely what 0037 clause (1) forbids here: the caller supplies a plan
identifier, never a parameter. **Borrow `parse` and `validate`; do not borrow
save-whatever-was-typed.** Plans are *generated* server-side from policy inputs
and *approved* — never authored. If that line blurs, the execution allowlist has
a back door and the ruling is worthless.

Cycle detection (`_detect_cycles`) is **not needed** while plans are linear. If
plans ever gain dependencies between steps, that function is the shape to reach
for — recorded so it is not reinvented.

## Task 5′ ▸ execution, streaming, the lock, and cancellation

Everything in the original Task 5 **carries forward unchanged** — streaming from
a `Popen` rather than `subprocess.run` (the governor's input is the live timing
stream), the pid-and-heartbeat lock with an explicit break action that names what
it breaks, stop-on-failure in `run_pipeline`'s shape, and re-deriving remaining
work from the caches rather than from the plan.

Added to it: **cancellation, taken from `ForgeEngine` rather than invented.**

- Distinguish cancelling a **queued** step — skipped when the plan reaches it —
  from cancelling an **in-flight** step, where the subprocess is signalled and
  stopped. `ForgeEngine` makes exactly this distinction (`_consume_cancel` on
  dequeue versus after the call returns) and an overnight run needs it: "stop
  after the current project" and "stop now" are different operator intents.
- **Atomic test-and-clear**, so a cancellation is one-shot and cannot fire twice.
- **A cancelled run must leave both caches consistent** — K2's per-conversation
  and K4's per-claim, the latter checkpointing every `--checkpoint-every` claims.
  Walk it; do not assert it.
- The state shape for Task 6 is `ForgeEngine._snapshot()`'s: **depth, active
  step, paused, pending.** Task 6 is otherwise unchanged.

## Explicitly not borrowed, and why

- **The worker pool and per-endpoint semaphores.** `forge.py`'s docstring gives
  the same motive this brief has — *"insulate local inference infrastructure from
  network or context bottleneck crashes"* — but solves it on the **concurrency**
  axis, where the conductor solves it on the **temporal** one. The conductor is
  deliberately single-stream (0037's lock, and the entire thermal point). A pool
  would fight the goal.
- **The EventBus, `SystemEvents` and the payload classes.** The app is
  request/response over a file lock, not an event-driven engine. Growing that
  architecture for this would be a large, unasked-for change.
- **Any CID import whatsoever.**

## Additional stop conditions

- **A plan is authored rather than generated**, or any route accepts plan JSON →
  stop. That is 0037 clause (1) via the back door.
- **A CID module is imported** → stop.
- **A worker pool, thread pool, or concurrent stage execution appears** → stop.
- **Validation raises on the first error** rather than reporting all of them →
  stop; that is the behaviour this addendum exists to import.

## Additional UAT

- `[G]` An invalid plan reports **every** violation at once, not the first.
- `[G]` An unknown policy name, profile name or stage key is refused at load,
  and the refusal names the closed vocabulary it failed against.
- `[G]` Adding a field to the plan dataclass round-trips without a serialiser
  edit.
- `[G]` A plan is re-validated immediately before execution, and a plan whose
  model is no longer loaded is refused at that point.
- `[G]` Cancelling a **queued** step skips it; cancelling an **in-flight** step
  stops it, and both caches are consistent afterwards.
- `[G]` No route accepts plan JSON, and there is no save-what-was-typed path.

## Growth path — recorded, not built

The Forge is what the conductor becomes **if** one runner ever drives both
Chronicler and the Curator across machines — the Command Deck's eventual "run
anything" surface. That is premature: 0036 stood the mesh down, 0023's gate is
unbuilt, and this is one machine.

It is recorded because it is the reason to build the plan as a validated,
serialisable artefact **now** rather than as an in-memory list. That artefact is
the seam an engine would later plug into, and building it any other way would
mean rewriting Task 4 to get there.

## Addendum reporting

In addition to the reporting above, record: which `chain_registry.py` patterns
were re-derived and which were deliberately left; the plan schema as implemented,
with its closed vocabularies; and the cancellation walk in both cases (queued and
in-flight) with the cache state after each.

---

# Addendum 2 — 2026-08-11 · Task 1 reopened: the timing record cannot measure throughput

**Source:** the thermal trial's first per-window data (`run3_windows.jsonl`) and
the LM Studio server logs for 10–11 August. **Status:** Task 1 is built and
reported; this reopens it for one missing field. Tasks 2 and 3 are unchanged in
intent, but **Task 3's unit changes** and two of its design choices are now
confirmed by evidence rather than argued.

## What the trial proved about the instrument

**`token_count` is input tokens only, so the record cannot express throughput.**
Wall-clock per window includes generating output the record has no count for. In
the real data one window ran **7,972 tokens in 14.6s** and another **2,596 tokens
in 111.7s** — a 24× swing in apparent speed, driven by how much the model *wrote*,
not by how loaded the machine was. Per-conversation trends came out +53%, −30%
and +81% on three conversations. That is noise wearing a metric's clothes.

**Consequence: Run 2's question is still unanswered.** Not for want of data, but
because the instrument cannot separate a slow window from a productive one. A
governor built on this field would pause hardest exactly when the model was being
most useful.

## What the trial proved about the run — and why Task 3 was right twice

The LM Studio logs carry `prompt eval time` and `eval time` separately; the
latter is generation speed, independent of output length. 239 samples across
11.5 hours on 10 August:

```
generation ms/token, by decile:
58.4  60.6  57.4  57.3  58.7 │ 79.0  98.0  79.3  80.2  80.2
```

A **step change and a plateau**, not a thermal ramp. Heat accumulates and
recovers; it does not jump 36% and hold flat for five deciles. The 11 August log
settles it: after an overnight cold start, the median is **79.2 ms/token** —
it begins at the degraded level and stays. Thermal degradation does not survive
a night with the machine off.

So the 36% loss is a **persistent configuration state**, most plausibly
`Offload KV Cache to GPU: Disabled` routing the KV cache to host RAM. Prompt eval
moved the same way (3.35 → 4.52 ms/token). It also explains the cool-down result:
90-second pauses across nine conversations bought **−2.3%**, because there was
little thermal throttling to recover.

**Two Task 3 decisions are now evidence-backed. Do not relitigate them:**

1. **The pause cap is load-bearing, not defensive.** A governor closing on
   throughput would have seen a 36% drop that *never recovered*. Without the cap
   and its recorded cap-reached, "pause until throughput returns to baseline"
   would have hung overnight.
2. **The baseline is per-run, never from the ledger.** A ledger baseline taken on
   the morning of the 10th would have marked every later run degraded, forever,
   for a reason that had nothing to do with any of those runs.

And the honesty requirement has now been vindicated twice: a governor permitted
to name a cause would have reported "thermal throttling" on both the 26.8%
figure and this 36% one, and been wrong both times.

## Task 1′ ▸ capture the model's own usage accounting

`call_lmstudio` (K2) and `call_lmstudio_generic` (K4) both parse the full
response into `response_body` and then return only
`response_body["choices"][0]["message"]["content"]`. **The `usage` block is
already in hand and is being thrown away.**

- Capture **`usage.completion_tokens` and `usage.prompt_tokens`** on every call,
  and derive **generation ms/token** into the timing record. That is the number
  the governor needs and the only one that separates a loaded machine from a
  verbose one.
- **Do not change what `caller` returns.** Four call sites bind it
  (`extract_claims` lines 385 and 448; `match_claims` lines 151 and 168) and
  every tester passes a stub caller returning a string. Add an optional
  **`on_usage` callback**, bound through the same `functools.partial` that
  already carries `ttl`, `timeout` and `json_mode`. The function keeps returning
  a string; usage leaves sideways. This is the module's existing pattern —
  `progress`, `on_timing`, `on_window_timing` all work this way.
- **A missing `usage` block is recorded as absent, never estimated.** Not every
  runtime returns it. Capability check, degrade, state it — the same discipline
  as the embedding-endpoint and FTS5 checks.
- **Keep `approx_token_count` for windowing.** It is a *pre-call* decision and
  cannot use post-call data; the module already says it is "never trusted for
  anything that needs to be exact." The real `prompt_tokens` is for the ledger's
  normalisation, not for the windowing choice.

## What this changes downstream

- **Task 2's ledger** derives throughput from **generation ms/token**, not
  wall-clock per window, partitioned on `cool_down_preceded` as already required.
- **Task 3's governor** closes its loop on that same unit. Wall-clock per window
  is not a throughput measure and must not be used as one.

## Additional stop conditions

- **Throughput is derived from wall-clock alone**, without an output-token count
  → stop. That is the defect this addendum exists to fix.
- **A missing `usage` block is filled with an estimate** → stop.
- **`caller`'s return type changes**, breaking the four call sites and the
  testers' stubs → stop; use the callback.

## Additional UAT

- `[G]` `usage` is captured on every call in both K2 and K4; a response carrying
  no `usage` records it as absent and the run continues.
- `[G]` Generation ms/token appears in the window and claim records, and is
  independent of output length — a long-output window and a short-output window
  of similar input size report similar figures.
- `[G]` The four `caller(...)` sites are unchanged and every existing tester stub
  still works.
- `[W]` **Replay the 10 August series against the governor.** Fed that step
  change, it must pause, fail to recover, hit its cap, record the cap as reached,
  and proceed — not wait indefinitely.
- `[H]` With the new unit, re-walk Run 2: does throughput decay *within* one
  conversation? This is the question the original instrument could not answer.

## Addendum 2 reporting

Record the `usage` capture as implemented and how a missing block is handled; the
generation-ms/token figures for a re-run of the trial with the fixed instrument;
and whether Run 2's intra-conversation question finally resolves. The step-change
finding above should be carried into `COWORK_REPORT_conductor_governor.md` as the
standing explanation for why the 10 August runs are not a usable baseline.
