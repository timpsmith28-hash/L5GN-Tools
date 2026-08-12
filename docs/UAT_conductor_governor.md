# UAT walk-sheet — the conductor, part 2 (Task 1 only, this round)

**Brief:** `docs/COWORK_BRIEF_conductor_governor.md`
**Report:** `docs/COWORK_REPORT_conductor_governor.md`

**Built:** 2026-08-10, in a Cowork sandbox with no LM Studio instance and no
real work rig reachable. `[G]` items below were verified programmatically
this session against `tests/tester_extract_claims.py` /
`tests/tester_match_claims.py` and are ticked with the evidence named.
**`[H]`/`[W]` items are left unticked** — they need the real work rig and
Tim's own judgement, per the brief's instruction not to fake a `[G]` on a
human-only item. A ticked `[G]` means "the code does what this line
claims," not "the feature is good" (0031). Only the subset of the brief's
full UAT list that Task 1 actually touches is listed here.

---

- [x] `[G]` Task 1's defaults reproduce today's behaviour; per-window and
  per-claim records appear alongside the per-conversation one.
  — Every pre-existing assertion in both testers (which never pass
  `on_window_timing`/`on_claim_timing`) still passes unmodified. New tests:
  a 12-message conversation windowed at `max_window_tokens=500` produces
  `windows_total >= 2` on_window_timing records (K2), correctly indexed
  `0..windows_total-1`; a batched group makes exactly zero on_window_timing
  calls (no window concept there). K4: `on_claim_timing` fires once per
  claim that made a network call (3 claims, 3 records), zero for an
  all-cache-hit re-run.

- [x] `[G]` A unit measured after a cool-down is flagged as such, and
  precision holds at sub-conversation granularity.
  — K2: 3 conversations run with `cool_down=1.0`; the first conversation's
  `cool_down_preceded` is False, the second and third are True (per-
  conversation), and at window granularity only the immediately-post-gap
  conversation's **first** window is flagged True, its later windows False.
  K4: same pattern at claim granularity — c-tl1 (first conversation) has
  neither claim flagged; c-tl2 (immediately after the cool-down)'s one claim
  is flagged True.

- [x] `[G]` K4's boundary assertion fires loudly on a synthetic
  non-contiguous claim stream instead of silently double-counting.
  — A claims list where `conversation_id` "c-x" appears, is followed by
  "c-y", then "c-x" reappears raises `ValueError` naming "c-x". The normal
  contiguous case (every other test in the file) never raises.

- [x] `[H]` Whether throughput decays *within* a single conversation
  (thermal trial Run 2, Q1) — **walked on the real rig, Addendum 3**: an
  isolated conversation measured twice independently
  (`run2iso_windows.jsonl` alone, then again inside `run3iso_windows.jsonl`)
  shows near-zero correlation between window position and
  `generation_ms_per_token` (r=0.234, then r=0.013) against strong,
  consistent correlation with input token count (r=0.869, r=0.813) in both
  measurements — the earlier "gets slower later" impression was the
  prompt-size confound Addendum 2 already named, not intra-conversation
  decay. **No measurable decay. Task 3 is unblocked on Q1.**

---

## Addendum 2 — the instrument fix

- [x] `[G]` `usage` is captured on every call in both K2 and K4; a response
  carrying no `usage` records it as absent and the run continues.
  — `call_lmstudio`/`call_lmstudio_generic`: monkeypatched transport tests
  confirm `on_usage` fires once with `{"completion_tokens", "prompt_tokens"}`
  when present, once with `None` when absent, and the function's own return
  value (the content string) is identical either way.

- [x] `[G]` Generation ms/token appears in the window and claim records, and
  is independent of output length.
  — `generation_ms_per_token(elapsed, usage)` tested directly: a long-output
  call (800 completion tokens / 16.0s) and a short-output call (40 tokens /
  0.8s) at the same real generation speed both report 20.0ms/token exactly.
  Zero completion_tokens and usage_available=False both yield `None`, never
  a division-by-zero or a fabricated figure. End-to-end: K2's
  `extract_for_conversation` and K4's `match_claims` both wire a caller-
  populated `usage_box` into the window/claim record correctly, and a
  multi-call unit (several `confirm_chunk` calls under one K4 match) SUMS
  across every call rather than keeping only the last.

- [x] `[G]` The four `caller(...)` sites are unchanged and every existing
  tester stub still works.
  — Confirmed by inspection (no edit to `extract_for_conversation`'s,
  `extract_batch`'s, `confirm_chunk`'s, or `confirm_supersede`'s call to
  `caller(...)`) and by every pre-existing test in both testers passing
  unmodified, including the many that use a stub caller with no `usage_box`
  at all.

- [ ] `[W]` **Replay the 10 August series against the governor.** Not
  possible without Task 3 (the governor itself), not built this round.

- [x] `[H]` **With the new unit, re-walk Run 2**: does throughput decay
  *within* one conversation? **Walked, Addendum 3 — no.** See above.

---

## Addendum 3 — the real-rig walk

- [x] `[H]` Q1 (Run 2, isolated conversation): no measurable
  intra-conversation decay. See above.
- [x] `[H]` Q3 (Run 3, true `--cool-down 90` vs `run1`/`run2` baseline):
  cool-down alone shows no measurable benefit — per-conversation ratios
  flat at 0.90–1.06, aggregate mean/median within noise of baseline. The
  token-dial reduction (Run 5, first pass) remains the only lever with a
  demonstrated effect.
- [x] `[H]` Reload penalty, reassessed on `run3iso`'s own
  `cool_down_preceded` windows: no measurable penalty once one
  low-completion/high-input outlier (the same contamination pattern
  Addendum 2 named) is excluded.
