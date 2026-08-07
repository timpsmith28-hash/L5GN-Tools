# Cowork report — Knowledge Curator, K0–K5

**Brief:** `docs/COWORK_BRIEF_knowledge_curator.md`. **Ratification:**
DECISIONS 0032. **Status:** built, gate-GREEN on a personal-rig machine
(`LucasGoonPC`) that has no MCF corpus, no Cowork transcript store beyond
this toolkit's own, and no LM Studio instance — **the real run against the
MCF corpus has not happened yet.** It must run on the work rig (`10280L`
in `config/local.json`), where the MCF repos, the real Cowork transcript
store, and LM Studio all actually live. This report records what was built
and hermetically verified here; the sections the brief's own Reporting
requirement asks for (ratification record, quote-rejection rate,
per-project yield, how often Superseded fired) can only be filled in after
that real run, and are marked pending below rather than fabricated.

## What was built

- **DECISIONS 0032** — the precondition ruling the brief required before any
  code: local-store-only, MCF-scoped, recency-as-truth-order.
- **`chronicler/pipeline/local_transcripts.py`** extended (not replaced,
  per the brief's explicit "do not write a second discoverer") to surface:
  - `conversation_id` (the `local_<uuid>` folder) and `cowork_project_dir`
    (the Cowork store's own `<project-id>` segment) on every
    `TranscriptFile`/`ParsedSession`.
  - `group_conversations()` — one conversation, N transcript files (resumes,
    `subagents/agent-*.jsonl`), with real-time resolution in the brief's own
    three-source priority (last message timestamp → file mtime → folder
    mtime), naming which source was used, and excluding (never guessing)
    a conversation with no resolvable time.
  - `order_newest_first()`, `first_user_message()`, `earliest_session()`.
- **K0 — `chronicler/pipeline/bootstrap_conversation_map.py`.** Two-pass
  matcher (literal-prefix pass 1, floor-gated full-content substring pass 2)
  producing a **candidate** map for human ratification, never applied
  automatically. Implements the brief's ambiguity rule exactly: colliding
  candidates in the same on-disk Cowork project are accepted and paired by
  date; colliding candidates across different projects are refused, both
  named, left unmatched. Emits all six required counts, including the
  zeroes.
- **K1 — `chronicler/pipeline/knowledge_index.py`.** Loads the *ratified*
  `config/mcf_conversation_map.tsv` (currently a header-only template —
  nothing has been ratified yet, see below), reconciles it against the real
  store in both directions, sanity-checks curated labels against each
  conversation's own title (report-only, never auto-resolved), and globs
  each mapped project's `*KNOWLEDGE*.md` via `doc_census`'s existing rule
  (no second rule invented). Three-state `unresolved` per project: no
  mapping / mapped but folder absent on this machine / present but
  unreadable.
- **K2 — `chronicler/pipeline/extract_claims.py`.** Newest-first claim
  extraction via a local LM Studio call (stdlib `urllib.request` only,
  OpenAI-compatible `/v1/chat/completions`), with `quoted_source` verified
  as a literal Python-checked substring of the transcript — never trusted
  from the model's own "confirmed" flag. Rejections counted, not retried.
  Zero-claim conversations recorded, never omitted. Cached on each
  conversation's source files' `(path, mtime)`, so an unchanged conversation
  is never re-extracted.
- **K3 — `chronicler/pipeline/corpus_index.py`.** Chunks each knowledge file
  by heading; a file with no headings at all becomes one whole-file chunk,
  **flagged**. Hashed per file; re-chunks only what moved.
- **K4 — `chronicler/pipeline/match_claims.py`.** Two-stage match
  (similarity shortlist, LM Studio confirm with a Python-verified literal
  matched span) against the claim's own project corpus first. The four
  outcomes (captured / gap / superseded / cross-project), with supersession
  resolved by ordering alone — the newest claim on a topic "establishes"
  current truth (whether or not it is itself captured in a knowledge file
  yet), and a conflicting older claim is flagged against it without ever
  deciding which one is *true*.
- **K5 — `chronicler/pipeline/compile_report.py`.** Assembles
  `data/knowledge_curator/report_<date>.md` (never under `docs/`, per 0030)
  in the brief's five-section order, with a header carrying model id,
  endpoint, counts, and the quote-rejection rate, so a thin run reads as
  thin.
- **`config/mcf_conversation_map.tsv`** — committed as a header-only
  template. Real rows are K0's output, ratified by Tim, on the work rig.
- **Tests:** `tests/tester_bootstrap_conversation_map.py`,
  `tests/tester_knowledge_index.py`, `tests/tester_extract_claims.py`,
  `tests/tester_corpus_index.py`, `tests/tester_match_claims.py`,
  `tests/tester_compile_report.py`, plus extensions to
  `tests/tester_local_transcripts.py` for the new grouping/id surfacing.
  Every K2/K4 test drives the extraction/match logic against a **stub**
  caller — no LM Studio instance is required to keep the gate green.
  Registered in `verify.py`.

## Explicitly not done here (machine constraint, not scope cut)

This session ran on `LucasGoonPC`, a personal rig with no `mcf`-scoped root,
no Cowork transcript store beyond L5GN-Tools' own, and no LM Studio
endpoint reachable. That means, on this machine:

- **K0 cannot run for real** — there is no real curated sheet and no real
  MCF conversations to match it against.
- **K1's project-folder resolution has nothing to glob** — no `mcf` root is
  configured here.
- **K2/K4's LM Studio calls cannot execute** — nothing is listening on
  `localhost:1234` (or anywhere) on this machine.
- **K5 has nothing real to compile from.**

Everything above was instead verified **hermetically**: synthetic stores,
synthetic sheets, synthetic project trees, and stub model callers built to
match the brief's own worked examples (the WizForge same-project pairing,
the cross-project collision refusal, the churn-threshold supersession, the
60-character pass-2 floor, the no-heading whole-file flag). `python
verify.py` is GREEN with these tests registered.

## What still has to happen on `10280L`

1. Build the curated sheet (`local_folder`, `project_id`,
   `conversation_name`, `date`, `1st User Message`) for the 48 known MCF
   conversations, per K0's input shape.
2. Run `bootstrap_conversation_map.py` against it. **Ratify the candidate
   map by hand** — read the evidence column, not just the answers (brief's
   own `[H]` UAT item) — before it becomes `config/mcf_conversation_map.tsv`.
3. Run K1 → K5 in sequence, pointed at the real store, the real `mcf` root,
   and a real LM Studio model.
4. Fill in `docs/UAT_knowledge_curator.md` against the real output — the
   walk-sheet below is currently a skeleton with every item unwalked.
5. Update this report's provenance section with: the ratified map's
   inconsistency resolutions, the real quote-rejection rate, per-project
   yield, and how often Superseded actually fired (the brief is explicit
   that if it never fires, the ordering design bought nothing, and that
   has to be said plainly, not omitted).

## Provenance (pending real run)

- Ratified map inconsistency resolutions: **pending**
- Quote-rejection rate: **pending**
- Per-project yield: **pending**
- Superseded path fire count: **pending**
