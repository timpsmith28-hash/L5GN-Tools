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

---

# Task 5′ — streaming, the lock, and cancellation

**Precondition status at build time:** Task 3 (the governor) built and
gate-GREEN, with no caller yet — this task is what gives it one.

## What was built

All in `chronicler/review/curator_control.py` (the control strip Task 3 of
`COWORK_BRIEF_curator_tab.md` already built `run_stage`/`execute_with_lock`
in) — extended, not replaced; every pre-existing test kept its intent, only
the injection seam (`runner=` → `popen_factory=`) changed, since that seam
is exactly the thing the addendum says has to go.

**1. Streaming, not buffered to exit.** `run_stage` no longer calls
`subprocess.run(capture_output=True)` — it spawns via `popen_factory`
(defaults to `_default_popen`, a thin `Popen` wrapper with stderr merged
into stdout via `STDOUT` so a single stream carries both in real arrival
order, avoiding the two-pipe deadlock risk a naive dual-read would carry)
and reads it **line by line as it arrives**. `on_timing_line(kind,
ms_per_token, line)` fires for every `TIMING`/`TIMING_WINDOW`/`TIMING_CLAIM`
line K2/K4 already write to stderr — `kind` is `"conversation"`/`"window"`/
`"claim"`, `ms_per_token` is the parsed `generation_ms_per_token` figure
(`None` when the line marks it unavailable, Addendum 2's own discipline
carried through here rather than re-litigated). Purely observational, same
as every other optional callback in this codebase: what a caller does with
it — feed it into `governor.observe()`, or ignore it — is not this
function's concern. **This is what makes the governor possible at all**,
per the brief's own words: Task 3's `GovernorState`/`observe` had no real
caller until this round.

**2. The lock: a pid, a heartbeat, staleness reported not acted on.** The
original `O_CREAT|O_EXCL` lock (Task 3 of `COWORK_BRIEF_curator_tab.md`)
had neither a pid nor a heartbeat — an unreadable lock counted as locked,
correct for a five-minute stage, a trap for an overnight run killed by a
crash or reboot, with nothing to ever tell that state apart from one still
genuinely running.

- `acquire_lock` now stamps `pid` and an initial `heartbeat_at`.
- `heartbeat(lock_path)` updates `heartbeat_at` in place (read-modify-write,
  never a blind rewrite) — `execute_with_lock` binds this automatically to
  the held lock unless a caller overrides it, so a streamed run heartbeats
  once per line, far more often than any staleness threshold could mistake
  for a crash.
