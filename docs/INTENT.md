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

**It is currently ~13% proven.** ~150 `link_evidence` links across ~1,171 threads.
That number is the single most important figure in this estate, and it should appear
in any honest description of the system's state. The mesh that moves the data is
finished; the thing the mesh exists to carry is one-eighth connected.

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

- **Not a product.** One operator, three machines, an SSH key. Not multi-tenant,
  not hardened against an adversary, not for anyone else. The deposit contract
  is a wall against *mistakes*, not attackers.
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

## 6. How we'd know this failed

Honest failure modes, in rough order of likelihood:

1. **It becomes the thing it catches.** A system built to detect talked-not-built,
   elaborately discussed and thinly used. The infrastructure is done and the thesis
   is at 13% — this is not a hypothetical, it's the current reading.
2. **The record gets believed while being wrong.** Worse than failure #1, because
   #1 is merely wasted effort. Low-confidence links that get trusted make the
   estate *less* knowable than no links at all.
3. **The operator can't maintain it.** The gap between directing a build and owning
   it. Measured against the 2am test, not against whether the build lands.
4. **The upkeep exceeds the answers.** If the manual loop stays manual, the honest
   move is to shrink the system, not to add to it.

Any of these is a reason to stop or cut scope. None of them is a reason to add
features.

## 7. What this doc is not allowed to do

Contain a fact. No counts, no status, no "currently implemented as." The one number
above (~13%) is here because it's the thesis's own scoreboard — **[CONFIRM]** and if
that proves too tempting to let rot, cut it and let the reader derive it.

Everything else this doc might want to say about the present belongs in
`ARCHITECTURE.md`, the git log, or `verify.py`.
