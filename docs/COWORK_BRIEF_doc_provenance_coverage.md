# Cowork brief — document provenance and coverage: make the doc census mean something

**Origin:** design thread, 2026-07-28, after the archiving sweep and the
cross-estate document measurement.
**Implements:** DECISIONS **0026** (knowledge documents are a first-class
governance artefact with their own shape).
**Deliverable:** `doc_census` reports *authored vs generated*, classifies by
document type, and the report gains a coverage grid.

Measured on both estates on 2026-07-28: the work estate has **77 docs, 36
classified (46.8%)**, with `_KNOWLEDGE_` docs in four of nine projects. The
personal estate has **824 docs, 45 classified (5.5%)** — and that second number is
not a governance signal. **646 of those 824 are generated output in two
projects.** A ratio computed over a denominator full of machine output measures
nothing, and would report the personal estate as catastrophically undocumented
when the real difference is that it generates markdown as a side effect.

Two changes, one scanner: give documents a provenance tier so the denominator is
honest, then say *which* load-bearing document types each project has and lacks.

**Read first:** `l5gntools/scanners/doc_census.py` (the whole file — it is short),
`l5gntools/scanners/file_census.py`'s tiering and `_at_risk_note` (the precedent
to copy), `l5gntools/scanners/_scope.py`, `docs/DECISIONS.md` **0026**, and
`archive/COWORK_BRIEF_governance_scanners.md`'s stamp (why `decisions_count` is
narrow and must stay so).

---

## Working rules

- Stdlib-only, read-only, no new dependency. Gate GREEN before commit.
- **Path-and-name rules only. Never inspect content to decide provenance.** A
  classifier that reads prose is the large check that rots; this estate's
  doctrine is small mechanical checks that always run (`auditor_doc_claims`'s own
  design note).
- Every rule must be **statable in one sentence** and listed in the report.
- Counts are always shown **beside** ratios, per 0026.

---

## Grounding — what is already there

`doc_census.scan` walks `.md` files through `Scope`, and returns per project:
`doc_count`, `has_readme`, `has_claude_md`, `has_glossary`, `adr_files`, and a
`docs` list of `{path, title, headings, words, bytes}`. It already skips
gitignored paths — which is exactly why the two worst offenders are invisible to
that skip: **CID and Crystal-Spire commit their generated docs, and L5GN-Archive
is not a git repo at all**, so there is no `.gitignore` to classify anything out.

`file_census` is the precedent for everything below: three honest tiers, a
`truncated` flag that never lies, `basenames_beyond_cap` so a cap doesn't create
a blind spot, and `_at_risk_note` stating *why* a project is unprotected.

### The measured evidence — do not re-derive this, but do verify it

| project | generated docs under | share |
|---|---|---|
| L5GN-Continuous-Ingestion-Daemon | `.vault/` (282 in `.vault/gap`) | 341 / 358 |
| L5GN_Armory_v4 | `_citadel_intel_docs/` (227 in `campaign_modules`) | 286 / 288 |
| L5GN-Crystal-Spire | `_archive/` (43 in `pipeline_data`), `logs/` | 53 / 97 |
| L5GN-Armory_v2 | `output/`, `_citadel_artifacts/` | 21 / 27 |
| L5GN-Archive | `AutoFiles/` (versioned v1.1–v1.3) | 24 / 25 |

**A path segment beginning with `.` or `_` accounts for roughly 685 of the 779
unclassified documents by itself.** The estate has been following a convention it
never named.

---

## Task A ▸ classify by document type (0026)

Add a `doc_type` to each entry in the `docs` list, and a per-project tally.

- **`knowledge`** — filename contains **`_KNOWLEDGE_`, case-insensitive,
  unanchored** (0026 as ratified). In practice a suffix
  (`SolConfig_Knowledge.md`, `LEGACY_BUNDLE_KNOWLEDGE.md`), but do not anchor it.
