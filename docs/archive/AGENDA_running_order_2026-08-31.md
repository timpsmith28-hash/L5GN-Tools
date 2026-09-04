> **ARCHIVED** 2026-09-04 · superseded · no report — an agenda is a planning act and has no pair
> Superseded by `AGENDA_running_order_2026-09-04.md`, which supersedes §1 by name and records in its own §0 what of this order actually landed · Original purpose: the running order that promoted the conformance reader ahead of Cards C and D, on the operator's call of 2026-08-31.
> Accurate history: §0's evidence for the promotion, §0a's sizing — `auditor_doc_claims` named as the pattern to build to, which is what `auditor_rule_subjects` and later `auditor_authors_declaration` were built against — and §0b's stated cost, that Cards C and D would slip, named rather than absorbed. All of it held. **Stop trusting:** §1's five sessions as a plan. S2 through S5 landed in full; **S1 landed one item of four**. And **§1 S1's instruction to "check `tests/tester_authors.py` first" is a wrong pointer** — that tester covers git commit author aliasing (`config.author_aliases`, `config/authors.json`), not **0054** clause 6's per-artefact `authors`. Two unrelated things in this repo carry that name; following the pointer on 2026-09-04 produced a false claim that clause 6 was still live, corrected in the 09-04 order's own amendment. §2's "Cards C and D — deferred" no longer holds.

# Agenda — the running order, 2026-08-31

The planning act that follows `AGENDA_restart_2026-08-31.md`. Frozen at its date.
It names rounds and their sequence; it writes no brief and no code, and it
**ratifies nothing**.

**Host:** `LucasGoonPC`. **HEAD at writing:** `065c117`. Every figure was read out
of the tree on 2026-08-31 and is cited with its file.

> **This file does not amend `AGENDA_running_order_2026-08-28.md`.** That file
> declared its third amendment its last, and a fourth would be the plan becoming
> the work. This is a **new order that supersedes §4 of that one**, and it says
> below exactly what it changes and on whose instruction. The 08-28 file stands
> as written and as evidence.

---

## 0. What changed, and who changed it

**§6a's open call has been made by the operator: promote the conformance
reader.** 08-28 §4 deferred it behind Cards C and D, on the reasoning that C and
D test the join with briefs and data that already exist. The operator has
reversed that deferral on the budget conversation of 2026-08-31.

**Recorded as the operator's call, not this thread's**, and 08-28 §6a's own
framing is why it was his to make: *"deciding it is a restructure and belongs to
a thread that opens on it."* This is that thread.

**The evidence that accumulated between the two orders**, none of it solicited:

- **Seven rulings accepted in one afternoon** (0051-0057), creating seven more
  unenforced rules. **Two more proposed since** (0058, 0059).
- **Two conventions added 2026-08-29** (`CONVENTION_project_process.md`,
  `CONVENTION_skills.md`), both declared STUB, **neither enforced and neither
  carrying 0057 clause 7's adoption header.** Conventions now number **11**.
- **0056 is accepted and violated today**, with the gate green over it.
- **Card B's prerequisite turned out to be a contradiction, not an ambiguity**
  (§1 below) — an accepted clause and the code asserting opposite things, with
  nothing able to notice.

**The count of rules without readers is growing faster than any card mechanism
can raise questions about them.** That was §6a's aggregate finding and four days
have strengthened it.

## 0a. The sizing that makes this affordable, and it was not obvious

**The conformance reader is a restructure at the rule level and a small build at
the code level.** Measured on this reading:

| | |
|---|---|
| auditors registered in `verify.py` | **12** |
| largest | `auditor_doc_claims.py`, **192 lines** |
| median | ~55 lines |
| smallest | `auditor_tool_contract.py`, 27 lines |

`auditor_doc_claims`' own docstring states the house pattern and it is the
precedent to build against: *"Narrow and mechanical by design: it checks exactly
ONE class of claim… A small auditor that always runs beats a large one that
rots; extend only to claims with one authoritative source."*

**So the promotion does not mean a general conformance engine.** It means **one
ruling on how a rule declares itself checkable, then two or three small auditors
in that pattern.** The 08-28 deferral priced this as a restructure. It is a
restructure of the rule set and an ordinary week of code.