- `lock_status` now reports `stale`/`stale_reasons` — a heartbeat older than
  `STALE_HEARTBEAT_SECONDS` (120s default), or a pid `_pid_alive` can
  positively say is gone (cross-platform: `os.kill(pid, 0)` on POSIX,
  `OpenProcess` via `ctypes` on Windows; `None` — genuinely unknown — is
  never silently treated as either alive or dead). This is a report, never
  a verdict acted on (0031's own discipline, applied to the lock).
- **`acquire_lock` never auto-reclaims a lock it would itself call stale.**
  The only sanctioned clear is `break_lock(reason, lock_path)` — `reason`
  is mandatory (an empty one is refused outright), and the return value
  names what was broken. Explicit, always, per the brief's own stop
  condition ("a stale lock is reclaimed automatically → stop").

**3. Cancellation — queued vs in-flight, one token, re-derived from
`ForgeEngine._consume_cancel`.** `CancelToken` is a one-shot, thread-safe
flag with atomic test-and-clear (`consume()`) and a non-consuming peek
(`is_set()`). The same token tells queued from in-flight apart by nothing
more than *when* it's read:

- `execute_with_lock` calls `consume()` immediately after acquiring the
  lock, before `run_stage` is ever called — a token already set at that
  point means the step was still queued when cancellation was requested,
  so it's skipped entirely (`state="blocked"`, `cancelled=True`), never
  started and then stopped.
- `run_stage` checks `is_set()` after every streamed line — a request
  arriving *while* the step is running terminates the subprocess
  (`Popen.terminate()`, cross-platform) and marks the outcome
  `cancelled=True`, `state="failed"`.
- **No fifth `classify_outcome` state.** `StageOutcome` gained a `cancelled:
  bool` field layered *alongside* the existing four states, never a state
  of its own — the brief's explicit stop condition, satisfied structurally:
  the field exists precisely so cancellation is distinguishable without
  inventing a new value for `state`.
- **Both caches already stay consistent on a cancel** — no new work
  required here. Addendum 4's K2 checkpointing (fires every group) and
  K4's pre-existing `--checkpoint-every` mean an in-flight-terminated
  subprocess loses at most the group/claims-batch that was running when
  `terminate()` landed, exactly the same guarantee a crash already gets.
  This UAT item is a **walk**, not a build.

## What was deliberately not done this round

**Not borrowed from `ForgeEngine`:** the worker pool and per-endpoint
semaphores (the conductor is deliberately single-stream — 0037's lock, and
the whole thermal point of this brief; a pool would fight the goal), and
the EventBus/`SystemEvents` (this app is request/response over a file
lock, not event-driven; growing that architecture would be a large,
unasked-for change). Recorded so neither is reinvented later by accident.

**No multi-step loop yet.** `run_stage`/`execute_with_lock` still run
**one** stage per call, exactly as before — "governor pausing between
steps" (the brief's phrase) needs a *sequence* of steps to pause between,
which is Task 4's job (the planner defines what a step is and its order).
This round built the primitive Task 4's execution loop will call.

## UAT

- `[G]` Timing records reach a live consumer while the process is running —
  streamed, not buffered to exit.
- `[G]` The lock carries a pid and a heartbeat; staleness is reported, never
  acted on automatically; `break_lock` is the only way one is ever cleared,
  and it always names why.
- `[G]` A queued cancellation skips a step entirely; an in-flight
  cancellation terminates the subprocess; neither invents a fifth
  `classify_outcome` state.
- `[H]` Kill the conductor mid-plan on the real rig and confirm both caches
  stay consistent, re-planning re-derives the remainder — not possible
  until Task 4 exists to define "mid-plan."

**Commit:** `ada2088`.
**Gate status: GREEN.** `python verify.py` → all auditors + testers pass,
including `tester_curator_control.py`'s new coverage for the streaming
seam, lock heartbeat/staleness/`break_lock`, and queued-vs-in-flight
cancellation (verified again by the pre-commit hook at commit time).

---

# Task 4′ — the planner

**Precondition status at build time:** Task 5′ built — the streaming
executor and the lock exist, so a future execution loop has something real
to drive a plan against. Built last, per the agreed order, since a plan is
pointless to validate against execution machinery that couldn't yet run it.

## What was built

`chronicler/review/planner.py` — new module, app tier (needs
`curator_control.STAGE_TABLE`, the one declaration point for stage keys;
the dependency only runs app → pipeline, never back, same direction
`governor.py`'s own docstring already states for itself). Re-derives
`chain_registry.py`'s pattern, imports nothing from it.

**`PlanSpec`/`PlanStep` — a validated, serialisable artefact, not an
in-memory list.** Schema `l5gn.plan.v1` from day one. A dataclass-derived
field table (`dataclasses.fields`) drives `to_dict`/`from_dict`, so a later
field addition round-trips without touching the serialiser — proven
directly by a round-trip test (`PlanSpec.from_dict(spec.to_dict()) ==
spec`). `PlanValidationError`, accumulate-then-raise: a plan with an
unknown policy *and* an unknown stage key reports both in one exception,
not one-fix-at-a-time.

**Closed vocabularies.** Policy names (`coverage`, `freshness`, `breadth` —
the brief's own three) as a module-level frozenset. Stage keys default to
`frozenset(curator_control.STAGE_TABLE)`, resolved lazily so this module
carries no hard import-time dependency on the app being fully wired — the
single declaration point stays single; nothing here redeclares it.

**Unit of work is a project, structurally, not just by convention.**
`PlanStep` has no field that could name a partial project — one step is
always one project's stage invocation in full. `PlanSpec.validate` also
checks directly that no project appears twice across `steps` (interleaving
would require exactly that) and that no project appears in both `steps`
and `remainder` at once. (A finer "newest-first prefix of a project" — the
other unit 0037 clause 3 permits — would need per-conversation steps; not
built this round, recorded as a known simplification.)

**The budget is a strict prefix, never a cherry-pick.** `build_plan` ranks
candidates by the chosen policy, then fills the budget by walking that
order and stopping at the FIRST candidate that doesn't fit — it never
skips ahead to grab a smaller later one that would individually fit. This
is the brief's own instruction ("filling the time with work that corrupts
the ordering") turned into code, and tested directly: a candidate costing
10s that would easily fit inside a budget's slack is still cut to
`remainder` because an earlier, larger candidate consumed the space first.
Every step after the first pays the profile's `cool_down_seconds` before
its own estimate — the budget accounts for pause time, not just inference,
per the brief's explicit correction.

**No estimate without a measurement behind it.** A budgeted `build_plan`
call refuses (`PlanValidationError`) if any candidate carries
`estimated_seconds=None` — Task 2's calibration ledger (not built) is the
natural future source of real per-project estimates; this module will not
guess one to make a budget "work." The same candidates are perfectly fine
for an *unbudgeted* plan (policy order, no time claim at all) — mirrors
Task 2's own stated rule ("no measurements → no estimate, offer an
unbudgeted ordering instead") applied to the same situation here.

**Approval is explicit, per-plan, and never mutates in place.** `approve()`
returns a NEW `PlanSpec` with `approved=True`/`approved_at` stamped —
frozen dataclasses don't mutate, so a plan handed to one caller can't be
silently un-approved by another's edit. `validate_for_execution` is the
re-check immediately before a plan runs: structural validity again (not
just trusted from build time), refusal if never approved (`ValueError`,
deliberately a different exception type than `PlanValidationError` — "this
plan is malformed" and "this plan is fine but nobody signed off on it" are
different problems), and refusal if `profile_name` isn't in a
caller-supplied `known_profiles` set — a plan approved against a profile
since renamed or removed is refused rather than run against something that
may have changed meaning.

**No save-what-was-typed path.** There is no function anywhere in this
module that accepts arbitrary caller-supplied plan JSON and persists it as
approved or ready-to-run — `PlanRegistry.save` always calls `spec.validate()`
first, and the only way to build a `PlanSpec` at all is `build_plan` (from
policy inputs) or `PlanSpec.from_dict` (round-tripping something this
module itself already wrote). The line the addendum draws against CID's
`chain_builder.py`/`chain_authoring.save_chain_text()` is not crossed.

**`PlanRegistry`** — file-backed, atomic `.tmp` + `os.replace` persistence
under `data/knowledge_curator/plans/`, `ChainRegistry`'s own shape: a
malformed sibling file is recorded in `.errors` and skipped, never crashes
the registry or blocks loading the valid ones.

## What was deliberately not done this round

**No adapter from real curator data to `ProjectCandidate`.** This module
ranks and budgets whatever `ProjectCandidate` objects a caller supplies —
it does not itself read `knowledge_index.json`/`claims.json` to produce
them. Building that adapter without Task 2's ledger behind it would mean
either fabricating `estimated_seconds` (the exact thing this module
refuses to do) or shipping an adapter that can only ever produce unbudgeted
plans — a real but partial piece, deliberately left for when Task 2 exists
to feed it honestly.

**No execution loop.** Nothing in this module calls
`curator_control.execute_with_lock`. A future loop — walk `spec.steps` in
order, `validate_for_execution` before each, execute, re-derive remaining
work from the caches, honour the governor's pause actions between steps —
is what Task 5′'s primitives and this module's artefact both exist to
support, not built here. `run.py`'s eventual conductor command is the
natural home for it.

## UAT

- `[G]` A plan never interleaves projects or reorders within one — checked
  structurally (`PlanStep` cannot name a partial project; `validate`
  rejects a project appearing twice in `steps`).
- `[G]` A budget fitting some prefix of the ranked candidates yields
  exactly that prefix, never a cherry-picked subset — a smaller candidate
  that would individually fit past the cutoff is still excluded.
- `[G]` The plan's budget includes pause time (`cool_down_seconds` charged
  between steps), not just inference.
- `[G]` An estimate is never produced with no measurement behind it — a
  budgeted plan refuses outright if any candidate lacks `estimated_seconds`.
- `[G]` A plan is re-validated immediately before execution, and an
  unapproved plan, a structurally invalid one, or one whose profile is no
  longer known are each refused with a distinguishable reason.
- `[G]` No route accepts caller-supplied plan JSON as something to save
  and run — the only ways to produce a `PlanSpec` are `build_plan` (from
  policy inputs) and round-tripping this module's own output.
- `[H]` A real multi-project plan, walked on the real rig once an execution
  loop exists to drive it — not possible until that loop (and Task 2's
  ledger, for a budgeted plan with real numbers) exist.

**Commit:** `ea5fb67`.
**Gate status: GREEN.** `python verify.py` → all auditors + testers pass,
including the new `tests/tester_planner.py` (policy ranking, the
strict-prefix budget fill, closed-vocabulary validation, round-trip,
approval, and `validate_for_execution`) (verified again by the pre-commit
hook at commit time).

---

# Task 2 — the calibration ledger

## What was built

`chronicler/pipeline/ledger.py` — new module, pipeline tier, stdlib +
`l5gntools` only. Append-only JSONL, one observation per line, same shape
this repo already uses for `--timing-log`/`--window-timing-log`/
`--claim-timing-log`.

- **`record_from_timing(timing, *, stage)`** turns a K2/K4 timing record
  into a ledger entry, or `None` if `generation_ms_per_token` is absent —
  absence in, absence out, never estimated. `stage` is supplied by the
  caller because the timing record itself doesn't know it (only
  `curator_control.STAGE_TABLE` does).
- **`append_entry`** — real file, genuine append (never a rewrite), a
  timestamp stamped on write, and a loud `ValueError` if a required field
  is missing rather than a half-formed line.
- **`make_ledger_feeder(path, stage=...)`** returns an `on_timing_line`-
  shaped callback — `curator_control.run_stage`'s own contract — so wiring
  the ledger into a real streamed run is `execute_with_lock(...,
  on_timing_line=ledger.make_ledger_feeder(path, stage="K2"))` and nothing
  else. Fires for a window/claim line carrying a real measurement, silently
  does nothing for a non-timing line or one marked unavailable.
- **`summarize(entries, *, model_id, stage, cool_down_preceded)`** — the
  brief's three requirements, all structural rather than optional: throughput
  **per model** (never averaged across models — tested directly: two
  models' entries in the same ledger produce independent, non-blended
  summaries); **partitioned on `cool_down_preceded`**, always, as a
  required filter argument rather than an optional one a caller could
  forget; **reports the spread** (`median`, `p25`, `p75`, `min`, `max`),
  never a mean alone. Returns `None` — plainly, not a zero or a guess —
  when nothing matches the exact filter.
- **`known_models(entries)`** — every distinct `model_id` a ledger has ever
  recorded, so a caller can build a full calibration report without
  already knowing what's in it.

## What was deliberately not done this round

**Not wired into a real run yet.** `make_ledger_feeder` exists and is
tested against a realistic `TIMING_CLAIM` line, but nothing currently
calls `execute_with_lock(..., on_timing_line=ledger.make_ledger_feeder(...))`
— that wiring, plus turning a `CalibrationSummary` into
`ProjectCandidate.estimated_seconds` for the planner, is the adapter
already flagged as not built when Task 4′ shipped. This ledger is what
that adapter now has something real to read from.

## UAT

- `[G]` Throughput is reported per model, partitioned on
  `cool_down_preceded`, as the spread — never a mean alone, never blended
  across models or across the cool-down partition.
- `[G]` No measurements for a given `(model_id, stage, cool_down_preceded)`
  → `summarize` returns `None` plainly, never a fabricated figure.
- `[G]` `record_from_timing` never estimates a missing
  `generation_ms_per_token` — absence in, absence out.
- `[H]` A real run's ledger, walked over a full evening's calibration data
  on the real rig — not possible until the feeder is actually wired into a
  real `execute_with_lock` call.

**Commit:** `2ec01ed`.
**Gate status: GREEN.** `python verify.py` → all auditors + testers pass,
including the new `tests/tester_ledger.py` (partitioning discipline,
spread reporting, absence-never-estimated, the streaming feeder against a
realistic timing line) (verified again by the pre-commit hook at commit
time).

---

# Task 6 — the conductor panel, backend half

**Scope for this round, agreed with Tim explicitly:** the panel's
read/plan-build/approve data layer and API surface — not the frontend
HTML/JS rendering it into the curator tab. Tim separately flagged a
possible future reorganisation of the review app's structure; this round's
additions follow today's existing conventions exactly (thin FastAPI routes
in `app.py` delegating to a plain-function data module, the same shape
`curator_data.py`/`curator_control.py` already established) so nothing
here is at odds with a later restructure.

