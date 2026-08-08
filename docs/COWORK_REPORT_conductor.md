# Cowork report — the conductor (Task 1 only, this round)

**Brief:** `docs/COWORK_BRIEF_conductor.md`
**Precondition:** DECISIONS **0037** (execution parameters are generated from
a ratified plan, never supplied by a caller; a budgeted run's unit of work is
a project or a newest-first prefix of one) — already **accepted** at commit
`8687d25` before this round started. Not re-litigated here.
**Built:** 2026-08-08, in a Cowork sandbox with no LM Studio instance and no
real work rig reachable — the same working constraint every prior
`COWORK_REPORT_*` in this repo was built under.
**Scope of this round:** Task 1 only, by explicit choice — the smallest
possible change to K2/K4, deferred TTL evidence, and nothing from Tasks 2–6
(calibration ledger, thermal governor, planner, executor/lock rework,
surface). Those remain to be scoped in a future round.

## What was built

Three flags, additive and off by default, in `chronicler/pipeline/extract_claims.py`
(K2) and `chronicler/pipeline/match_claims.py` (K4):

- **`--cool-down SECONDS`** (default `0`) — sleeps *between* conversations
  after a group that actually made a network call, never mid-conversation and
  never after the last group. In K2 a "group" is a single conversation or a
  batched set of small ones (`run_extraction`'s existing grouping); in K4,
  which never sees a `Conversation` object, the boundary is a run of claims
  sharing a `conversation_id` in K2's already-newest-first, per-project
  stream. Sleeping is injected via `sleep_fn` (default `time.sleep`) so it is
  hermetically testable without a real wall-clock wait — every new test in
  `tests/tester_extract_claims.py` / `tests/tester_match_claims.py` passes a
  list-`.append`-collecting stub instead of actually sleeping.
- **`--model-ttl SECONDS`** (default: omitted) — passed through verbatim as
  the chat-completions payload's `ttl` field, in both `call_lmstudio` (K2)
  and `call_lmstudio_generic` (K4). No new field is invented; this is LM
  Studio's own documented idle-TTL/auto-evict mechanism
  ([Idle TTL and Auto-Evict](https://lmstudio.ai/docs/developer/core/ttl-and-auto-evict),
  [LM Studio REST API](https://lmstudio.ai/docs/developer/rest)), which
  unloads a JIT-loaded model after this many idle seconds — the payload
  field the brief's finding said should be tried before any load/unload
  controller is built.
- **Per-conversation timing line** — `make_timing_reporter()` in each module
  emits one `TIMING ...` line per conversation to stderr, and (if
  `--timing-log PATH` is given) also appends the same record as a UTC-ISO-
  8601-stamped JSON line to a file, which is the shape Task 2's calibration
  ledger is meant to read. K2's record carries `message_count` (real, from
  the `Conversation` object); K4's carries `claim_count` instead, honestly,
  since K4 works at claim granularity and never sees message counts — no
  fabricated substitute was invented for either gap. A batched K2 group's
  members all report the group's *shared* wall-clock time, tagged with the
  real `batch_size`, rather than an invented equal split — Task 2, when
  built, needs to see that distinction to avoid averaging a shared cost as
  if it were several independent measurements.

`--cool-down 0` and no `--model-ttl` (the defaults) reproduce today's
behaviour exactly — confirmed by every pre-existing test in both testers
still passing unmodified, plus new assertions that `cool_down=0.0` never
calls `sleep_fn` and that omitting `ttl` never adds the payload field.

Nothing else about K2 or K4 changed: no claim, no verdict, no cache key is
touched by any of the three flags.

**Commit:** `<pending>` — see below.
**Gate status: GREEN.** `python verify.py` → all auditors + testers pass,
including the extended `tester_extract_claims` and `tester_match_claims`.

## The TTL question — evidence, and what is still missing

The brief's finding said Task 1 should try the TTL field first and report
whether it was sufficient, "before anything is built." That trial has two
halves, and only one was possible in this sandbox:

**What is now true (code-level, verifiable here):** `--model-ttl` puts a
real, documented LM Studio field on the wire. `ttl` is accepted on the
OpenAI-compatible `/v1/chat/completions` endpoint K2 and K4 already POST to,
per LM Studio's own docs. Passing it costs nothing extra — no new
subprocess, no `lms` CLI dependency, one field in a payload that already
exists, exactly as the brief's finding predicted. This is verified by two
new tests (`tester_extract_claims`, `tester_match_claims`) that monkeypatch
`urllib.request.urlopen` and assert the field's presence/absence and value.

**What is still missing (requires the real work rig — an `[H]` item, not
buildable in this sandbox):** whether a short TTL, left to expire during the
cool-down gap between projects, actually keeps GPU memory healthy across a
long run *without* the manual reload Tim currently does by hand. That
requires `nvidia-smi`/LM Studio observation on real hardware across a
multi-project run — a real thermal/memory measurement this sandbox has no
access to (no GPU, no LM Studio instance). Per the brief's own UAT list, this
is `[W]`: **"the TTL question is answered with evidence — a long run with a
short TTL, and a statement of whether memory stayed healthy without manual
reloads."**

**Recommended next step for Tim:** run K2 (or K4) over two or more projects
back-to-back with `--cool-down` set to something longer than the intended
`--model-ttl` (e.g. `--model-ttl 60 --cool-down 90`), and watch LM Studio's
own model list / `nvidia-smi` between projects. If memory is released and
reloaded automatically without a manual step, TTL is sufficient and the
explicit load/unload controller in the brief's "explicitly out of scope"
section stays dropped, as the brief already anticipates. If it is not
released, or if reload is slow/unreliable, that failure needs to be
described concretely (what degraded, how) — that description is what would
justify building the controller in a future round, not before.

## What was deliberately not done this round

Per the scoping decision made at the start of this round: no calibration
ledger (Task 2), no thermal governor (Task 3), no planner (Task 4), no
executor/lock rework (Task 5), no surface (Task 6). The timing line's shape
(`message_count`/`claim_count`, `batch_size`, `wall_clock_seconds`,
`project_id`, `model_id`, UTC-ISO-8601 `timestamp` when logged to a file) was
chosen with Task 2 in mind but Task 2 itself — deriving per-model throughput,
reporting spread, refusing an estimate with no measurement — was not built.

## UAT

Walk-sheet: `docs/UAT_conductor.md` (Task 1 subset only — see that file for
which of the brief's full UAT list applies to this round's slice). The two
items requiring real hardware (`[H]`/`[W]`) cannot be walked in this sandbox
and are Tim's to run.
