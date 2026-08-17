<!-- uat: commit=174e57e dirty=true host=LucasGoonPC walked=2026-08-17 -->

# UAT results — the conductor, part 2 (`COWORK_BRIEF_conductor_governor.md`)

Sheet: `docs/UAT_conductor_governor.md`. Pair:
`docs/COWORK_BRIEF_conductor_governor.md` + `docs/COWORK_REPORT_conductor_governor.md`.

**Walked:** 2026-08-17 on `LucasGoonPC`, against `174e57e`.
`dirty=true` — Grand Walk results logs were uncommitted at walk time; no code
was.

**Gate:** `python verify.py` GREEN. `tester_governor`, `tester_planner`,
`tester_ledger`, `tester_conductor_panel`, `tester_conductor_run` and
`tester_candidates` all `[ OK ]`.

---

## This is a partial walk on a sheet that is already 59/62 done

The sheet carries **59 items already walked**, the bulk of them closed by the
real-rig session of 2026-08-13 (`035cbc1`) against two live plans on `10280L`.
This log records the **3 that remained open**: one walked here, two deferred.

The docs board will read `conductor_governor` as *Walked* on this log existing.
With 59 of 62 already closed that is very nearly true — but two items remain,
and they are named below rather than absorbed.

---

## Walked

- [x] **Confirm the select-dropdown contrast fix visually in a browser.**
  **Passed.** Tim: *"confirm the contrast works."*

  Worth recording why this stayed open as long as it did: the fix
  (`813d285` — `select option { background-color: Canvas; color: CanvasText }`)
  addressed a **pre-existing, site-wide** select CSS gap that the Conductor
  sub-tab's selects merely happened to surface first. The 2026-08-13 real-rig
  session covered the CLI only, so the fix was *believed correct from the CSS*
  and never re-observed. It has now been observed.

  That is the exact gap `[W]`/`[H]` marking exists to catch: a change proven by
  reading the diff is not a change proven by looking at the screen.

## Deferred to `10280L` — named, not guessed

- [ ] **Replay the 10 August series against the governor.**
  **Deferred — and the sheet's stated reason for it being blocked is now
  wrong.**

  The sheet says: *"Not possible without Task 3 (the governor itself), not
  built this round."* That was true when written. **It is no longer true.**
  `chronicler/pipeline/governor.py` exists (11,512 bytes, 2026-08-12), is
  registered in `verify.py` as `tester_governor`, and is green on every gate
  run. `conductor_run.run_plan` wires it live off the same `on_timing_line`
  stream the calibration ledger feeds from, and the 2026-08-13 real-rig session
  observed *"the governor's full baseline/pause/pause/cap_reached/proceeding
  sequence … under real load"*.

  So this item is **not blocked by unbuilt code.** But the calibration ledger,
  pulled from `10280L` on 2026-08-17, shows the real obstacle:

  ```
  entries: 116   model: gemma-4   stages: K2, K4
  earliest entry: 2026-08-12T16:04:09+00:00
  ```

  **The ledger contains no 10 August data and structurally cannot.**
  `chronicler/pipeline/ledger.py` landed at `2ec01ed` on **2026-08-12 15:39**;
  the first entry is ~85 minutes later. The instrument did not exist on the
  10th, so the series this item names was never recorded by it.

  **The item is therefore walkable only if the raw timing logs survive.**
  `record_from_timing`'s docstring states it accepts *"the same shape read back
  from a `--window-timing-log`/`--claim-timing-log` JSONL file"* — so if those
  logs were written on 10 August and still exist on `10280L`, the replay is a
  `record_from_timing` loop over them into a scratch ledger and a governor run
  against the result. **If they do not exist, this item cannot be walked by
  anyone, ever, and should be closed as unwalkable rather than left open.**

  Next action is a search on `10280L`, not a walk: look for
  `--window-timing-log` / `--claim-timing-log` output dated 2026-08-10.

  **This correction matters beyond one checkbox.** The stale note was read at
  face value during this Grand Walk and propagated into a fix list and a work
  list as *"the governor is not built"*, where it would have sat as a phantom
  blocker on a round that is substantially complete. A frozen document's claim
  believed instead of verified — the same failure class as
  `docs/UAT_ui_witness_results.md` finding 8, twice in one walk.