## What was built

**`chronicler/review/conductor_panel.py`** — new module, pure data-shaping
over `curator_control`, `ledger`, and `planner`; no new I/O of its own and
no execution logic.

- `preconditions(curator, endpoint=...)` — `curator_control.preflight`
  unchanged, reused, plus `calibration_available` (whether the ledger has
  anything in it at all).
- `calibration_state(...)` — `ledger.summarize` fanned out over every known
  model and both model-calling stages (`curator_control.
  MODEL_SELECTABLE_STAGES`, not a redeclared copy), both cool-down
  partitions each. A model/stage/partition with nothing recorded reports
  `None` — exactly what `summarize` itself would say, never upgraded to a
  guess by this layer.
- `plan_preview(spec)` — flattens a `PlanSpec` into the panel's rendering
  shape: steps, remainder, budget, approval state.
- `run_state(lock_path=...)` — the REAL lock status, `governor: None`, and
  an explicit `note` naming exactly why: no execution loop exists yet.
  **Never a fabricated "in progress" view** — tested directly: an idle
  lock path reads `locked: False`, a genuinely held one reads the real
  stage and pid, and `governor` is `None` in both cases because nothing
  produces a live reading yet.

**Four new routes in `app.py`**, alongside the existing
`/api/curator/control/*` family, same conventions (`_need_curator_estate()`
guard first, lazy imports inside the handler):

