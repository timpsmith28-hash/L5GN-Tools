# Chronicler — Cowork tasks: post-build cleanup & quality-of-life
### Two task sets, run in order (Set A is quick, Set B is the real build)

Context for a fresh session: the build spec in `chronicler_system_design.md`
§10 is complete (items 1–10 plus 4b). These are follow-on tasks. The as-built
reference is `chronicler_design_and_intent_v2.md` — read that first if this
session has no other context; its §7 is where these tasks come from.

---

## Set A — Housekeeping (small, do first)

### A1. Refresh STATUS.md
`pipeline/STATUS.md` predates the last two build sessions — it still lists
items 5–10 as "not started" and the raw_gem_files decode as "deferred," all
of which are now done. Rewrite it to reflect the true current state: build
complete (items 1–10 + 4b), what each pipeline script does, the /tmp
SQLite-locking workaround note (keep that — it's still true of this sandbox
and worth not rediscovering), and a pointer to
`chronicler_design_and_intent_v2.md` as the authoritative reference. Keep it
short — it's a handoff note, not documentation.

### A2. Sandbox debris deletion attempt
These files are inert test/diagnostic leftovers. Attempt deletion from the
sandbox; any that fail with permission errors (known mount quirk), list at
the end of your reply for Tim to delete from Windows Explorer:
- `<Chronicler root>/_lock_test.txt`
- `<Chronicler root>/_test.db`
- `<Chronicler root>/_test.db-journal`
- `<Chronicler root>/_orphaned_chronicler.db-journal.bak`
- `chat_threads/vault_staging/_rename_test2.txt`
- `pipeline/_reconcile_gemini_verify.py` (12-byte stub)

Do NOT touch: `pipeline/_presync_suggested_close.py` (kept deliberately, has
explanatory comments), `chat_threads/vault_staging/._archived_pre_frontmatter`
(the render-archive guard marker — deleting it would cause re-archiving).

### A3. Takeout drop-folder decision — ASK, then implement
`normalize_gemini_personal.py`'s DEFAULT_INPUT currently points into
`chat_threads/raw_gemini_files_test_refresh/` — a folder named for a one-off
test. **Ask Tim** where future Takeout extractions should permanently live
(suggested: `chat_threads/raw_gemini_files/`, replacing its now-superseded
HTML-era contents — but it's his call). Then: update DEFAULT_INPUT, move the
current `My Activity.json` (+ sidecar attachment files) to the chosen home,
and note the convention in STATUS.md. Don't guess this one — wrong default
silently breaks the next ingest.

---

## Set B — Quality-of-life builds

### B1. Bulk-accept for high-confidence review items
**Problem:** 1,022 pending `thread_grouping` rows in `review_queue`; 839 are
at confidence ≥0.95. Confirming those one-by-one in Obsidian frontmatter is
pointless toil — the whole point of confidence tiers was to enable exactly
this.

**Build:** `pipeline/bulk_review.py`
- `--accept-groupings --min-confidence 0.95` → marks matching pending
  `thread_grouping` rows confirmed, sets the corresponding threads'
  `review_status: confirmed`
- `--dry-run` (default ON — must pass `--apply` to actually write): prints
  what would change, count + a 10-row sample, so Tim can eyeball before
  committing
- Every bulk action writes ONE summary row to `review_queue` (type
  `bulk_accept`, listing criteria + count) — the audit trail must show a
  human ran a bulk-accept with these parameters, not silently mutate 839 rows
- Must respect the override rule: rows already confirmed/rejected/reassigned
  by hand are never touched, regardless of criteria
- After DB update, run the standard render so frontmatter reflects the new
  review_status values (sync-back safety: these fields flow DB→file here
  because the human action *was* the CLI invocation — same authority as an
  Obsidian edit)

**Explicitly not in scope:** auto-accepting `reconciliation_gap`,
`reopen_candidate`, or `close_suggestion` rows — those are individually
meaningful and stay manual.

### B2. Single pipeline runner
**Problem:** the periodic loop is currently five manual script invocations in
the right order. Should be one command.

**Build:** `pipeline/run_pipeline.py`
- Runs, in order: `normalize_claude` → `normalize_gemini_personal` →
  `reconcile_gemini` → `group_fallback` → `suggest_close` → `render_md`
- (Note: `normalize_gemini_work` is NOT in the chain — closed historical
  corpus, per design §9.2)
- Per-stage skip flags (`--skip-claude`, `--skip-takeout`, etc.) for partial
  runs — e.g. a render-only pass after Obsidian edits is just
  `run_pipeline.py --render-only` (or skip-everything-else; pick the cleaner
  CLI shape and document it)
- Each stage: print a one-line summary (rows new/changed/skipped, from the
  same numbers the ingestion_log row gets); on stage failure, STOP the chain
  with a clear message — never continue past a failed normalize into
  reconcile/render (loud-failure principle, design §1)
- Idempotency is already guaranteed per-script; the runner adds nothing
  clever, it's pure orchestration + ordering + stop-on-failure
- Missing input files (e.g. no new Takeout since last run) = skip that stage
  with a note, NOT a failure — the common case is "re-run everything, only
  some sources have new data"
- Update STATUS.md's workflow section once this exists: the documented
  periodic loop becomes "drop exports in → `python pipeline/run_pipeline.py`
  → review in Obsidian"

**Acceptance for both:** run against the real DB/vault (or the /tmp mirror
pattern if the mount still blocks SQLite locking), show before/after counts,
confirm zero sync-back conflicts on the follow-up render, and confirm a
second identical invocation is a clean no-op.

---

## Parked (do NOT start — Tim is deciding when/whether)
- Copilot or any new source normalizer
- Local web UI for review
