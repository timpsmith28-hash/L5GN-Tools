# Cowork brief — the local deck, slice 1: the knowledge base, and the time dimension

**Origin:** design thread, 2026-07-28. First slice of a **local-only Command
Deck** — the mesh vision, standing alone on one machine.
**Builds on:** DECISIONS 0025 (visibility is scoped by surface), 0026 (knowledge
documents), and the doc provenance/coverage round (`87253c8`).
**Deliverable:** the deck reads authored documents and searches them, and renders
the time dimension the report has never shown.

Two enrichments, one slice, because they are complementary joins over data already
on disk: **what you know**, and **when it happened**. Neither needs a new scanner,
a new dependency, or the vault.

---

## Precondition ▸ DECISIONS 0027 must be ratified before any code

This slice renders **document content**, which no current decision authorises. The
reports have always been summary-only, and that rule is right — but its reason is
specific, and understanding it is what makes this safe rather than a relaxation.

**Draft the entry below to Tim, get it ratified and committed, and only then
build.** If he rules against it, Task 2 and Task 3 fall away and the slice becomes
Task 4 alone.

> ## 0027 — Summary-only governs artefacts that travel; a local surface reads the source at render time
>
> **Date:** 2026-07-28 · **Status:** proposed · **Builds on:** 0010 (the wall),
> 0013 (serve a snapshot), 0025 (gate the surface, not the data) ·
> **Source:** design thread
>
> **Context.** Scanners capture summaries and never contents — sizes, counts,
> titles, 120-character marker excerpts — and `blast_radius` explicitly stores no
> script body, alias or credential. The reason is that **the report is a deposit
> artefact**: it is pushed to the knight, consumed by other estates, and lands
> beside material it must never carry. That is why 1.A2 treats even leaked *paths*
> as a defect. The rule protects the artefact, not the operator.
>
> A local-only surface is not an artefact. It renders on the machine that owns
> the files, to the person who already owns them, and nothing it displays leaves
> the process. The constraint that makes summary-only necessary simply is not
> present.
>
> **Decision.** The summary-only rule is **unchanged for anything that is
> captured, written to `data/`, or deposited.** Separately, a **local-only
> surface may read a file from disk at render time** and display its contents,
> provided:
> 1. it persists nothing — no cache, no copy under `data/`, nothing that could be
>    deposited;
> 2. it is bound to loopback, enforced structurally as 0025 already requires; and
> 3. it reads only within the configured estate roots and vault home — never an
>    arbitrary path supplied by the caller.
>
> **Consequences.** `blast_radius`' guardrail stays literally true: nothing is
> stored, so nothing can leak through a deposit. The deck gains full fidelity
> without a single scanner capturing more than it does today. The risk moves from
> *what the artefact contains* to *what the surface can reach*, which is why (3)
> is a hard requirement and not a nicety: a render-time reader with a path
> parameter is a file-disclosure bug waiting for the day someone binds it wrong.

---

## Working rules

- Stdlib-only. **FTS5 is available** in the bundled sqlite3 (confirmed, 3.37.2) —
  but capability-check it at runtime and degrade to a plain substring search with
  a visible notice rather than crashing. Honest failure, per house style.
- Read-only. This slice adds **no write path whatsoever**.
- Gate GREEN before commit. All logic in testable functions, not route handlers.
- Nothing persisted: no index file under `data/`, no cached document text. Build
  the FTS index **in memory** at startup, or accept the search cost per query and
  say which was chosen and why.

---

## Grounding — what exists, and the one real obstacle

- **`data/estate.json`** (via `common.DATA_DIR`) carries every project's
  `doc_census` (now with `doc_type` and `provenance` per document, from `87253c8`),
  `git_summary`, `git_deep_history`, `blast_radius`, `todo_adr_scanner` and
  `file_census`. All of it is already on disk after `run.py build`.
- **`data/history/estate-*.json`** — prior builds, the input to "what changed".
- **`config/authors.json`** — author aliasing, already used by `tester_authors`.
- **`chronicler/review/app.py`** is the surface to extend (the standing ruling: one
  service, not two). It already resolves the estate, enforces the loopback rule for
  a non-personal estate, and refuses to serve when the estate is `both` — this
  slice inherits all three for free, which is most of 0027's condition (2).

**The obstacle, and it needs solving explicitly:** `run.py review`'s preflight
exits 2 when the **vault DB** or the **registry** is missing — reasonable for a
write endpoint over threads, wrong for a document viewer that needs neither. On a
plain producer rig with no vault, this slice must still run.

Fix it properly rather than around it: split the preflight into *what the surface
needs* rather than one all-or-nothing check. Vault-backed routes (the review
queue) degrade to a clear "no vault on this machine" state; estate-backed routes
(this slice) require only `data/estate.json`. **A machine with a vault and no
estate build, or an estate build and no vault, must both work.** Say in the report
which routes now require what.

