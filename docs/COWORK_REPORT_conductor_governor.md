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

## The trial's four answers, per the design thread

- **Q1 (Run 2 — intra-conversation decay):** **not measured.** The design
  thread's own words: "It is unreadable until Task 1's per-window timing
  exists — a single conversation emits one timing record today, so there is
  no intra-conversation signal." The correct record of this round is "not
  yet measurable," not "no decay" — nothing licenses the latter. **Task 3
  stays open pending it.** Task 1's per-window timing (built this round, see
  below) is exactly what makes Run 2 readable the next time it's attempted.
- **Q2 (Run 4 — TTL unattended):** **confirmed.** TTL frees and reloads the
  model unattended during the cool-down gap; the explicit load/unload
  controller stays dropped, per the original brief's finding. This makes
  Task 1 item 2 (flagging a unit measured after a cool-down)
  **mandatory, not precautionary** — real evictions mean real reload time
  landing inside the first measurement after every gap, which is exactly
  what `cool_down_preceded` now exists to keep separate from a plain
  measurement.
- **Q3 (Run 5 — which lever):** **not run.** A Task 3 input only; does not
  block Task 1.
- **Scope confirmation:** Task 1's four items are unconditional and branch
  on nothing in the trial — building all four regardless of Q1/Q3's status
  was the right call, confirmed after the fact rather than before it.

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

**Commit:** `7709652`.
**Gate status: GREEN.** `python verify.py` → all auditors + testers pass,
including both extended testers (verified again by the pre-commit hook at
commit time).

## What was deliberately not done this round

No calibration ledger (Task 2), no governor (Task 3), no planner (Task 4),
no streaming executor/lock rework (Task 5), no surface (Task 6) — per the
scoping decision made before this round started. Task 1's record shapes
(`cool_down_preceded`, `token_count` on window records, `claim_count` /
`message_count`) were chosen with Task 2 in mind but Task 2 itself was not
built.

**Task 3 specifically stays open pending Q1** (per the design thread, above)
— not a scoping choice this round, a genuine blocker: whether the governor
needs an intra-conversation pause is unknown until Run 2 is re-attempted
with this round's per-window timing in place.

## UAT

Walk-sheet: `docs/UAT_conductor_governor.md` (Task 1 subset only). The
`[H]`/`[W]` items — real hour/overnight runs, whether the governor actually
helps, estimate-vs-actual trust — all depend on Tasks 3–6 and cannot be
walked yet.

---

# Addendum 2 — Task 1 reopened: the instrument couldn't measure throughput

**Source:** `docs/COWORK_BRIEF_conductor_governor.md`'s own Addendum 2, from
the trial's first per-window data and the LM Studio server logs for
10–11 August.

## The standing explanation for the 10 August runs

The trial's early data is not a usable baseline, for two independent
reasons, both now on record here per the addendum's instruction:

**The instrument was wrong.** `token_count` on a window record is *input*
tokens only; wall-clock includes generating output the record had no count
for. Real figures from the trial: one window ran 7,972 input tokens in
14.6s, another 2,596 in 111.7s — a 24× apparent swing driven by how much the
model *wrote*, not by machine load. Per-conversation trends of +53%, −30%
and +81% on three conversations were noise wearing a metric's clothes. A
governor built on wall-clock-per-window alone would have paused hardest
exactly when the model was being most productive — this is why the addendum
reopened Task 1 for one field rather than treating it as done.

**The 10 August run itself was not a thermal signal.** LM Studio's own logs
carry `eval time` (pure generation speed, independent of output length):
239 samples across 11.5 hours show a **step change and a plateau** — ~58
ms/token for the first half of the deciles, ~79–98 ms/token for the second —
not a thermal ramp (heat accumulates and recovers gradually; it does not
jump 36% and hold flat). The 11 August log, after an overnight cold start,
*begins* at ~79.2 ms/token and stays there — degradation that survives the
machine being off overnight is a **persistent configuration state**, most
plausibly `Offload KV Cache to GPU: Disabled`, not heat. This explains why
90-second cool-downs across nine conversations bought only −2.3%: there was
little actual thermal throttling to recover from that day.

