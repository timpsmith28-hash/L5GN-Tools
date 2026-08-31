# Project process convention — **STUB**

> **STUB, 2026-08-29, personal estate.** Nothing here is in force. Sections are
> marked **[SETTLED]**, **[STUB]** or **[OPEN]**, same as `CONVENTION_skills.md`,
> so the next session fills them in order rather than re-deriving what was
> decided. **Paired with the work rig's stub of the same date** — that one was
> written against a wider range of live projects; this one is written against a
> single-project estate that has one thing the work rig lacks: **a gate, and a
> week of walked evidence about where the process actually fails.**

**Status:** authored, not enforced, **new practice**, incomplete by declaration.

**Adopted from:** paired with the **work rig's** stub of **2026-08-29**, read
the same day. **Origin repo and file path are unconfirmed from this rig** —
same position as `CONVENTION_skills.md`, and for the same reason (0050: an
unreachable source reads as unknown, never as fresh). Recorded incomplete under
**0057** clause 7 rather than omitted. **Fill both fields from the work rig and
this line is done.**

**Adoption is weaker here than in `CONVENTION_skills.md`, and the difference
matters:** that one was written *from* the work rig's draft; this one was
written *alongside* a stub of the same date against a different estate shape —
a single-project estate that has a gate and a week of walked evidence, which
the work rig's did not. If clause 7's subject turns out to be "adopted whole"
rather than "written in parallel", this header is over-declaring and should be
cut. That call belongs to whoever rules on how clause 7 determines its own
subject; it is not made here.

**Scope:** the lifecycle of a **round** — intent to archived — and the seams
between the conventions that already rule its parts. **It does not restate
them.** Where an existing convention owns a stage, this file cites and stops.

**Cites:** 0028 cl.3 (the commit stays a human act), 0031, 0033, 0040 cl.7,
0045, 0048, 0050, 0052, 0059 *(proposed)*.

---

## 1. Why this exists [SETTLED]

**Ten conventions rule parts of the process and none rules the whole.** The work
rig's survey put it best and it reproduces here: **the process is well-ruled at
both ends and hollow in the middle.**

| stage | ruled by | skill |
|---|---|---|
| intent | `INTENT.md` | — |
| decisions | `CONVENTION_decisions.md` | `decision-scribe` |
| brief and walk-sheet | `CONVENTION_briefs.md` | `brief-scribe` |
| **build** | — | — |
| **report** | — | — |
| **walk** | — *(see §2)* | `round-closer` *(citing nothing — §2)* |
| **results log** | `CONVENTION_docs.md` §4 (the stamp only) | `round-closer` |
| **ratify** | 0033, and nothing else | — |
| archive | `CONVENTION_docs.md` §4 | `docs-archivist` |
| commit | `CONVENTION_commits.md` | `commit-scribe` |
| config | `CONVENTION_config.md` | — |
| skills delivery | `CONVENTION_skills.md` *(stub)* | `armory` *(unbuilt)* |
| restart | `CONVENTION_design_thread_restart.md` | `dtr` |

**Read the skill column against the convention column.** Every stage that has a
skill has a convention, **except the walk** — and every unruled stage has no
skill either, **except the walk**. The walk is the one place where a skill runs
against nothing, which is why §2 is a finding rather than a gap.

**Every defect this estate found on 2026-08-28 originated in an unruled stage.**
That is not an argument that rules would have caught them — nothing checks any
convention here — but it locates them precisely.

## 2. `round-closer` has been working from its own text [SETTLED — a live finding]

`CLAUDE.md`'s conventions table lists **closing a round → *(none here)* →
`round-closer`**, and 0052 says a skill that cannot read its convention **stops
rather than working from its own text**.

**It has not been stopping.** It was published into this repo on 2026-08-28 and
used the same day to walk two cards. Both walks produced good results logs — and
both ran on the skill's own text, with no convention behind them.

**This section is that convention's placeholder.** Until §3–§6 are filled,
`round-closer` is a skill whose authority is a stub, which is better than a skill
whose authority is nothing, and worse than one that can read a rule.

## 2a. The operator's positions on the five gaps [SETTLED as positions, not as rules]

Recorded in his framing, 2026-08-29, so the fill starts from a stated direction
rather than a blank section. **These are positions, not clauses.**

- **Build → `CONVENTION_build.md`.** *"Seems logical and boring but probably the
  answer."* Estate- or project-wide build conventions move out of individual
  briefs; **a brief then states where it overrides or adds to them.**
- **Report → the standard parts pulled out**, with the brief carrying a
  reference to what the standardised report output expects.
- **Both of those carry one idea worth naming on its own: a brief should carry
  the conventions it was written under — a copy, or a pinned reference.** This
  is **0045's pin mechanism applied to rules rather than to files**, and it
  answers a failure this estate has hit twice in a week: `round-closer` citing
  `UAT_<NN>_<slug>` because it was written under another repo's naming, and
  `orientation` citing bare `0019`/`0011` that resolve to unrelated rulings here.
  **A brief pinned to its conventions makes "which rules was this written under"
  a read rather than an archaeology.** Strong candidate to be ruled before
  `CONVENTION_build.md` is written, since it constrains its shape.
- **Walk — named as the current bottleneck.** *"Straightforward functional UAT
  is easy enough to answer… sometimes the questions get almost philosophical.
  I guess this is on me to read the proposed UAT more carefully before it."*

  **The self-blame is worth challenging before it becomes the rule.**
  `CONVENTION_briefs.md` §2 makes the brief and the walk-sheet one act, written
  **before** the build. So a check that reads philosophical at walk time was
  written that way at brief time, and reading it more carefully earlier catches
  it — but only if there is something to catch it *against*. **A `[H]` that
  cannot be answered from evidence the round produced is a defect in the
  sheet**, and `UAT_desk_stale_card_results.md` D9 is the proven case: it was
  unanswerable by construction, and no amount of careful reading at brief time
  would have shown that, because the thing that made it unanswerable happened
  six days later. **TO FILL:** a test for whether a `[H]` is answerable, applied
  when the sheet is written.
