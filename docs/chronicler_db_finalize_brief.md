# Chronicler — DB finalize & freeze (final session)

The goal of this session is to leave `chronicler.db` in a clean, honest, frozen
state that L5GN-Tools' `vault_reader` (toolkit Phase 3) can consume read-only.
This is the LAST Chronicler build session — S7/S8 are explicitly NOT built here
(they move to the toolkit; see "Scope boundary" below).

Read `chronicler_design_and_intent_v2.md` for context. Current state: linking
engine complete and applied (150 evidence links), render runs clean with
`--no-syncback`. What remains is three data-quality fixes + a schema freeze.

## Scope boundary (important — do NOT overbuild)

- **IN scope:** P1, P2, P3 below (DB hygiene), then a schema-freeze confirmation.
- **OUT of scope, deliberately handed to L5GN-Tools `vault_reader`:** S7
  (reverse-enrichment into Intent/Contents) and S8 (drift alerts). Chronicler is
  now purely a data store that freezes and gets *read*; it does not reach back
  out to write nav docs. Do not add `project_trail.py`, `drift_check.py`, or any
  Intent/Contents integration to Chronicler. If you see references to S7/S8 in
  older briefs, they are superseded by this decision.
- Chronicler also does NOT own estate/git data — that comes from the toolkit's
  `estate.json`. Do not add git-scanning to Chronicler.

## P1 — Repair thread-IDs leaked into project_link

Some early fuzzy links stored a thread_id (uuidv7 shape,
e.g. `019f4273-ae70-75ff-...`) in `threads.project_link` instead of a project
name. Confirmed bad values: `019f4273-...` (6 threads), `019edceb-...` (1),
`019e6a8b-...` (1).

- A valid `project_link` MUST be a known registry canonical_name. Any value that
  isn't (uuidv7 shape or otherwise unmatched) is invalid.
- Fix: set those rows `project_link=NULL, project_confidence=NULL`; log one
  `review_queue` row per repaired thread (type `link_repair`, note explaining
  the reset) so they re-enter normal review.
- Backup first (`cp chronicler.db chronicler.db.bak-<ts>`), print before/after
  counts, do NOT touch valid links.

## P2 — Normalize the two unlinked states

`project_confidence` currently holds BOTH SQL `NULL` (~885) and the string
`'none'` (~128) meaning the same thing. Migrate to ONE canonical form —
**use `NULL`** (what fresh threads get) — updating all `'none'` rows to `NULL`.

- After migration, confirm no `'none'` string values remain.
- This must not disturb `evidence` / `manual` / `exact` / `fuzzy` values.
- Note for downstream: after this, "unlinked" is unambiguously `project_link IS
  NULL`. Document this in a one-line schema comment so `vault_reader` relies on
  the single representation.

## P3 — Thin-thread flag (reporting honesty, no deletion)

The gemini-personal corpus is 1026 threads, but many are 1-2 message fragments
from the Takeout grouping fallback. Add a persistent, computed marker so
consumers can distinguish substantial threads from fragments WITHOUT re-counting
messages every query.

- Add column `threads.substantive` (INTEGER/bool), set `1` where the thread has
  `>= 4` messages, else `0`. (4 is the agreed cut; document it.)
- Populate it once now; note in a schema comment that any future ingest must set
  it (or a trigger/rebuild step maintains it).
- No deletion, no merging — fragments stay, just flagged.

## Schema freeze

After P1-P3:

1. Dump the final schema (`.schema` / `sqlite_master`) to
   `pipeline/schema_frozen.sql` with a header comment: version tag, date, and
   "FROZEN — vault_reader consumes this; changes require a migration + bump."
2. Add a `schema_version` value (e.g. a one-row `meta` table or PRAGMA
   user_version) so `vault_reader` can assert the schema it expects.
3. Produce a short `pipeline/SCHEMA.md` — one paragraph per table, the column
   list, and the two load-bearing conventions consumers must know:
   (a) unlinked = `project_link IS NULL`; (b) confidence authority order
   none/NULL < fuzzy < evidence < manual, 'exact' source-native; (c)
   `substantive` flag meaning. This is the contract vault_reader builds against.

## Verify & hand off

- `python pipeline/render_md.py --no-syncback` — confirm still clean, thread
  count unchanged (~1171), 0 sync-back conflicts, evidence links still 150.
- Print final table census: threads by confidence (should show NULL only, no
  'none'), evidence-link count, substantive vs fragment counts, review_queue by
  type (link_repair rows from P1 now present).
- Leave `chronicler.db` and `pipeline/schema_frozen.sql` + `SCHEMA.md` in place.
  Note in STATUS.md: DB is FROZEN as of this session; further linking refinement
  happens via re-runnable relink (evidence rows), not schema change; S7/S8 live
  in L5GN-Tools vault_reader now.

## Still-open (human, not this session)
- ~15 ambiguous + 4 downgrade review_queue items awaiting Tim's hand-ruling in
  Obsidian (data decisions, no schema impact — can happen anytime post-freeze).
- Author-identity normalization (`timpsmith28-hash` vs `L5GN` on smelt-gateway
  commits) is a TOOLKIT concern (estate/git data), not a Chronicler one — noted
  here only so it isn't lost; do not action in Chronicler.

## Environment reminders
- Sandbox can't SQLite-lock (/tmp copy pattern) and serves stale/torn reads of
  freshly-edited files (verify via Read tool). The real chronicler.db is healthy
  and lives on Tim's work rig — DB-mutating steps (P1-P3) likely run there.
- Backups before every mutating step.
