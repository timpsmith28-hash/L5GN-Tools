# INTENT

What this system is *for*, and how we'd know if it stopped being worth building.

This doc makes no claims about what exists — that's `ARCHITECTURE.md` (what it is)
and the git log (what happened). **Intent can never be contradicted by the code. It
can only go stale.** Nothing here is verifiable; everything here is a want. If you
find yourself checking this file against the repo, you're reading the wrong file.

Revisit when the answer to "why am I doing this?" has moved. Not on a schedule.

> Some claims below are marked **[CONFIRM]** — they were inferred by an assistant
> reading the estate cold, not stated by the operator. They are questions wearing
> the clothes of assertions. Resolve or delete them; don't let them harden into
> fact by sitting here unchallenged.

---

## 1. The problem

Work gets *discussed* in one place and *done* in another, and the two never meet.
Reasoning, decisions, dead ends and rationale accumulate in chat threads across
Claude and Gemini, across personal and work accounts. The artifacts accumulate in
git. Neither side knows the other exists.

The cost isn't sentimental. It's that **decisions become unrecoverable while their
consequences stay in production.** A threshold gets set to 0.6 for a reason someone
explained well at the time; six weeks later it's a magic number nobody dares touch.
A linking signal gets rolled back for a good reason; the code stays in the tree and
nobody knows if reviving it is smart or the exact mistake already made once. Git
records that these happened. It cannot record why, and the why was written down —
in a thread, in an account, in a window that's now closed.

**[CONFIRM]** The secondary problem is drift in the other direction: things
thoroughly designed and never built, or built differently from how they were
designed, with nobody noticing the gap. Talked-not-built.

## 2. The thesis

**That chat history, linked to the code it produced, is a recoverable record of
reasoning — and that the link can be established mechanically rather than by hand.**

This is a claim, and it can be wrong. It's wrong if the links can't be made at
useful coverage; wrong if the linked record turns out not to answer real questions;
wrong if maintaining it costs more than the answers are worth.

**It is currently ~8% proven.** The headline figure — 150 `link_evidence` links
across 1,171 threads (12.8%) — flatters the truth. Of the 332 *substantive* threads
(≥4 messages, the ones that actually hold reasoning), only 27 carry an evidence link:
**8.1%**. The other 123 evidence links land on sub-4-message Takeout fragments. So the
honest coverage of threads that matter is roughly one in twelve, and that 8% — not the
flattering 13% — is the single most important figure in this estate. The mesh that
moves the data is finished; the thing the mesh exists to carry is barely connected
where it counts.

**The falsification test:** ask the system a question only it can answer — *why was
vocabulary killed as a linking signal?*, *what was the reasoning behind
`similarity_threshold = 0.6`?* — and see if it answers. As of now it can't answer
either. That's not a bug list; it's the thesis not yet holding.

## 3. What success looks like

Not "the pipeline runs." The pipeline runs today. Success is:

- A question about *why* the code is the way it is gets answered from the record,
  without the answer being "I remember roughly."
- A drift report says something true and surprising — discussed but never built,
  or built without ever being discussed.
- The record can be *shown*, not just recalled. A question about *why* gets an
  answer you could hand to someone who needs the justification — a reviewer, a
  council, a future maintainer — not just one you half-remember. Recall serves
  you; **defensibility serves whoever doubts you**, and the second is the harder
  test the record either passes or doesn't.
- The record is trustworthy enough to act on. A link that's probably right is worse
  than no link, because it gets believed.

**[CONFIRM]** And a personal one, which shouldn't be left implicit because it drives
real decisions: **this is a vehicle for learning to build.** Three months from
spreadsheets to a working multi-machine system. That goal is legitimate and it
sometimes *conflicts* with the goals above — the fastest way to a working system is
to accept code you don't understand, and that's exactly how a subsystem arrived
whose tunables nobody can defend. Where they conflict, **understanding wins**, or
the learning goal has quietly eaten itself. The test isn't "can I direct the
building of this." It's "could I debug this at 2am, alone."

## 4. Non-goals

Named because each one, unstated, invites scope creep that looks like progress:

