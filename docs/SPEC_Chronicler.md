# Chronicler × L5GN Intel — Project-Linking Skill Set
### Design & build spec, v1 — for Cowork execution

Goal: raise thread→project linking from "fuzzy match on folder names" to a
multi-signal evidence system that improves over time, powered by artifacts
the nightly tasks already produce, and feeding results back into them.

Read first for context: `chronicler_design_and_intent_v2.md` (the as-built
Chronicler reference). The nightly L5GN Intent/Contents refresh task and the
MCF Knowledge Sync task are the existing scheduled jobs referenced below.

**Build order: S1 → S4 → S6 (core loop, ship first), then S2, S3, S5
(signal upgrades, each immediately consumed by re-running S6), then S7, S8
(payoff layer).** Each skill is independently testable; none blocks another
except as noted.

**Standing rules (apply to every skill, no exceptions):**
- `project_confidence: manual` links and human-resolved review_queue rows are
  never modified by any automated pass (established override rule).
- Every automated write that changes a link or a registry entry leaves an
  audit trail (review_queue row or revision-log line as appropriate).
- Loud failure: a skill that can't complete states so and stops; no partial
  silent writes. state/registry files are written whole, never half-updated.
- All file I/O UTF-8 explicit. All timestamps UTC ISO-8601.

---

## S1. Project Registry

**What:** One machine-readable file, `L5GN/.intel_sync/project_registry.json`,
as the canonical join surface between the filesystem world (repos) and the
conversation world (Chronicler DB). Maintained by the nightly Intent/Contents
refresh task as a new final step.

**Schema (per project entry):**
```json
{
  "canonical_name": "L5GN-Crystal-Spire",
  "path": "C:\\Users\\tim.smith\\Github\\L5GN\\L5GN-Crystal-Spire",
  "scope": "l5gn",                      // l5gn | mcf | other roots later
  "vcs": "git",                          // git | none
  "aliases": [
    "Crystal Spire", "the Spire", "SpireApp"
  ],
  "alias_sources": {                     // provenance per alias
    "Crystal Spire": "manual",
    "SpireApp": "vocabulary_extract"
  },
  "status": "active",                    // mirrors Intent.md status column
  "first_seen": "2026-05-02",
  "registry_updated": "2026-07-14T18:00:00Z"
}
```

**Build tasks:**
1. Generator script `pipeline/build_registry.py`: seeds the registry from (a)
   folder scan of L5GN + MCF roots, (b) the project rows already in
   `Intent.md`/`Contents.md` (parse the tables), (c) Chronicler's existing
   `projects` table (Claude project names → aliases of the matching repo).
2. Seed aliases conservatively: canonical name, name with separators varied
   (`L5GN_Armory_v4` ↔ "L5GN Armory v4" ↔ "Armory"), Claude project names.
   **Then STOP and present the seeded alias lists to Tim for a one-time
   review/extension in a single sitting** — Tim knows "Castle Doctrine",
   "Sovereign OS", "the Kingdom" etc. map to specific efforts; that mapping
   is tribal knowledge, not derivable. This is a designed HITL step, not a
   fallback. Aliases added by Tim get `"manual"` provenance and are never
   auto-removed.
3. Nightly integration: add a final step to the Intent/Contents refresh task
   prompt — after its normal run, regenerate registry entries for any
   project that changed (new folders → new entries; renames → flagged as
   discrepancy per its existing rule, never auto-merged).

**Acceptance:** registry file exists, validates against schema, contains
every current L5GN + MCF project folder, and Tim has reviewed/extended the
alias lists once.

---

## S2. Vocabulary Fingerprints

**What:** Per project, a weighted set of distinctive terms that appear in
that project's code/docs and (statistically) nowhere else — turning content
mentions inside a thread into link evidence.

**Storage:** `"vocabulary"` key added to each registry entry:
```json
"vocabulary": {
  "built_at": "2026-07-14T18:00:00Z",
  "source_commit": "abc1234",           // skip rebuild if unchanged
  "terms": { "SpireApp": 3.2, "world_graph": 2.9, "beta_logging": 2.7 }
}
```

**Build tasks:**
1. `pipeline/build_vocabulary.py`: per project, harvest candidate terms from
   (a) filenames (`git ls-files` for git projects, recursive listing capped
   at depth 3 for non-git), (b) top-level identifiers in code files (class /
   def / exported names — a light regex pass, not full parsing), (c) markdown
   headings in the project's own docs, (d) for `smelt-gateway`: shard titles.
2. Weight by distinctiveness: term frequency in this project ÷ frequency
   across ALL projects (a TF-IDF-shaped score). Discard generic terms
   (main, utils, README, test...) via a stopword list + a cross-project
   commonality cutoff. Keep top ~50 per project.
3. Skip-if-unchanged: store the commit SHA / signature the vocabulary was
   built from; nightly rebuild only for projects whose SHA moved (hooks the
   same change-detection the Intent task already does).

