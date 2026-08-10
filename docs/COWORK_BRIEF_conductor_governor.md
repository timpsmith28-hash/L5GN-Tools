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