**Two Task 3 design decisions are vindicated by this, not merely justified
by argument, and are not to be relitigated:** the pause cap is load-bearing
(a throughput-closed governor would have seen a 36% drop that never
recovered, and hung without one); the baseline must be per-run, never from
the ledger (a ledger baseline from the morning of the 10th would have marked
every later run "degraded" forever, for a config-state reason unrelated to
any of those runs). And the honesty requirement — the governor names no
cause — is vindicated twice over: a governor permitted to claim "thermal
throttling" would have been wrong about both the 26.8%-looking figure and
this 36% one.

## What was built

`chronicler/pipeline/extract_claims.py` (K2) and
`chronicler/pipeline/match_claims.py` (K4) already parsed the full LM Studio
response and threw away its `usage` block. Fixed with the pattern the addendum
specified — sideways through a callback, never through `caller`'s return
value:

- **`call_lmstudio` / `call_lmstudio_generic` gain `on_usage`**, bound
  through the same `functools.partial` that already carries `ttl`. Fires
  exactly once per HTTP call with `{"prompt_tokens": int, "completion_tokens":
  int}`, or `None` if the response carried no `usage` block at all — absent,
  never estimated. The four `caller(...)` call sites
  (`extract_for_conversation`'s window loop, `extract_batch`, `confirm_chunk`,
  `confirm_supersede`) are **byte-for-byte unchanged**; every pre-existing
  test using a stub caller still passes without modification.
- **A shared accumulator** (`reset_usage_box` / `make_usage_accumulator` /
  `usage_from_box`, in `extract_claims.py`, imported by `match_claims.py`)
  because a single record's unit of work can cost more than one HTTP call —
  K4's shortlist can trigger up to `SHORTLIST_SIZE` confirm calls plus a
  possible supersede check plus a possible cross-project retry, all for ONE
  claim. Reset before the unit's work starts, every `on_usage` call adds
  into it, read back after. `usage_available` is true only if **every** call
  since the last reset returned usage — a partial aggregate would silently
  understate the true total, which this module refuses to fabricate (tested:
  one call returning `None` among several makes the whole unit's usage
  unavailable, not partially available).
- **`generation_ms_per_token(elapsed, usage)`**: `None` unless usage was
  available AND at least one token was actually generated (never a
  division-by-zero, never a silent 0ms for an unmeasured call). Window
  records (K2) and claim records (K4) now carry `usage_available`,
  `prompt_tokens`, `completion_tokens`, `generation_ms_per_token` alongside
  the existing fields. Verified directly: a long-output call (800 tokens /
  16.0s) and a short-output call (40 tokens / 0.8s) at the same real
  generation speed report the identical 20.0ms/token — the exact property
  wall-clock-alone could not provide.
- **`approx_token_count` is untouched** — still the pre-call windowing
  decision the module already documents as "never trusted for anything that
  needs to be exact"; the real `prompt_tokens`/`completion_tokens` are for
  the ledger's normalisation (Task 2, not built), not for windowing.

**Commit:** `b81357e`.
**Gate status: GREEN.** `python verify.py` → all auditors + testers pass,
including new coverage for usage present/absent, multi-call accumulation
within one claim, the independent-of-output-length property, and that
omitting `usage_box` entirely still produces well-formed (all-absent)
fields rather than a `KeyError` (verified again by the pre-commit hook at
commit time).

## What this does not resolve

Re-walking Run 2 with the fixed instrument (`[H]`, per the addendum) is
Tim's to do on the real rig — this round could not run LM Studio. Q1
(intra-conversation decay) remains open; Task 3 remains blocked on it, now
with the correct instrument in hand rather than the wall-clock one that
could not have answered it regardless.

---

# Addendum 3 — Run 2 walked, Q1 answered, Q3 read against the real cool-down

**Source:** Tim's real-rig walk of the runbook on `10280L`, two batches. The
first batch (Run 1, Run 2 as originally attempted, Run 3, Run 4, Run 5) hit
two execution deviations caught by cross-checking `cool_down_preceded`
counts against the actual PowerShell used: Run 2 was run identically to
Run 1 (not isolated to one conversation — unreadable for Q1), and Run 3 was
run with `--cool-down 0` instead of `90` (unreadable for Q3). Both were
re-run correctly in the second batch: `run2iso_windows.jsonl` (one
conversation, `local_18c1d671-7cad-4b09-af75-6ec3142f714d`, isolated via a
one-row map) and `run3iso_windows.jsonl` (the full "Pricing Model" project,
true `--cool-down 90`, fresh cache path). The isolation map command itself
hit a `UnicodeDecodeError` on first attempt — PowerShell's `>`/`>>` write
UTF-16LE, K2 reads `utf-8-sig` — fixed with `Set-Content`/`Add-Content
-Encoding utf8`, now folded into the runbook itself (this commit) so it
doesn't trip the next run.

