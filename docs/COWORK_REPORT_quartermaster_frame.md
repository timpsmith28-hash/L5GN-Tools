<!-- gate-frozen: commit=a79bcc9 -->

# Cowork report — Phase 0: the Quartermaster frame

**Pair:** `docs/COWORK_BRIEF_quartermaster_frame.md`. Sessions 2026-08-17..19.
**Gate:** GREEN at `a79bcc9` through the pre-commit hook — **12 auditors + 81
testers**. Cited for the record, not as this round's achievement: no code was
written, so the gate's composition moved for reasons belonging to other rounds.

**A documentation round, and it stayed one.** No module, no schema, no
migration. The deliverable is text that every later phase cites, which is why
the brief insisted it exist first.

---

## What landed

**`docs/INTENT.md` §8 — the widened thesis.** The record is not the product;
the decision is. The system is named as an allocator of three scarce resources
— attention, frontier tokens, machine time — and the picture of the estate is
reclassified as the allocator's *input*. Four wants follow, and a closing
subsection states what a standing ruling is and what it costs. §6 gains three
new failure modes: the desk becoming a feed, policies hardening into
unrecognised automation, and the economy gaming its own metric.

**`docs/INTENT.md` §4 — amended, not softened.** The bullet keeps its
`[CONFIRM]` and its original sentence intact and appends the narrowing beneath
it, pointing at §8. The sentence with receipts still reads as it did.

**`docs/DECISIONS.md` 0048** — the unit of throughput is a decision; a surface
that wants attention raises a card. Five clauses: the unit, the fixed anatomy
(with *a card missing any field is not raised*), silence as a stated input,
`default`/`expiry` declared-now-inert, and a sunset on standing rulings.

**`docs/DECISIONS.md` 0049** — frontier conversations are a sensed input; the
system moves work down-tier rather than budgeting spend it cannot see. Five
clauses: no frontier invocation, no spend envelope, the corpus as sensor,
down-tier proposals requiring a named local capability plus evidence, and
success measured as recurrence declining in the corpus.

**`docs/investigation/2026-08-17_quartermaster_fable_2-response.md`** — the
vision thread, filed under `docs/README.md` §4, born frozen, `actioned:` block
empty. Its preamble states what it is allowed to claim: a want, not a ruling,
with 0048 and 0049 named as the two proposals drawn from it.

---

## What the editing pass changed — this round's real output

The brief asked for this above everything else, because the delta between the
drafts and what survived is the first honest test of whether the frame holds
when its operator handles it. Four changes, and one of them is a replacement.

### 1 · D-B was replaced, not edited

The draft read: *"Frontier tokens buy rulings or durable cost reductions,
nothing else… Spend is logged as events with stated purpose; **the envelope is
self-reported and says so**."*

That last clause is the tell. A self-reported envelope is a number the system
cannot observe being given the authority to refuse a plan — and disclosing that
it is self-reported does not repair it, because the refusal still lands with the
weight of a measurement. 0037 already refuses exactly this shape in the
estimation case: **refuse, never clamp; measurement before estimation.** The
draft was that same failure wearing a disclosure.

0049 inverts the subject rather than trimming the clause. The useful question
stops being *how much was spent* and becomes *what was asked repeatedly that a
local tier could have prepared*. Spend is unobservable; the conversations are
already ingested and already mined for claims.

Two consequences, both recorded in the entry rather than left implicit:

- **The economic half of the frame relocated.** It is a query over claims, so
  it belongs beside the Curator's linking work — not in a separate accounting
  round, which is where the draft would have put it.
- **Nothing now stops an expensive week.** 0049 offers no brake, and says so:
  the brake it replaced was decorative, and a decorative brake is worse than
  none because it invites the belief that spending is governed.

### 2 · D-A gained an expiry instead of a warden

Drafting D-A surfaced a question the draft did not answer: policy can become
the lazy way out, so who reviews policy? The obvious answer is a reviewer — a
role, an actor, something that watches.

0048 clause 5 answers it with a **sunset** instead. A standing ruling expires
unless renewed, and renewal is itself a card carrying that policy's own firing
record as evidence, so a policy that has authorised nothing since the week it
was made answers its own renewal question. Chosen for INTENT §5's reason:
prefer *can't* to *shouldn't*. A watcher is one more thing to own at 2am; an
expiry needs owning by no one.

### 3 · `default` and `expiry` were ratified as declared-now-inert, and told

Not in the draft at all. No policy engine exists, so in v1 every default reads
`hold — nothing runs` and expiry does nothing but re-raise a card marked
`aged`. Ratifying them anyway is deliberate — the anatomy is fixed now so a
surface does not hard-code a narrower one — but clause 4 names the cost: **a
field identical on every card for months trains the eye past it.** Their going
live later is a change the operator should be told to expect rather than
discover.

### 4 · "the Desk is the front door" left the ruling

The draft's D-A was titled *"the unit of throughput is a decision; **the Desk is
the front door**."* 0048's title names only the unit. The Desk survives in the
entry's *Consequences* — "the Desk becomes the front door aspiration made
literal" — and nowhere else.

