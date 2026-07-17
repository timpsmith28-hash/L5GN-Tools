# Chronicler schema contract (FROZEN)

**Schema version `1.0-frozen` (PRAGMA `user_version` = 1).** This is the contract
L5GN-Tools `vault_reader` builds against. `chronicler.db` is a read-only data
store from here on: linking is refined by re-running the evidence/relink pipeline
(which only rewrites rows), never by changing the schema. Any schema change
requires a migration script **and** a `schema_version` bump, after which this
document and `schema_frozen.sql` must be regenerated (`finalize_db.py --apply`
dumps the live schema).

Reverse-enrichment (S7) and drift alerts (S8) are **not** part of Chronicler —
they live in the toolkit's `vault_reader`. Estate/git data is the toolkit's
`estate.json`, not Chronicler.

## Load-bearing conventions (read these first)

1. **Unlinked is `threads.project_link IS NULL`.** There is exactly one
   representation. The legacy string `'none'` in `project_confidence` has been
   migrated to SQL `NULL`; do not test for `'none'`.
2. **Confidence authority, low → high: `NULL` < `fuzzy` < `evidence` < `manual`.**
   `'exact'` is source-native (a link the source system asserted) and, like
   `'manual'`, is never overwritten by automation. Automation may upgrade
   `fuzzy` → `evidence`; only a human may change an `evidence` link. A valid
   `project_link` always resolves to a `projects.project_id` row (which may be a
   registry canonical_name or a source-native project uuid).
3. **`threads.substantive` = 1 iff the thread has ≥ 4 messages**, else 0. This is
   a precomputed honesty flag so consumers can separate real threads from
   Takeout-grouping fragments without counting messages per query. Any future
   ingest must set it (or re-run `finalize_db.py --apply` to repopulate).

## Tables

**projects** — one row per known project. `project_id` (PK) is either a registry
canonical_name (written by `relink.py`) or a source-native project uuid (written
by `normalize_claude.py`); `name` is the display name; `repo_folder_path` and
`source_system_id` are optional provenance. `threads.project_link` is a foreign
key into this table.

**threads** — one row per conversation. Key columns: `thread_id` (PK, source
uuid or synthetic), `source` (claude/gemini), `account` (e.g. gemini-personal),
`title`, `created_at`/`updated_at`, `gem_name`/`is_custom_gem`, `status`
(open/closed) + `closed_at`, `project_link` (FK → projects, NULL when unlinked),
`project_confidence` (NULL/fuzzy/evidence/manual/exact — see convention 2),
`review_status` (auto/confirmed/pending), `raw_ref`, `parser_version`,
frontmatter fields `review_note`/`suggested_close`/`tags` (JSON array),
`link_evidence_ids` (JSON array of the `link_evidence.evidence_id` values that
justify the current link; NULL if never re-linked), and `substantive` (see
convention 3).

**messages** — one row per turn. `message_id` (PK), `thread_id` (FK, nullable
until a Gemini turn is reconciled), `seq` (order within thread), `role`
(user/assistant/activity_log), `content`, `created_at`, `source_turn_hash`
(attachment-batch join anchor).

**attachments** — `attachment_id` (PK), `message_id` (FK, nullable until linked),
`filename`, `turn_hash`, `file_path` (archived location), `mime`,
`extracted_content` (Claude's inline extraction — a strong project-link signal).

**ingestion_log** — one row per import batch: `batch_id` (PK), `source`,
`account`, `file_hash`, `imported_at`, `rows_new`/`rows_changed`/`rows_skipped`,
`parser_version`.

**review_queue** — human-review items. `item_id` (PK), `type`
(thread_grouping/project_link/reopen_candidate/close_suggestion, plus
`link_upgrade`/`link_ambiguous`/`link_downgrade` from relink and `link_repair`
from the finalize pass), `thread_id`, `candidate_thread_id`, `confidence`,
`status` (pending/confirmed/rejected/reassigned), `note`, `created_at`,
`resolved_at`.

**link_evidence** — the evidence model behind every automated link. One row per
(thread, project, signal) contribution: `evidence_id` (PK), `thread_id`,
`project` (canonical_name), `signal` (`name_alias`/`filename_xref`/`path_mention`
/`time_window`), `weight` (0..1), `detail` (matched basename/alias/path),
`produced_at`, `producer_version`. `relink.py` combines these into decisions.
(The `vocabulary` signal was evaluated and **dropped** — it degraded linking — so
no `vocabulary` rows exist; `build_vocabulary.py` remains on disk unused.)

**path_scan_log** — single-row watermark for `extract_path_mentions.py`
(`scanned_through` = highest `messages.rowid` scanned) so path extraction is
incremental.

**render_log** — per-thread snapshot of last-rendered editable fields
(`thread_id` PK, `rendered_fields` JSON, `rendered_at`), the 3-way base that lets
`render_md.py` sync-back distinguish a real Obsidian edit from a stale default.

**meta** — key/value schema stamp: `schema_version`, `frozen_at`,
`substantive_min_messages`. `vault_reader` should assert `schema_version` (and/or
`PRAGMA user_version`) before reading.