## Q1 — does throughput decay within one conversation? No.

The isolated conversation was measured twice, independently: alone in
`run2iso` (13 windows, nothing else running), and again inside the full
`run3iso` project scan (same conversation, same content, different run).
Both measurements agree:

| Measurement | window_index vs ms/token (r) | input token_count vs ms/token (r) |
|---|---|---|
| `run2iso` (isolated) | 0.234 | 0.869 |
| `run3iso` (in-project) | 0.013 | 0.813 |

Position in the conversation carries almost no correlation with speed
(0.234, then 0.013 on the independent re-measurement — consistent with
noise, not a real effect). Input size carries a strong, stable correlation
in both (0.869, 0.813) — the "gets slower later" pattern seen in the first
pass's raw wall-clock reading was the same prompt-size confound Addendum 2
already diagnosed in general, now confirmed specifically for the
intra-conversation case Run 2 exists to test.

**Answer: no measurable intra-conversation decay.** The current
between-conversation pause granularity is sufficient — Task 3 does not need
an intra-conversation pause. **Task 3 is unblocked on Q1.**

## Q3 — does the cool-down alone help? Not measurably, on this data.

Clean comparison (`completion_tokens >= 20`, filtering out the low-output
windows Addendum 2 already flagged as unreliable), same 11 conversations,
same order:

| Run | cool-down | n | mean ms/token | median ms/token |
|---|---|---|---|---|
| `run1` | 0 | 79 | 157.1 | 126.8 |
| `run2` | 0 | 79 | 170.7 | 139.1 |
| `run3iso` | 90 (true) | 70 | 154.4 | 120.0 |

Per-conversation `run3iso`/`run1` ratios cluster tightly between 0.90 and
1.06 across all 11 conversations — no conversation shows the "later ones
recover more" pattern that would signal pausing counteracting a real
degradation. Per the runbook's own stated criterion, a flat ratio means
pausing bought nothing (beyond its own wall-clock cost). This lines up with
Addendum 2's reading of the 10 August data: if the observed slowdown there
was mostly the KV-cache-offload config state rather than genuine thermal
throttling, a cool-down has nothing to recover from, which is exactly what
this cleanly-executed comparison now shows directly rather than inferring
from a suspect wall-clock figure.

This contrasts with Run 5 (peak-token reduction), which showed a clear
improvement in the first pass (median ~88 vs baseline ~124–139) — the
signal so far points at the token dials, not the pause, as the lever that
actually helps.

## Reload penalty (Run 4/Q2 confirmatory) — resolved via `run3iso`'s own data

`run3iso`'s 10 `cool_down_preceded: true` windows (mean 185.8, median 115.9)
looked worse than the 60 non-preceded windows (mean 149.2, median 120.0) on
first read — mean inflated, median roughly flat, which is the signature of
an outlier rather than a real effect. It is: one preceded window has
`completion_tokens=79` against a 6,419-token input, reporting 835 ms/token —
the exact low-completion/high-input pattern Addendum 2 already named as
contaminated by prompt-eval time. Excluding it, the remaining 9 preceded
windows read mean 113.6 / median 102.3, both *at or below* the non-preceded
figures.

**No measurable reload penalty in this data.** This narrows what Task 2's
ledger needs to model — `cool_down_preceded` is worth keeping as a flag for
transparency, but nothing here says the ledger must add a reload-cost term
on top of ordinary variance.

## Operational notes, not findings

- **The cache trap fired once, exactly as documented.** A first `run3iso`
  attempt reused `run3`'s (the deviant `--cool-down 0`) cache file and
  produced 0 re-extracted / 11 from cache — self-corrected by switching to a
  fresh `run3iso_cache.json`, per the runbook's own instruction to always
  use a per-run cache path.