- **`adr`** — an `adr` path segment (today's `adr_files` rule, kept).
- **`decisions`** — filename contains `DECISIONS`.
- Plus the shapes both estates already use: `readme`, `intent`, `architecture`,
  `runbook`/`playbook`, `brief`, `report`, `uat`/`checklist`, `plan`/`status`,
  `glossary`, `claude_md`.
- **`unclassified`** — everything else. Not a failure state; most documents in a
  healthy repo are ordinary prose.

Report per project: `doc_count`, `classified_count`, `classified_pct`, and the
tally by type. **Raw counts always beside the ratio** (0026).

**Do not** extend `todo_adr_scanner._DECISION_ENTRY`. 0026 rules that the ADR
counter stays narrow; a count that catches knowledge docs too distinguishes
neither.

## Task B ▸ the provenance tier — authored vs generated

Each document gets `provenance: "authored" | "generated"`. Every metric in Task A
is computed over **authored only**, with the generated count reported separately
and visibly — never silently dropped.

**Candidate rule, to verify before adopting:** a document is `generated` if any
path segment begins with `.` or `_`, or is one of a short explicit list
(`output`, `logs`, and whatever the verification below justifies adding).

**Verify it against both estates before it ships**, and put the numbers in the
report:

1. How many of the personal estate's 824 does the rule catch? (Expect ~685 from
   the dot/underscore rule alone; ~725 with `output`/`logs`/`AutoFiles`.)
2. **False positives are the thing to hunt.** Does the rule wrongly mark any
   *authored* document as generated — on either estate? The work estate's docs sit
   under `docs/`, `briefs/`, `PoC/` with no leading dots or underscores, so the
   expected answer is none; confirm it rather than assume it.
3. If a rule earns its place only by catching one project's folder name
   (`AutoFiles`), say so plainly and let Tim rule on whether it belongs. A rule
   that generalises is worth more than a rule that fits.

**A project may legitimately be almost entirely generated.** L5GN-Archive at 24/25
is not a finding about documentation practice; it is a fact about that folder.
Report it as such.

## Task C ▸ the coverage grid

In `report.html`'s Docs tab: a matrix of **project × document type**, ticks and
blanks, over authored documents only.

The point is *what is missing where*, not a score. Tonight's data is the worked
example: SolConfig has a knowledge doc and a runbook; ValidationAutomation has a
decisions log and an intent; UnifedIntelligenceSource has three documents and
none of the load-bearing types.

**Present it as coverage, never as a score, and give it no total or rank.** A
scorecard invites gaming, and a project with one excellent README does not need a
row of ticks to be in good order.

## Task D ▸ an out-of-band document count is an anomaly

`file_census` already flags a capped or oversized payload in the report banner.
Do the same for a project whose authored document count is wildly out of band
with the rest of the estate — 358 markdown files in one repo is worth surfacing
in its own right.

Threshold should be **relative to the estate**, not a hardcoded number; state the
rule chosen and why.

---

## Report back on, but do not decide

- **Whether the Task B rules would classify `L5GN-Castle`'s payload out.** Castle
  still emits a capped 1.1 MB `file_census` payload (2026-07-28 build), and the
  suspicion is backup and duplicated folders. This is evidence for the open 1.A2
  ruling — how a non-git folder's data directories get classified out when there
  is no `.gitignore` to do it. **Gather it; do not rule on it.**
- **Whether to capture each document's mtime while you are in there.** One field,
  and it is the input to a staleness check (a knowledge doc untouched since the
  code moved past it) that the defensibility direction will want. Re-walking every
  document later to add one field is wasteful; building a metric nobody asked for
  is worse. **Put it to Tim; do not build the staleness metric.**

## Explicitly out of scope

- Joining vault/thread data into the report (the third enrichment option,
  deliberately deferred — it renders only where both halves exist and needs the
  0023/0025 visibility rules applied to a second surface, so it wants its own
  decision entry).
- Any change to `todo_adr_scanner`'s counters.
- The 1.A2 ruling itself; the Castle investigation.

---

## UAT — acceptance checks (Tim walks these)

- **The personal estate's number becomes honest.** Authored-only classified % is
  reported, with the generated count beside it, and the two projects holding 646
  generated docs are visible as such rather than dragging the ratio down silently.
- **No authored document is marked generated** on either estate — the false
  positives from Task B step 2, checked by eye against a handful of real paths.
- **`_KNOWLEDGE_` matches unanchored and case-insensitively**, and finds the six
  known docs across ActivityStatements, ChurnLevelIndictor, SolConfig, TSsToAssets.
- **The grid reads as coverage.** Opening the Docs tab, it is obvious what
  UnifedIntelligenceSource lacks without any number implying it is *failing*.
- **The rules are listed in the report**, so a cold reader can see what "generated"
  meant on this build.
- `verify.py` GREEN; existing `doc_census` consumers unaffected.

Mark each **ready to walk**. Results log needs a uat stamp naming the commit; do
not write a `gate=` field.

---

## Reporting

`docs/COWORK_REPORT_doc_provenance_coverage.md`, walk-sheet
`docs/UAT_doc_provenance_coverage.md`, stamped results after the walk. Record the
before/after numbers for both estates, the final rule list, every false positive
found, and the two report-back items above.