- `GET /api/curator/conductor/preconditions`
- `GET /api/curator/conductor/calibration`
- `GET /api/curator/conductor/run`
- `POST /api/curator/conductor/plan/preview` — body is a policy, a profile
  name, an optional budget, and a list of candidates (`project_id`,
  `claim_count`, `changed_conversations`, `message_count`,
  `estimated_seconds`) — **never a plan itself**. Builds via
  `planner.build_plan`, validates, saves to the real `PlanRegistry`, and
  returns the preview. A `PlanValidationError` (e.g. a budget with no
  estimates behind it) surfaces as `400`, not a silent fallback.
- `POST /api/curator/conductor/plan/approve` — body is a bare `plan_id`.
  Loads the already-saved plan from the registry, approves it
  (`planner.approve`, a new object), re-saves, returns the preview. A
  `plan_id` never on record is `404`.

**The line stays uncrossed here too.** No route accepts a `PlanSpec`
(or anything shaped like one) as input — `ConductorPlanPreview`'s
candidates carry only the facts a `ProjectCandidate` needs, never a step,
an argv, or a stage list. The only way a plan gets INTO the registry is
this server building one itself from those inputs.

Verified end-to-end with a live `TestClient` round-trip (not just the
hermetic tester): preconditions → calibration → run → plan/preview →
plan/approve, all five returning exactly the shapes described above
against a real (temp-directory) `Curator` and a real `PlanRegistry` write.

