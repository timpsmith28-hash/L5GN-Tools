# UAT walk-sheet — the conductor (Task 1 only, this round)

**Brief:** `docs/COWORK_BRIEF_conductor.md`
**Report:** `docs/COWORK_REPORT_conductor.md`

**Built:** 2026-08-08, in a Cowork sandbox with no LM Studio instance and no
real work rig reachable. `[G]` items below were verified programmatically
this session against `tests/tester_extract_claims.py` /
`tests/tester_match_claims.py` and are ticked with the evidence named.
**`[H]`/`[W]` items are left unticked** — they require the real work rig and
Tim's own judgement reading evidence, per the brief's own instruction not to
fake a `[G]` on a human-only item. A ticked `[G]` here means "the code does
what this line claims," not "the feature is good" (0031). Only the subset of
the brief's full UAT list that Task 1 actually touches is listed; the rest
(planner, governor, executor, surface) is not applicable to this round and is
not listed here as pending — it belongs to a future round's own walk-sheet.

---

- [x] `[H]`→checked-but-still-`[H]` **0037 is ratified and committed before
  any code lands.**
  — Already true before this round started: `docs/DECISIONS.md` shows 0037
  as `Status: accepted`, committed at `8687d25`. Left as `[H]` per the
  brief's own layer even though the fact itself is machine-checkable — worth
  a `git log` glance, not a rubber stamp.

- [x] `[G]` `--cool-down 0` and no `--model-ttl` reproduce today's behaviour
  exactly.
  — `tester_extract_claims.py`: `cool_down=0.0` never calls `sleep_fn`, and
  `call_lmstudio` with no `ttl` given never adds the payload's `ttl` field.
  `tester_match_claims.py`: same two assertions for K4's
  `call_lmstudio_generic` and `match_claims`. Every pre-existing assertion in
  both testers (which never pass either new argument) still passes
  unmodified — the new parameters are additive, not a behaviour change to
  the default path.

- [x] `[G]` `--cool-down N` pauses **between** conversations, never inside
  one; a conversation's windows stay contiguous and the cache is unchanged.
  — `tester_extract_claims.py`: 3 conversations with `cool_down=5.0` sleep
  exactly twice (never after the last); a batched group's `extract_batch`
  call is unaffected internally (windowing/cache tests from the pre-existing
  suite are untouched and still pass). `tester_match_claims.py`: 2 claims
  sharing one `conversation_id` plus 1 claim in a second conversation sleep
  exactly once (between the two conversations, not between the two claims of
  the first) with `cool_down=7.0`.

- [ ] `[W]` **The TTL question is answered with evidence** — a long run with
  a short TTL, and a statement of whether memory stayed healthy without
  manual reloads.
  — Not walkable in this sandbox (no GPU, no LM Studio). What *is* verified:
  `--model-ttl SECONDS` puts LM Studio's own documented `ttl` field on the
  wire correctly (`tester_extract_claims.py` / `tester_match_claims.py`
  monkeypatch `urllib.request.urlopen` and assert the field's value). See
  `COWORK_REPORT_conductor.md`'s "TTL question" section for the recommended
  real-rig run.

- [x] `[G]` Per-conversation timings are emitted and land in the ledger.
  — "Land in the ledger" is Task 2, out of scope this round (no ledger
  exists yet to land in). What Task 1 owns: a `TIMING ...` line is emitted
  per conversation (stderr always; also appended as a UTC-ISO-8601-stamped
  JSON line to `--timing-log PATH` if given) — verified by
  `make_timing_reporter()` tests in both testers, and by `run_extraction`
  (K2) / `match_claims` (K4) emitting one record per conversation
  (`batch_size`-tagged for a shared K2 batch call; `claim_count`-carrying for
  K4, which has no message count to report).

---

Everything else in the brief's UAT list (planner ordering/remainder,
governor loop state, lock staleness/pid/heartbeat, surface behaviour,
real-hardware hour/overnight walks, which thermal lever helped,
estimate-vs-actual trust) belongs to Tasks 2–6, not built this round, and is
intentionally absent from this walk-sheet rather than listed as a failing or
skipped check.