---

## Task 1 ▸ the estate data layer

A read-only module (suggested `chronicler/review/estate_data.py`, or a sibling if
that crosses a boundary you can name) that loads `estate.json` once at startup and
exposes it. Stale-data honesty matters: surface `generated_at`, `toolkit_commit`
and `toolkit_dirty` in the UI header, because a deck rendering a three-day-old
build must say so.

If `estate.json` is absent, the estate routes report that cleanly and the rest of
the app still serves.

## Task 2 ▸ the knowledge base — readable

- The coverage grid from `87253c8` becomes **navigable**: project → its authored
  documents, grouped by `doc_type`, with `knowledge` first.
- Selecting a document **renders it**, read from disk at render time per 0027.
  Markdown may be rendered as text with headings preserved, or lightly formatted —
  no markdown library, so a minimal heading/paragraph pass or `<pre>` is fine.
  Choose the simpler one and say why.
- **The path safety requirement is the whole security story.** The route must
  **not** accept a filesystem path. It takes an opaque identifier (project +
  index, or a hash) resolved against the in-memory document list built from
  `estate.json`. Any resolved path must then be verified to sit inside the
  configured estate roots before a single byte is read. Two independent checks,
  both required, with a tester for each: a path outside the roots, and an attempt
  to traverse (`../`) through the identifier.
- **Generated documents are not offered.** This slice reads authored docs only.
  The 734 generated documents on the personal estate are machine output; making
  them browsable is a different feature with a different justification.

## Task 3 ▸ search across the knowledge base

- Full-text search over **authored** documents, FTS5 where available.
- Results carry project, document title, `doc_type` and a snippet with the match
  in context. Ranked by relevance; `knowledge` documents surfaced distinctly,
  since 0026 makes them the artefact of record.
- Scope the search to one project or the whole estate.
- **This is the feature that justifies the slice.** The work estate exists to get
  knowledge out of Tim's head; "I wrote that down somewhere" becoming a query is
  the return on it.

## Task 4 ▸ the time dimension

The report renders none of this today, and all of it is already on disk.

- **Per project:** first and last commit, commit count, active span, and
  contributors resolved through `config/authors.json`.
- **Estate timeline:** projects laid out on a shared time axis, so the lineage is
  visible — Armory → Armory_v2 → Armory_v4, Castle → mesh-vertex.
- **What changed since the last build:** diff the current `estate.json` against
  the most recent `data/history/estate-*.json` — projects appeared or vanished,
  document counts moved, markers appeared, blast-radius tiers changed. Say plainly
  which two builds are being compared, by timestamp and commit.

Where a project has no git history (four non-git folders on the work estate, two
on the personal), say so — do not invent a span from mtimes. The
`build_activity` `Path("")` defect is the cautionary tale: a fabricated window is
worse than an absent one.

---

## Explicitly out of scope

- **Threads and vault data** — the separate slice, deliberately deferred.
- **Evidence drill-down** (markers, blast-radius hits, secrets shown in context) —
  the next brief. It depends on 0027 and on Task 2's path-safety machinery being
  proven first, which is why it follows rather than rides along.
- Cross-project document overlap — the fourth slice, and much stronger once search
  exists.
- Any LLM or inference feature (0018/0019). Out of this round entirely.
- Any write path. This slice writes nothing.

---

## UAT — acceptance checks (Tim walks these)

- **A knowledge document opens in the deck**, on the machine that owns it, and the
  content matches the file.
- **Search finds something you had forgotten.** The honest test: search a term you
  know is somewhere in the MCF knowledge docs and see whether it surfaces the right
  document. If it doesn't, that is a finding.
- **Path safety.** A crafted identifier cannot read a file outside the estate
  roots — tester-proven, and worth one manual attempt.
- **No vault, still serves.** On a machine with `estate.json` and no vault, the
  document and time views work and the queue view says why it can't.
- **Staleness is visible.** The header states the build's `generated_at` and
  commit, and a deliberately stale build reads as stale.
- **Nothing persisted.** After browsing and searching, `data/` contains no new
  file and no cached document text.
- **Time views are honest.** A non-git project shows "no history", not a made-up
  span.

Mark each **ready to walk**. Results log needs a uat stamp naming the commit; do
not write a `gate=` field.

---

## Reporting

`docs/COWORK_REPORT_local_deck_docs_and_time.md`, walk-sheet
`docs/UAT_local_deck_docs_and_time.md`, stamped results after the walk. Record the
0027 ratification, the preflight split (which routes need what), the FTS5
capability result, and the path-safety tests in full.