- [x] `[G]` Runbook's isolation-map commands fixed for the UTF-16LE/
  `utf-8-sig` encoding mismatch that raised `UnicodeDecodeError` on first
  live attempt — `docs/RUNBOOK_conductor_thermal_trial.md`, `Set-Content`/
  `Add-Content -Encoding utf8` in place of bare `>`/`>>`.

## Addendum 4 — resilience (retry, K2 checkpointing)

- [x] `[G]` A transient transport failure (HTTP 400, `URLError`, `OSError`)
  is retried before being treated as a real failure; a persistent one still
  raises once retries are exhausted; `retries=0` restores exact
  fail-immediately behaviour.
  — `tests/tester_extract_claims.py` / `tests/tester_match_claims.py`:
  monkeypatched transport fails N times then succeeds (correct attempt/sleep
  count, return value unaffected); a transport that never clears still
  raises after exactly `retries + 1` attempts; `retries=0` makes exactly one
  attempt and never sleeps.

- [x] `[G]` K2 checkpoints (cache + partial `--out`) after every group, not
  only at the end — a crash mid-run loses at most the in-flight group.
  — Three single-conversation groups produce exactly 3 checkpoints, each a
  strict superset of conversations covered by the last; a simulated crash
  raised from inside `on_checkpoint` after the 2nd of 3 groups still leaves
  the first two conversations' entries in the (in-memory, mutated in place)
  cache dict — the resumability property itself, not just the callback
  firing. Omitting `on_checkpoint` entirely changes nothing about the
  result.

## Task 3 — the governor

- [x] `[G]` The governor pauses on a synthetic decaying-throughput stream,
  resumes on recovery, and hits its cap on a stream that never recovers —
  recording that it did.
  — `tests/tester_governor.py`: baseline established from the first 4
  units (median); a stream degraded to 40% of baseline for 4 consecutive
  units produces exactly 1 `pause`; recovering back to baseline produces
  exactly 1 `resume`; a stream that never recovers produces exactly
  `pause_cap` (3) `pause` actions then exactly 1 `cap_reached` — never
  repeated on later still-degraded units, and never hangs (every
  subsequent unit reads `none`, proceeding). A later genuine recovery
  after the cap still resumes normally and resets `cap_reached`.

- [x] `[G]` **The governor's output names no cause.**
  — Every message produced across every test scenario (baseline
  establishment, steady state, decay, pause, cap, resume, `None`/unmeasured
  units) is scanned for `thermal`/`overheat`/`throttl`; none found. This is
  a test assertion (`_FORBIDDEN_WORDS`), not a review-by-eye promise.

- [x] `[G]` Named, machine-scoped profiles round-trip through
  `config/local.json`, and the default profile leads with the token dials.
  — `get_profile`/`set_profile` tested against a temp path: a never-stored
  profile name returns `DEFAULT_PROFILE` exactly; a partially-specified
  stored profile is layered over the default so every key is still
  present; writing one host/profile never disturbs another. Addendum 3's
  real data (cool-down alone: no measurable benefit; token-dial reduction:
  a real one) is why `DEFAULT_PROFILE` leads with `max_window_tokens`/
  `batch_target_tokens` rather than `cool_down_seconds`.

- [ ] `[H]` Wired into a real run and walked live (hour/overnight budget,
  did it help, did you want to intervene) — not possible until Task 4 (the
  planner) exists to define a multi-step run for it to pace.

## Task 5′ — streaming, the lock, cancellation

- [x] `[G]` Timing records reach a live consumer while the process is
  running — streamed, not buffered to exit.
  — `tests/tester_curator_control.py`: `on_timing_line` fires exactly for
  each `TIMING_WINDOW`/`TIMING_CLAIM` line a fake streamed process emits
  (2 of 4 lines in the fixture), with the parsed `generation_ms_per_token`
  or `None` when the line marks it unavailable; never fires for a
  non-timing line. Omitting the callback changes nothing about the result.

- [x] `[G]` The lock carries a pid and a heartbeat; staleness is reported,
  never acted on automatically; `break_lock` is the only way one is ever
  cleared, and it always names why.
  — A freshly acquired lock carries a pid and an initial `heartbeat_at`
  and does not read stale; `heartbeat()` updates `heartbeat_at` in place
  (read-modify-write, preserving every other field) and returns `False`
  without creating a lock file when nothing is held; a lock whose
  heartbeat is old relative to an injected `now` reads `stale=True`, a
  freshly-heartbeated one does not; `break_lock("")` is refused
  (`ValueError`); `break_lock(reason, ...)` records the reason and what
  was broken, and actually clears the lock; `acquire_lock` never
  auto-reclaims a lock it would itself call stale — only `break_lock`
  ever does, and only when called explicitly.

- [x] `[G]` A queued cancellation skips a step entirely; an in-flight
  cancellation terminates the subprocess; neither invents a fifth
  `classify_outcome` state.
  — A `CancelToken` set before `execute_with_lock` ever calls `run_stage`
  produces `state="blocked"`, `cancelled=True`, and `popen_factory` is
  never even invoked (asserted via a factory that raises if called); the
  token reads un-set afterward (one-shot). A token set 3 lines into a
  50-line streamed fixture causes `Popen.terminate()` to be called and
  the run to stop reading well short of the process's own output ending;
  outcome is `cancelled=True`, `state="failed"` — never a new state value.
  Both cases release the lock.

- [ ] `[H]` Kill the conductor mid-plan on the real rig and confirm both
  caches stay consistent, re-planning re-derives the remainder — not
  possible until Task 4 (the planner) exists to define "mid-plan."

---

Everything else in the brief's UAT list (the calibration ledger, the
planner's ordering and remainder, the surface, and every real-hardware
walk) belongs to Tasks 2, 4 and 6, not built this round, and is
intentionally absent here rather than listed as failing or skipped.