- **Not a product — but no longer only mine.** One operator, three machines, an
  SSH key. Not multi-tenant, not hardened against an adversary, no SLA.
  **[CONFIRM]** A second workstream (WizForgeAnalytics) now vendors this toolkit
  and floats on `main` — that makes `main` load-bearing for someone else, but it
  is a *consumer who complains*, not a customer who is owed. The deposit contract
  is still a wall against *mistakes*, not attackers. If this ever grows users with
  expectations, that's a different project, and this non-goal is where it must be
  re-argued.
- **Not a chat archive.** Archiving is the cheap part. Unlinked chat is a pile.
  Linkage is the whole product; storage is table stakes.
- **Not comprehensive.** Work-account Gemini going forward is out of scope by
  decision, not omission. Coverage of what matters beats coverage.
- **Not automated judgment.** The system produces deterministic facts. Reading
  them is the operator's job. Confidence scores route attention; they don't rule.
  **[CONFIRM]** Nothing closes, links, or reopens without a human — this is stated
  here as a standing *value*, not a v1 limitation to be optimised away later. If it
  is really just a v1 limitation, move it to ARCHITECTURE and delete it here, or
  this section is lying to future-you.
  **Narrowed by §8, deliberately and at a stated cost.** A ruling may be
  *standing* — made once, explicitly, revocable in one act — so a settled shape
  of decision is applied without being asked again. What does not move: no
  judgment is ever the system's. What narrows: per-instance review, given up
  only where looking again adds nothing. §8 states the price and the test; this
  bullet is not softened to fit it, it is amended by it.
- **Not a rewrite of git.** Git holds what changed. This holds why.

## 5. Standing constraints

These generate the architecture. If a design decision contradicts one of these,
the design is wrong — or this list needs an argument made against it.

- **Guarantees are structural, not behavioural.** Prefer *can't* to *shouldn't*.
  The wall is path separation, not a field you remember to set. The deposit target
  makes a cross-estate write physically impossible. The auditors scope to
  `registry.SCANNERS`. The gate is a hook, not a resolution. Any rule that survives
  only because the operator remembers it is a defect awaiting its incident — and
  we have the receipt: the one convention-based invariant in the estate is the one
  that lost 133 links.
- **Fail loud, never silently wrong.** A stale schema fails; it doesn't lie. An
  unmatched turn is recorded as a gap; it is not fabricated. **A plausible wrong
  answer is the worst thing this system can produce**, because the entire value
  proposition is being able to trust the record.
- **Read-only until proven otherwise.** The scanners cannot write. Detection and
  action are different programs.
- **The data is irreplaceable; the derived is free.** A deleted share link doesn't
  come back. Embeddings, renders and reports are caches — rebuild them, never
  merge them. Spend paranoia only where loss is permanent.
- **One writer.** Concurrency isn't a feature worth its cost here.
- **The wall is real.** Work and personal do not mix, structurally, at rest.
- **Rigor is graduated, not maximal.** The gates exist because willpower fails,
  but ceremony applied everywhere is its own failure — the operator routes around
  a tool that demands a decision log for a throwaway script, and a routed-around
  gate protects nothing. **[CONFIRM]** The stakes are declared, not assumed: a
  PII-handling work repo and a scratch experiment do not earn the same friction.
  Strict where it matters, quiet where it doesn't — a tool that cannot dial down
  is one that gets abandoned, and an abandoned governance tool defends nothing.

## 6. How we'd know this failed

Honest failure modes, in rough order of likelihood:

1. **It becomes the thing it catches.** A system built to detect talked-not-built,
   elaborately discussed and thinly used. The infrastructure is done and the thesis
   is at 8% on threads that matter — this is not a hypothetical, it's the current
   reading.
2. **The record gets believed while being wrong.** Worse than failure #1, because
   #1 is merely wasted effort. Low-confidence links that get trusted make the
   estate *less* knowable than no links at all.
3. **The operator can't maintain it.** The gap between directing a build and owning
   it. Measured against the 2am test, not against whether the build lands.
4. **It gets too tight to use.** The discipline that makes it defensible becomes
   the discipline that makes it unbearable; the operator starts skipping the
   decision entry "just this once," and the defensibility claim is quietly false
   from that day. **[CONFIRM]** This is the failure the graduated-rigor constraint
   exists to prevent, and the one most likely to arrive disguised as diligence.
