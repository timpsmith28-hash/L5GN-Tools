# Knowledge Curator — Design & Build Spec, v1

Goal: catch knowledge that lives in conversation but never made it into a
project's authored `KNOWLEDGE*.md` files, and catch knowledge that's useful
across more than one project but only written down in one — without ever
writing into those files itself.

A standalone tool, not a Chronicler pipeline stage. It **reads** `chronicler.db`
(threads, messages) and each project's `KNOWLEDGE*.md` files; it never writes
to the DB and never edits a KNOWLEDGE file. Its one output is a compiled
report for Tim to act on by hand. Same posture as `relink.py`'s dry-run
default and the "manual is never auto-touched" rule elsewhere in this repo —
here the entire tool is the dry-run.

**Build order: K1 → K2 → K3 → K4 → K5 (core loop, ship first), then K6
(open questions / polish).** Each stage is independently testable.

**Standing rules (apply to every stage, no exceptions):**
- Read-only against `chronicler.db`. No new tables, no writes to `threads`,
  `messages`, `review_queue`, or any existing Chronicler table.
- Never edits a `KNOWLEDGE*.md` file. The report is the only output.
- Loud failure: a stage that can't complete states so and stops; no partial
  report. If LM Studio is unreachable, the run aborts before producing
  output — a half-run report that looks complete is worse than no report.
- Every claim in the report is **quoted, not summarized**, from both sides —
  the thread text it came from and the KNOWLEDGE line it matched (or didn't).
  Small local models narrate confidently and wrongly; forcing quotes keeps
  the report checkable in one glance, same reasoning as Chronicler's
  evidence-row discipline (`link_evidence`, never a bare score).
- All file I/O UTF-8 explicit. All timestamps UTC ISO-8601.

---

## K1. Project ↔ Knowledge-File Registry

**What:** For every project, resolve two things: its `project_link` id (to
scope Chronicler threads) and the on-disk paths of its `KNOWLEDGE*.md` files.

**Source:** Read the **generated** registry (Chronicler's `relink.py`
`REGISTRY_PATH` output, not the manual `config/project_registry.json` seed) —
the generated file carries the `path` field per repo, attached from estate
snapshots (see `SPEC_Chronicler.md` S1). Do not re-derive paths separately;
reuse this join surface so the two tools never disagree about where a
project lives.

**Build tasks:**
1. `pipeline/build_knowledge_index.py`: for each repo entry with a resolved
   `path`, glob `**/*KNOWLEDGE*.md` (case-insensitive) under that path,
   capped at a reasonable depth to avoid walking into `node_modules`/`.venv`
   equivalents (reuse whatever ignore list `build_registry.py` already uses
   for its file inventories — don't invent a second one).
2. Output `data/knowledge_curator/knowledge_index.json`:
```json
{
  "generated_at": "2026-08-06T12:00:00Z",
  "registry_source": "<path to the generated registry read>",
  "projects": [
    {
      "project_id": "citadel-microide",
      "canonical_name": "Citadel MicroIDE",
      "knowledge_files": [
        "L5GN-Armory_v4/docs/KNOWLEDGE.md",
        "L5GN-Armory_v4/docs/KNOWLEDGE_deploy.md"
      ]
    }
  ],
  "unresolved": ["<project ids with no repo path in the registry — logged, not silently skipped>"]
}
```

**Acceptance:** every project with at least one on-disk `KNOWLEDGE*.md` file
appears with correct paths; projects with none appear with an empty list
(not omitted — an empty list is itself informative for K2/K4); `unresolved`
is non-empty only for genuinely path-less registry entries (e.g. Command
Deck, per its "no repo on disk yet" note).

---

## K2. Claim Extraction (LM Studio pass)

**What:** Turn thread content into atomic, checkable candidate claims —
"decided X because Y", "learned Z about the API" — the unit K4 matches
against KNOWLEDGE files. Thread-level "this thread relates to this file"
matching was ruled out in design discussion: too coarse, produces false
confidence.

**Model:** LM Studio, local, OpenAI-compatible endpoint
(`http://localhost:1234/v1` by default, configurable). Small/fast model by
design intent — this runs over every substantive thread across every
project, so cost-per-call matters more than frontier reasoning. The
extraction task (pull out declarative claims from a chat transcript) is
well within a small model's competence; the harder judgment calls (is this
*actually* new, is this a contradiction) are deliberately pushed to K4's
retrieval step and to Tim, not asked of the extraction model.

**Scope:** Chronicler threads with `project_confidence` in (`evidence`,
`manual`) only — same bar S7 uses for "counts as real." Suggestion-tier
links are noise for this purpose. Within scope, `substantive = 1` threads
only (the field already exists on `threads`; reuse it, don't re-derive).

**Build tasks:**
1. `pipeline/extract_claims.py`: per in-scope thread, feed `messages.content`
   (ordered by `seq`) to the model with a prompt constrained to: extract 0–N
   atomic claims, each as `{claim_text, quoted_source}` where
   `quoted_source` must be a verbatim substring of the thread content (not
   the model's own paraphrase) — reject/retry any claim whose quoted_source
   doesn't literally appear in the input.
2. Cache: watermark on `messages.message_id` / thread `updated_at`, same
   pattern as S5's `path_scan_log` — only re-extract threads that are new or
   changed since the last run.
3. Output rows to `data/knowledge_curator/claims.json` (or a small local
   sqlite table if volume warrants — decide at build time based on real
   thread counts, not in advance):
```json
{
  "thread_id": "...",
  "project_link": "citadel-microide",
  "claim_text": "Retry backoff on the ingest daemon is capped at 30s, not exponential past that",
  "quoted_source": "...",
  "extracted_at": "2026-08-06T12:00:00Z"
}
```

**Acceptance:** run against a real sample of ~20 threads spanning at least 3
projects; spot-check that every `quoted_source` is a real substring of the
source thread; confirm the cache watermark skips unchanged threads on a
second run.

---

## K3. Knowledge Corpus Index

**What:** Parse each project's `KNOWLEDGE*.md` files into matchable chunks
(the retrieval side K4 checks claims against).

**Build tasks:**
1. `pipeline/index_knowledge_corpus.py`: chunk by heading section (H2/H3 —
   whatever granularity the actual files use; inspect a sample before
   committing to a rule), not by fixed token windows — headings are the
   author's own claim boundaries and preserve citability (K4's report needs
   to point at a real heading, not "somewhere in a 4000-word file").
2. Output `data/knowledge_curator/corpus_index.json`, one entry per chunk:
   `{project_id, file, heading_path, text, line_start}`.
3. Skip-if-unchanged: hash each file's content, only re-chunk files whose
   hash moved since the last run.

**Acceptance:** every file listed in K1's `knowledge_files` produces at
least one chunk (a file with zero headings still yields one whole-file
chunk, never silently dropped); re-run with no file changes touches zero
chunks.

---

## K4. Match Pass — the engine

**What:** For every extracted claim (K2), check it against the corpus (K3)
twice: against its **own** project's chunks (gap check, output a) and
against **every other** project's chunks (cross-project relevance, output
b). Same claim, same retrieval mechanics, two different questions asked of
the result — deliberately one pass, not two separate pipelines, since the
match step is the expensive part and both questions consume its output.

**Matching:** start with lexical/embedding similarity (whatever's already
available locally — reuse LM Studio's embedding endpoint if the loaded
model exposes one, otherwise a simple TF-IDF-shaped score in the spirit of
`SPEC_Chronicler.md` S2, not a new dependency) to shortlist candidate
chunks per claim, then a second local-model call to confirm/reject each
shortlisted pair with a yes/no + the matched span quoted back. Two-stage
because "does this claim already appear in this file" is a confirm
decision, not a similarity score, and similarity alone over-triggers on
generic phrasing.

**Decision rules:**
- Own-project check, no confirmed match anywhere in that project's chunks →
  **gap candidate** (output a).
- Own-project check, confirmed match → **captured**, logged for the report's
  audit section (output c) — proves the run actually checked it, not just
  that nothing fired.
- Other-project check, confirmed match in project B's corpus for a claim
  whose thread is scoped to project A, AND no confirmed match already
  exists in A's own corpus for that claim → **cross-project candidate**
  (output b): "this is written down in B, may be useful in A, isn't in A
  yet." (If it's already in both, that's just `captured` for both — not
  flagged twice.)
