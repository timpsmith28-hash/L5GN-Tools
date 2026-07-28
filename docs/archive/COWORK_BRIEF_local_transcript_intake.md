> **ARCHIVED** 2026-07-28 · completed pair · brief + report; walked as Part 4 of
> `UAT_work_rig_solo.md` rather than via a walk-sheet of its own
> Superseded by: nothing — `chronicler/pipeline/{local_transcripts,ingest_local_transcripts}.py`
> are the living output.
> Accurate history: Phases 0–3 in full, including Phase 0's record-type schema read from real
> files, and the rulings (source `claude-local`, account `<source>-<estate>` from machine config
> only, conversation-text-only content).
> Stop trusting: **the brief's own premise.** It assumed the personal export and the local store
> describe the same conversations, so the local store could be checked against a known-good
> answer. Phase 3 measured **zero overlap** — 71 local-only threads, 39 export-only, not one
> match — so the two sources are empirically disjoint and no dedupe rule is needed anywhere.
> Also: `local_transcripts.py` as described here could not see a Cowork store on Windows at all
> past MAX_PATH; fixed later at `a1f9169`, after this round closed.

# Cowork brief — local transcript intake: the route in for chats with no export

**Origin:** design thread, 2026-07-27, after the estate-scoped visibility round.
**Closes:** the estate's one known permanent gap — work-account chat threads.
**Evidence base:** `docs/investigation/2026-07-27_cowork-transcript-store.md`.

Personal Claude has a full export and is already an intake source. **Work does
not, and will not.** Every apply-alignment round has recorded this as a
by-design miss. The desktop client and CLI both persist transcripts to local
disk, so the gap closes from the other direction: not by obtaining an export,
but by reading what is already written.

Immediate motivation: the MCF walk on the work laptop has a clean project
registry and no chat data. Without this, the deck there has nothing to group.

**This brief is deliberately staged, and every stage has a stop.** It is the kind
of task that becomes a rabbit hole if the whole thing is attempted at once, so
the phases below are gates, not suggestions: **do not begin a phase until the
previous one's acceptance is met and Tim has seen it.**

