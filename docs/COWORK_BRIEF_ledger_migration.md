# Cowork brief — Phase 2: the ledger — chronicler.db grows event tables, DECISIONS.md inverts to a render

**Origin:** `docs/investigation/2026-08-17_quartermaster_fable_2-response.md` Phase 2; Tim's substrate ruling of
2026-08-17 (chronicler as the ledger's home).
**Precondition — two, both hard:** (1) Phase 1's falsifier answered **yes**
in its stamped results — this round does not start on an unproven card
mechanic. (2) **A walked backup-and-restore of the live vault**:
`l5gntools/backup.py` already takes atomic `VACUUM INTO` snapshots
(`vacuum_into`, `make_backup`, off-box push) — what has never been walked is
the *restore*. Before any migration code: take a snapshot, restore it on
another machine or path, open it, run `vault_reader` against it green. The
restore walk is recorded in the report. No walk, no round.
**Depends on — this repo's rulings:** **0033** (propose/ratify/execute),
**0034** (package boundaries; the ledger writer lives with the other
writers, never in `l5gntools/`), the frozen-vault contract as stated in
ARCHITECTURE §5/§6 (readers open `mode=ro` and refuse an unexpected
`user_version` — this round is that contract *doing its job*, not an
exception to it), DECISIONS **0002/0008** (render is DB→file, one-way — the
precedent D-D generalises), **0044** (`data/knowledge_curator/` posture for
new data directories).
**Ratify before code:** **D-C** and **D-D** from the plan, as full DECISIONS
entries (0048+; draft text in `docs/investigation/2026-08-17_quartermaster_fable_2-response.md`, tightened against
this brief).
**Deliverable:** `chronicler.db` extended by governed migration with an
append-only `events` table family (facts, rulings, runs, costs, spend, each
with mandatory provenance); every reader's version guard updated in the same
round; `DECISIONS.md` inverted to a one-way render of ruling events, with
the existing 0001–0047 history parsed in under human verification; Phase 1's
`data/desk/events.jsonl` migrated; run/cost events flowing from the wizard
and conductor runners.

---

## What already exists — verified 2026-08-17

- `l5gntools/backup.py` — `vacuum_into` (read-lock only, atomic),
  `list_snapshots`, `prune_snapshots`, `push_command`, `make_backup`. The
  precondition's tooling is built; only the restore walk is new.
- `chronicler/pipeline/schema_frozen.sql` at a stamped `user_version`;
  `l5gntools/dbsafe.py` and every estate reader
  (`vault_reader`, `project_trail`, `drift`, `viewer`) enforce the guard.
- `chronicler/review/core.py` — the narrow-write precedent: single-writer
  preserved by **column/table scope**, not a lock. The events writer extends
  this pattern, not the pipeline.
- `finalize_db.py` writes `meta`; migrations have a precedent shape in
  `migrate_s6.py` / `deck_migration` (tested).
- Phase 1's `data/desk/events.jsonl` — the seed corpus, and the proof of
  which event fields real use actually needed.

## Working rules

- **The irreplaceable tables are untouched.** `threads`, `messages`,
  `attachments` — no ALTER, no UPDATE, no new writer. The migration only
  *adds* tables and bumps `user_version`. A diff of those three tables'
  content before/after the migration is empty, and the report proves it.
- **Append-only means append-only.** No UPDATE or DELETE on event tables,
  structurally: correction is a superseding event citing the corrected one,
  the same recency-resolves discipline 0046 already established for the
  curated map.
- **Provenance columns are NOT NULL.** An event without an actor, a source,
  and a timestamp cannot be inserted. Fail loud beats a mystery fact.
- **One writer per table set**, extended by scope: the pipeline keeps its
  tables; `review/core.py` keeps its ruling columns; the new events writer
  (one module) owns the event tables and nothing else. Three disjoint
  scopes, zero locks, same proof as before.
- **Version guards move in lockstep.** Every reader's expected
  `user_version` updates in the same commit series as the migration; at no
  commit does a green gate contain a reader that would misread the new
  schema. A refusal is correct behaviour; a misread is the incident.
- **DECISIONS.md becomes output.** After inversion, the file carries a
  generated header (the `_architecture_shape.md` convention, DECISIONS
  0030's shape/rationale split applied to rulings) and hand-editing it is a
  defect. Authoring goes through the entry path.
- UTF-8 explicit, UTC ISO-8601.

## Task 1 ▸ the schema and the migration

- Design the `events` family small: one `events` table
  (`event_id` PK, `kind` in {fact, ruling, run, cost, spend}, `ts`, `actor`,
  `source`, `payload` JSON, `supersedes` nullable FK) plus one `event_cites`
  join table (event → event, and event → ruling number for the parsed
  history). Resist per-kind tables until a kind's queries demand it —
  document the choice either way.
- `chronicler/pipeline/migrate_ledger.py`: asserts current `user_version`,
  adds tables, bumps the version, writes a `meta` row naming this migration
  and its producing commit. Idempotent to re-run (asserts, then no-ops).
  Refuses to run at all unless a snapshot newer than the working tree's
  HEAD commit time exists in the backup dir — the precondition enforced in
  code, not remembered.
- Update every reader's guard; extend `dbsafe`'s helpers rather than
  scattering the new version literal.

## Task 2 ▸ the events writer

- One module (`chronicler/review/ledger.py` or sibling — decide at build,
  record why) exposing narrow append functions per kind. No general
  `execute` surface. The wizard's `write_run_marker` call sites and the
  conductor's per-step outcome path gain one call each: run events (stage,
  outcome, wall-clock) and cost events (tier when known). Markers stay for
  now — removal is a later cleanup, not a this-round risk.
- Migrate `data/desk/events.jsonl` in: sightings and rulings become events
  with their original timestamps and `source: "desk-v1-sidecar"`. The Desk's
  read/write path switches to the ledger; the sidecar is archived, not
  deleted.

## Task 3 ▸ the DECISIONS inversion

- **Parse 0001–0047 into ruling events, human-verified entry by entry.**
  The parser proposes; a review pass (the Desk is allowed to serve this —
  one verification card per entry — if it is cheaper than a checklist,
  builder's call) confirms each entry's number, title, date, status, and
  body landed intact. Not sampled — *every* entry; this history is the
  estate's crown jewels and a parser is not trusted with them unreviewed.
- `render_decisions.py`: events → `DECISIONS.md`, one-way. **Byte-stability
  is the acceptance bar**: the render of the parsed history diffs empty (or
  whitespace-trivially, each difference itemised) against the hand-written
  file at the moment of inversion.
- The authoring path: a small CLI (`run.py decision new/supersede`) or a
  deck form — builder's call, recorded. It writes the event; the render
  regenerates the file; the pre-commit gate gains an auditor check that the
  committed `DECISIONS.md` matches its render (the
  `auditor_architecture_current` pattern applied to rulings).

## Explicitly out of scope

- Policies, promotion, tiers, envelopes — Phase 4. The ledger *records*
  spend events if something writes them; nothing budgets yet.
- Any change to what the pipeline ingests or how linking works — Phase 3.
- Retiring run markers, or any consumer rewrite beyond version guards.
- Mesh implications. The ledger is this machine's, same as the vault (0036).

## Stop conditions

- Migration attempted without the walked restore recorded → stop.
- Any write, however small, to `threads`/`messages`/`attachments` content →
  stop.
- An UPDATE or DELETE path on event tables → stop; supersede instead (0046's
  discipline).
- A reader at any commit that would *misread* rather than refuse the other
  schema version → stop.
- The parsed history lands with any entry unverified by a human → stop.
- The inversion's render is not byte-stable against the hand-written file
  and the differences are not itemised and accepted one by one → stop.
- `DECISIONS.md` is hand-edited after inversion (outside the render) → stop;
  the auditor exists to make this loud.
- A second events writer appears outside the one module's scope → stop.

## UAT — acceptance checks (Tim walks these)

- `[H]` **The restore walk, done by you**: snapshot, restore, open, reader
  green. You are the one who needs to believe the vault is safe.
- `[G]` Old reader + new DB, and new reader + old snapshot: both **refuse
  loudly** with the stated remedy; neither misreads.
- `[G]` The three irreplaceable tables diff empty across the migration.
- `[G]` An event without actor/source/ts refuses at insert.
- `[G]` The inversion render diffs empty against hand-written DECISIONS.md;
  the gate fails a hand-edit to the rendered file.
- `[H]` **Author one real ruling through the new path** end to end. Is it
  cheaper than editing markdown was? If it is not, that finding outranks
  the feature — an authoring path with more friction than the file it
  replaced will get routed around (INTENT §5, graduated rigor).
- `[H]` **Spot-read five parsed historical entries of your choosing**
  against your memory of them, beyond the mechanical verification.
- `[G]` Desk cards still derive and rule correctly against the ledger; the
  latency footer survives the migration with history intact.

Results log needs a `uat` stamp naming the commit; do not write a `gate=`
field.

## Reporting

`docs/COWORK_REPORT_ledger_migration.md`, walk-sheet
`docs/UAT_ledger_migration.md`, stamped results.

Record: the restore walk; D-C/D-D as ratified with final numbers; the schema
as landed and the per-kind-table decision; the byte-stability diff outcome
itemised; where the events writer lives and why; the authoring path's
friction verdict; and the migration's before/after `user_version` pair.