## 0b. What the promotion costs, stated rather than absorbed

**Cards C and D do not get built this week.** They were the deferral's
beneficiaries and they are what slips. `staleness_feeds` (497 lines) and the
promotion step both open with a rewrite, and neither is started here.

**That is the trade and it should be visible in a month.** 08-28 §7's falsifier
still stands: *"a month from now the Desk still has one real card type — then
this plan spent its rounds feeding a trial nobody was running."* Promoting the
reader does not answer that falsifier; it postpones the evidence for it.

---

## 1. The order

**Sequenced so that stopping after any session leaves something built,
committed, and walkable — never an eleventh brief.** That constraint is the
whole point of this file: the pattern that produced 10 unbuilt briefs and 8
unwalked reports is that planning is cheap and building is not, so rounds ended
in a brief.

### Session 1 — the prerequisite and the seed instances

**Not a warm-up.** Every item is an instance of the class the reader generalises
from, so doing them first is how S3 gets a rule with worked examples instead of
a theory.

1. **0054 clause 6 — settle the contradiction.** It is Card B's named
   prerequisite and it is not an ambiguity. The accepted clause says `authors`
   *"lives in the tracked file only"*; `authors` sits in **both**
   `config/machines.json` (tracked) **and** `config/local.json` (untracked), and
   `run.py:900` documents the untracked one as where it lives. **Check
   `tests/tester_authors.py` first** — a reader may already exist and be reading
   the wrong file, which would make this the fourth seed instance rather than a
   config fix.
2. **0056 gap 1 — close the live violation.** Pin
   `config/personal_conversation_map.tsv`; stop `auditor_conversation_map_pin`
   binding `ARTEFACT`/`PIN_FILE` to one hardcoded path at module level. **This
   is the cleanest seed instance in the estate**: the ruling names a *pattern*
   and the code names a *path*, which is 0056 clause 1's own wording turned on
   0056's own auditor.
3. **The two registry resolvers.** `chronicler/pipeline/db.py:52` has two steps;
   `chronicler/review/core.py:247` has three. The review endpoint validates
   against a registry the pipeline would have skipped. Small, and it sits inside
   Card B's blast radius, so it is cheaper here than during B.
4. **Gap 6 — the adoption-header pass.** 5 of 11 conventions carry 0057 clause
   7's header. A pass, not a round.

**Ends on:** commits, a green gate, and **four worked instances of one shape**.
**Does not end on:** a brief.

### Session 2 — Card B: the relink stage learns to report

Unchanged from 08-28 §4 except that its prerequisite cleared in S1. Two defects
remain live and both were re-verified on 2026-08-31:

- **Skipped:** `has_registry()` false prints `[relink] skipped (no input
  available)` (`run_pipeline.py:204`) — the identical line every input-gated
  stage prints — and the chain finishes green. **Its own docstring claims the
  skip is "clean and loud". It is neither**, and `relink.py:174`'s `SystemExit`
  is never reached. A docstring asserting a loudness the code does not implement
  is 0048 clause 4 with a comment attached.
- **Ran:** `relink.py` contains **zero** references to `ingestion_log`, so
  `summarize_from_log` returns `None` and the stage prints `[relink] ok — no new
  rows` (`run_pipeline.py:232`) whatever it did. Wrong in the reassuring
  direction, not merely vacuous.
- **Failed:** fixed at `198bcdd`. Third defect closed.

Scope against **0053** (authority, not dependency). **A code change here touches
`chronicler/`, so `docs/_architecture_shape.md` regenerates in the same commit**
(0030, `CONVENTION_commits.md` §6) or `auditor_architecture_current` blocks it.

**Ends on:** a stage that answers for itself in all three outcomes.

### Session 3 — the ruling, then the brief

**The only session that legitimately ends in a brief, because S4 is
contractually the build.**

1. **Draft 0060 as `proposed`** (`decision-scribe`): what makes a rule
   machine-checkable, and how a convention or ruling **declares its own
   reader**. This is the restructure. It is not a taxonomy — the falsifier
   should be that a rule which cannot name a reader is either not a rule or not
   yet checkable, and saying which is the point.
2. **Write the brief and its walk-sheet** (`brief-scribe`) from the four-plus
   instances S1 and S2 produced, not from theory.

