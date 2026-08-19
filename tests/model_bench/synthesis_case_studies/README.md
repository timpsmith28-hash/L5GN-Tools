# `tests/model_bench/synthesis_case_studies/`

Cross-conversation synthesis is a new eval dimension for the model bench,
sitting alongside Level 1 (eval set) and Level 2 (single-conversation
claim-to-ruling ground truth): can a candidate model correctly reconstruct
the full story behind a `DECISIONS.md` ruling when the evidence for it is
scattered across several separate conversations, days apart?

This directory holds one JSON file per case study -- the "answer key" a
candidate model's synthesis output gets checked against. Nothing here is
wired into `verify.py` or the K2/K4 pipeline; these are hand-verified
research artifacts, built the same way Level 2 ground truth is: read the
real transcript, quote the real text, cite the real ruling number, never
invent a mapping without a literal anchor (repo ruling 0037's ethos).

## How a case study is built

1. Run `scan_all_decisions.py` (in this folder) against a `claude_migration`-
   style backup snapshot. It reports three things -- see "The scanner" below.
2. Pick a ruling whose EXACT conversation-count sits in the volume band you
   want -- conversation-count, not raw mention-count, is the primary signal
   (see 0008 and 0012's caveats in the table below for why raw counts
   mislead).
3. Read every conversation that mentions it, in timestamp order, and log
   each event as a `{conversation_id, timestamp, speaker, quoted_substring}`
   entry.
4. Cross-check the assembled timeline against `docs/DECISIONS.md`'s own
   text for that ruling. Note any place the transcript confirms, extends,
   or (if it happens) appears to contradict the ratified text.
5. Write a short "why this is a good benchmark item" section: what makes
   the story genuinely require multiple conversations, what a shallow read
   would plausibly get wrong, and any trap in the raw scan numbers
   themselves (boilerplate repetition, single-conversation mention counts
   that look like spread but aren't, etc).

## The scanner

`scan_all_decisions.py` reports three things:

- **Exact matches** -- the literal `00NN` form (`0017`, `0012`, ...). High
  precision; this is what the six case studies below are built from.
- **Fuzzy matches** -- "decision seventeen", "ruling #17", "DECISIONS no. 9"
  -- a reference naming a ruling near the word "decision"/"ruling" without
  the zero-padded form. Lower precision: a 2026-08-18 test run found
  `0001` and `0002` with implausibly high fuzzy counts (9-10 conversations,
  28-38 mentions), almost certainly generic ordinal-list false positives
  ("decision 1: ...", "step 2 of 3") rather than real references to
  `docs/DECISIONS.md`. Fuzzy hits are a lead to go read, never evidence on
  their own.
- **Co-mention pairs** -- two flavours. Per-message (tight: both ruling
  numbers named in the same message) and per-conversation (loose: both
  appear somewhere in the same conversation). These are how the
  `local_e9841a20` intersection below was found systematically rather than
  by accident.

## Co-mention findings worth following up (2026-08-18 run)

Per-message, tightest coupling: `0023+0025` (36 messages), `0017+0018` (30),
`0017+0023` (30), `0025+0028` (26), `0027+0028` (26), `0018+0023` (26),
`0025+0027` (24), `0011+0017` (22).

Per-conversation: `0005+0006` and `0012+0017` both hit 6 conversations each
-- the joint-widest spread of any pair. `0025+0027`, `0025+0028`, `0027+0028`
each hit 5 -- suggesting 0025/0027/0028 (all governance-surface rulings) may
be as tightly bound a cluster as 0012/0017/0018 turned out to be, and worth
its own case study or a combined one.

## The six case studies

Counts are exact-match only, from the 2026-08-18 scan against
`C:\Users\timps\backups\claude_migration`. Real `DECISIONS.md` entries run
0001-0049; `0000` and any number with no matching `## 00NN -- ...` heading
is a scan false positive (a version string, a port number, etc) and should
be discarded.

| tier | ruling | title | n_conversations | n_mentions | note |
|---|---|---|---|---|---|
| low | 0008 | Rendered `.md` is read-only output; sync-back to be removed | 1 | 14 | deliberate null case -- genuinely one conversation, a good test of not over-synthesizing |
| low | 0009 | Deferred: a self-hosted git-backed notes vault | 2 | 10 | small, clean two-conversation arc a week apart |
| mid | 0018 | Persona/LLM inference is a separate, pluggable service | 5 | 54 | clean drafted -> relied-upon -> audited -> reused-as-precedent arc over 14 days; co-mentions heavily with 0017 and 0023 |
| mid | 0026 | Knowledge documents are a first-class governance artefact | 4 | 110 | fast draft-to-shipped-code loop (hours); most raw mentions are boilerplate co-listing with sibling rulings, not independent discussion |
| high | 0012 | The registry is three-tier: program -> project -> repo | 10 | 80 | raw count inflated by 5 conversations that only contain a pasted reference header, not discussion -- real story is ~5 substantive conversations; ties 0005+0006 for widest per-conversation co-occurrence spread, paired with 0017 |
| high | 0017 | The `projects` table is reset and rebuilt, not migrated | 6 | 174 | the founding case study -- drafted, lost, rediscovered, ratified, all across 6 conversations over 6 days; highest per-message co-mention volume of any ruling (with 0018, 0023, 0011) |

0012, 0017 and 0018 all intersect in one conversation --
`local_e9841a20-5eed-4d79-a613-b5f17b8f49fd`, 2026-07-27 -- where three
separate rulings' threads converge in a single audit session. Worth using
as a combined benchmark item once individual case studies are validated.

## Files in this folder

- `scan_all_decisions.py` -- the census script, rerunnable any time against
  a backup snapshot: `python scan_all_decisions.py --root <path>`.
- `case_study_decisions_0008.json`
- `case_study_decisions_0009.json`
- `case_study_decisions_0012.json`
- `case_study_decisions_0017.json`
- `case_study_decisions_0018.json`
- `case_study_decisions_0026.json`

## Next step: the Knowledge Curator itself

Once these are trusted, the real test is whether the Curator (K2/K4) can
independently reconstruct a case study's story from the raw conversations
-- decision-record checking is explicitly part of what the Curator is
meant to do. That's a full pipeline run against real LM Studio, which
(per this whole brief's ground rules) happens on your machine, not here.

## Known limitation

Every case study here was built from a single reader's (mine) pass over
the transcripts -- there's been no adversarial check that a quoted
substring is read in correct context, or that no relevant conversation was
missed. The fuzzy-match false-positive rate found in this run (0001, 0002)
is a concrete reminder to spot-check rather than trust these as audited
ground truth.