- **One `HTTPError: HTTP Error 400: Bad Request`** interrupted a fresh-cache
  `run3iso` attempt four windows into the first conversation. A straight
  retry of the identical command completed cleanly, redoing that
  conversation from scratch (K2's cache is whole-conversation granularity,
  so a mid-conversation failure isn't partially cached). Root cause not
  diagnosed — no repeat on the retry, nothing in the LM Studio log
  pinpointing a payload issue. Worth watching for recurrence; not
  investigated further this round.

## What this resolves

**Task 3 is unblocked on Q1** (no intra-conversation pause needed) and has a
real, if unhelpful, Q3 reading (cool-down alone shows no measurable benefit
on this data; the token dials are the lever with a demonstrated effect).
Both are now fit to design Task 3 against. Run 4 (Q2, TTL-unattended) was
already answered in the design thread and was not re-run — nothing above
depends on it.

**Commit:** `22763df`.
**Gate status:** N/A — no code touched this round; `verify.py` GREEN via the
pre-commit hook regardless (doc-only commit).

---

# Addendum 4 — resilience, ahead of Task 3: bounded retry and K2 checkpointing

**Source:** Tim's own read of the HTTP 400 that interrupted `run3iso` —
attributed to local resource pressure (other apps competing with LM Studio
for RAM), not a payload defect. Two small, independent fixes, requested
before Task 3 itself, since a governor sitting on top of a pipeline that
loses a whole run's progress to one transient error isn't solving the more
pressing problem.

## 1. Bounded retry on transport failures

`extract_claims.py` gains `post_json_with_retry` — wraps the `urlopen` call
both K2's `call_lmstudio` and K4's `call_lmstudio_generic` already made,
retrying up to `--retries` times (default 2, short backoff) on **any**
transport failure (`HTTPError` including a 400, `URLError`, `OSError`)
before re-raising. The module's existing "loud failure, no partial report"
contract is deferred, not weakened — a persistent failure still surfaces
after a short, bounded delay; only a transient one clears silently.
`call_lmstudio_generic` reuses the same function (imported via `k2.`)
rather than a second implementation. `retries=0` restores exact
fail-immediately behaviour. Tested: a failure that clears within budget
returns normally with the expected attempt/sleep count; a failure that
never clears still raises once retries are exhausted; `retries=0` makes
exactly one attempt and never sleeps.

## 2. K2 checkpoints on every group boundary

K4 already checkpoints (`--checkpoint-every`, cache + partial `--out` every
N claims) — K2 didn't; `save_cache` fired once, in `main()`, only after
`run_extraction` returned. A crash mid-run lost every conversation finished
before it, not just the one in flight, which is exactly what happened on
the work rig: four conversations K2 had already completed were re-done on
the retry, for no reason other than nothing had been written to disk yet.

`run_extraction` gains an `on_checkpoint` callback, fired after **every**
group (one model call's worth of newly-finished conversations — whichever
of the three paths produced them) with a partial report in the exact shape
the final report already uses (report construction was factored into a
shared `_build_report` helper so there's only one shape, not two). `main()`
wires it to write `cache` and a partial `--out` at each checkpoint, merging
under `--project` scope exactly as the final write already does. Purely
observational — omitting `on_checkpoint` changes nothing about the result,
same discipline as every other optional callback in this module.

Tested: three single-conversation groups produce exactly three checkpoints,
each a strict superset of conversations covered by the last; a simulated
crash inside `on_checkpoint` (raised after the 2nd of 3 groups) still
leaves the first two conversations' entries in the (in-memory, mutated in
place) cache dict — the actual resumability property, not just the
callback firing.

## What this does not change

Neither fix touches Task 3's design. They sit underneath the governor: a
transient HTTP failure or a mid-run crash is now cheap to recover from
regardless of whether the governor is paused, running, or not yet built.

**Commit:** `7fc17fa`.
**Gate status: GREEN.** `python verify.py` → all auditors + testers pass,
including new coverage for retry exhaustion/success/opt-out and
checkpoint accumulation/crash-survival (verified again by the pre-commit
hook at commit time).

---

# Task 3 — the governor, built

**Precondition status at build time:** Q1 (no intra-conversation decay) and
Q3 (cool-down alone shows no measurable benefit; token dials do) both
resolved by Addendum 3. Neither blocks this task any further.

## What was built

`chronicler/pipeline/governor.py` — new module, pipeline tier, stdlib +
`l5gntools` only (no import of `chronicler.review`; dependency runs the
other way, same direction DECISIONS 0034 clause 3 establishes for
`l5gntools`, applied here even though the auditor scanning for it only
covers that specific pair). Plain functions and dataclasses a tester calls
directly with a temp directory — same posture as `curator_control.py`, for
the same reason (INTENT: guarantees are structural).

**The decision loop** (`GovernorState`, `new_governor`, `observe`):

- **Baseline from the run's own opening units**, never the ledger (Task 2
  isn't built; the field names line up for when it is). The first
  `baseline_units` (default 4) measured units, median. Established once
  per state; never recomputed mid-run — Addendum 2's own finding for why
  (a ledger or stale baseline would misattribute a persistent config-state
  change to every later run).
- **Rolling-median decay detection.** A `rolling_window` (default 4) sliding
  window of the most recent units, compared against baseline as a ratio.
  One slow unit never triggers anything; four consecutive slow ones do —
  the brief's own words.
- **Pause, resume, or cap.** Below `pause_threshold` (default 75% of
  baseline) → pause `pause_seconds` (default 60s). Still degraded after
  waking → pause again, up to `pause_cap` (default 3) consecutive times,
  then **proceed anyway and record `cap_reached` exactly once** — never a
  second time while still capped, and the cap resets cleanly on a genuine
  later recovery. A governor that can wait forever is a hang; Addendum 2's
  10 August data (a 36% drop that never recovered in 11.5 hours) is the
  standing proof this isn't a defensive nicety.
- **`None` (usage unavailable for a unit) is skipped entirely** — not
  counted toward the baseline, not counted toward the rolling window, never
  treated as zero or estimated. Same discipline Addendum 2 already applies
  to the timing records this module consumes.
- **The honesty requirement, mechanically enforced.** Every message reports
  an observation and an action only — "throughput fell to 61% of this run's
  baseline over the last four units; pausing 60s", the brief's own example
  phrasing, never a named cause. `_FORBIDDEN_WORDS` (`thermal`, `overheat`,
  `throttl`) exists so this is a test assertion, not a review-by-eye
  promise: every message produced across every test scenario is scanned.

**Two dials, the default profile now evidence-led rather than assumed.**
Addendum 3's real data showed cool-down alone bought nothing measurable
(per-conversation ratios 0.90–1.06) while the token-dial reduction (Run 5)
showed a real effect. `DEFAULT_PROFILE` leads with `max_window_tokens` /
`batch_target_tokens`, keeps `cool_down_seconds` modest and secondary — the
reverse of the original brief's framing, now built that way on purpose
rather than by default.

**Profiles are named and machine-scoped.** `get_profile`/`set_profile`
read/write `config/local.json` under this hostname's `governor_profiles`
key, layering a partially-specified stored profile over `DEFAULT_PROFILE`
so every key is always present — mirrors `curator_control.get_curator_models`
/ `set_curator_model`'s read-modify-write discipline exactly (writing one
host or profile never disturbs another).

