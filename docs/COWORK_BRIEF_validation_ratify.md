# Cowork brief — the work rig's first non-staleness card: a pending batch is a decision

> **Draft status:** written 2026-08-19 in the design thread, **without sight
> of the source it describes**. Its Task 1 is a discovery step, and every
> later task here is provisional on what that discovery finds — the same
> posture `COWORK_BRIEF_project_wizard.md` took toward PricingModel rather
> than inventing a shape and then bending the source to fit it. **Expect to
> rewrite Tasks 2–4 at round-open. That rewrite is the round's first real
> work, not an overhead on it.**

**Origin:** design thread, 2026-08-19. The question it answers is not "how do
we automate validation write-back" — it is **"does the card mechanic
generalise past staleness?"**, and this source was chosen because it is the
sharpest available test of that.
**Precondition — two, both hard:** (1) Phase 1's falsifier answered in
`docs/COWORK_REPORT_desk_stale_card.md`. (2) `COWORK_BRIEF_staleness_feeds
.md` closed green and **0050 ratified** — this round is the feed contract's
first non-staleness consumer, and building it against an unratified contract
would mean designing the contract from inside its own first exception.
**Runs on:** the work rig, against its own Desk instance, its own allowlist,
its own manifests, its own sidecar. Nothing crosses to the personal rig but
the contract itself and this brief (`COWORK_BRIEF_staleness_feeds.md`, "Two
desks, one contract, no mesh").
**Depends on — this repo's rulings:** **0048** (the card anatomy — this round
is its first test against a decision that is not about freshness at all),
**0042** (clause 4 especially: a manifest command is a **fixed, literal argv
with no parameter slot** — the hardest constraint this round has to design
around, and the most valuable one), **0037** (the caller names the work,
never the parameters of it; refuse, never clamp), **0031** (findings, never
verdicts), **0033**, **0050** as ratified.
**Deliverable:** one repo declares a feed of **pending decisions**; the Desk
raises each as a card with real evidence and named options; a ruling
authorises an already-declared stage to act; the write-back happens in the
source repo, by the source repo, and refuses if the world moved since the
card was drawn. **Exit test: a manual review step the operator was doing by
hand is now done from the Desk, and they would not go back.**

---

## Why this source, and why it is the right hard case

Every card the Desk has raised so far asks the same question in different
clothes: *this output looks out of date — rebuild it?* The evidence is
timestamps, the option is a rebuild, and the cost of a wrong ruling is a
wasted rebuild.

A pending review batch is a different animal on all three counts. The
question is *these computed results are waiting on a human pass/fail — do
they go in?* The evidence is the results themselves, not a clock. And a
wrong ruling writes something into a system of record. If 0048's anatomy —
question, trigger, evidence with provenance, costed options, default, expiry
— holds for that, it is a general mechanic. If it only holds for staleness,
the estate has learned something more important than a feature, and 0048 is
the entry to re-argue.

It is also the first card that **retires a manual step** rather than
replacing a patrol. Phase 1 removed the need to go looking; this removes the
step itself. That is a different and larger claim, and its exit test is
correspondingly personal: would you go back?

## Task 1 ▸ discovery — write nothing until this is written down

**Read the source before designing against it.** Produce a short findings
note (`docs/investigation/<date>_validation_pending_shape.md` on the rig that
owns it) answering, from the artifacts rather than from memory:

- **What is the unit a human currently rules on?** One case, a batch, a run,
  a file, a sheet tab? Whatever the *human* has been treating as one
  decision, the card must match — a card that splits or merges the operator's
  natural unit will be resented within a week.
- **How many units are pending, and at what rate do they arrive?** A card
  type that can produce hundreds is a flood, and flood is the Desk's named
  failure mode (`COWORK_BRIEF_curator_linking.md` reached the same wall from
  the linking side). If the honest answer is "hundreds", the unit is wrong
  and Task 1 loops before Task 2 starts.
