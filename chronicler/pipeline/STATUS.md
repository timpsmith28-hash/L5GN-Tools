# Pipeline status — handoff note

**State: build complete. DB FROZEN as of 2026-07-17 (schema_version 1.0-frozen,
PRAGMA user_version = 1).** All of section 10's build spec (items 1–10, plus 4b)
is done and verified. This file is a handoff note, not documentation — the
authoritative reference is `chronicler_system_design.md` in the repo root.
(A `chronicler_design_and_intent_v2.md` was referenced in an earlier task
brief but does not exist in this repo; `chronicler_system_design.md` is the
current source of truth.)

## Freeze (this session)

`chronicler.db` is now a **read-only data store** — the contract L5GN-Tools
`vault_reader` builds against. The schema contract lives in `pipeline/SCHEMA.md`;
the DDL reference is `pipeline/schema_frozen.sql` (regenerated authoritatively by
`finalize_db.py --apply`, which dumps the live schema).

Further **linking refinement happens by re-running the evidence/relink pipeline**
(it only rewrites rows) — **not** by changing the schema. Any schema change
requires a migration script AND a `schema_version` bump, after which SCHEMA.md
and schema_frozen.sql must be regenerated.

Reverse-enrichment (S7) and drift alerts (S8) are **NOT** part of Chronicler —
they live in the toolkit's `vault_reader`. Estate/git data is the toolkit's
`estate.json`, not Chronicler. Do not add `project_trail.py`, `drift_check.py`,
or git-scanning here.

### What `finalize_db.py` did (idempotent, --apply-gated, auto-backup)

- **P1** — repaired thread-IDs that had leaked into `threads.project_link`. A
  valid `project_link` must resolve to a `projects.project_id` row (FK integrity,
  which preserves legit Claude-uuid `exact` links). Invalid ones →
  `project_link=NULL, project_confidence=NULL` + one `review_queue` row per repair
  (type `link_repair`).
- **P2** — migrated the legacy string `project_confidence='none'` → SQL `NULL`.
  Unlinked now has exactly ONE representation: `project_link IS NULL`.
- **P3** — added `threads.substantive` (INTEGER); 1 iff the thread has ≥ 4
  messages, else 0. Precomputed honesty flag separating real threads from
  Takeout-grouping fragments.
- **Stamp** — created `meta(key,value)` with `schema_version`/`frozen_at`/
  `substantive_min_messages`; set `PRAGMA user_version = 1`. Dumped
  `schema_frozen.sql`.

### Freeze runbook (run on Tim's real machine — NOT the sandbox)

Prereq: the two Session-B DB steps must already be applied — vocabulary evidence
rolled back (`DELETE FROM link_evidence WHERE signal='vocabulary'`, back to the
filename_xref/path_mention baseline) and `extract_path_mentions.py --rescan
--apply` run. Linking should stand at 150 evidence links.

```
cd <repo root>
cp chronicler.db chronicler.db.bak-$(date +%Y%m%d-%H%M%S)   # backup FIRST
python pipeline/finalize_db.py                               # dry-run: review P1/P2/P3 report + census
python pipeline/finalize_db.py --apply                       # apply migrations + stamp + dump schema
python pipeline/render_md.py --no-syncback                   # re-render; must be a clean no-op
```

Verify after apply:
- threads-by-confidence census shows `NULL` only (zero `'none'`).
- 0 invalid `project_link` (all resolve to a projects row).
- 150 `link_evidence` links; `link_evidence` has zero `signal='vocabulary'` rows.
- `substantive` populated (real-thread vs fragment split).
- `review_queue` has one `link_repair` row per P1 reset.
- `render_md.py --no-syncback` reports 0 conflicts, ~1171 threads.

### Still open — human, not this session

- ~15 `link_ambiguous` + 4 `link_downgrade` `review_queue` items await Tim's
  ruling in Obsidian (edits flow back on next render).
- Author-identity normalization is a **toolkit (`vault_reader`) concern**, not
  Chronicler's.

## The pipeline scripts (in run order)

- `db.py` — schema helper + connection factory. `CHRONICLER_DB_PATH` env var
  overrides the default DB location (see sandbox note below).
- `schema.sql` — the section-5 schema (threads / messages / attachments /
  projects / ingestion_log / review_queue).
