# Chronicler — System Design Reference (v1 consolidation)

Everything agreed so far, in one place, for review before we build the reconciliation piece.

---

## 1. Goal

A unified, enriched archive of chat history across LLM tools (Claude, Gemini — work
+ personal accounts — with Copilot etc. in mind for later), linked to the GitHub
project folders they relate to, browsable as clean `.md` files, with the real,
queryable data living in a structured store rather than the files themselves.

---

## 2. Sources & formats

| Source | Account | Export method | Native ID? | Status |
|---|---|---|---|---|
| Claude | (single, so far) | `conversations.json` full export | Yes — stable `uuid` | Solved. Full snapshot each time, includes `updated_at`. |
| Claude Projects | (single, so far) | `projects/*.json` in same export | Yes — project `uuid` | Solved. No direct FK to conversations, but `prompt_template` text-matches the first message of linked threads. |
| Gemini | Work | Share-export (binary, DC2-separated) → scraped via public share links | No native ID | **Solved this session** — `scrape_gemini_share.py`, DOM-based, produces clean per-conversation JSON with correct turn order. |
| Gemini | Personal | Google Takeout, JSON format, `My Activity.json` | No conversation/thread ID at all — only a stable per-turn attachment-hash (~23% of turns) and a unique millisecond timestamp (100% of turns) | Confirmed complete + accurate content, richer than HTML (has response bodies). **Grouping into conversations is the unsolved piece** — that's the reconciliation work next. |

Confirmed via testing: Gemini work-account and personal-account conversations are
**genuinely exclusive sets** — no real duplication (the one apparent overlap traced
to a screenshot-transcription artifact, not duplicate conversations).

---

## 3. Storage model

**SQLite is the source of truth.** `.md` files in `vault_staging` are a *generated,
Obsidian-browsable view* — never hand-edited directly. Any manual correction (tags,
project links, thread grouping, notes) goes through a review step that writes back
to the DB, so regenerating `.md` never loses anything.

---

## 4. Pipeline stages, end to end

```
1. INGEST        — new export/scrape lands in raw_<source>_files, gets archived (not overwritten)
2. NORMALIZE     — per-source parser → unified Thread/Message JSON → written into SQLite
3. RECONCILE     — [Gemini only] join share-scrape skeletons against Activity turns by
                    fingerprint + timestamp, to inherit correct thread boundaries/order
4. GROUP         — for any turns not resolved by step 3, layered heuristics attempt
                    grouping, each layer with a confidence score
5. LINK          — project-linker matches threads to GitHub repo folders
                    (exact match for Claude, fuzzy for Gemini)
6. REVIEW (HITL) — anything below a confidence threshold surfaces for confirmation
7. RENDER        — .md regenerated in vault_staging from current DB state
```

---

## 5. Data model (SQLite)

**threads**
`thread_id` (PK, source-native uuid where available else synthetic) · `source`
(claude/gemini) · `account` (work/personal — modeled separately from source) ·
`title` · `created_at` / `updated_at` (UTC) · `gem_name` · `is_custom_gem` ·
`status` (open/closed) · `closed_at` · `project_link` · `project_confidence`
(exact/fuzzy/manual/none) · `review_status` (auto/confirmed/pending) · `raw_ref`
(path back to source file) · `parser_version`

**messages**
`message_id` (PK) · `thread_id` (FK) · `seq` · `role` · `content` · `created_at` ·
`source_turn_hash` (the 16-hex attachment-batch id, secondary join anchor)

**attachments**
`attachment_id`/hash (PK) · `message_id` (FK, nullable until linked) · `filename` ·
`turn_hash` · `file_path` (archived location) · `mime`

**projects**
`project_id` · `name` · `repo_folder_path` · `source_system_id` (e.g. Claude project uuid)

**ingestion_log**
`batch_id` · `source` · `account` · `file_hash` · `imported_at` · `rows_new` /
`rows_changed` / `rows_skipped` · `parser_version`

**review_queue** (the HITL surface)
`item_id` · `type` (thread_grouping / project_link / reopen_candidate) ·
`thread_id` / `candidate_thread_id` · `confidence` · `status` (pending/confirmed/
rejected/reassigned) · `created_at` / `resolved_at`

---

## 6. Every HITL touchpoint (explicit)

