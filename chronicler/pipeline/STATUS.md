# Pipeline status — handoff note

Short handoff note, **not** documentation. The authoritative reference is
`docs/ARCHITECTURE.md` (DECISIONS 0016 — the `chronicler_design_and_intent_v2.md`
referenced in an earlier brief never existed, and the question is now closed).
Design rulings live in `docs/DECISIONS.md`; the linking spec is
`docs/project_linking_skillset_spec.md`.

**State:** the ingest build is complete and the DB was frozen 2026-07-17
(schema_version 1.0-frozen, `PRAGMA user_version = 1`). Since then the work has
been in the *linking* layer, not the schema.

## What changed after the freeze (so this note stops claiming "not started")

- **S6 relink** is live and idempotent, with the S3 time signal in the score.
- **Write endpoint** (`run.py review`) is built: the narrow, column-scoped
  project-link writer (DECISIONS 0007 stage 2).
- **Registry is three-tier** — program → project → repo (DECISIONS 0012).
  `build_registry.py` no longer walks folders; it reads the **deposited
  estate.json** snapshots, which is what finally made it runnable (the old
  `L5GN/` + `MCF/` layout it scanned existed on neither machine).
- **One identifier scheme:** `threads.project_link` holds a registry `id` at
  every tier. relink and the review endpoint now write the same value; before
  this they wrote canonical_names and ids into the same column.
- **Concurrency is structural, not conventional** (DECISIONS 0014): every
  connection opens WAL + `busy_timeout` via `l5gntools/dbsafe.py`. There is no
  longer a code path that opens the vault without them.
- **The read surface serves a snapshot** (DECISIONS 0013): `run.py serve` takes a
  fresh `VACUUM INTO` copy and points Datasette `--immutable` at *that*. This
  removes the false-`malformed` class at the root.

## Still open — human, not code

- `link_ambiguous` / `link_downgrade` `review_queue` items await Tim's rulings.
- The work rig has not deposited yet, so every MCF project in the registry is
  present as a link target but has no repo facts attached. See
  `docs/PRODUCER_SETUP.md`.
- S2 vocabulary remains **off**; it is revivable with guards under DECISIONS
  0015, dry-run first.

## The pipeline scripts (in run order)

- `db.py` — schema helper + connection factory. Re-exports the shared pragma
  helper from `l5gntools/dbsafe.py`; `CHRONICLER_DB_PATH` overrides the DB
  location.
- `schema.sql` — the section-5 schema (threads / messages / attachments /
  projects / ingestion_log / review_queue / link_evidence).
- `normalize_claude.py` — Claude export → threads/messages/attachments/projects.
- `normalize_gemini_personal.py` — Takeout `My Activity.json` → messages
  (thread_id NULL until reconciled) + attachments.
- `reconcile_gemini.py` — joins scraped share skeletons against unresolved
  Takeout turns; assigns thread_id + seq.
- `group_fallback.py` — layered grouping (exact-hash → session → semantic).
  Layer C needs `sentence-transformers` and skips cleanly without it.
- `suggest_close.py` — flags threads idle 30+ days; never auto-closes.
- `render_md.py` — renders threads to `vault_staging/`.
- `build_registry.py` — S1, the registry generator (estate-driven, three-tier).
- `build_activity.py` — S3 activity windows feeding `time_plausibility`.
- `relink.py` — S6, the scoring/decision pass. Dry-run is the default.

`run_pipeline.py` runs the periodic loop; `bulk_review.py` clears the
high-confidence grouping backlog. `normalize_gemini_work` is deliberately not in
the chain (work account is closed/historical).

## Periodic workflow

1. Drop new exports into place.
2. `python run.py ingest` (backup → intake → pipeline).
3. `python pipeline/relink.py` — read the decision table, then `--apply`.
4. `python run.py review` — rule the queue from a phone on the tailnet.

## Sandbox environment gotcha (still true, don't rediscover)

The Cowork sandbox's mounted filesystem does not support SQLite file locking — a
direct write against a file on the mount throws `disk I/O error`. Workaround: set
`CHRONICLER_DB_PATH` to a `/tmp` path, run there, then copy the finished `.db`
back. The mount can also serve briefly stale reads right after a Windows-side
rename. **None of this happens on Tim's real machine** — it is a sandbox artifact.

## Leftover debris

None outstanding. `pipeline/_reconcile_gemini_verify.py` (the 12-byte stub) was
deleted in build round 3; no `_test.db` / `_lock_test.txt` / `_orphaned_*.bak`
leftovers remain in the tree.

Do NOT delete `pipeline/_presync_suggested_close.py` (kept deliberately) or
`chat_threads/vault_staging/._archived_pre_frontmatter` (the render-archive guard
marker — removing it re-triggers the one-time archive migration).