- `normalize_claude.py` — parses `raw_claude_files/conversations.json` +
  `projects/*.json` → threads/messages/attachments/projects; exact +
  prompt_template project-linking.
- `normalize_gemini_personal.py` — parses the Takeout `My Activity.json`
  → messages (thread_id NULL until reconciled) + attachments.
- `reconcile_gemini.py` — joins `scraped_gemini/*.json` share skeletons
  against unresolved Takeout turns; assigns thread_id + seq.
- `group_fallback.py` — layered grouping (A exact-hash → B gem/idle-gap
  session → C semantic) for Takeout turns never shared/scraped. Layer C
  needs `sentence-transformers`; it skips cleanly if that isn't installed.
- `suggest_close.py` — flags `suggested_close=1` on threads idle 30+ days
  (never auto-closes; you confirm in Obsidian).
- `render_md.py` — sync-back (file→DB, file wins) then re-renders every
  thread to `vault_staging/<source>/<account>/<thread_id>.md`.

### Quality-of-life tools (added this session)

- `run_pipeline.py` — **one command for the whole periodic loop.** Runs the
  six stages above in order, one-line summary per stage, stops the chain on
  any real failure, and treats a missing input (no new Takeout, empty
  `scraped_gemini/`) as a skip rather than an error. Per-stage skip flags
  (`--skip-claude`, `--skip-takeout`, `--skip-reconcile`, `--skip-group`,
  `--skip-suggest-close`, `--skip-render`) and `--render-only` for a
  render-only pass after Obsidian edits. `normalize_gemini_work` is
  deliberately NOT in the chain — work account is closed/historical (9.2).
- `bulk_review.py` — bulk-confirms high-confidence `thread_grouping` review
  rows. `--accept-groupings --min-confidence 0.95` (dry-run by default; add
  `--apply` to commit). Writes ONE `bulk_accept` audit row per sweep, never
  touches rows a human already ruled on, and pre-syncs the affected `.md`
  frontmatter before rendering so sync-back stays a clean no-op. Reconciliation
  and close-suggestion rows are out of scope — those stay manual.

## Periodic workflow

1. Drop new exports into place (Takeout → `raw_gemini_files/`,
   Claude export → `raw_claude_files/`, share scrapes → `scraped_gemini/`).
2. `python pipeline/run_pipeline.py`
3. (Optional, one-time-ish) `python pipeline/bulk_review.py --accept-groupings
   --min-confidence 0.95 --apply` to clear the high-confidence grouping backlog.
4. Review the rest in Obsidian; edits flow back on the next render.

## Input-path convention (confirmed with Tim 2026-07-15)

Ongoing Google Takeout exports live permanently at
`chat_threads/raw_gemini_files/Takeout/My Activity/Gemini Apps/My Activity.json`.
`normalize_gemini_personal.py`'s `DEFAULT_INPUT` points there. (This replaced
the earlier one-off `raw_gemini_files_test_refresh` folder.) Pass `--input`
for a one-off run against a different drop.

## Sandbox environment gotcha (still true, don't rediscover)

The Cowork sandbox's mounted filesystem does **not** support SQLite's file
locking — a direct `sqlite3.connect()` write against a file on the `Chronicler`
mount throws `disk I/O error`, and stuck `.db`/`.db-journal` files there can't
be deleted from inside the sandbox (`Operation not permitted`). Workaround:
set `CHRONICLER_DB_PATH` to a `/tmp` path, run there, then `cp` the finished
`.db` back over the mount (plain copies work; only SQLite locking and deletion
are broken). The mount can also serve briefly stale/torn reads right after a
Windows-side rename — re-copy if a file looks corrupt in the sandbox but is
fine via the editor. **None of this happens on Tim's real machine** — it's a
sandbox artifact only.

## Leftover debris for manual deletion

Two inert files can't be removed from the sandbox (mount quirk above) — delete
from Windows Explorer whenever convenient:
- `_test.db-journal` (repo root)
- `pipeline/_reconcile_gemini_verify.py` (12-byte stub)

Do NOT delete `pipeline/_presync_suggested_close.py` (kept deliberately) or
`chat_threads/vault_staging/._archived_pre_frontmatter` (the render-archive
guard marker — removing it re-triggers the one-time archive migration).