- No decision is ever written back into `threads` or any KNOWLEDGE file.
  This stage only produces the report's row data.

**Acceptance:** dry-run against real data across all projects; manually spot
-check 10 gap candidates and 10 cross-project candidates for whether the
quoted spans actually support the verdict; confirm idempotency (re-run with
no new threads/files produces the same report content, modulo the
`generated_at` stamp).

---

## K5. Compiled Report

**What:** The single human-facing output — everything upstream exists to
produce this.

**Build tasks:**
1. `pipeline/render_report.py` → `docs/investigation/<date>_knowledge-curator-report.md`
   (dated, per the investigation-doc convention in `docs/README.md` — this
   is evidence from a run, not a maintained doc; if it earns a permanent
   home later that's a separate decision, not this tool's job).
2. Three sections, in this order:
   - **Not yet formalized** — one row per gap candidate: project, claim
     text, source thread (id + date), quoted source.
   - **Cross-project relevance** — one row per cross-project candidate:
     claim text, origin project (where it's written), target project (where
     it isn't), quoted span from the origin file.
   - **Confirmed captured** (audit) — count per project + a small sample,
     not the full list, so the report stays readable; proves coverage
     without burying the two sections that need action.
3. Header block on the report itself: run timestamp, thread count scanned,
   claim count extracted, projects covered, projects in `unresolved` from
   K1 (so a thin run is visible as thin, not mistaken for a clean bill of
   health).

**Acceptance:** report renders from real data across all projects in one
run; every row in sections a) and b) is traceable back to a real thread and
a real file location; report is readable top-to-bottom without needing the
underlying JSON.

---

## K6. Open questions (parked, not blocking K1–K5)

- **Re-run cadence.** Nightly like the other scheduled tasks, or on-demand
  only? Given LM Studio is a local model with no API cost, nightly is
  plausible, but decide after seeing real K2/K4 runtime on the full thread
  volume — no point scheduling a run that takes longer than the interval.
- **Report accumulation.** Each run is a new dated file per K5 — fine
  short-term, but if gap candidates recur unresolved across many runs
  that's noise, not signal. Consider a "seen before, still open" dedupe
  once there's more than one real run to look at — not designed blind.
- **Confirmed-captured drift.** If a KNOWLEDGE file is edited to *contradict*
  a previously-captured claim, this spec doesn't currently detect that as
  distinct from "gap" — it would just show as unmatched again next run.
  True contradiction detection (same topic, different answer) is a harder
  match-pass question than gap-or-not; parked until K1–K5 are running on
  real data and it's clear whether it's actually needed.

## What this does NOT include (parked, per standing decision)
- Any write path into `KNOWLEDGE*.md` files — this tool proposes, Tim edits.
- A UI. The report is a markdown file, read like any other investigation doc.
- Coupling to Chronicler's ingest pipeline — this stays a separate tool that
  happens to read `chronicler.db`, not a new pipeline stage inside it.
