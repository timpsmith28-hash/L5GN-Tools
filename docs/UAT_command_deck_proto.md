<!-- gate-frozen: commit=26079ed -->

# UAT walk-sheet — Command Deck prototype (project-grouped queue, batch rulings)

Pair: `docs/COWORK_BRIEF_command_deck_proto.md` → `docs/COWORK_REPORT_command_deck_proto.md`.
Built on `26079ed` (0024 ratified). Gate at build time: `python verify.py`
**GREEN**, 6 auditors + **45** testers (frozen build-time count). Mark each
check **ready to walk**, never "passed" — the walk is Tim's.

Nothing is committed from this round yet. These check staged changes.

Two rounds of proof already done this session, distinct from Tim's walk:
hermetic testers (`tests/tester_review.py`, `tests/tester_relink_apply.py`,
`tests/tester_backfill_candidate_project.py`) prove the write-path invariants
against synthetic sqlite fixtures, and a one-off `TestClient` smoke test
(not part of the gate) exercised every endpoint end-to-end against a
throwaway seeded DB. Neither substitutes for walking the real dev vault —
they're noted per-item below where they cover part of the ground.

## Task 1 — structured candidate

- [ ] **1.1.** `python chronicler/pipeline/backfill_candidate_project.py`
  (dry-run) against the dev vault reports the resolved/unresolved split for
  the real ~500 pending rows. *(Not yet run against the real dev vault this
  session — sandbox has no access to `chronicler_dev`.)*
- [ ] **1.2.** `--apply` leaves every pending row with a `candidate_project`
  that resolves in the registry, or on the unresolved list with a reason —
  never a guess.
- [ ] **1.3.** A fresh `relink.py --apply` (dry-run reviewed first) writes
  `candidate_project`/`rival_project` on new rows going forward. *(Covered
  hermetically by `tests/tester_relink_apply.py`; not yet walked live.)*

## Task 2/5/6 — the wall becomes a list of walls

- [ ] **2.1.** Open the deck (`run.py review`, optional web stack installed)
  on the dev vault; every project with pending threads shows its own count in
  the left nav, and picking one shows only its batch. *(Smoke-tested against
  synthetic data via `TestClient` — `GET /api/queue/projects` and
  `GET /api/pending?project=…` both correct; needs walking on the real deck.)*
- [ ] **2.2. The rival case.** A `link_ambiguous` thread appears in **both**
  candidates' batches, the non-primary one visibly marked (orange left-border,
  "rival candidate" badge). *(Smoke-tested: `T2` appeared in both `l5gn-os`
  and `crystal-spire` batches, `is_rival` correct in each.)*
- [ ] **2.3. Work is unreachable, not merely unshown.** A work-account thread
  with a pending suggestion never appears in `GET /api/queue/projects` or any
  `GET /api/pending` response, filtered or not — confirmed structurally (code
  has no path that can return one; DECISIONS 0023) and by both the hermetic
  tester and the smoke test (`TWORK` never appeared anywhere).

## Task 3/4 — rulings

- [ ] **3.1. Batch accept.** Ticking several threads and hitting Confirm
  writes them all as `manual` in one request; re-running relink leaves them
  alone (skip_manual). *(Smoke-tested via `POST /api/rule/batch`.)*
- [ ] **3.2. Partial failure is visible.** An invalid id inside a batch
  reports per-thread (`{"ok": false, "error": …}`) rather than silently
  succeeding or failing the whole batch. *(Smoke-tested directly: one good +
  one bad pair in the same request, good one committed, bad one reported.)*
- [ ] **3.3. Rejection clears.** "Not this project" removes the row from that
  batch and it does not resurface on reload; it does NOT remove the thread
  from a *different* project's batch if it's still a live candidate there
  (the rival case again, from the other side). *(Smoke-tested: rejecting T2
  against `l5gn-os` cleared it from that batch while it stayed in
  `crystal-spire`'s.)*
- [ ] **3.4. Column scope held.** `tester_review`'s invariant still passes:
  `apply_ruling`/`apply_ruling_batch` touch only `threads.project_link` +
  `threads.project_confidence` (+ the `projects` identity row);
  `apply_rejection` touches only `review_rulings`. `review_queue` is written
  by neither. Confirmed by the hermetic tester's byte-for-byte snapshot
  comparisons.

## Honest skip

- [ ] **4.1.** Without the optional web stack (`fastapi`/`uvicorn` not
  installed), `run.py review` still refuses cleanly with the install hint —
  unchanged this round, `app.available()` untouched.

---
*Ready-to-walk sheet. The results log you produce needs a uat stamp
(`docs/README.md` §3) before the pair can close.*