**Acceptance:** every registry entry has a vocabulary block; spot-check that
`L5GN-Crystal-Spire`'s top terms include tui/Spire-specific identifiers and
NOT generic Python noise.

---

## S3. Activity Windows

**What:** Per project, the date ranges when it was actually being worked on —
used to score time-plausibility of a candidate link and disambiguate projects
that share vocabulary.

**Storage:** `"activity"` key per registry entry:
```json
"activity": {
  "first_commit": "2026-05-02",
  "last_commit": "2026-07-12",
  "bursts": [ {"from": "2026-05-02", "to": "2026-05-19"},
               {"from": "2026-06-28", "to": "2026-07-12"} ]
}
```

**Build tasks:**
1. `pipeline/build_activity.py`: git projects → `git log --format=%aI`, dates
   only; cluster into bursts (gap > 7 days splits a burst). Non-git projects
   → file mtimes as a coarse fallback (flag `"precision": "mtime"`).
2. Scoring helper (used by S6): `time_plausibility(thread_date, project)` →
   1.0 inside a burst, decaying toward 0.1 outside all bursts, hard 0.0
   before first_commit minus 14 days (a thread can slightly predate the
   first commit — design talk before code — but not by a month).

**Acceptance:** activity blocks exist for all git projects; the
plausibility function returns sane values for known thread/project pairs
(e.g. the tui.py thread of 11 July lands inside a Crystal Spire burst).

---

## S4. Filename Cross-Reference

**What:** Join Chronicler's `attachments` table (~2,800 filenames) against
per-project file inventories. An exact filename match is the strongest
automatic link signal available.

**Build tasks:**
1. Inventory: `"file_inventory"` key per registry entry (from S2's harvest —
   share the `git ls-files` pass, don't run it twice). Store basenames +
   relative paths.
2. `pipeline/xref_filenames.py`: for every attachment in the DB, look up its
   basename across all project inventories:
   - Unique hit (one project owns that basename) → strong evidence vote for
     that thread→project link, weight 1.0.
   - Multi-hit (several projects have e.g. `main.py`) → weak vote per hit,
     weight 1/n, and only if the basename isn't in the generic stoplist
     (main.py, README.md, requirements.txt, __init__.py...).
   - No hit → no signal (not negative evidence — attachments legitimately
     include non-repo files).
3. Output: `evidence` rows (see S6 schema) — this skill only *produces
   evidence*, it never writes links itself.

**Acceptance:** run against the real DB; verify `tui.py` attachment produces
a unique-hit vote for L5GN-Crystal-Spire; report evidence counts per project.

---

## S5. Path-Mention Extraction

**What:** Mine thread message content for literal filesystem paths (pasted
tracebacks, terminal prompts, file references) and convert them into
project votes.

**The normalization requirement (learned from real data):** the same repo
appears as `C:\Users\timps\Documents\GitHub\L5GN-Crystal-Spire` (other
machine) and `C:\Users\tim.smith\Github\L5GN\L5GN-Crystal-Spire` (this one).
Match on the **repo-folder segment only**: extract path-like strings, split
on separators, and test each segment (and each trailing segment pair) against
registry canonical names + aliases, case-insensitive, separator-insensitive
(`-`/`_`/space equivalent). Everything left of the matched segment is
ignored by design.

**Build tasks:**
1. `pipeline/extract_path_mentions.py`: regex for Windows + POSIX path shapes
   over `messages.content`; segment-match per above; emit evidence votes
   (weight 0.9 — near-filename strength; a pasted traceback containing the
   repo folder is nearly conclusive).
2. Cache: store scanned `message_id`s (a `path_scan_log` table or a max-rowid
   watermark) so the nightly run only scans new messages.

**Acceptance:** the tui.py traceback thread yields a Crystal-Spire vote from
its pasted path despite the foreign username/parent-dir; no false hits from
generic paths like `C:\Python314\Lib`.

---

## S6. Re-Link Pass (the consumer — this is the engine)

**What:** The nightly-runnable pass that combines all evidence into link
decisions. Replaces "link once at ingest, frozen forever" with "links improve
as evidence accumulates."

**Evidence model (new table `link_evidence`):**
```
thread_id · project (canonical_name) · signal (name_alias | vocabulary |
filename_xref | path_mention | time_window) · weight (0–1) · detail (text,
e.g. the matched term/filename/path) · produced_at · producer_version
```
S4/S5 write rows here; S6 additionally computes name/alias and vocabulary
and time signals inline at scoring time (cheap, no need to persist
separately — but persist the *winning* evidence set on decision, see below).

**Scoring:** per thread, per candidate project:
```
score = 1 - Π(1 - weight_i)        # independent-evidence combination
adjusted = score × time_plausibility(thread_date, project)
```
(Signal weights: filename unique 1.0 → capped at 0.97 pre-combination so no
single signal is ever *absolute*; path_mention 0.9; alias-in-title 0.8;
alias-in-content 0.6; vocabulary hits 0.3 each, max 3 counted; these are
starting values, tunable in one config block at the top of the script.)

**Decision rules:**
- adjusted ≥ 0.90 and best candidate leads second-best by ≥ 0.25 →
  auto-link, `project_confidence: evidence`, log review_queue row type
  `link_upgrade` (informational, auto-resolved).
- adjusted ≥ 0.60 → queue as `project_link` suggestion, pending, with the
  evidence list in the note (so review shows *why*, not just a score).
- Two candidates both ≥ 0.60 within 0.25 of each other → queue as
  `link_ambiguous` with both evidence sets. Never guess between rivals.
- Existing `fuzzy` links get re-scored: upgraded to `evidence` if they clear
  the bar, DOWNGRADED to a pending suggestion if new evidence points
  elsewhere (with old + new evidence both shown). `manual` never touched.
- Store the winning evidence rows' ids on the thread (a `link_evidence_ids`
  json field) — every link must be explainable later.