Small edit, deliberate: a ruling about what a decision *is* should not be
hostage to whether one particular tab survives its trial. Phase 1 can fail
without taking 0048 with it.

---

## The §4 reconciliation

The brief's first `[H]` check, and the one that could have cut promotion from
the frame cheaply. The resolution as landed does not argue §4 away; it splits
the sentence into what moves and what does not.

**What does not move:** no judgment is made by the system, nothing is inferred
or scored into action, and where there is no human decision, work waits for a
hand.

**What narrows:** *a human* becomes *a human ruling*, and a ruling may be
standing rather than per-instance.

**What that costs, stated rather than dissolved:** per-instance review is given
up for that shape of decision — *"a real reduction in oversight, chosen, not a
technicality"* — and, in the append's own words, *"calling a policy 'a ruling
made once' does not make the tenth application of it something the operator
looked at."*

Five conditions guard the narrowing (raised as a question and answered
explicitly, cites its prompting decisions, revocable in one act, every action
names its authorising ruling, all standing rulings enumerable on demand), and
the whole thing reduces to one test:

> if the operator cannot say what the system is currently allowed to do without
> asking, the value in §4 has been breached — whatever the mechanism is called.

That line is the alarm, and it is better than any wording because it is
answerable by asking the operator rather than by reading the code.

---

## The `[G]` acceptance check — answered here

- **DECISIONS numbering is sequential.** 0044 → 0050, no gaps, no reuse.
- **Both entries carry Source lines naming the vision thread**, each citing its
  draft letter (`D-A`, `D-B`) so the cross-reference survives the renumbering.
- **INTENT holds no facts after the append.** §8 carries no counts, no file
  paths, no module names and no "currently implemented as". The single
  occurrence of *"currently"* is inside the §4 test line — a statement about
  what the operator can say, not about what the code does.

The three `[H]` checks are Tim's and are not answered here. See below.

---

## What this round did not close

Recorded rather than smoothed, because a Phase 0 that reports itself clean
while later phases already cite it is the failure this whole frame exists to
catch.

**1 · The ratification is uncommitted.** Both entries read `Status: accepted`
in the working tree and `Status: proposed` in committed history at `d6d75da`.
Meanwhile `d4f1c54` and `a79bcc9` (Phase 1's Desk) and draft 0050 all already
cite 0048. **This report and that status flip belong in the same commit** —
until then the log says the frame is unratified while three things built on it
say otherwise.

**2 · The different-day rule was kept, but the log cannot show it.** The brief
made same-sitting ratification a stop condition, and it was honoured — the
entries were drafted 2026-08-18 and approved on a later reading. But both
carry only `Date: 2026-08-18`, the drafting date, and no ratification date, so
nothing in `DECISIONS.md` evidences the rule. **Recommend a `Ratified:` field
on both**, which also gives 0048 clause 5's sunset an anchor to count from —
a policy cannot expire from a date the log does not hold.

**3 · There is no walk-sheet.** `docs/UAT_quartermaster_frame.md` does not
exist, so the three `[H]` checks have nothing to be walked against. The one
that matters most is the third: **read 0049 against the last three frontier
spends, and say which of the two legitimate purchases each was.** That check
is the cheapest available refutation of 0049 and it has not been run.

**4 · 0049's own homework is written but not run.** The entry's *What would
show this wrong* says clause 3 is testable against the existing corpus and
*should be tested before anything is built on it*.
`docs/investigation/2026-08-19_downtier_recurrence_probe.py` is that test,
written and untracked, scoped as `COWORK_BRIEF_curator_linking.md`'s Task 0.
Until it runs, **0049 is accepted on argument, not on evidence** — and its own
stated failure mode is that the corpus holds no legible repetition, in which
case clause 3 is an elegant description of nothing.

**5 · Phase 1 started before Phase 0 closed.** The brief's out-of-scope section
says the first line of code belongs to Phase 1's brief and *lands only after
this round closes*. The Desk landed at `d6fa9b7` on 2026-08-18, the same day
the entries were drafted and before they were ratified in any committed form.
No defect in the Desk — its own round is running and going well — but the
ordering the brief specified was not kept, and the reason the ordering existed
(later phases must not be able to force a ratification) is exactly the pressure
finding 1 now describes.

**6 · Task 4 of the brief names the same file twice.** It instructs committing
`…2026-08-17_quartermaster_fable_2-response.md` **and**
`…2026-08-17_quartermaster_fable_2-response.md` — a leftover from before the
vision and plan were consolidated into a single document. There is no missing
second file; recorded so a later reader does not go looking for one.

---

## Where this leaves the pair

The frame is written, coherent, and already load-bearing: 0050 builds on 0048,
the Desk implements its anatomy, and `curator_linking` is scoped against 0049.
What it is not, yet, is **closed** — and the gap is administrative rather than
intellectual.

**The pair closes when three things happen:** the `accepted` flip is committed
alongside this report; a `Ratified:` date is added to both entries; and the
three `[H]` checks are walked against a sheet. The third is the only one that
can still change the answer — specifically the frontier-spend check, which is
the one place a real recent fact could refuse 0049.

This report is testimony as of `a79bcc9` and is not maintained
(`docs/README.md` §2).
