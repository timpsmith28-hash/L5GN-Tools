# Project process convention — **STUB**

> **STUB, 2026-08-29, personal estate.** Nothing here is in force. Sections are
> marked **[SETTLED]**, **[STUB]** or **[OPEN]**, same as `CONVENTION_skills.md`,
> so the next session fills them in order rather than re-deriving what was
> decided. **Paired with the work rig's stub of the same date** — that one was
> written against a wider range of live projects; this one is written against a
> single-project estate that has one thing the work rig lacks: **a gate, and a
> week of walked evidence about where the process actually fails.**

**Status:** authored, not enforced, **new practice**, incomplete by declaration.

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

| stage | ruled by |
|---|---|
| intent, decisions | `INTENT.md`, `CONVENTION_decisions.md` |
| brief and walk-sheet | `CONVENTION_briefs.md` |
| **build** | — |
| **report** | — |
| **walk** | — *(see §2)* |
| **results log** | `CONVENTION_docs.md` §4 (the stamp only) |
| **ratify** | 0033, and nothing else |
| archive, commit, config, docs | `CONVENTION_docs.md`, `_commits.md`, `_config.md` |

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
