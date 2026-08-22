---
name: decision-scribe
description: Draft DECISIONS entries to the house format — next free number, the metadata line with its cited rulings, and the four sections including a concrete "What would show this wrong". Use when asked to write, draft or record a ruling or decision, to add a DECISIONS entry, to supersede an earlier one, or to start a DECISIONS.md in a repo that has none. Drafts as `proposed`; never ratifies, never edits an accepted entry's body.
---

# decision-scribe

Scripts the **shape** of a ruling. Does not make it, and does not ratify it.

`docs/DECISIONS.md` is the authority on its own format, and that format is set
by practice rather than by a template. **Read the last three or four entries
before drafting** — they are the spec. If this file and the log disagree, the
log wins and this file needs updating.

The log exists because the reasoning behind a threshold was nearly lost once —
found in a schema comment rather than in a ruling, with the evaluation data
behind it gone for good. Every rule below is downstream of that.

## The hard rules

**Append-only. An entry is never rewritten.** A later decision supersedes an
earlier one by adding a new entry that says so. The single exception is the
**status line**, which is stamped at ratification (`proposed` →
`accepted <date>`) or at supersession. Nothing else in a landed entry changes,
ever — not a number, not a claim, not a typo.

**Never ratify.** Draft as `proposed`. Ratification is a re-read by the
operator **on a different day than the drafting**, because same-sitting
ratification of your own reasoning is the rubber stamp the propose/ratify
split exists to prevent. A skill that marks its own draft accepted has
defeated the mechanism.

**Clause numbers are frozen once accepted.** Other documents, briefs and
commit trailers cite "0042 clause 4" by number. Renumbering a clause silently
breaks every citation in the estate. Add clauses at the end; never insert,
never resequence.

**Number from the file, never from memory.** Count the entries in
`DECISIONS.md` and take the next free number. Two entries sharing a number is
unrecoverable in an append-only log.

## Procedure

### 1. Establish the number and read the neighbours

Take the next free number from the file itself. Then read the entries it
builds on — not summaries of them, the entries. A `Builds on:` citation you
have not read is a guess, and the parenthetical gloss beside it will be wrong
in a way that reads authoritative.

### 2. The title states the decision, not the topic

A reader scanning the log's headings should learn what was decided without
opening anything.

- Good: *"A consumer repo declares its own runnable stages; the toolkit
  executes them under a committed allowlist and never widens what they can
  do."*
- Bad: *"Repo allowlist and manifests."*

Long is fine. The heading is doing real work.

### 3. The metadata line

```
**Date:** YYYY-MM-DD · **Status:** proposed · **Builds on:** NNNN (one-line
gloss of what that ruling established), NNNN (…) · **Source:** where this came
from · **Brief:** COWORK_BRIEF_<x>.md
```

- **`Builds on`** carries a gloss per citation — the reader should not have to
  open four entries to follow the argument.
- **Cross-repo rulings carry their repo at every mention** (`sfds-0029`), never
  a bare number. A bare number means *this* repo's log.
- **`Source`** names the thread, review or finding that forced it. "Design
  thread" plus a date is enough; anonymous rulings age badly.

### 4. The four sections

**Context** — what *forced* the decision. Not background: the specific thing
that stopped working, or the specific choice that could no longer be deferred.
If nothing forced it, ask whether it is a ruling or a preference.

**Decision** — numbered clauses, each a rule that can be checked. A clause
stating an aspiration ("we should prefer…") is not a rule and will not be
enforceable later. Write what is permitted, what is refused, and by what
mechanism.

**Consequences** — **including the bad parts**, and this is the section that
separates a real ruling from a press release. What does this cost? What
becomes harder, slower, or invisible? What is being given up, and is the trade
being taken knowingly? An entry whose consequences are all benefits has not
been thought through, and the log's best entries are the ones that state the
uncomfortable half plainly rather than absorbing it.

**What would show this wrong** — **mandatory, and concrete.** The test that
would falsify the ruling, written so a future reader can actually run it.
Countable beats descriptive: *"count the schema changes per source wired — one
extension across three sources vindicates this; three refutes it"* is a test.
*"If it turns out not to work"* is not. This section is the one a drafter
omits first and the one that makes the log worth keeping.

### 5. Self-check before presenting

- Number is next-free, verified against the file.
- Status is `proposed`. Date is the drafting date.
- Every `Builds on` entry was read, and its gloss is accurate.
- Every clause is a rule, not an intention.
- Consequences name at least one real cost.
- "What would show this wrong" is something a person could go and check.
- No clause renumbers or contradicts an accepted entry without saying so.

### 6. Present, and stop

Show the entry in full, name where it appends, and stop. The operator appends
it and ratifies it on a later day.

## Superseding

A superseding entry cites the one it replaces in `Builds on` (or a
`Supersedes:` field where the log uses one), states in Context what changed,
and says explicitly which clauses of the old entry survive. The superseded
entry's **status line** is stamped; its body is untouched. Partial supersession
is normal and should be exact about which clauses fall.

## Starting a `DECISIONS.md` where none exists

Common in a repo whose rulings are scattered across briefs, reports and notes.

- Number from **0001**, in the order the decisions were actually made, not the
  order you found them.
- **Each recovered entry says it is recovered**, names where the reasoning was
  found, and does not pretend to be contemporaneous testimony. A reconstructed
  Context is inference and must be labelled as inference.
- **Do not recover what you cannot source.** A ruling you are confident about
  but cannot point to is a candidate for a *new* entry, drafted today, not a
  backdated one.
- Recovered entries are still `proposed` until the operator confirms each one
  actually was the decision taken.

## Anti-patterns

- Ratifying, or stamping a status the operator did not give.
- Editing an accepted entry's body — to fix a number, a typo, or a claim that
  turned out wrong. The claim being wrong is what supersession is for.
- Inserting or renumbering clauses in an accepted entry.
- "What would show this wrong" written as a platitude.
- Consequences listing only benefits.
- A `Builds on` citation you did not open.
- Drafting and ratifying in the same sitting.
- Writing a ruling for something nobody has done yet and nothing forced — the
  log records decisions, not plans.