- **What does a human actually look at to decide?** Name the exact fields.
  This becomes the card's evidence list, and anything not on it is a hunt —
  which Phase 1's `[H]` walk already established as the thing that kills a
  card's usefulness.
- **What are the real options?** Approve-all, reject-all, and partial are
  three different mechanics. If partial approval is how the work actually
  happens, say so now: it changes the contract (below) and possibly this
  whole design.
- **What does the write-back touch, and is it reversible?** If it is not,
  that fact belongs on the card face, and the default gets more conservative,
  not less.
- **What already exists in that repo that could serve as the feed's
  command?** Same question 0042 clause 7 always asks: the source knows; the
  Desk must not learn.

**Stop condition on Task 1 itself:** if the discovery note cannot name the
unit, the volume, and the evidence fields, the round stops here and reports
that. A card designed against a guess is exactly the "plausible wrong card"
that INTENT §5 says is worse than no card.

## Task 2 ▸ the contract extension — **inherited, not invented** (amended 2026-08-19)

**The options extension moved.** `COWORK_BRIEF_staleness_feeds.md` Task 4 now
lands source-declared `options` and per-card ruling validation, because the
workcycle feed needed a vocabulary that `rebuild / snooze / dismiss` could not
express (0050 clause 8). By the time this round opens, an item can already
declare `kind` and a list of options, and the Desk already validates a ruling
against the options that card offered.

So this task shrinks to the part that only this source can prove: **does the
inherited extension hold for a decision whose consequence is a write-back?**
Everything below is retained as the standard it must still meet — and if the
extension as landed does *not* fit, that is a finding about 0050's generality,
reported as one, not patched here.

A staleness item carries a `state` and, at most, one `action`. A pending
decision carries a **question and several named options**. The rule for the
extension, unchanged:

> **The extension is general or it is refused.** An item may declare a
> `kind` and a list of `options`, each option naming a label and an optional
> `action`. Nothing in the schema, the parser, or `desk.py` may contain the
> word "validation", or any concept specific to this source. If the extension
> cannot be written generally, this round has found that the card mechanic
> does *not* generalise, which is the answer it was sent to get — report that
> and stop.

Sketch, to be rewritten against Task 1's findings:

```jsonc
{
  "key": "batch_2026_08_19",
  "kind": "pending_decision",              // staleness | pending_decision
  "label": "Validation batch — 412 cases computed, awaiting pass/fail",
  "state": "stale",                        // "wants a ruling"; vocabulary reviewed in Task 2
  "observable_since": "2026-08-18T22:10:00Z",
  "evidence": [ "…", "…" ],                // verbatim, source-authored
  "content_digest": "sha256:…",            // what the options were computed against — see below
  "options": [
    {"id": "approve", "label": "Write back 412 results",
     "action": {"repo_key": "…", "stage_key": "…"}},
    {"id": "hold",    "label": "Hold — nothing runs"}
  ]
}
```

`hold` remains the default on every card and remains inert (0048 clause 4).
Expiry still only re-raises `aged`. Nothing here acts on silence.

## Task 3 ▸ the parameter problem, which is the actual design work

0042 clause 4 says a manifest command is a fixed, literal argv with **no
parameter slot**. So the card cannot tell the stage *which* batch to write
back — and that constraint is right, because the alternative is a request
body that names work by parameter, which is precisely what 0037 exists to
prevent.

The resolution, and the part of this round worth the most to every later card
type:

1. **The source owns the selection.** The declared stage writes back
   *whatever that repo itself currently holds as pending* — the same set its
   own feed just reported. The card authorises; it does not select. The argv
   stays literal because there is nothing to pass.
2. **The digest closes the gap that opens.** Between the card being drawn and
   the button being pressed, the pending set can change. So the feed item
   carries a `content_digest` over the exact set it reported; the write-back
   stage recomputes that digest as its first act and **refuses, loudly, if it
   differs** — the run marker records the refusal, the next render raises a
   fresh card against the new set. Refuse, never clamp; never "write back
   what matches and skip the rest" (0037's discipline, and a partial silent
   write is the worst outcome available here).
