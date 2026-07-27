<!-- gate-frozen: commit=26079ed -->

# UAT walk-sheet — Command Deck prototype (project-grouped queue, batch rulings)

Pair: `docs/COWORK_BRIEF_command_deck_proto.md` → `docs/COWORK_REPORT_command_deck_proto.md`.
Built on `26079ed` (0024 ratified), plus the existing-vault-migration
follow-up. Gate at build time: `python verify.py` **GREEN**, 6 auditors +
**46** testers (frozen build-time count). Mark each check **ready to walk**,
never "passed" — the walk is Tim's.

Nothing is committed from this round yet. These check staged changes.

Two rounds of proof already done this session, distinct from Tim's walk:
hermetic testers (`tests/tester_review.py`, `tests/tester_relink_apply.py`,
`tests/tester_backfill_candidate_project.py`) prove the write-path invariants
against synthetic sqlite fixtures, and a one-off `TestClient` smoke test
(not part of the gate) exercised every endpoint end-to-end against a
throwaway seeded DB. Neither substitutes for walking the real dev vault —
they're noted per-item below where they cover part of the ground.

## Task 1 — structured candidate

- [x] **1.1. Migration works live; the backfill's real job is untested.**
  Walked on the dev vault 2026-07-27: the script runs instead of throwing
  `no such column: candidate_project`, so `db.ensure_deck_schema` migrates a
  real pre-existing vault in place. **But it reported 0 rows** — the dev vault
  had no `project_link`/`link_ambiguous`/`link_downgrade` rows at all, because
  the solo-playbook walk only ever ran `relink` in dry-run there. So the
  migration half is walked and the note-parsing half is **not exercised**.
- [ ] **1.2. The note-parsing recovery, against real notes.** Still open, and
  it is the item that matters for the knight — the live vault's rows predate
  the columns and can only be recovered from `note` prose. Reproduce that
  condition on dev after a relink apply:
  `UPDATE review_queue SET candidate_project=NULL, rival_project=NULL`, then
  dry-run the backfill and read the resolved/unresolved split. Until this is
  walked, the regex has never met a real note.
- [x] **1.3. Relink writes the columns going forward.** `relink.py --apply`
  walked on the dev vault; the deck's grouping, counts and rival badges are all
  driven by `candidate_project`/`rival_project` written by that run.
- [x] **1.4.** `run.py review` opens against the migrated dev vault — walked,
  bound on `0.0.0.0:8002`, 61 link-target ids loaded, UI served.
- [ ] **1.5.** Against a deliberately unmigrated copy of the vault,
  `run.py review` refuses cleanly (exit 2) naming
  `backfill_candidate_project.py` as the fix, rather than a stack trace.
  *(Smoke-tested directly against a synthetic pre-deck DB — confirmed exit 2
  and the exact remedy text; needs walking against a real unmigrated copy.)*

## Task 2/5/6 — the wall becomes a list of walls

- [x] **2.1.** Walked on the dev vault: **29 projects with pending threads**,
  each with its own count and breadcrumb in the left nav; picking one loads
  only its batch. Tim's read: *"that definitely feels easier and already it
  sharpens the view and mind properly."*
- [x] **2.2. The rival case.** Walked on real data — e.g. *"Building a
  terminal-based D&D world for Discord"* appears under `build-it-yourself`
  marked **rival candidate** (orange border + badge), with
  `l5gn-crystal-spire` as its scored primary.
- [ ] **2.3. Work is unreachable, not merely unshown.** **Cannot be walked on
  this vault** and should not be claimed from it: the dev vault contains only
  `gemini-personal` (1062) and `claude-personal` (39) accounts — there is no
  work-account thread to be excluded, so a clean result here proves nothing.
  Covered structurally (the SQL has no path that returns a non-personal row;
  DECISIONS 0023), by the hermetic tester and by the smoke test (`TWORK`).
  **The real walk for this is the work rig**, against a vault that actually
  holds both.

### UI affordances (added during the walk, 2026-07-27)

- [x] **2.4. The project nav scrolls independently.** With 29 projects the nav
  ran past the fold, forcing a scroll down to pick a project and back up to
  read its batch. `#nav` is now `position: sticky` with its own `overflow-y`
  and `max-height: calc(100vh - 2rem)`; static again under the 45rem
  breakpoint, where the nav sits above the batch and pinning would eat the
  viewport. Walked.
- [x] **2.5. Rival tag as a one-click ruling.** An ambiguous row now carries a
  `→ <other candidate>` button beside "Not this project", rendered **only**
  where a second scored candidate exists (`link_ambiguous`), so it can never
  offer a target relink didn't score. It reuses the existing single-thread
  `POST /api/rule` — same validated write, same `manual` confidence — so one
  click resolves the thread in **both** candidates' batches. Walked
  (`POST /api/rule` 200, row cleared, nav counts refreshed).

## Task 3/4 — rulings

- [~] **3.1. Batch accept — half walked.** `POST /api/rule/batch` walked on the
  dev vault (200, rows cleared, nav counts refreshed). The **second half is
  still open**: re-run `relink.py` and confirm the accepted threads are skipped
  (`skip_manual`) rather than re-queued. That is the half that proves the write
  is also the lock.
- [ ] **3.2. Partial failure is visible.** An invalid id inside a batch
  reports per-thread (`{"ok": false, "error": …}`) rather than silently
  succeeding or failing the whole batch. *(Smoke-tested directly against
  synthetic data: one good + one bad pair in the same request, good one
  committed, bad one reported. Not reproduced in the browser — it needs a
  deliberately bad id, so it may stay tester-covered.)*
- [x] **3.3. Rejection clears, and the rival stays live.** Walked 2026-07-27 —
  both routes exercised on real data: "Not this project" clears the row from
  that batch without touching the other candidate's, and the `→ <other>` tag
  rules it across. Confirmed by Tim at the deck.
- [ ] **3.4. Column scope held.** `tester_review`'s invariant still passes:
  `apply_ruling`/`apply_ruling_batch` touch only `threads.project_link` +
  `threads.project_confidence` (+ the `projects` identity row);
  `apply_rejection` touches only `review_rulings`. `review_queue` is written
  by neither. Confirmed by the hermetic tester's byte-for-byte snapshot
  comparisons.

## Honest skip

- [x] **4.1.** Walked — incidentally, and for real. On the dev rig the web
  stack genuinely wasn't installed, and `run.py review` refused with
  `"FastAPI/uvicorn are not installed. They are an OPTIONAL extra, kept out of
  the stdlib-only core: pip install -e .[review]"` before doing anything else.
  Not a simulated skip: the actual condition, hit unplanned.

---

## Still open after 2026-07-27

1. **1.2** — the backfill's note-parsing against real notes. The one that
   blocks trusting this on the knight.
2. **3.1 second half** — relink skips accepted threads on re-run.
3. **1.5** — clean refusal against a real unmigrated vault copy.
4. **2.3** — the wall, walkable only where a work-account thread exists.
5. **3.2** — partial-failure surfacing in the browser (may stay tester-covered).

*Ready-to-walk sheet. The results log needs a uat stamp
(`docs/README.md` §3) naming the commit walked, before the pair can close —
so the sheet's ticks above are evidence to transcribe into that log, not the
log itself.*
