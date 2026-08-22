---
name: brief-scribe
description: Draft a Cowork brief and its UAT walk-sheet together, to the house shape — origin, preconditions, cited rulings, deliverable, tasks, out-of-scope, stop conditions, and acceptance checks marked [G]/[H]. Use when asked to write or draft a brief, scope a round, turn a design discussion into a buildable brief, or write the walk-sheet for one. Enforces structure and falsifiability, never content.
---

# brief-scribe

Scripts the **shape** of a round, not its substance. What goes in a brief is
the operator's judgement; whether the brief can be built from and checked
against is mechanical, and that is what this skill enforces.

**There is no written convention for briefs yet.** The spec is the accumulated
practice in `docs/COWORK_BRIEF_*.md` — **read two or three recent ones before
drafting**, and prefer what they do over what this file says where the two
disagree. When a convention document is written, it becomes the authority and
this file cites it instead. That gap is real and this skill is the drift risk
until it closes.

## Why the bar is falsifiability

A brief complete enough that the build is *determined* by it is a brief a
cheaper model can build from. That is not a style preference — it is the
condition under which build work moves down a tier, and whether a given brief
clears it is measurable by handing it to that tier and judging the output
against the brief's own checks.

So the property to optimise is not length or polish. It is: **could someone
who was not in the design conversation build this, and could a machine tell
whether they had?**

## The two documents are written together

The brief and its walk-sheet (`docs/UAT_<slug>.md`) are one act. The
walk-sheet is the brief's acceptance section, extracted so it can be walked
and stamped.

**Never write the walk-sheet after the build.** By then you know which
properties are awkward to verify mechanically, and `[H]` checks proliferate to
cover them. Written at brief time, an awkward property forces a better design
instead — which is the whole value.

## The parts

Not a template to fill; a checklist of what a reader needs. Order follows
existing practice.

- **Draft-status note** — required whenever the brief is written ahead of its
  build. Say how far ahead, what is likely to have moved, and that re-verifying
  every "already exists" claim is the round's first task. A brief that
  describes remembered code rather than the code in front of it is the failure
  this note exists to flag.
- **Origin** — the thread, finding or ruling that produced it.
- **Precondition** — what must be true before this round opens, stated so it
  can be checked rather than felt. "Phase N closed" is checkable; "when we're
  ready" is not.
- **Depends on — this repo's rulings** — cited by number with a one-line gloss
  each. Cross-repo rulings carry their repo prefix at every mention.
- **Ratify before code** — where the round needs a ruling that does not exist
  yet, name it, and say the round may not be built while it is `proposed`.
- **Deliverable** — one paragraph, ending in something testable. If the last
  sentence cannot be checked, the round has no finish line.
- **Working rules** — the disciplines that hold *throughout*, restated at the
  point they bind rather than assumed from elsewhere.
- **Tasks** — numbered, each naming what lands and where. A task nobody could
  tell was finished is not a task.
- **Explicitly out of scope** — the section that most often saves the round.
  Name the adjacent work that will tempt whoever builds this.
- **The one deliberate widening, named** — where the round crosses a line an
  earlier ruling drew, say so, say why, and say what still bounds it. A
  widening taken silently is the one that gets inherited.
- **Stop conditions** — each ending `→ stop`. These are the round's tripwires,
  and they should be things a builder can notice mid-build, not verdicts only
  visible afterwards.
- **UAT — acceptance checks** — below.
- **Reporting** — the report path, the walk-sheet path, and specifically what
  the report must record. "Record what happened" is not an instruction;
  "record the delta between the drafted anatomy and what landed, field by
  field" is.

## The acceptance checks — where the falsifiability bar bites

Every check carries `[G]` or `[H]`.

- **`[G]`** — a machine, or an unambiguous procedure, decides. Someone who was
  not in the design conversation gets the same answer as someone who was.
- **`[H]`** — a human judgement is genuinely required. Legitimate and
  sometimes the most valuable check in the round — *"was the evidence enough,
  or did you go hunting?"* cannot be mechanised and should not be.

**Every `[H]` is a cost.** Count them. For each, ask whether it is human
because the property is genuinely a judgement, or because the design made it
awkward to check. The second case is a design finding, not a check.

A useful shape for the `[H]`s that earn their place: they ask about the
operator's *experience* of the thing, not its behaviour. Did you trust it. Did
you go back to doing it by hand. Would you defend this on re-read.

**State the round's own falsifier** where the round is an experiment — the
single question whose "no" cancels what follows, with the consequence written
down before the answer is known.

## Procedure

1. **Read the neighbours.** Two or three recent briefs, and every ruling the
   round will cite. A cited ruling you have not opened will be glossed wrongly.
2. **Verify the "already exists" claims against the tree**, not against the
   design conversation. List what the round builds on, with the function or
   file names, and check each.
3. **Draft the brief.**
4. **Extract the walk-sheet** from the acceptance section, as its own document.
5. **Self-check** (below).
6. **Present both, and stop.** The operator ratifies the scope; nothing is
   built from an unratified brief.

## Self-check

- Every task names what lands and where.
- Every stop condition is noticeable mid-build.
- The deliverable's last sentence is testable.
- `[G]`/`[H]` on every check; the `[H]` count is deliberate, not residual.
- Any `[H]` that could have been `[G]` is either fixed or recorded as a design
  finding.
- Out-of-scope names the specific adjacent temptations, not "anything else".
- Every cited ruling was read.
- The walk-sheet matches the brief's acceptance section exactly.
- If the round is an experiment, its falsifier is stated with its consequence.

## Anti-patterns

- Writing the walk-sheet after the build.
- `[H]` used as a shrug for a property nobody worked out how to check.
- A deliverable phrased as an activity ("improve the…") rather than an
  outcome.
- Scope creep through "and while we're in there".
- A brief that cites rulings by number without reading them, producing glosses
  that are subtly wrong and read authoritative.
- Restating a ruling's content instead of citing it — the ruling can change;
  the restatement will not.
- Describing code from memory rather than from the tree.
- A round with no stop conditions. Every round has a way to go wrong; a brief
  that names none has not looked.
- Padding a brief to look thorough. Length is not the bar — determinacy is.