## What was deliberately not done this round

**No frontend.** The curator tab's HTML/JS does not yet render any of
this — these four routes exist and are tested, but nothing in
`static/index.html` calls them. This is the explicitly agreed scope for
this round, not an oversight, and follows `curator_data.py`'s own
precedent (Task 1 of `COWORK_BRIEF_curator_tab.md` shipped its data layer
before any UI existed for it).

**No live governor/progress data.** `run_state`'s `governor` field is
`None` by construction — there is still no execution loop wiring a
`GovernorState` to anything. Once one exists (the natural follow-on to
Task 4′/5′), `run_state` is the seam it would report through.

## UAT

- `[G]` `calibration_state` never fabricates a figure `ledger.summarize`
  wouldn't itself produce — a stage/partition with nothing recorded reads
  `None`, never borrowed from a sibling stage or partition.
- `[G]` `plan_preview` mirrors a `PlanSpec` exactly, including its
  approval state.
- `[G]` `run_state` never shows a fabricated "in progress" view — reports
  the real lock, `governor: None`, and an explicit note naming why.
- `[G]` No conductor route accepts a plan (or a step, or an argv) as
  input — only policy-level candidate facts; a `PlanValidationError`
  surfaces as `400`, an unknown `plan_id` on approve as `404`.
- `[H]` The panel walked as an actual UI in the curator tab — not possible
  until the frontend half is built, out of scope this round by agreement.

**Commit:** `3e31675`.
**Gate status: GREEN.** `python verify.py` → all auditors + testers pass,
including the new `tests/tester_conductor_panel.py`, plus a live
`TestClient` round-trip through all five routes (not part of the gate,
run manually against this commit) (verified again by the pre-commit hook
at commit time).

---

# The real-data adapter

**Source:** the gap Task 4′'s own report flagged — `planner.py` ranks and
budgets `ProjectCandidate`s a caller supplies; nothing turned real Curator
data into them.

## What was built

`chronicler/review/candidates.py` — `candidates_from_curator(...)`, one
function, one project per ratified `map_rows` entry:

- **`claim_count`** — summed from `claims.json`'s conversations via the
  ratified session→project join, the same join K4 itself uses.
- **`message_count`** (breadth proxy) — conversation count, from K1's
  `knowledge_index.json` when available, falling back to counting
  `map_rows` directly when K1 hasn't run yet (never zero just because a
  stage is behind). Stated plainly as a proxy, not a true message count —
  a real one needs re-parsing every transcript, duplicating work K0/K2
  already do.
- **`changed_conversations`** and **`estimated_seconds`** — both require
  REAL conversation objects and the K2 cache together; both default to `0`
  / `None` (never guessed) if either is omitted. Changed-detection reuses
  K2's own cache-identity check (`source_identity`) directly rather than
  reimplementing it — a conversation whose sources match the cache is a
  clean hit, costs nothing on a re-run, and is correctly excluded from
  both the changed count and the size estimate.
- **`estimated_seconds`** is calibration median ms/token (Task 2's ledger,
  clean/not-preceded partition) × the ACTUAL token count of the CHANGED
  conversations only, via `approx_token_count`/`full_transcript_text` —
  never the whole project's size, since unchanged conversations are cache
  hits. Stays `None` whenever the ledger has no measurement for the
  selected model/stage, exactly `summarize`'s own rule, carried through
  rather than papered over with a default.

Tested directly against `build_plan` at the end — the adapter's output is
proven to build a real, valid plan, not just checked in isolation.

## UAT

- `[G]` `claim_count` sums correctly via the real ratified-map join.
- `[G]` Breadth falls back to counting `map_rows` when K1 hasn't run,
  never reads zero.
- `[G]` `changed_conversations` reuses K2's own cache-identity check — a
  clean cache hit is correctly excluded.
- `[G]` `estimated_seconds` is `None` unless both real conversations AND a
  ledger measurement for the selected model are present; scales by the
  changed conversations' real token count only, never the whole project's.
- `[G]` The adapter's output builds a real, valid `PlanSpec` via
  `planner.build_plan`.
- `[H]` A real run against the real `10280L` ledger and knowledge base —
  not possible until the ledger has real entries in it (the feeder isn't
  wired into a live run yet either).

