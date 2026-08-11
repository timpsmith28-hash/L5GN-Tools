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

- [ ] `[W]` Whether throughput decays *within* a single conversation
  (thermal trial Run 2, Q1) — **not measured**, per the design thread: Run 2
  was unreadable before this round (one timing record per conversation, no
  intra-conversation signal). Recorded as "not yet measurable," not "no
  decay." Task 1's per-window timing (built this round) is what makes Run 2
  readable the next time it's attempted; Task 3 stays open until it is.

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

- [ ] `[H]` **With the new unit, re-walk Run 2**: does throughput decay
  *within* one conversation? Still open — this is Tim's real-rig walk with
  the fixed instrument now available.

---

Everything else in the brief's UAT list (the calibration ledger, the
governor's pause/resume/cap behaviour and its "no cause" language, the
planner's ordering and remainder, the streaming executor, the lock's
stale-detection, the surface, and every real-hardware walk) belongs to
Tasks 2–6, not built this round, and is intentionally absent here rather
than listed as failing or skipped.