**Build tasks:**
1. Schema migration: `link_evidence` table + `link_evidence_ids` on threads +
   new `project_confidence` value `evidence` (between fuzzy and manual in
   authority: automation may upgrade fuzzy→evidence but only a human may
   change evidence→anything).
2. `pipeline/relink.py` implementing the above, with `--dry-run` default ON
   (same convention as bulk_review.py): prints decision table before writing.
3. Wire into the pipeline runner (`run_pipeline.py`) as a stage after
   group_fallback, before suggest_close; per-stage skip flag like the rest.
4. Render pass after: frontmatter picks up new links (DB→file flow is
   legitimate here, same authority argument as bulk_review).

**Acceptance:** dry-run against the full real DB; manually verify a sample of
10 auto-link decisions and all ambiguous flags; confirm zero `manual` rows
touched; confirm idempotency (second run = no-op); confirm every auto-link's
evidence chain is inspectable in the DB.

---

## S7. Reverse Enrichment (conversation trail → Intent/Contents)

**What:** Flow solid links back into the navigation docs, so each project row
answers "what have I been thinking about here, and when."

**Build tasks:**
1. `pipeline/project_trail.py`: per registry project, query Chronicler for
   linked threads (confidence `evidence` or `manual` only — suggestions don't
   count): thread count, last-discussed date, 3 most recent thread titles.
   Output `“trail”` block per registry entry.
2. Nightly Intent/Contents task integration: new column in `Contents.md`'s
   folder-map table — `Last discussed` (date + thread count, e.g.
   "12 Jul (41 threads)") — and revision-log lines only when a trail value
   actually changed. Keep it to one column; the 3 recent titles go in the
   registry only (Contents.md stays scannable).
3. Guard: if `chronicler.db` is missing/locked at run time, skip the trail
   step with a note in the summary — never block the Intent/Contents refresh
   on Chronicler availability.

**Acceptance:** Contents.md gains the column, values match hand-checked DB
queries, revision log notes the change once (not nightly noise).

---

## S8. Drift Alerts

**What:** Surface mismatches between the code world and the conversation
world as open questions — never auto-fix.

**Detectors (run inside the nightly task after S7's trail refresh):**
- **Silent building:** project has commits in the last 14 days but zero
  threads linked in the last 30 → "building without documented thinking?"
- **Talking without building:** ≥3 threads linked in the last 14 days but no
  commits in 30+ (git projects only) → "discussion outpacing code, or links
  misassigned?"
- **Orphan cluster:** ≥5 threads sharing a dominant vocabulary/alias signal
  for something with NO registry entry → "is there a project missing from
  the registry?" (this catches codename-drift creating a new effort before
  its folder exists).

**Build tasks:**
1. `pipeline/drift_check.py` implementing the three detectors, each emitting
   at most ONE line per project per run.
2. Output goes to `Intent.md`'s "Open questions" section — append-only, per
   that task's existing rule, and dedupe: never re-add a question that's
   already present verbatim/near-verbatim and unresolved.

**Acceptance:** run against real data; each fired alert is true on manual
inspection; re-run adds no duplicates.

---

## What this does NOT include (parked, per standing decision)
- Copilot or new-source ingestion
- Local web UI for review
- MCF-side conversation linking (MCF has knowledge docs in the sync task but
  its threads live in the same Chronicler DB — registry `scope` field is the
  hook for extending later; do not build MCF-specific logic now)

## Suggested Cowork session split (compute-friendly atoms)
- **Session 1:** S1 complete (including presenting alias lists to Tim) + S4
- **Session 2:** S6 core (schema, scoring, dry-run output) — pause for Tim's
  review of the dry-run decision table before first `--apply`
- **Session 3:** S2 + S3, rerun S6, apply
- **Session 4:** S5, rerun S6 · S7 + S8 + nightly-task prompt updates
