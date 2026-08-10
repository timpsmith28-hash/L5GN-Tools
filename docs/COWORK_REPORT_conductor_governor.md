# Cowork report — the conductor, part 2 (Task 1 only, this round)

**Brief:** `docs/COWORK_BRIEF_conductor_governor.md`
**Supersedes:** Tasks 2–6 of `docs/COWORK_BRIEF_conductor.md` (Task 1 of that
brief stayed frozen and built — `docs/COWORK_REPORT_conductor.md`, commit
`0873d02`/`dc8e6eb`). This report covers this brief's own Task 1 only, by
explicit scoping choice at the start of this round.
**Precondition:** DECISIONS **0037**, already accepted at `8687d25`. This
brief needs no new DECISIONS entry (its own text says so — 0037 governs
plans/parameters and is unchanged; 0031 already governs the
observation/diagnosis line Task 3 draws, when Task 3 is built).
**Built:** 2026-08-10, in a Cowork sandbox with no LM Studio instance and no
real work rig reachable.

## Open question this round did not resolve

Task 3 (the throughput governor, not built this round) branches materially
on the thermal trial's Q1: does throughput decay **within** a single
conversation (`RUNBOOK_conductor_thermal_trial.md` Run 2)? If yes, the
governor needs an intra-conversation pause — a bigger change to K2 than
Task 3 as scoped. Tim flagged this as unresolved and is checking the design
thread before it's answered here; **Task 1's per-window timing (below) is
exactly what makes Run 2 readable once he does**, so nothing in this round
was blocked by leaving it open.

Q2 (does `--model-ttl` free/reload the model unattended?) is answered: yes,
per Tim. Q3 (which lever — cool-down or token dials — preserves throughput
better) was not run. Neither answer changes what Task 1 needed to build.

## What was built

Four changes, all additive, in `chronicler/pipeline/extract_claims.py` (K2)
and `chronicler/pipeline/match_claims.py` (K4) — the brief's own four items:

**1. A finer timing unit.** K2 now emits one record per **window** (inside
`extract_for_conversation`, via an `on_window_timing` callback threaded
through `run_extraction`) alongside the existing per-conversation one — the
window loop already existed; this is an emission, not a restructure, exactly
as the brief specified. Batched small-conversation groups (`extract_batch`)
make one call for the whole batch and have no window concept, so
`on_window_timing` correctly never fires for them (asserted by a new test).
K4 now emits one record per **claim** (`on_claim_timing`) — K4's
shortlist-plus-confirm call per claim already was the finest unit available;
there is no window concept to add underneath it. Both are purely
observational (new tests confirm omitting either callback changes nothing
about results), and both use the same `make_*_timing_reporter()` shape as
the existing per-conversation reporters (`TIMING_WINDOW` / `TIMING_CLAIM`
lines to stderr, optional JSONL via `--window-timing-log` /
`--claim-timing-log`).

**2. `cool_down_preceded` on every timing record.** With `--model-ttl`
shorter than `--cool-down` (the trial's recommended configuration), the
model is evicted during the gap and JIT-reloads on the next call — that
reload lands inside the first unit's `wall_clock_seconds` after every gap.
Every timing record (conversation, window, claim) now carries a
`cool_down_preceded` bool. Precision matters here: the reload happens once
per gap, so only the group's/conversation's **first** window or claim is
flagged True — later windows/claims in the same conversation are False, even
though the conversation-level record itself is True for the whole group
(the aggregate measurement genuinely does include the reload cost within
it). This distinction is exercised directly by new tests (a multi-window
conversation immediately after a cool-down: window 0 flagged, window 1+
not). Built **before** any ledger reads the field, per the brief's explicit
ordering.

**3. K4's conversation-boundary assumption is now asserted, not assumed.**
`_flush_conv` treats "the `conversation_id` changed" as a reliable boundary,
reasoning that conversation runs are contiguous within a project. A new
`seen_ids` set makes that reasoning fail loudly (`ValueError`, naming the
conversation) if a `conversation_id` ever reappears after its run already
closed out — the alternative was silently double-counting that
conversation's timing and inserting an extra cool-down. A new test feeds a
deliberately non-contiguous stream and confirms the raise; the normal
(contiguous) case, exercised by every other test in the file, confirms it
never fires there.

**4. What `--cool-down` does not do, documented.** `group_idx < len(groups)
- 1` (K2) means a single-group run — one conversation, or one small-batch —
never sleeps at all; a single-conversation claims stream (K4) never sleeps
either, since there's only ever one boundary and it's the last one. Both are
now stated explicitly in `run_extraction`'s and `match_claims`'s own
docstrings: the conductor drives K2/K4 once per project, so the
**inter-project** pause has to come entirely from the conductor's own
pacing — K2/K4's `--cool-down` only ever reaches inside a single
invocation's own conversation list. This was written down nowhere before.

Defaults reproduce today's behaviour exactly — every pre-existing test in
both testers still passes unmodified except two fixture dicts that needed
the new `cool_down_preceded` key added (`make_timing_reporter` is not
backward-compatible with a record missing that key by design, same as every
other required field in these record shapes).

**Commit:** see below.
**Gate status: GREEN.** `python verify.py` → all auditors + testers pass,
including both extended testers.

## What was deliberately not done this round

No calibration ledger (Task 2), no governor (Task 3), no planner (Task 4),
no streaming executor/lock rework (Task 5), no surface (Task 6) — per the
scoping decision made before this round started. Task 1's record shapes
(`cool_down_preceded`, `token_count` on window records, `claim_count` /
`message_count`) were chosen with Task 2 in mind but Task 2 itself was not
built.

## UAT

Walk-sheet: `docs/UAT_conductor_governor.md` (Task 1 subset only). The
`[H]`/`[W]` items — real hour/overnight runs, whether the governor actually
helps, estimate-vs-actual trust — all depend on Tasks 3–6 and cannot be
walked yet.