**Read first:** `docs/investigation/2026-07-27_cowork-transcript-store.md`,
`chronicler/pipeline/intake.py`, `chronicler/pipeline/normalize_claude.py` (how
an existing source maps to `threads`/`messages`, and `ACCOUNT_LABEL`),
`chronicler/pipeline/schema.sql` (the two target tables), DECISIONS **0010**
(linkage is estate-agnostic; the deposit wall is the hard one), **0023**/**0025**
(account labels are now load-bearing for *visibility*), **0012** (three tiers).

---

## Working rules

- Stdlib-only. JSONL is `json` plus a loop; no new dependency is justified here.
- **Read-only until Phase 2, dev vault only until Phase 3.** The work laptop is
  the last machine to run this, never the first.
- The source files are **inputs, not ours**: never modify, move, or clean up
  anything under the transcript stores. Copy out, never write in.
- Gate GREEN before every commit. Each phase is its own commit.

---

## Phase 0 ▸ read one file and write down what is actually in it

**Nobody has opened one of these files.** Everything known so far comes from a
census — paths, sizes, extensions. The format is *assumed* to be one JSON object
per line describing a message. That assumption is load-bearing for the entire
rest of this brief and it is unverified.

Take one CLI transcript (`~\.claude\projects\<encoded-cwd>\<uuid>.jsonl`) and one
Cowork transcript (under the MSIX `LocalCache` path in the investigation note)
and document, in the report:

- The record types present, and which carry human/assistant conversation text as
  opposed to tool calls, tool results, file contents, or internal bookkeeping.
- Where a **stable id** lives for the session and for each record.
- Where timestamps live, and their format/timezone.
- Whether a title exists anywhere, or must be synthesised (first user message?).
- Whether the two stores' records differ at all, or are genuinely one format.
- Roughly what fraction of bytes is conversation versus tool noise.

**Acceptance:** a schema description in the report, written from real records,
with a short redacted sample of each record type.

**STOP condition — take it seriously.** If the format is not tractable as
conversation (e.g. content is chunked across records in a way that needs a
stateful reassembler, or the bulk is tool traffic with no clean conversational
layer), **stop and report that**. A negative result here is a good outcome and
saves the rest of the work. Do not start building a parser to find out.

---

## Phase 1 ▸ a read-only reader and a census, no DB

A module under `chronicler/pipeline/` (suggested `local_transcripts.py`) that
discovers and parses, and a CLI that only ever **reports**:

- **Discovery** of both stores, config-driven, never hardcoded — the MSIX path
  and `~/.claude` are machine facts and belong beside `chronicler_home` in
  config, resolved like every other path. Absent store → report it, don't crash.
- **Parse** to an in-memory shape mirroring `threads`/`messages`: thread id,
  title, created/updated, and ordered `(seq, role, content, created_at)`.
- **Explicitly excluded**, and say so in the code: `audit.jsonl` (tool-level, up
  to 8.9 MB each), `local_<id>.json` (a second Cowork-only representation of the
  same content — one format, one parser), `.claude/tasks/*.json`.
- **The report**: sessions found per store, message counts, date range, total
  bytes, the encoded-cwd of each, and anything that failed to parse — listed,
  never swallowed.

**Acceptance:** run on the gaming rig, output a census of the real 33 Cowork
sessions and 26 CLI ones. No DB touched. No writes anywhere.

---

## Phase 2 ▸ ingest into the dev vault, behind `--apply`

Map to `threads` / `messages` and write, dry-run by default.

Rulings the brief settles now, so the thread doesn't invent them:

1. **`source`** is a new value alongside `claude` / `gemini` — propose one and
   state it. It must be distinguishable from export-derived Claude threads
   forever, because the two overlap on the personal estate.
2. **`account`** follows the convention `<source>-<estate>` and takes the estate
   from **the machine's config**, not from the content. `t.account LIKE
   '%-work'` is now what makes work data visible on the work box (0025) — get
   this wrong and the threads either vanish or land on the wrong side of a wall
   that governs display. Never infer estate from what a thread talks about.
3. **`thread_id`** is derived from the session uuid, stably, so a re-run updates
   rather than duplicates. `message_id` likewise — source-native id if one
   exists, else a synthetic hash, per the schema's own comment.
4. **Idempotency is the hard requirement.** These files **grow**: a session
   appended to after ingest must add its new messages and not re-insert the old
   ones. Prove it with a re-run in the tester, not by inspection.
5. **`raw_ref`** carries the path back to the source file. `parser_version` is
   set. Both exist for exactly this case.
6. **Dedupe against the export is Phase 3's problem, not this one.** Ingest into
   the dev vault where the overlap is visible and measurable first.

**Acceptance:** dev vault gains the threads; a second run changes nothing; a run
after appending to a transcript adds only the new messages. Hermetic testers for
the parser and for idempotency.

---

## Phase 3 ▸ the coherence check — the reason personal goes first

**This is the point of doing personal at all.** The personal Claude export should
already contain every personal thread, so the local store can be checked against
a known-good answer — the only chance to measure this pipeline before it is used
where nothing can check it.

Measure and report:

- Threads present in the local store but **not** in the export, and vice versa.
- For threads in both: does the reconstruction match — same message count, same
  ordering, same content modulo formatting? Sample and diff, don't assert.
- What the local store **loses** relative to an export, and what it **gains**
  (tool activity, file paths, work sessions that were never exportable).
- A dedupe rule that falls out of the above, stated explicitly.

**Acceptance:** a written comparison with real numbers. **The GO/NO-GO for the
work rig is this measurement**, not the fact that Phase 2 ran.

---

## Phase 4 ▸ the work rig

Only after Phase 3. Solo, loopback, MCF-only registry, per
`SOLO_PLAYBOOK.md` §10/§11 and 0025. The threads land as `*-work`, and the deck
shows them because the estate is declared `work` on that machine.

---

## Rulings needed from Tim before Phase 2 writes anything

Put these in the report as questions with recommendations; do not decide them
alone:

- **Content sensitivity.** These transcripts contain pasted file contents,
  command output, and plausibly secrets — material never intended for a
  durable store. Options: ingest whole; ingest conversation records only
  (Phase 0 tells us if that separation is clean); or ingest whole and run the
  estate's existing tracked-secret scanning over it. **Recommend the middle
  one**, with the reasoning that a chat archive should hold the chat.
- **Attribution.** A CLI session's encoded cwd names the repo it ran in — a
  deterministic project link, stronger than anything S4/S5 infers, belonging at
  the `exact` end of the authority ladder. **Cowork sessions carry no such
  signal** (their cwd encodes the session's own outputs dir). Ruling needed on
  whether the CLI case writes `project_confidence='exact'` directly, or goes
  through evidence like everything else.
- **Volume.** 333 MB in one Cowork subtree before exclusions. If Phase 1 says
  the conversational layer is still large, a retention or truncation rule is a
  decision, not an implementation detail.

---

## Explicitly out of scope

The deck, the run ledger, personas, the TOTP gate, the knight. Any change to
`intake.py`'s zip handling. Any write outside the dev vault before Phase 3
passes.

---

## UAT — acceptance checks (Tim walks these)

- **Phase 0's schema description matches a file he opens himself.**
- Phase 1's census matches what is on disk (33 Cowork, 26 CLI at last count).
- Re-running Phase 2 twice changes nothing; appending to a transcript adds only
  the new messages.
- Phase 3's comparison is real numbers against the export, not a claim of
  equivalence.
- On the work rig: threads land as `*-work`, the deck shows them, and no
  personal thread is present.
- Nothing under either transcript store was modified — verify by mtime.

Mark each **ready to walk**. Results log needs a uat stamp naming the commit; do
not write a `gate=` field.

---

## Reporting

`docs/COWORK_REPORT_local_transcript_intake.md`, walk-sheet
`docs/UAT_local_transcript_intake.md`, stamped results after the walk. **Report
at the end of every phase, not only at the end** — this is the brief most likely
to discover that its own premise was wrong, and that discovery is worth more
than a finished parser built on a bad assumption.