**Commit:** `99c010f`.
**Gate status: GREEN.** `python verify.py` → all auditors + testers pass,
including the new `tests/tester_candidates.py` (join correctness, the K1
fallback, cache-identity reuse, and the estimate-scaling behaviour,
finishing with a real `build_plan` call over the adapter's own output)
(verified again by the pre-commit hook at commit time).

# The execution loop

**Source:** the last gap named in the brief's own "What was deliberately
not done this round" note under Task 5′ — `run_stage`/`execute_with_lock`
ran exactly one stage per call; nothing yet turned an approved `PlanSpec`
into a real, multi-step run, and "governor pausing between steps... needs
a sequence of steps to pause between" was explicitly left for this piece.

## A gap found and closed first: project scoping

Before the loop itself, one thing was missing that made it dishonest to
build: `curator_control.STAGE_TABLE`'s argv builders never passed
`--project` through to K2/K4, even though both scripts already support it
(`extract_claims.py`/`match_claims.py`, `action="append"`, scoped-merge on
write — the planner's own docstring already claimed this scoping existed).
Without it, "running a `PlanStep` for `proj-a`" would have silently run
the WHOLE corpus every time — duplicating work across every step of a
multi-project plan and defeating the entire point of having one.

Closed in `curator_control.py`: a new `PROJECT_SCOPED_STAGES = frozenset({
"K2", "K4"})`, and `run_stage` now takes a `project_id` parameter — when
given AND the stage is in that set, `--project {project_id}` is appended
to the fixed argv; for every other stage (K0/K1/K3/K5, none of which have
a `--project` flag of their own) it is silently not applied, never
invented as an argv those parsers don't accept (0037 clause 1 stays
satisfied — no caller-supplied parameter reaches the subprocess other than
through this one declared channel). `execute_with_lock` needed no change
at all: `project_id` passes straight through its existing `**kwargs`.

## What was built

`chronicler/review/conductor_run.py` (new):

- **`RunControl`** — two independent stop intents over one
  `curator_control.CancelToken`: a plain `stop_after_step` flag the loop
  peeks (non-consuming) before scheduling the next step, and the wrapped
  token for the in-flight/queued half Task 5′ already built.
  `request_stop_now()` sets both — there is no step left to "let finish"
  once the current one has been asked to stop immediately.
- **`run_plan(spec, ...)`** — runs every step of an APPROVED `PlanSpec`, in
  the order `spec.steps` already carries (reorders nothing — 0037 clause
  3). One `GovernorState` lives for the whole run (baseline is per-run,
  `governor.py`'s own rule); `on_timing_line` feeds the SAME stream to
  both `governor.observe` and `ledger.make_ledger_feeder` — one run now
  measures itself and paces itself off nothing new. `validate_for_
  execution` re-runs before **every** step, not just once — a mid-run
  failure (a profile renamed, a stage's model unselected) is a stop
  condition that preserves every result already collected, never an
  exception that discards them. If the last governor action for a step was
  `"pause"`, the loop sleeps `pause_seconds` via an injectable `sleep_fn`
  before the *next* step — never mid-step, and never after the last one
  (nothing follows it to pause before).
- **Re-derives, never trusts (0037/0031).** After every step,
  `curator.stage_states()` is re-read fresh from disk and attached to the
  result as `post_state` — an outcome's `state == "success"` is a
  subprocess's return code, not proof of what the caches actually show
  now; this loop reports the observation, not the inference.
- **`run.py conductor --plan-id ID`** — the thin CLI shell. Loads the named
  plan from the real `PlanRegistry`, wires a SIGINT handler for the two-
  gesture cancel (first Ctrl-C → `stop_after_step`; second → also fires
  the `CancelToken`, terminating the in-flight subprocess), prints each
  step's outcome and any pause, and reports a non-zero exit whenever the
  run stopped early — the same three-state honesty `curator_control`
  already established (never a silent partial success).

## What was deliberately not done this round

Mid-stream pausing (interrupting a step that is already running to sleep,
then resuming it) — not attempted; nothing in this codebase can safely
pause a live subprocess mid-generation, and the brief's own words already
scoped pausing to *between* steps, which this loop does.

## UAT

- `[G]` `--project` now reaches K2/K4's own existing flag through the
  execution allowlist; every other stage silently ignores a `project_id`
  it has no flag to accept.
- `[G]` `run_plan` re-validates before every step, not just once; a
  mid-run failure stops the run but preserves every result already
  collected.
- `[G]` The governor and the ledger are fed off the identical timing
  stream a step already emits; a `"pause"` action sleeps `pause_seconds`
  before the next step only, never mid-step, never after the last step.
- `[G]` `post_state` is a real, fresh `curator_data.Curator.stage_states()`
  read after each step — never inferred from the step's own outcome.
- `[G]` A queued stop (`stop_after_step` already set) never calls
  `execute_fn` for step 0; an in-flight cancellation stops the run right
  after the cancelled step's own result is recorded, never starts the
  next one.
- `[H]` A real overnight run against the real `10280L` rig, including a
  real two-gesture Ctrl-C sequence — not yet exercised outside the
  hermetic tester.

**Commit:** `25e977d`.
**Gate status: GREEN.** `python verify.py` → all auditors + testers pass,
including the new `tests/tester_conductor_run.py` (unapproved-plan
refusal, the happy path with a real governor pause + ledger feed +
post-step state read, queued cancellation, in-flight cancellation, and
mid-run re-validation failure preserving already-collected results)
(verified again by the pre-commit hook at commit time).

# The curator-tab frontend

**Source:** the brief's own last remaining piece — every other round built
the data layer; nothing rendered it in the tab.

## A real bug found and fixed first

Wiring the frontend to real data (rather than the adapter's own synthetic
test fixtures) surfaced a genuine latent defect in `candidates.py`:
`candidates_from_curator` read `row.session_id` / `row.project_id`
(attribute access), but `curator_data.ratified_map_rows()` — the REAL
source of `map_rows` — returns plain dicts (`csv.DictReader` rows), not
objects. `tester_candidates.py`'s own `_Row` helper class silently papered
over this by fabricating an object with those attributes; it would have
broken the first time this ran against the real ratified map. Fixed:
`candidates.py` now reads `row["session_id"]` / `row["project_id"]`
(dict-style, matching `ratified_map_rows`'s real return shape), and the
tester's fixture was changed from a bespoke class to a plain dict
constructor so the same bug can't hide behind it again.

## A route closing the last gap: real candidates over HTTP

Task 6's `POST /plan/preview` always required the CALLER to supply
`ProjectCandidate` facts — there was no route that computed them from real
Curator data, so a browser had nothing to preview a plan from except
hand-typed JSON. New: `GET /api/curator/conductor/candidates` (optional
`model_id`/`stage`/`host` query params), which calls
`candidates.candidates_from_curator` against this machine's real ratified
map, `claims.json`, `knowledge_index.json`, K2's cache, real discovered
conversations (`curator_findings.build_conversation_map`, reused, not
reimplemented), and the calibration ledger. Omitting `model_id` leaves
every `estimated_seconds` honestly `None` — the same "no measurement, no
estimate" rule carried all the way to the browser.

`conductor_panel.run_state`'s docstring/note were also brought up to date
— they still said "no execution loop exists yet," which stopped being
true the round before this one. Corrected to say plainly what IS and
ISN'T visible now: the real lock (shared with `run.py conductor`) shows
up here, but the governor's pacing state lives only in that CLI process's
memory and is never persisted anywhere this read-only panel could read it
from — a structural absence, not a gap to paper over with a placeholder.

## What was built

New "Conductor" sub-tab in the curator pane
(`chronicler/review/static/panes/curator.js` + `index.html`), following
the existing sub-tab convention exactly (`showCuratorSub`, `curator-sub-*`
containers, `jget`/`esc` from `shared.js`) — purely additive, no change to
any other pane, no restructuring of the app shell (the standing
constraint: a possible future reorganisation is being weighed separately
and this round doesn't pre-empt it):

- **Preconditions / run state / calibration**, read on tab activation —
  LM Studio reachability, map-ratified state, calibration-data presence,
  the real lock, and a per-model/per-stage/per-cool-down-partition
  calibration table (median/p25/p75/n), all straight passthroughs of the
  existing Task 6 routes.
- **Plan builder** — policy/stage/model/budget form → `Preview plan`
  fetches real candidates from the new route, POSTs them to
  `/plan/preview`, and renders the resulting steps, remainder, and
  budget fit.
- **Approve** — a button on an unapproved preview; once approved, the
  panel shows the exact command to actually run it:
  `python run.py conductor --plan-id <id>` — never an in-browser "run"
  button, for the reason given above.

## What was deliberately not done this round

No live in-browser progress view of a running plan (the governor's
pacing/pause state isn't visible to any route, as `run_state`'s note now
says plainly) — polling `run_state` while a CLI run is in progress would
show the real lock going from free to held and back, which the panel
already supports without any further change; a richer live view would
need the execution loop to persist progress somewhere this panel could
read it from, which is new scope, not a missing wire-up.

## UAT

- `[G]` `candidates.py` reads `map_rows` as plain dicts (matching
  `ratified_map_rows`'s real shape), not a bespoke attribute-style object
  — verified via `tester_candidates.py`'s corrected fixture.
- `[G]` `GET /api/curator/conductor/candidates` returns real,
  live-computed candidates from a temp Curator estate (verified via a
  live `TestClient` call, not just by inspection).
- `[G]` A full preview → approve round-trip through the real routes,
  driven by the same request shapes the frontend JS sends, verified live
  end-to-end via `TestClient` (preconditions → calibration → run →
  candidates → plan/preview → plan/approve, all 200, the approved plan
  carrying a real `approved_at` timestamp).
- `[G]` The new pane follows the existing sub-tab convention exactly; no
  other pane's markup or JS changed.
- `[H]` A real walk of the tab in a browser against the real `10280L`
  Curator estate — not exercised this round (no browser available here);
  the live `TestClient` round-trip exercises every route the frontend
  calls, in the same order, with the same payload shapes.

**Commit:** `92b159c`.
**Gate status: GREEN.** `python verify.py` → all auditors + testers pass,
including the corrected `tests/tester_candidates.py` (dict-shaped
`map_rows`, matching `ratified_map_rows`'s real return shape) (verified
again by the pre-commit hook at commit time). Additionally exercised live
via `TestClient` end-to-end (not gate-registered, same posture as the
Task 6 smoke test): a full preconditions → calibration → run →
candidates → plan/preview → plan/approve round-trip against a temp
Curator estate, all 200, the approved plan carrying a real
`approved_at` timestamp.

---

**COWORK_BRIEF_conductor_governor.md is now closed out.** Every task the
brief and its addenda scoped as buildable without the real `10280L` rig —
resilience (retry, checkpointing), the governor, the streaming executor
and lock, the planner, the calibration ledger, the conductor panel
backend, the real-data adapter, the execution loop, and the curator-tab
frontend — is built, hermetically tested, gate-GREEN, and committed with
a stamped report/UAT section. What remains is exactly the `[H]` items
listed throughout: real-hardware walks (an overnight run, a two-gesture
Ctrl-C sequence, a browser session) against the real machine, which this
environment cannot exercise.

# Three real-rig findings, fixed

The first live walk on `10280L` (approved a plan, triggered a real run,
watched it unattended) surfaced three things — two cosmetic, one a
genuine functional gap in the execution loop itself.

**1. Select dropdown options rendered white-on-white.** The shared
`select { background: transparent; color: inherit; }` rule (present
site-wide, not new this round) lets the CLOSED select box blend with the
page correctly, but several browsers don't apply that same rule to the
native OPTION popup — it renders with a plain white popup background
while still inheriting the page's light-on-dark text colour, unreadable
until hovered. Fixed with `select option { background-color: Canvas;
color: CanvasText; }` — CSS system colours that resolve to the browser's
real current colour scheme, honouring the page's existing `color-scheme:
light dark` rather than hand-picking a colour that only works in one
theme. Applies to every select on the page (a pre-existing gap the new
Conductor sub-tab's three selects just happened to be the first to
surface, not something this round introduced).

**2. No click-to-copy for the `run.py conductor` command.** Added a
`Copy` button next to the command shown after approval
(`navigator.clipboard.writeText`, with visible "Copied!"/failure feedback
and a plain-text fallback already sitting right there in the `<code>` if
the Clipboard API is unavailable on that origin).

**3. The real functional gap: the execution loop showed zero progress
during a real run.** `conductor_run.run_plan` only *returns* once the
WHOLE plan is done — `run.py conductor` was reading nothing but that
return value, so a multi-hour real run showed nothing in the terminal at
all while LM Studio was visibly, actively working through requests. This
was a genuine defect in the round that built the execution loop, not a
missing nice-to-have: a caller had no way to distinguish "working" from
"hung" for the entire duration of a run.

Fixed with three optional callbacks on `run_plan`, all firing LIVE from
inside the same blocking read loop `curator_control.run_stage` already
streams a step's output through (nothing new to instrument — these hook
the exact point Task 5' already made line-by-line):

- `on_step_start(step_index, step)` — right before that step's
  `execute_fn` is called.
- `on_timing_line(kind, ms_per_token, line, action)` — for every TIMING*
  line, AFTER the governor has already observed it and the ledger has
  already recorded it; `action` is that exact `GovernorAction`, not the
  step's eventual final one.
- `on_step_end(step_result)` — right after that step's `StepResult` is
  recorded.

`run.py conductor` now wires all three to `print()` — one line per K2
window / K4 claim as it happens, plus a step-start and step-end line —
and the old end-of-run recap loop (which only ever printed after
`run_plan` returned, i.e. the exact thing that produced this gremlin) was
removed as redundant.

## UAT

- `[G]` `select option` styling verified via inspection of the resolved
  rule (no browser available in this environment to screenshot the fix
  against — the real-rig walk that found the bug is what will confirm it).
- `[G]` The copy button and its fallback text verified by inspection.
- `[G]` `on_step_start`/`on_timing_line`/`on_step_end` all fire live, in
  order, with the correct arguments — including that `on_timing_line`'s
  `action` is the REAL per-line `GovernorAction`, not a stand-in for the
  step's eventual last one — added to `tester_conductor_run.py`'s
  existing happy-path scenario rather than a new one, since it's the same
  run being observed two ways at once.
- `[H]` The real `10280L` run already in flight when this was found used
  the OLD, silent code — it will still complete correctly (nothing about
  execution itself changed, only what's printed), but won't show this
  fix; the next run will.

**Commit:** pending — code round, gate run before commit.