- **Ratify → a convention, and the operator's own doubt about the skill.**
  *"Could be made into a convention + skill quite easily `/ratify-decision ####`
  — but does that make it too easy? maybe just a convention."*

  **The doubt is correct and should be recorded as the reasoning, not the
  hesitation.** 0033's protection is that ratification is a re-read on a
  different day; **the friction is the safeguard, not a cost sitting beside it.**
  A one-command ratify removes exactly the pause that makes the different-day
  rule mean anything. A skill could still help — assembling what changed since
  the entry was drafted, refusing a same-day stamp, producing the artefact
  ratification currently leaves behind — **but a skill that ratifies is the
  wrong shape, and a skill that prepares a ratification is the right one.**
  Same split as `commit-scribe`, which drafts and hands back rather than
  committing.
- **`round-closer`'s convention — an easy win, early next week.** §2.

## 3. Transitions — what may start when [STUB]

**TO FILL.** The candidate clause, carried from the work rig's stub with its home
still undecided: *no new card is started while the previous one is built and not
walked.*

**Its home is genuinely open** — here, or `CONVENTION_briefs.md`. **Do not settle
it by writing it in one of them.** The evidence to settle it against: this estate
reached **ten built-and-unwalked cards** before anyone noticed, and the noticing
came from a restart rather than from any rule.

## 4. Thread boundaries [STUB]

**TO FILL.** What a thread must establish before it may build, and what it must
leave behind so the next one can start cold. The restart convention rules the
*re-entry*; nothing rules the *exit*.

**Evidence to write it from:** the 2026-08-31 restart prompt was written by hand
at the end of a session because nothing required it. It worked. Making it a rule
costs a sentence.

## 5. State is derived, never asserted [SETTLED]

**A card's state is a function of which files exist**, not of what anyone
believes or of a status field. `CONVENTION_docs.md` §3 already rules this and
`round-closer` §1 already enforces it; it is restated here **only** as the spine
the rest of the file hangs on, and it must not grow a second definition.

**The corollary, which is unruled:** a board that derives state correctly still
obliges nobody. Twenty cards accumulated in flight without a single rule being
broken.

## 6. Findings must stay falsifiable after they are written [STUB — the prize]

**TO FILL, and fill this one first.** The work rig identified this as the highest
leverage section and the reasoning transfers exactly.

**The clause, roughly:** *a finding conditional on repo state names the condition
as something re-runnable.* An adjective — "stale", "missing", "green" — is not
re-runnable. A command or a path is.

**Local evidence, from one week:**

- `pipeline_stage_encoding-1.msg` asserted *"Fixed on both sides of the pipe"* in
  the past tense for a fix that was never made. Caught by a sweep, not by a rule.
- `UAT_desk_stale_card_results.md` D9 deferred on a blocker that had already been
  removed six days earlier — a deferral naming the wrong reason reads exactly
  like one naming the right reason, right up until the blocker is supposed to
  clear.
- Two conventions rotted their own counts inside three days.

**Three instances, three stages, one shape.** All were caught by someone
happening to look.

## 7. Rounds that do not finish [STUB]

**TO FILL.** What happens to a card that is abandoned, superseded, or blocked on
something that never clears. Today there is no state for it, so it sits on the
board looking identical to work in progress.

**Note the interaction with 0059** *(proposed)*: `insufficient` as a ruling
carrying a named thing to fetch is the Desk's version of this same gap. **The two
should be written together or neither** — one is the card mechanic, the other is
the round mechanic, and inventing separate vocabularies for them would be the
sixth time this estate has re-invented one mechanism.

## 8. Cadence and yield [OPEN]

**Not written, and it needs a number this estate does not collect.** The work rig
raised the ratio — rounds built versus rounds walked, and defects found per walk
— and observed that walking may be the cheaper half. **On this rig, one day of
walking closed three checks, corrected a superseded worry, and found A2 failing
on its own evidence.**

**That is one day, and one day is not a rate.** Recording defects-per-walk
somewhere is the precondition for this section, because the case for walking
currently rests on instinct, and instinct loses to deadlines.

## 9. What this may not do [SETTLED]

- **May not restate a rule another convention owns.** Cite and stop.
- **May not become the harness convention.** How the toolkit runs a project
  end to end is a different document that does not exist.
- **May not authorise anything to run unbidden** (0036), or to repair (0045).
- **May not assert a state a file can derive** (§5).
- **May not carry a count.** Same rule as `CONVENTION_skills.md` §7.

## 10. Gaps, in the order I would close them [OPEN — ordering is judgement]

1. **§6, findings staying falsifiable.** Cheapest, and three instances already.
2. **§2's real convention**, so `round-closer` stops citing a stub.
3. **§7**, written with 0059 rather than beside it.
4. **§3's clause**, once its home is settled.
5. **§4**, which the restart prompt already does by hand.
6. **§8**, which cannot be written until something counts.

**This ordering is judgement, not derivation, and is worth disagreeing with.**
The work rig's stub says the same of its own §10; **neither ordering has been
tested against the other**, and comparing them is a cheap round in itself.

## 11. The check [STUB]

**TO FILL** once §3–§7 exist. A check written against stubs would check nothing
and would read green, which is this estate's most-repeated defect.
