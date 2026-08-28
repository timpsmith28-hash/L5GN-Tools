---
name: round-closer
description: Close a card by walking its UAT sheet with the operator and writing the stamped results log — verify the [G] checks with evidence, put the [H] checks to the operator verbatim, and record the answers in their words. Use when asked to close a round, walk a UAT sheet, write a results log, stamp a card as walked, or find which cards are built but not walked. Never answers a check on the operator's behalf.
---

# round-closer

**Published here 2026-08-28.** Authored on the work rig and loaded there; it
existed in no repository until now, which under **0057** made it a skill with no
source of truth. Two estate assumptions that were false in this repo were
corrected on arrival, at the point of each — a skill that cannot read its
convention stops rather than working from its own text (**0052**), and one
carrying a wrong fact about the repo it runs in is the same defect better
disguised.

Closes a card. **The card's state is a function of which files exist**
(`CONVENTION_docs.md` §3), so this skill's whole product is one file:
`docs/UAT_<slug>_results.md`. Until it exists the card reads *built, not
walked*, whatever anyone believes about it.

**Walking is a human act** (`CONVENTION_briefs.md` §6). This skill verifies
evidence and asks questions. It does not decide whether the round was
acceptable, and it never writes an answer the operator did not give.

Authorities, not restated here: `CONVENTION_briefs.md` §4 (`[G]`/`[H]`), §5
(operator's words, not paraphrase), §6 (the stamp and the human act);
`CONVENTION_docs.md` §4 (the stamp's fields). Read them if a case is unclear.

## Procedure

### 1. Establish the card and refuse the wrong ones

List `docs/` and report which of the card's four files exist. Then:

- **No walk-sheet** → stop. There is nothing to walk, and writing one now is the
  failure `CONVENTION_briefs.md` §2 exists to prevent.
- **Results log already exists** → stop. It is frozen. A second walk is a new
  card, not an edit. **One exception, and only one:** a log that declared itself
  `INTERIM` at first writing may be re-walked, under `CONVENTION_docs.md` §4's
  four conditions. A log that did not declare itself interim does not become
  interim because a re-walk is now wanted.
- **No report** → stop and ask. The walk is *against* the report.

### 2. Establish the commit walked

The operator runs, in the repo being closed:

```
git rev-parse HEAD
git status --porcelain
```

`commit` and `dirty` come from those, `host` from the machine, `walked` from
today's date. **A results log without a real commit is worthless** — it is the
one document asserting "this was tested, here, at this commit."

### 3. Verify the `[G]` checks

One line of evidence per check, naming what was read or run. Not "pass".

- A check the thread cannot verify is **unconfirmed**, never a pass. Say what
  would confirm it.
- A check that cannot fail in this repo is a **vacuous pass**. Name it as one.
- A check added to the brief or prompt *after* this round ran is **not
  backdated** onto it. Note that the sheet had N checks and record the walk that
  happened.

### 4. Put the `[H]` checks to the operator

All of them, in one message, **quoted verbatim from the walk-sheet**. Do not
rephrase them, do not answer them, do not suggest answers.

Then wait. An `[H]` the operator did not answer is recorded **not answered** —
that is a real result and the most common thing a closer gets wrong is turning
it into a pass.

Where an answer was given about something adjacent rather than the check as
written, record it as **partial** and say what was actually said.

### 5. Write the results log

`docs/UAT_<slug>_results.md`, stamped per `CONVENTION_docs.md` §4 as its
**first line**, then:

- what was walked, against which report, at which commit, by whom, on what date;
- the `[G]` table with its evidence;
- the `[H]` answers in the operator's own words, marked as quotation;
- **defects the walk found in the brief or the prompt rather than in the repo**,
  and where they were carried. This section is usually the round's most valuable
  output and it has nowhere else to live;
- any check left unanswered, stated plainly.

A failed check is the walk working. Record it and do not soften it.

### 6. Hand back and stop

Draft the commit per `commit-scribe` and hand back the `-F` command. Do not
commit. The results log is the only file this skill writes.

## Anti-patterns

- Writing the results log from the brief, the report, or your own reading of the
  round, without the operator having walked it.
- Answering an `[H]`, or inferring one from something the operator said about a
  different check.
- Recording unconfirmed as pass, or a vacuous pass as evidence.
- Editing the walk-sheet, brief or report to match what happened. They are
  frozen; the results log is where the divergence is recorded.
- Backdating checks added to the prompt after the round ran.
- Omitting the stamp. **`gate=` is optional and is checked against `verify.py`
  when present** (`auditor_uat_stamp`) — so omit it rather than assert a count
  you did not observe, and never invent one. This repo *does* have a gate:
  `.githooks/pre-commit` runs `verify.py`.
- Growing this file into a copy of `CONVENTION_briefs.md`. Cite it instead.