This is everything that still needs *you*, mapped to the pipeline stage it belongs to:

| # | Touchpoint | Stage | Frequency |
|---|---|---|---|
| 1 | Trigger Claude export download | Ingest | Periodic, manual |
| 2 | Trigger Google Takeout (JSON, Gemini Apps) | Ingest | Periodic, manual |
| 3 | **Gemini work-account share-link workflow**: open convo → three-dot menu → Share conversation → paste URL into batch file → run scraper → spot-check `manifest.jsonl` → un-share the link | Ingest | Ongoing, batches of ~10 |
| 4 | Confirm/reject fuzzy project-links (Gemini; Claude's exact-match ones likely auto-accept) | Link → Review | Per new thread, low-effort |
| 5 | Confirm/reassign uncertain thread groupings (Gemini personal, anything below confidence threshold) | Group → Review | Per new/ambiguous thread |
| 6 | **Declare a thread "closed"** — deliberate decision that it's finished | Review | Whenever you decide |
| 7 | **Confirm a "possible reopen" of a closed thread** — system never silently reattaches, always asks | Review | Rare, only on resembling new turns |
| 8 | Add tags / notes to a thread (protected from being overwritten by re-runs) | Review, anytime | Ad hoc |

Everything else (parsing, joining, deduping, rendering) is mechanical and doesn't need you.

---

## 7. Open questions — need a decision or confirmation before reconciliation work starts

1. **HITL interface** — what should the review surface actually *be*? Options: (a) a plain file you hand-edit (JSON/markdown with a defined convention), (b) a small local web UI reading the SQLite file directly, (c) frontmatter fields you edit in the rendered `.md` with a defined sync-back convention. This materially changes how much building is needed — pick one to prioritize.

2. **Gemini work-account, going forward** — is the share-link scrape meant to be your *permanent* ongoing method for new work-account conversations too, or is it worth 5 minutes checking whether your Workspace admin settings allow a proper Takeout export for that account (would remove the manual share/unshare cycle entirely for future conversations, even if backfill still needs the scrape)?

3. **Semantic-similarity clustering** (the weakest/last-resort grouping layer) needs embeddings. Local model (e.g. sentence-transformers, stays entirely on your machine) vs an API-based embedding service (faster/better quality, but sends conversation text — some of it work-sensitive — off-device)? Given the content mix, I'd lean local-only unless you say otherwise.

4. **Fingerprint-matching threshold** for the skeleton↔Activity join (exact substring vs fuzzy distance) — not urgent, will tune empirically, just flagging it's a real tunable, not a solved constant.

5. **Second accounts elsewhere** — same pattern as Gemini work/personal: is there (or will there be) a second Claude account, or any other split account situation, that the schema should assume now rather than retrofit later?

6. **Attachment scope for v1** — currently deferred (share-scrape only pulls text, not attachment filenames/content). Given attachments like `tui.py` are a strong *project-link* signal (it's literally named after the repo it belongs to), is this worth pulling into scope now rather than later?

7. **Raw export archiving convention** — agreed principle is "archive, don't overwrite." Want a specific folder convention (e.g. `zip_downloads/archive/<date>/`), or should I just design one?

8. **Close-out granularity** — per-thread only, or also a bulk sweep ("close everything untouched for 60+ days") given the size of the existing backlog?

---

## 8. Open questions — Responses

1. **HITL interface** — working through an editable `.md` seems the easy approach for now (via Obsidian, which allows direct view/edit of `.md`) — a nice local web UI would be nice but that can be figured out at the end. `.md` route it is, accepting the external Obsidian dependency for now.
2. **Gemini work-account, going forward** — the `raw_gem_files` scrapes are a **one-off, now complete** backfill of personal-project-relevant work-account conversations. Going forward, work-account Gemini use is pure web-search, out of scope. Going forward = Takeout data (personal account) **paired with share-links on that same account**, to align thread order.
3. **Semantic-similarity clustering** — sentence-transformers, installed and run locally.
4. **Fingerprint-matching threshold** — proceed as planned (tune empirically).
5. **Second accounts elsewhere** — yes, assume multiple accounts per platform are possible, and that work/personal accounts on the same platform may even need genuinely different ingestion methods (as already true for Gemini).
6. **Attachment scope for v1** — Gemini attachments are already fairly accessible; Claude's turned out **richer than expected** (see 9.6 below) — bring both into v1 scope.
7. **Raw export archiving convention** — delegated: "make what works for you" (see 9.7).
8. **Close-out granularity** — add a suggested-close signal: threads with no activity for 30+ days get flagged as *close candidates*, surfaced for confirmation rather than auto-closed.

---

## 9. Resulting design updates

**9.1 — HITL via Obsidian `.md`, with a real sync-back convention**
Since `.md` becomes an *edit* surface (not just a view), rendering needs a defined
two-way contract via frontmatter:

```yaml
---
thread_id: 439dd11e6940
source: gemini
account: personal
title: Merging Codebases and Database Concepts
status: open              # flip to `closed` yourself to close a thread
project_link: null        # correct/confirm here — editing this sets project_confidence: manual
project_confidence: fuzzy
review_status: pending     # auto | confirmed | pending
review_note: "Suggested project: L5GN-Crystal-Spire (confidence 0.71)"
suggested_close: false     # auto-set true at 30+ days inactive; you decide, system never auto-closes
tags: []
---
```
**Sync-back step runs before every render:** reads all `.md` frontmatter, diffs
against the DB, and any field a human changed becomes an authoritative override
(logged, never silently re-clobbered by a later automated pass) — consistent with
the "user-override always wins" rule established earlier for project-links.

**9.2 — Gemini pipeline finalized as:** Takeout (`My Activity.json`, personal
account only, periodic) + share-link scrape (same account, ongoing, batches of
~10) → reconciliation join for ordering. `raw_gem_files` (work account) is now
a closed, historical input — ingested once, never revisited for new data.

**9.3 — Embeddings: sentence-transformers, local-only.** No conversation text
leaves your machine for the grouping layer. (Reasonable default model to start
with: `all-MiniLM-L6-v2` — small, fast, good enough for continuity-detection;
can upgrade later if grouping quality needs it.)

**9.5 — `account` becomes a free-form identifier, not a boolean.** e.g.
`claude-personal`, `gemini-work`, `gemini-personal` — schema already supports
this (was a string field), just confirming the assumption formally: **every
source × account combination should be assumed to potentially need its own
ingestion method**, not just its own row.

**9.6 — Attachments, both sources, now in v1 scope:**
- **Claude**: already present in `conversations.json` — `attachments[]` (with
  `file_name`, `file_size`, and — genuinely useful — `extracted_content`, the
  full text inline, no separate download needed) and `files[]` (`file_uuid` +
  `file_name` for anything referenced without extracted text). 292 messages
  in your current export alone carry attachments.
- **Gemini**: attachment filenames/hashes already identified via the Takeout
  sidecar files and the 16-hex turn-hash; the share-scraper itself doesn't
  currently pull attachment chips from the DOM — needs a small extension.
- Both feed the `attachments` table from section 5, and — per your own
  observation earlier — attachment filenames are a genuinely strong
  project-link signal (`tui.py` → `L5GN-Crystal-Spire`) worth using directly
  in the linker, not just archiving passively.

**9.7 — Archiving convention (proposed, since delegated):**
```
zip_downloads/archive/<source>/<account>/<YYYYMMDD_HHMMSS>__<original_filename>
```
Raw files **moved** (not copied) here immediately after a successful ingest,
so `zip_downloads/` itself always reflects "not yet processed."

**9.8 — Close-out suggestion, not automation:**
A scheduled/on-run check flags `suggested_close: true` in frontmatter (and adds
a `close_suggestion` entry to `review_queue`) for any `open` thread whose
`updated_at` is 30+ days in the past. You confirm by flipping `status: closed`
yourself in Obsidian — nothing closes without that.

---

## 10. Build spec — ready for Cowork after reset

**Scope for this build pass:**
1. SQLite schema from section 5, with the `account`-as-string and attachment
   fields from 9.5/9.6 included from the start
2. Claude normalizer: `conversations.json` + `projects/*.json` → `threads` /
   `messages` / `attachments`, project-linking via exact name + `prompt_template`
   substring match
3. Gemini normalizer: `My Activity.json` (personal account) → `messages` with
   real UTC timestamps, unresolved `thread_id` (pending reconciliation)
4. ~~Gemini share-scraper attachment extension: pull attachment chip
   filenames/hashes into the same JSON output as the message skeleton~~ —
   **investigated and descoped, see 11.3a.** Direct DOM inspection of four
   live share pages (via Claude in Chrome) found no per-attachment hash, ID,
   file size, or timestamp anywhere in the markup — only a visible filename
   in some cases (and even that's truncated/extension-stripped in the file
   chip, only appearing in full inside an `aria-label` on citation chips).
   There is nothing to extract that could anchor against the Takeout side's
   `source_turn_hash`. Reconciliation proceeds on fuzzy content-match alone.
5. Reconciliation join: share-scrape skeletons ↔ Activity turns, by fingerprint
   + nearest timestamp, assigning `thread_id`/`seq` to matched Activity rows
6. Layered grouping for anything left unmatched (exact fingerprint → gem+time-
   adjacency → sentence-transformers similarity), each writing a confidence
   and, where below threshold, a `review_queue` row
7. `.md` renderer with the frontmatter contract from 9.1, **plus** the sync-back
   reader that runs before every render
8. `ingestion_log` writes on every batch (source, account, file hash, counts)
9. Archiving step per 9.7 convention
10. 30-day `suggested_close` check per 9.8

**Explicitly out of scope for this pass:** any local web UI (deferred per 9.1),
Copilot or any other new source, work-account Gemini (closed/historical per 9.2).

**Known inputs already on disk, ready to use:**
- `raw_claude_files/` (conversations.json, projects/, users.json)
- `raw_gem_files/` (110 files, one-off historical, already the batch to ingest once)
- `raw_gemini_files/Takeout/My Activity/Gemini Apps/My Activity.json`
- `scraped_gemini/` (4 conversations scraped so far via `scrape_gemini_share.py`,
  more to come in ongoing batches)
- `scrape_gemini_share.py` (working, DOM-based, in `chat_threads/`)

---

## 11. Reconciliation join algorithm (build spec item 5)

**11.1 Purpose & inputs**
Share-scrape skeletons (`scraped_gemini/<share_id>.json`) have correct turn
order and boundaries but no native ID and, confirmed against real output,
often **no usable timestamp at all** (`created_date`/`published_date` are
frequently `null`). Takeout `messages` rows (`thread_id IS NULL`, written by
`normalize_gemini_personal.py`) have real UTC timestamps and correct content
but no thread boundary. Reconciliation's only job: for each skeleton, find
its matching Takeout rows and stamp them with a synthetic `thread_id` +
sequential `seq`, inheriting the skeleton's order as ground truth.

Candidate pool per skeleton: `SELECT * FROM messages WHERE source_turn_hash IS
NOT NULL OR thread_id IS NULL` restricted to `role IN ('user','assistant')`
and not yet claimed by an earlier skeleton in this same run (already-`NOT
NULL` thread rows from prior runs are excluded automatically by the
`thread_id IS NULL` filter — this is what makes reruns idempotent).

**11.2 Normalization**
`normalize(text) = re.sub(r"\s+", " ", text).strip()`. Applied to both sides
before any comparison. Known fuzz factor to expect, not a bug to chase: the
live share DOM and the Takeout HTML (`html_to_text()` in
`normalize_gemini_personal.py`) render inline grounding/citation chips (e.g.
literal `"Google Docs"` / `"+ 4"` fragments visible mid-paragraph in scraped
samples) slightly differently — this is why matching needs a fuzzy fallback,
not exact-string-only.

**11.3a Fingerprint match — confirmed dead path, kept for forward-compat only**
`find_hash_anchors()` in `reconcile_gemini.py` looks for a `turn_hash` on
each skeleton message's attachments and always returns `{}` today. This is
now a *confirmed* permanent state, not a "pending item 4" placeholder: a
live DOM inspection of four real share pages (382bedba6a5f, 439dd11e6940,
4577d22c19f5, f499add109e2) found three attachment markup patterns (file
chip, code-block/canvas, inline source-citation chip) and none of them
expose a hash, ID, file size, or per-attachment timestamp — only an
occasional filename, and even that's inconsistent (truncated in the file
chip, only appearing in full inside a citation chip's `aria-label`). There
is nothing on the share-scrape side that could ever be matched against the
Takeout side's `source_turn_hash`. The function is left in place exactly as
written (returns `{}`, costs nothing) in case a future Gemini UI change or
an undocumented `bard-initial-data` JSON blob on the page turns out to
carry something usable — but no further scraper work should be scheduled
against this path. Reconciliation runs on steps 3/4 below (content match)
for 100% of turns, always.

**11.3 Matching, per skeleton message in order (i = 0..N-1)**
1. **Fingerprint match (dead path — see 11.3a)** — if the skeleton message
   has a `turn_hash` (never true in practice today), look for an unclaimed
   candidate with the same `source_turn_hash`. Exact hash match → claim
   immediately, similarity = 1.0. Originally scoped as the strong anchor
   layer (~23% of turns, per the Takeout survey) but only reachable from the
   Takeout side — the share-scrape side has nothing to offer it.
2. **Windowed content match** — for messages without a hash, or once at
   least one hash anchor exists in this skeleton, restrict the candidate
   pool to rows whose `created_at` falls between the nearest preceding and
   following hash-anchor timestamps (chronological bracketing). This is the
   main defense against false positives from repeated stock phrasing (the
   sample transcripts are full of recurring boilerplate like "Sovereign
   Architect" — pure content matching without a time window would
   misattribute these across unrelated conversations).
3. Within the (possibly windowed) pool, first look for an exact
   `normalize()` match on content, same role. Claim if found (similarity
   1.0).
4. Else compute `difflib.SequenceMatcher(None, a, b).ratio()` (stdlib, no
   install needed) against every remaining same-role candidate in the pool;
   take the best. Claim it only if `ratio >= 0.90` (tunable — flagged as an
   open tunable in section 7, item 4; start here and adjust empirically).
5. If no candidate clears the threshold, the skeleton message is
   **unmatched** — do not fabricate a row for it. Record the gap for review
   (11.5). Takeout is the assumed complete content source for this account,
   so a persistent gap means either the scrape and Takeout genuinely
   disagree, or Takeout is missing that turn — both are review-worthy, not
   auto-resolvable.
6. If a skeleton has **zero** hash anchors at all (no attachments anywhere
   in it), there is no time window to restrict step 2/4 to — matching runs
   against the *entire* unclaimed pool. Because collision risk is highest
   here, **every thread assembled this way gets `review_status: pending`
   regardless of match rate**, not just the low-confidence ones.

**11.4 Thread assembly**
- `thread_id = synth_id("gemini-share", share_id)` (share_id = the slug in
  the share URL, e.g. `4577d22c19f5` — already stable and unique, no need
  to hash the whole URL).
- `seq` = skeleton position (0..N-1), **not** derived from matched
  timestamps — the skeleton's order is the whole reason reconciliation
  exists; a matched timestamp that's out of order relative to `seq` is a
  signal something's wrong, not a reason to reorder (see 11.5).
- `created_at`/`updated_at` on the `threads` row = min/max of the *matched*
  timestamps only (unmatched turns contribute nothing).
- Title: the scraped `title` field has a confirmed live bug — all 4 current
  samples show the generic fallback string
  `"‎Gemini - direct access to Google AI"` (a `page.title()` capture issue in
  `extract_title()`, tracked separately, not part of this build item). Until
  fixed: if `title` equals that literal fallback string, use the first ~60
  normalized characters of the first matched user message instead.
- `raw_ref` = relative path to the skeleton JSON. `parser_version =
  "reconcile_v1"`.
- Before processing a skeleton, check for an existing `threads` row with
  that `raw_ref` — skip entirely unless `--force` (idempotent re-runs; new
  scrape batches land in the same folder over time and shouldn't reprocess
  old ones).
- For every claimed candidate: `UPDATE messages SET thread_id=?, seq=?
  WHERE message_id=?`.

**11.5 Confidence & review_queue**
- `match_rate = claimed / N`. If `match_rate < 1.0`: one `review_queue` row,
  `type='reconciliation_gap'`, `thread_id`, `confidence=match_rate`, `note`
  listing the unmatched skeleton indices/snippets.
- Any individual claimed pair with `ratio < 0.97` (i.e. fuzzy, not exact):
  one `review_queue` row, `type='reconciliation_fuzzy_match'`,
  `confidence=ratio`.
- Any claimed timestamp sequence that isn't monotonically non-decreasing
  across `seq` order: one `review_queue` row,
  `type='reconciliation_order_conflict'` — likely sign of a bad match,
  surfaced rather than silently trusted.

---

## 12. Layered grouping fallback (build spec item 6)

Operates only on `messages WHERE thread_id IS NULL` left over after section
11 — i.e. genuine personal Gemini usage that was never shared/scraped
(the large majority: 4 skeletons scraped so far vs. 3507 Takeout records).
Layers run in strict order; each only touches what the previous layer left
unresolved; a message with a non-`NULL` `thread_id` is permanently out of
scope for all layers and all future reruns.

**12.1 Layer A — exact fingerprint**
Group unclaimed messages sharing the same `source_turn_hash` into one
synthetic thread (`thread_id = synth_id("gemini-fingerprint", turn_hash)`).
Cheap, high-confidence, low-coverage by design — a `turn_hash` is logged
only on the turn where a file was actually attached, not on every later
turn that references it from context, so this layer will under-group
multi-turn conversations that only attach a file once. That's expected;
layers B/C exist specifically to pick up the rest.

**12.2 Layer B — gem-context + idle-gap session segmentation**
Takeout's `activity_log`-role rows (`"Used <GemName>"` / `"Created ..."`)
are the only source of gem context for `'Prompted'` turns — the normalizer
doesn't currently attach gem name to individual turns. Before segmenting:
walk all `NULL`-thread messages (`user`/`assistant`/`activity_log`) sorted
by `created_at`; for each `activity_log` row matching `"Used (.+)"`, treat
that gem name as the presumptive context for subsequent turns until the
next such log row.

Then segment strictly by time within each gem-context stretch: sort,
walk in order, start a new synthetic thread whenever (a) the inferred gem
context changes, or (b) the gap since the previous turn exceeds
`idle_gap_minutes` (default 30 — configurable, another real tunable, not a
solved constant). `thread_id = synth_id("gemini-session", first_message_id
_in_group)`, `seq` assigned in walk order.

Every Layer B thread gets one `review_queue` row (`type='thread_grouping'`,
`confidence` = a simple tightness score, e.g. `1 - avg_gap_minutes /
idle_gap_minutes` clipped to `[0,1]`) — none of this is scrape-confirmed,
so none of it auto-graduates to `review_status: confirmed`.

**12.3 Layer C — semantic similarity (sentence-transformers, local-only)**
For whatever Layer A+B still left unresolved (isolated turns with large
gaps on both sides, or ambiguous gem context): embed each candidate
(`all-MiniLM-L6-v2`, `pip install sentence-transformers --break-system-
packages`) and compare against the anchor embeddings of existing threads
(first + last message of each thread already established by section 11,
Layer A, or Layer B) whose own `updated_at` is within
`semantic_window_days` (default 14, tunable) of the candidate's
`created_at` — this bounds the comparison set and reduces false positives
from topic drift over long gaps (at ~3500 records a full pairwise pass is
cheap enough anyway; the window is about precision, not performance).

If the best cosine similarity `>= similarity_threshold` (default 0.6,
explicitly flagged as an empirical guess in section 7 item 3 — expect to
retune once real output exists): append the candidate to that thread as a
new max-`seq` message. Otherwise: spin up a brand-new singleton synthetic
thread rather than dropping the turn. Either way, write one `review_queue`
row (`type='thread_grouping'`, `confidence=best_score_found` even when
below threshold, so the review surface can show "closest match, not close
enough" candidates rather than nothing).

**12.4 Ordering & idempotency**
A / B / C run in that fixed order every pipeline pass, each scoped to
`thread_id IS NULL` only. Reruns naturally pick up only new Takeout/scrape
data since the last pass — nothing already assigned is re-evaluated.

---

## 13. `.md` renderer + sync-back (build spec item 7)

**13.1 Filename convention**
`vault_staging/<source>/<account>/<thread_id>.md` — filename keyed on
`thread_id` only, **never** on title. Title can change (human edit, or a
better `extract_title()` later); if it were embedded in the filename,
Obsidian backlinks/graph position would break on every rename. Title lives
in frontmatter and as the `.md`'s H1, not the path.

The existing 35 `vault_staging/*.md` files (zero frontmatter, `shatter.py`
output) are a **full regeneration**, not a patch — confirmed in STATUS.md.
Before the first regeneration pass only: move the old files to
`vault_staging/_archive/<YYYYMMDD_HHMMSS>__<old_filename>.md` (same spirit
as the 9.7 archiving convention) rather than deleting them, in case any
manual notes were ever hand-added to them outside the sync-back contract.
This is a one-time safety step, not a routine part of every render.

**13.2 Render**
For every thread, on every run: pull the current DB row fresh (see 13.5 for
why "fresh" matters), write frontmatter per the 9.1 contract exactly, then
the body as the full transcript in `seq` order (`**User:**` / `**Assistant:**`
blocks, or equivalent — full re-render every time, no incremental diffing;
cheap at this scale, and far simpler to reason about than trying to
append only new messages).

**13.3 Sync-back — field authority rules**
Read-only fields, never accepted from the file even if a human edits them:
`thread_id`, `source`, `account`, `created_at`, `updated_at` (identity/
derived fields — not even listed as editable in the 9.1 sample). If a human
changes one of these in Obsidian, the next render silently overwrites it
back to DB truth — no log entry, this isn't a "conflict," it's an
out-of-contract edit.

Editable fields (`status`, `project_link`, `project_confidence`,
`review_status`, `review_note`, `suggested_close`, `tags`): for each,
compare the parsed frontmatter value against the current DB value.
- If different: **file wins, unconditionally** — even if the DB value also
  changed since the last render (e.g. an automated pass just touched
  `project_confidence` while a human simultaneously edited `project_link`
  in Obsidian). This is the concrete case the "user-override always wins"
  principle has to handle, not just the abstract rule.
  `UPDATE threads SET <field>=<file_value> [, project_confidence='manual'
  IF field == 'project_link'] WHERE thread_id=?`.
- A field simply **absent** from a given `.md`'s frontmatter (someone
  deleted the line) is "no opinion," not a clear-this-field signal — skip
  it, don't touch the DB value.
- A missing/deleted `.md` file entirely is **not** treated as a delete or
  close signal on the thread — it's just regenerated fresh on the next
  render, as if new.
- Log every applied override as a `review_queue` row: `type=
  'manual_override'`, `thread_id`, `note = f"{field}: {old!r} -> {new!r}"`,
  `status='confirmed'` (it's already applied, not pending), `confidence=
  NULL`, `resolved_at=now`. This reuses the existing `review_queue` table
  rather than adding a new one, avoiding a schema migration.
- Parser: use `pyyaml` (`pip install pyyaml --break-system-packages` if not
  already present) for the frontmatter block rather than hand-rolling a
  parser — the field set is small but includes a list (`tags`) and a bool
  (`suggested_close`), both easy to get subtly wrong with regex.

**13.4 Reopen is out of scope here**
Touchpoint #7 ("confirm a possible reopen of a closed thread") is a
grouping-time concern — it happens when Layer C (12.3) considers attaching
a new turn to a thread whose `status` is already `closed`; that must always
route to `review_queue` rather than silently reopening, regardless of
similarity score. It is **not** a sync-back concern: a human flipping
`status: closed` → `open` directly in frontmatter is a deliberate edit and
is always honored immediately like any other editable field — the human
editing it *is* the confirmation.

**13.5 Ordering guarantee**
Sync-back must fully drain into the DB **before** that thread's `.md` is
regenerated in the same pass — otherwise the freshly-written file would
overwrite the human's own just-applied edit with stale pre-edit content,
which reads as silent data loss even though the DB is actually correct.
Treat it as one atomic per-thread step: read frontmatter → diff/apply to
DB → re-read the thread row fresh from DB → render from that fresh row.
Running sync-back for all threads before rendering any of them also works,
as long as no render reads a thread row before that thread's own sync-back
has completed.

---

*Sections 11–13 are precise enough to build without further design
questions. Remaining open tunables (fuzzy-match threshold, idle-gap
minutes, semantic-similarity threshold/window) are called out inline where
they occur — start with the stated defaults and retune empirically once
real reconciliation/grouping output exists, per section 7 item 4.*

