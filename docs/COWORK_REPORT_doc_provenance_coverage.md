# Cowork report — document provenance and coverage

**Brief:** `docs/COWORK_BRIEF_doc_provenance_coverage.md`. **Implements:**
DECISIONS 0026. **Status:** built and gate-GREEN; walk-sheet is
`docs/UAT_doc_provenance_coverage.md`.

---

## What changed

`l5gntools/scanners/doc_census.py`:

- **Task A — `doc_type`.** Every markdown document gets a `doc_type`, decided
  by filename and path alone (`classify_doc_type`): `adr` (an `adr` path
  segment, unchanged), `knowledge` (stem contains `_knowledge`, case-
  insensitive, unanchored — 0026 as ratified), `claude_md` / `readme` /
  `glossary` (existing exact-name rules), `decisions` / `intent` /
  `architecture` / `runbook` (also matches `playbook`) / `uat` (also matches
  `checklist`) / `plan` (also matches `status`) / `brief` / `report` (stem
  contains the marker word, unanchored), and `unclassified` for everything
  else — stated in the brief as not a failure state, and it isn't: most of
  this repo's own `docs/` is ordinary prose that lands there correctly.
- **Task B — `provenance`.** Every document also gets `authored` or
  `generated` (`classify_provenance`): generated if any *directory* segment
  (never the filename) starts with `.` or `_`, or is `output`, `logs`, or
  `AutoFiles`. Every ratio in the module — `classified_count`,
  `classified_pct`, the type tally — is computed over authored documents
  only. `generated_count` is reported beside it, never dropped.
- **Task D — out-of-band doc count.** `out_of_band(projects)` flags a project
  whose raw `doc_count` (all provenance — this is a payload/scale question,
  not a governance one) exceeds 3x the estate's median `doc_count`, and needs
  at least 3 projects with a nonzero count before it computes anything.

`l5gntools/report.py`:

- The Docs tab now shows authored count (with generated noted beside it in
  parentheses), classified count, classified %, plus the existing README /
  CLAUDE.md / ADR columns (now themselves authored-only, since `readme` /
  `claude_md` / `adr` are Task A types).
- **Task C — the coverage grid.** A project × document-type table under the
  main Docs table, ticks (with the count) and dashes, over authored documents
  only. No total column, no rank, no colour implying pass/fail — coverage,
  not a score, per the brief.
- A `doc_anomalies` banner (Task D) renders inside the Docs tab when any
  project trips the out-of-band threshold, separate from the existing
  bytes-based `anomalies` banner because the unit and the question differ.
- `build_estate` now computes `doc_anomalies` via `doc_census.out_of_band`
  and writes it into `estate.json` beside the existing `anomalies` key.

`tests/tester_doc_census.py` (new, registered in `verify.py`): exact-mapping
checks for every `doc_type` case, a false-positive hunt for `classify_
provenance` against a set of authored-looking paths, a full `scan()` check
against a synthetic mixed project (authored/generated, several types), and
`out_of_band` behaviour (below the minimum project count, a clear outlier,
and a zero-doc project not crashing the median).

---

## Verification against real data

The personal estate's cached `data/estate.json` (824 real documents across 8
projects, built 2026-07-28) was used to verify the Task B rule *before*
shipping it, per the brief's instruction not to re-derive the evidence table
but to confirm it:

| project | docs | authored | generated | classified | classified % |
|---|---:|---:|---:|---:|---:|
| L5GN-Archive | 25 | 1 | 24 | 1 | 100.0 |
| L5GN-Armory | 9 | 0 | 9 | 0 | — |
| L5GN-Armory_v2 | 27 | 6 | 21 | 0 | 0.0 |
| L5GN-Castle | 19 | 19 | 0 | 5 | 26.3 |
| L5GN-Continuous-Ingestion-Daemon | 358 | 17 | 341 | 12 | 70.6 |
| L5GN-Crystal-Spire | 97 | 44 | 53 | 3 | 6.8 |
| L5GN_Armory_v4 | 288 | 2 | 286 | 2 | 100.0 |
| L5GN_Managed_Workspace | 1 | 1 | 0 | 1 | 100.0 |
| **estate total** | **824** | **90** | **734** | **24** | **26.7** |