3. **The digest is computed by the source, both times.** The Desk stores it,
   shows it, and compares nothing. It is an opaque string on this side of the
   boundary.

If Task 1 found that **partial** approval is how the work really happens,
this resolution does not survive, and the honest options are: the source
exposes each partition as its own item (preferred — it keeps the contract
intact and moves the granularity to where the knowledge is), or 0042 clause 4
is revisited by its own entry with its own reasoning (expensive, and not to
be done inside this round).

## Task 4 ▸ the round on the rig

- The feed command in the source repo, printing the item shape; the
  write-back stage declared in that repo's manifest; the repo added to the
  work rig's allowlist — a reviewed, committed edit (0042 clause 2).
- The digest check inside the write-back path, with its refusal wired to the
  existing four outcomes — **no fifth state** (standing stop condition).
- The work rig's Desk instance running against them.
- Ten real batches ruled from the Desk, and the manual step not done by hand
  once during that period.

## Explicitly out of scope

- Any auto-approval, confidence floor, or policy that acts. There are no
  ratified policies and this is not the round that makes one — a decision
  made repeatedly here is *evidence for* Phase 4's promotion, and the
  reasons on those rulings are what promotion will feed on. Write real
  reasons.
- Any change to what the source computes, or to how it validates. This round
  moves the *decision*, not the work.
- Any cross-rig anything (0036).
- Cost estimates on options. No measurement, no estimate (0037 clause 4) —
  and the run marker still records no duration.
- Generalising the Desk into a workflow engine. Two card kinds is two, not a
  framework.

## Stop conditions

- A source-specific concept lands in the schema, the parser, or `desk.py` →
  stop; the extension is general or it is not made.
- The Desk selects, filters, batches, or partitions anything → stop; the
  source owns selection.
- A write-back proceeds when the digest has changed → stop.
- A partial write-back happens silently → stop.
- Card volume exceeds the operator's actual review cadence → stop; the unit
  is wrong, go back to Task 1.
- Anything writes without a ruling → stop (INTENT §4).
- `classify_outcome` gains a fifth state → stop (standing).
- The round proceeds without Task 1's discovery note committed → stop.

## UAT — acceptance checks (Tim walks these)

- `[G]` A pending batch raises exactly one card carrying every 0048 field;
  approving it runs the declared stage through the existing execute route,
  with the existing lock and the existing four outcomes.
- `[G]` Change the pending set behind the Desk's back, then approve the stale
  card: the stage **refuses** on the digest, the refusal is on the run
  marker, and the next render shows a fresh card against the new set.
- `[G]` `hold` does nothing; expiry only marks `aged`; no path writes without
  a click.
- `[G]` The staleness cards from Phase 1b still derive, unchanged, alongside
  the new kind on the same board.
- `[H]` **Rule ten real batches.** Was the evidence on the card enough, or
  did you open the source to decide? Every open is a finding naming the
  missing field — same instrument as Phase 1's hunt count, pointed at a
  harder card.
- `[H]` **The generalisation verdict, in one paragraph.** Did 0048's anatomy
  fit a decision that has nothing to do with freshness — or did it fit only
  after the source was bent to it? A "no" here is worth more than the
  feature and outranks it in the report.
- `[H]` **Would you go back to doing this by hand?** The exit test, answered
  plainly. If yes, say what the Desk cost you that the manual step did not.

Results log needs a `uat` stamp naming the commit; do not write a `gate=`
field.

## Reporting

`docs/COWORK_REPORT_validation_ratify.md`, walk-sheet
`docs/UAT_validation_ratify.md`, stamped results after ten real batches — not
after the build.

Record: Task 1's discovery findings and everything they changed in Tasks 2–4;
the contract extension exactly as landed, with proof it names nothing
source-specific; the digest mechanism and every refusal it produced in real
use; the hunt count; and the generalisation verdict, which is this round's
actual output — the write-back automation is a side effect of asking it.