5. **The upkeep exceeds the answers.** If the manual loop stays manual, the honest
   move is to shrink the system, not to add to it.

Any of these is a reason to stop or cut scope. None of them is a reason to add
features.

## 7. What this doc is not allowed to do

Contain a fact. No counts, no status, no "currently implemented as." The one number
above (~8%) is here because it's the thesis's own scoreboard — **[CONFIRM]** and if
that proves too tempting to let rot, cut it and let the reader derive it.

Everything else this doc might want to say about the present belongs in
`ARCHITECTURE.md`, the git log, or `verify.py`.

---

## 8. The widened thesis: Quartermaster

The original thesis stands: chat history, linked to the code it produced, is a
recoverable record of reasoning. What it under-claimed is *why* the record is
worth keeping. The record is not the product. **The decision is the product.**
The record exists so decisions arrive cheaper, fewer, and durable.

So the widened thesis: **this system is an allocator of three scarce resources
— the operator's attention, frontier tokens, and machine time — and everything
in it exists to spend those three well.** The picture of the estate is the
allocator's input, not its output. A surface that shows facts without moving a
decision is furniture.

What "spending well" means, as wants:

- **A decision should arrive assembled, or not arrive.** The question, the
  trigger, the evidence with provenance, the options with their costs, a
  default and an expiry. Assembling context is the system's job; judging is
  the operator's. Any card that makes the operator go hunting has failed at
  the desk's one purpose.
- **A decision made three times is a policy not yet written down.** The system
  should notice repetition and offer promotion. A ratified policy is a
  standing ruling that executes with citation — it is not the system deciding;
  it is a decision the operator already made, still binding, finally cheap.
- **Frontier tokens are capital, not fuel.** They may buy exactly two things:
  judgment that unblocks stalled work, and artifacts that permanently lower
  the cost of future work by moving it down to local tiers. Spend that buys
  only an answer, once, is the spend to eliminate.
- **Work runs at the cheapest capable tier**, escalates only on evidence, and
  every escalation is recorded with its cost — so the question "what does
  each tier deliver per pound and per hour" is always answerable from the
  record, never from impression.

### What a standing ruling is, and what it costs

§4 says *nothing closes, links, or reopens without a human*, and says it as a
standing value rather than a limitation to be optimised away. Promotion tests
that sentence, so the test is taken head-on rather than argued around.

**What does not move.** No judgment is made by the system. Nothing is inferred,
scored into action, or decided by a confidence threshold. Every action the
system takes still traces to a human decision, and where there is no such
decision, work waits for a hand.

**What narrows, deliberately.** *A human* becomes *a human ruling*, and a ruling
may be **standing** rather than per-instance. The operator may decide once that
a recurring shape of decision has a settled answer, and have that answer applied
without being asked again.

**What that costs, stated rather than dissolved.** Per-instance review is given
up for that shape of decision. That is a real reduction in oversight, chosen,
not a technicality — and calling a policy "a ruling made once" does not make the
tenth application of it something the operator looked at. It is worth paying only
where looking again adds nothing.

**What the narrowing is worth only if it holds.** A standing ruling must be
raised as a question and answered explicitly — never inferred from repetition
alone. It must cite the decisions that prompted it. It must be revocable in one
act. Every action taken under it must say which ruling authorised it. And the
operator must be able to enumerate every standing ruling in force, on demand.

**The test, in one line:** if the operator cannot say what the system is
currently allowed to do without asking, the value in §4 has been breached —
whatever the mechanism is called. That is the failure to watch for, and it is a
better alarm than any wording.

### How we'd know *this* failed (additions to §6)

- **The desk becomes a feed.** Cards arriving faster than rulings, defaults
  firing unread — attention routed, then flooded. The desk's worth is measured
  in decisions retired per week, not cards raised.
- **Policies harden into automation the operator no longer recognises.** A
  promoted policy the operator can't recall ratifying is §4's "not automated
  judgment" quietly breached. Every policy must trace to its rulings, and
  revoking one must be one act.
- **The economy gets gamed by its own metric.** Frontier spend that launders
  itself as "distillation" while the local tiers never actually keep more
  work. The test is the retirement of future spend, measured, not the label
  on the purchase.