**Before (0026's own measurement, ratio over all 824 docs):** 45/824 = 5.5%,
the number the brief calls "not a governance signal".
**After (this build, ratio over the 90 authored docs):** 24/90 = **26.7%**,
with the 734 generated documents visible beside it rather than silently
dragging the denominator down. The personal estate's number is now honest, in
the sense the UAT check asks for: the two heaviest generator projects
(Continuous-Ingestion-Daemon at 341/358 generated, `L5GN_Armory_v4` at
286/288) are visible as such rather than reading as undocumented.

The generated-count breakdown matched the brief's evidence table exactly, per
project: CID 341/358, Armory_v4 286/288, Crystal-Spire 53/97, Armory_v2
21/27, Archive 24/25. The rule's catch rate: the dot/underscore convention
alone catches 694 of 824; adding `output` / `logs` / `AutoFiles` brings it to
734 — both numbers land inside the brief's own predicted ranges (~685, ~725).

**`out_of_band` on the same data**, 3x-median rule (median 26, threshold 78):
flags exactly `L5GN-Continuous-Ingestion-Daemon` (358), `L5GN_Armory_v4`
(288) and `L5GN-Crystal-Spire` (97) — the same three projects the brief's own
evidence table calls out, and none of the five smaller ones.

**Work estate:** this session had no access to the work estate's filesystem
(a different machine/`CHRONICLER_HOME`), so the numbers above could not be
re-verified there. The rule itself is unchanged from what the brief already
verified against both estates before this build (§"Measured evidence"); the
work-estate side of the before/after table is the brief's own figures
(36/77 → expect a modest increase once computed authored-only, since the work
estate's docs sit under `docs/`, `briefs/`, `PoC/` with no generated share to
subtract).

### False positives — none found

Every authored document in the personal estate's real data was inspected by
eye for a wrong `generated` call. None found. The one project with the
largest authored-but-unclassified set, `L5GN-Armory_v2` (6 of 6 authored docs
unclassified), is a personal journal
(`L5GN_Journal/StopAskingQuestionsStartBuildingPipelines/…`) — genuinely
ordinary prose, correctly left unclassified rather than miscategorised.

Applied to this repo's own `docs/` (84 documents, all authored — no
directory here starts with `.` or `_`): 74/84 classified (88.1%), with the 10
unclassified being `SPEC_Chronicler.md` and a handful of `archive/` and
`investigation/` notes — exactly the "ordinary prose" case the brief says is
not a failure state.

---

## Report back (evidence gathered, not ruled on)

**L5GN-Castle and Task B's rule (1.A2).** Castle's `file_census` payload
(1.1 MB, capped) is dominated by `data/Chronicler_Backup/raw_gem_files` and
`data/chat_threads/raw_gem_files` — **byte-for-byte identical**
(165,246,539 bytes, 110 files, in both places), plus matching duplicate pairs
under `raw_gemini_files` and `raw_claude_files`. This confirms the brief's
suspicion of backup and duplicated folders. But **Task B's provenance rule
would not classify this payload out**: none of `Chronicler_Backup`,
`raw_gem_files`, `raw_gemini_files`, or `raw_claude_files` start with `.` or
`_`, and none are on the explicit list. (They *are* already excluded from
`doc_census`'s own content walk by `_scope.py`'s `DATA_DIR_PREFIXES`/
`DATA_DIR_SUFFIXES` — `raw_*` and `*_files` — but that is the existing
data-dir wall, not this brief's provenance rule, and it doesn't touch
`file_census`, which is where the 1.1 MB payload actually lives.) The 1.A2
ruling — how a non-git folder's data directories get classified out when
there is no `.gitignore` to do it — is still open, and this build's rule does
not close it.

**Document mtime.** Not captured. Per the brief, this is Tim's call, not
built speculatively: one field, cheap to add now, wasteful to re-walk every
document later for. Flagging for a decision, not building the staleness
metric it would feed.

---

## Explicitly out of scope (unchanged from the brief)

Vault/thread data joining, any change to `todo_adr_scanner`'s counters, and
the 1.A2 ruling itself remain undone, as specified.
