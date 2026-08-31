> **ARCHIVED** 2026-08-31 · completed pair · pair `COWORK_BRIEF_uat_sidebar.md` + `COWORK_REPORT_uat_sidebar.md`, walked 2026-08-03
> Superseded by the sidebar being live, and by `CONVENTION_docs.md` §4's uat-stamp rules · Original purpose: slice 2 of two — give the *built, not walked* column a real action, so walking a sheet emits a stamped results log that advances the card itself.
> Accurate history: why the action had to record a verdict rather than compute a pass. **Stop trusting:** its opening instruction *"do not start this until the board has been walked"* — the board round ran, was walked 2026-08-01, and was archived the same day as this file. That precondition is spent.

# Cowork brief — the UAT sidebar: walking a sheet becomes an action

**Origin:** design thread, 2026-07-28. Slice 2 of two.
**Depends on:** `COWORK_BRIEF_docs_board.md` being **built and walked** first —
not merely written. DECISIONS **0027** and **0028**.
**Deliverable:** the *built, not walked* column gains a real action — walk the
sheet in the deck, and the results log it emits advances the card by itself.

**Do not start this until the board has been walked.** Its walk answers two
questions this brief would otherwise have to guess: whether ratification should be
session-scoped or persisted, and what the checkbox-convention inconsistency
actually means for how a sheet is filled in. Both change this design. If the board
round has not run, hand this back.

---

## Why it exists

The uat stamp is the one artefact in the system asserting *"this was tested, here,
at this commit"* — and it is typed by hand. It has already drifted three times in
a single day (43t → 45t → 46t), each time by someone doing the locally-correct
thing to keep the gate green. The fix landed as "stop writing the `gate=` field",
which is right but treats the symptom.

**The machine walking the sheet knows the commit, the host and the date.** It
should write them. That is the whole provenance argument, and it is most of this
slice's value before a single checkbox is ticked.

---

## The design tension, stated up front

**Most UAT items are not deterministic.** From the sheets we have actually walked:

- *"Does the estate list match Tim's sense of the sharp edges?"* — pure judgement.
- *"Does the grouping feel right — does one project's batch read as one topic?"* —
  the question the entire deck exists to answer, and unanswerable by a machine.
- *"`run.py review --host 0.0.0.0` must exit non-zero and name 0025"* — fully
  deterministic, and was walked by pasting terminal output.

So the sidebar must **record a verdict and its evidence, never compute a pass**.
That is the same split `auditor_uat_stamp` already makes: police where an
acceptance claim came from, never whether it was earned. Some items may carry a
*pre-check* — run this query, show the number — but the human still rules.

**A sidebar that grades itself is worse than no sidebar**, because it produces
acceptance claims nobody made.

---

## Working rules

- Stdlib-only logic; more views in `chronicler/review`. Gate GREEN before commit.
- Writes are confined by 0028: `docs/` only, staged, **never committed**.
- The sheet is the source of truth for *what to walk*. The sidebar reads it; it
  does not maintain a parallel task list.

---

## Task 1 ▸ read a walk-sheet as items

Parse a `UAT_<x>.md` into items: identifier (`2.1`, `4.3`), text, current state
(`- [ ]` / `- [x]` / `- [~]`), and section.

**Handle the inconsistency the board found.** Two walked pairs
(`doc_provenance_coverage`, `repo_tier_producers`) have entirely unticked sheets
because their evidence went into the results log instead. So an unticked sheet
does **not** mean unwalked. The sidebar must not present those as untouched work —
show the results log alongside, and let the board's finding inform how. **The
board's walk should have produced a ruling on this; follow it.**

## Task 2 ▸ record verdicts and evidence

Per item: a verdict (walked / deferred / blocked / not applicable — mirror the
vocabulary already in use in `archive/UAT_cowork_run_2026-07-24_results.md`:
`[EVIDENCE]`, `[FIXTURE]`, `[BLOCKED]`, `[DEFERRED]`), plus a free-text evidence
box.

- **Pasting terminal output must be first-class.** Every results log we have is
  mostly pasted output; that is the evidence, and it must survive verbatim into
  the emitted markdown.
- **Deferred and blocked need a reason**, enforced. The most useful lines in the
  existing logs are the ones saying *why* something could not be walked — *"this
  vault cannot answer it: only `*-personal` accounts exist"* is worth more than a
  tick.
- Nothing is persisted until Task 3 emits. In-progress state is session-scoped;
  say plainly in the UI that a lost session loses the notes.

## Task 3 ▸ emit the results log, stamped

Generate `docs/UAT_<x>_results.md`:

- **The stamp is computed, not typed:** `commit` from `git rev-parse HEAD`,
  `dirty` from the working tree's real state, `host` from the machine, `walked`
  from today. **Do not write a `gate=` field** — settled, with the reasoning in
  `archive/UAT_solo_playbook_results.md`'s stamp comment.
- **`dirty=true` must be reported honestly.** The work-rig log carries
  `dirty=true` because the tree was modified mid-walk, and that is the correct
  record. Do not suppress it, and do not refuse to emit because of it.
- Body: items grouped by section with verdicts and evidence, then what was **not**
  walked and why — that section has carried the most value in every log so far.
- **Staged, never committed** (0028). The UI says so explicitly.

**If a results log already exists**, do not overwrite it silently. Offer to append
a new walk section, or refuse and say so. A results log is testimony; the golden
close-out deliberately preserved a superseded first pass rather than editing it.

## Task 4 ▸ close the loop with the board

Emitting a results log moves the card from *built, not walked* to *walked* on the
next board load — because the column is derived from file existence, not from a
flag the sidebar sets. **Verify that happens by itself.** If the board needs
telling, the derivation is wrong and that is a bug in the board, not something to
patch around here.

---

## Explicitly out of scope

- Computing whether an item passed. Ever.
- Ticking the source walk-sheet. The sheet is the request; the results log is the
  answer. (**Unless the board's walk ruled otherwise** — if so, follow that.)
- Committing anything (0028).
- The run ledger (0022) — adjacent and tempting, since "this was walked" and
  "this was run" are the same provenance instinct, but it is a knight-side
  concern with its own decision.
- Editing briefs, reports, or any document body.

---

## UAT — acceptance checks (Tim walks these)

The pleasing part: **this slice's own walk-sheet is walked using the sidebar**,
and the results log it emits is the acceptance artefact. If it cannot walk itself,
that is the finding.

- A sheet loads with its real items and current states.
- A deterministic item records pasted terminal output verbatim.
- A judgement item records a verdict with prose and no computed pass.
- Deferring without a reason is refused.
- The emitted stamp's `commit` and `host` are correct, `dirty` is honest, and
  there is no `gate=` field.
- The unticked-but-walked pairs are not presented as untouched work.
- An existing results log is never silently overwritten.
- The card advances on the board with nothing else touched.
- Staged, not committed; `verify.py` GREEN afterwards.

Mark each **ready to walk**. The results log needs a uat stamp naming the commit.

---

## Reporting

`docs/COWORK_REPORT_uat_sidebar.md`, walk-sheet `docs/UAT_uat_sidebar.md`, and
stamped results — emitted by the sidebar itself. Record which of this brief's
assumptions the board's walk had already invalidated, because some will have been.