**Cooling is a conductor state, never a stage state.** Nothing in this
module touches `classify_outcome`; a caller tracks `GovernorState` alongside
a stage outcome, never folds pause/resume into it — the fifth-state trap the
brief names explicitly is structurally unreachable from here, since this
module has no notion of `classify_outcome`'s vocabulary at all.

## What was deliberately not done this round

**No wiring into a live run.** This module has no caller yet — Task 5 (the
streaming executor) is what will feed it a live per-window/per-claim
timing stream and act on `pause_seconds`/`resume`. Building the decision
logic ahead of its caller, hermetically testable on its own, follows the
same order Task 1 already established (the timing record existed before
anything consumed it). **No calibration ledger** (Task 2) — `DEFAULT_PROFILE`'s
numbers are reasoned from the trial's own evidence (Addendum 3) and the
brief's stated defaults, not learned from accumulated runs; nothing here
prevents Task 2 tuning them later. **No `nvidia-smi` or any temperature
probe** — out of scope per the brief, unchanged.

## UAT

- `[G]` The governor pauses on a synthetic decaying-throughput stream,
  resumes on recovery, and hits its cap on a stream that never recovers —
  recording that it did, exactly once.
- `[G]` The governor's output names no cause — every message across every
  test scenario scanned for `thermal`/`overheat`/`throttl`; none found.
- `[H]` Wiring this into a real run (Task 5) and walking an hour/overnight
  budget with it live — not possible until Task 5 exists.

**Commit:** `798f82c`.
**Gate status: GREEN.** `python verify.py` → all auditors + testers pass,
including the new `tests/tester_governor.py` (baseline/rolling-median/
pause/resume/cap, the honesty-requirement scan, and profile round-tripping)
(verified again by the pre-commit hook at commit time).