- [ ] **Reproduce deliberately and diagnose why `stop_after_step` didn't stop
  the run.** **Deferred.** Filed as an open finding by `035cbc1` and correctly
  not fixed there: the SIGINT handler fired and printed its graceful-stop
  message, but the run completed all steps anyway.

  Needs a deliberate repro against a real plan on the real rig. The build's own
  note is the standing instruction and is right: *"needs a deliberate repro on
  the real rig, not guessed at from one transcript."* A two-stage cancel that
  prints success and does not cancel is worth diagnosing rather than patching
  toward.

---

## Where this leaves the pair

**60 of 62 walked.** The two open items are both `10280L` work, both with a
named cause, and neither blocked by missing code.

The pair is closer to completion than the board or the sheet suggested at the
start of this walk, because the sheet's own blocking note had gone stale.

## What the ledger does confirm

Pulled from `10280L` at `174e57e`. 116 entries, one model (`gemma-4`), two
stages, three sessions.

| | n | median ms/token | p25 | p75 | max |
|---|---|---|---|---|---|
| K2 | 83 | 131.8 | 106.8 | 154.3 | **20742.5** |
| K4 | 33 | 344.3 | 278.8 | 406.4 | 700.3 |

**The 20742.5 ms/token outlier is real and present** (2026-08-12T17:12:07,
K2) — the exact figure `035cbc1`'s report cites as the one the rolling median
absorbed without a false pause. K2's median across the whole population is
131.8 with a p75 of 154.3, so an outlier **157× the median** moved neither.
That corroborates the already-walked `[H]` item with data rather than
testimony.

**K4 is ~2.6× slower per token than K2** (344 vs 132 median). Recorded because
it is the kind of fact a plan budget depends on and nothing else states it.

## Carried findings

1. **The sheet's replay item cites a blocker that no longer exists** (above).
   The note is frozen by convention and should not be edited; this log is the
   correction, and the item should be re-read against the tree rather than
   against the note.

2. **`stop_after_step` remains an open, undiagnosed finding** from `035cbc1`,
   restated here so it is not lost between two results logs. It is the only
   known case in the conductor where a control gesture reports success and does
   not take effect.

3. **The ledger's cool-down partition is empty after 116 measurements.**
   `cool_down_preceded` is `false` on **every** entry — 0 true, across three
   sessions, two stages and both rigs.

   The plumbing is correct and not at fault: `extract_claims` and `match_claims`
   set the flag True only for the *first* window or claim of a group following a
   cool-down sleep, which is exactly the post-gap JIT-reload unit the partition
   exists to isolate. All-false means **no cool-down sleep ever preceded a
   measured unit** — a legitimate state, not a bug.

   But `ledger.py` treats the partition as mandatory: *"Every read here takes
   `cool_down_preceded` as part of its filter, never averages across it
   silently."* So `summarize(cool_down_preceded=True)` returns `None` for every
   model and stage, and **half the calibration space has never been measured on
   any rig.**

   That matters because `build_plan` charges `cool_down_seconds` between steps —
   it budgets for runs that *will* take cool-downs, while the only measurements
   available describe units that did not follow one. Those are precisely the
   units the module says pay a cost the rest of the population did not.

   **Not diagnosed, and not necessarily wrong** — under-estimating a post-gap
   unit may be acceptable. But it is currently invisible: a summary built
   entirely from `cool_down_preceded=False` data does not announce that the
   other partition is empty. Worth confirming which partition `build_plan`
   actually queries before the next budgeted run.