**The seed instances already known**, and they are what keeps this honest:
0056 gap 1; 0054 clause 6; 0040 clause 1 (08-28 §5a records that *"the query
that finds every violation of clause 1 can be written today against the schema
as it stands"*); 0057 clause 7's adoption headers; and `CLAUDE.md`'s own Debt,
*"nothing checks any convention in this file."*

**Stop condition, and it is this week's sharpest:** if S3 ends with a brief and
no ruling, the session failed. The ruling is the expensive half and the brief is
downstream of it.

### Session 4 — build the readers

Two or three auditors in `auditor_doc_claims`' pattern — narrow, one claim class
each, one authoritative source each, registered in `verify.py`'s `AUDITORS`.
**Not one large reader.** 0056's own Consequences admit it created *"an unknown
quantity of latent non-conformance and no list of it"*; producing that list is
the first reader's output, and a list is a deliverable a walk can check.

**Ends on:** a green gate that is green for a better reason than it was on
2026-08-31.

### Session 5 — walk it, and let it raise what it raises

`round-closer` on S3's sheet. **The reader's real falsifier is not whether it
passes its own walk** — it is whether the non-conformance it lists gets acted on
or ignored, which is 08-28 §7's second falsifier arriving early and cheap.

**If S5 finishes early:** re-verify `COWORK_BRIEF_staleness_feeds.md` against the
tree as a **read**, and stop there. Its header demands that re-verification at
round-open, doing it costs nothing, and it sets Card C up for next week. **Do not
start the rewrite.** A rewrite begun in a tail budget is how this estate got ten
unbuilt briefs.

---

## 2. Not in this order, and why

- **Cards C and D** — the thin slice. Deferred by the promotion, per §0b. Card C
  gets its re-verification read in S5 if there is room.
- **`hermetic_gate`** — unblocked by 0053, briefed 2026-08-24 and current, still
  unscheduled. Its slot relative to Card B remains **an open call nobody has
  made**, and this file does not make it either. If S2 finishes early it is the
  best candidate, because it is gate hygiene and S4 is about to add to the gate.
- **Card E (Governor's route)** — cannot precede C and D. Untouched.
- **Card F (copy currency)** — unblocked by 0057, unscheduled.
- **0051 clause 2's containment auditor** — the most serious gap in consequence
  and the least urgent operationally. **It is the same shape as the conformance
  reader** and S3's ruling should be checked against it, but it is its own card.
- **0055's registry migration** — undone; no card, no urgency against this order.
- **The tenant migration investigation** — written and unrun. **Hard
  precondition: the post-migration snapshot must cover a full working week.**
  Check its date range before opening it; stop if short.
- **`INTENT.md` §2 / `ARCHITECTURE.md` §7 still read ~8%** against a measured
  10.42%. **Both move together or neither does, and it is the operator's call.**
  Not scheduled.

## 3. The budget shape, and what I cannot see

**Approximately five sessions were allocated.** I have **no visibility into
session limits or usage** and cannot plan against a clock — so the unit above is
**a card, not an hour**, and each session boundary is a commit rather than a
timer.

**Where the natural stops are:** S1 and S2 each end green and committed. S3 ends
on a proposed ruling and a brief — the one boundary that carries a debt into the
next session, and the reason S4 is written as contractually the build. S4 and S5
each end green.

**If the week runs short, the honest truncation is after S2** — the prerequisite
cleared, the seed instances collected, Card B built. The reader would then open
next week with better evidence than it has today and nothing wasted.

## 4. What would show this order wrong

- **S3 produces a taxonomy rather than a mechanism.** Then the promotion bought a
  vocabulary, and 08-28 §2a's warning about grading schemes applies to rules as
  it did to cards.
- **S4's readers pass on day one and never fire again.** Then they are 0048
  clause 4's check that cannot fail, built by a thread that cited 0048 clause 4
  as its reason for existing.
- **The list S4 produces is read by nobody.** Then non-conformance was never the
  constraint, the 08-28 deferral was right, and Cards C and D were the better
  week.
- **A month from now the Desk still has one real card type.** Unchanged from
  08-28 §7, and this order makes it *more* likely, not less. It is named here so
  the promotion cannot claim to have addressed it.
