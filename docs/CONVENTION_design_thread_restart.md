# Design thread restart convention

**Status:** authored, not enforced, and **new practice**. Unlike the artefact
conventions, this one does not describe something the repo already does. It
describes a recurring act the operator has been doing irregularly and wants to
do deliberately. Two of its five stages have no surface to read yet, and those
are named rather than assumed (§4, §6).

**Scope:** this repo and the design thread that runs against it. A restart on
the work rig would be a different document, because it reads different sources
and sits behind a different wall.

**This governs a practice, not an artefact.** Every other convention in `docs/`
rules on a file. This one rules on a **human act performed with a machine**, and
that difference sets its two hardest rules: §2 (read, never recall) and §7 (a
shape, not a schedule).

**Cites:** 0012 (the registry's program/project tiers — the axis §4 wants and
`DECISIONS.md` does not have), 0027 (summary-only governs artefacts that
travel; a local surface reads the source at render time),
0031 (a non-gating surface reports findings, never a verdict), 0033 (propose,
ratify, execute), 0036 (the cross-machine mesh stands down -- the objection was
the standing channel, not the transfer), 0040 clause 7 (gaps are named, with their reason, and sized where they
can be), 0045 (report, never repair), 0050 (a source declares its own staleness;
one that cannot be reached reads as unknown, never as fresh), 0051 (containment
by construction), 0052 (a skill scripts a procedure and cites its convention),
0054 (a machine fact is derived and reported, including nothing).

---

## 1. What a restart is, and what it is not

**A restart is a re-entry into a design thread from the artefacts rather than
from memory.** The operator's own framing is a morning briefing: you arrive, you
find out what the situation actually is, and only then do you decide what today
is for.

**It is not a status report.** Nothing is produced for an audience. The output
is an agenda for the round that follows.

**It is not a planning session.** A restart establishes state. What to do with
that state is the design work, and it starts when the restart ends.

**It is not a gate.** Nothing fails a restart. It reports, including reporting
that it could not read something (0031, 0045).

**The failure it exists to prevent** is the one this estate keeps finding in
other forms: a long thread accumulates context that lives only in the thread,
and a cold restart silently drops it. `CONVENTION_config.md` §1 records a config
divergence that survived days because two machines each held half of it.
0052 records a hazard learned twice by two threads. A restart is the moment that
class of loss is supposed to surface, which is why §2 is the rule that matters
most.

---

## 2. Read, never recall — including the operator

**Every stage reads an artefact. No stage is answered from memory.** Not from
the operator's, and not from an assistant's summary of an earlier session.

This is not a statement about trust. Every silent failure this estate has
recorded had the same shape: someone knew a thing, the knowledge was not in a
file, and a later reader could not tell the difference between *unknown* and
*not written down*. A restart that begins *"where were we"* reproduces exactly
that.

**The corollary is uncomfortable and load-bearing:** where an input exists only
in the operator's memory — a corridor conversation, a decision taken in the
shower, a complaint someone made verbally — **the restart is where it becomes an
artefact, or it does not enter the round.** Writing it down is part of the
restart, not preparation for it. §6 is where this bites hardest.

**An unreadable source reports as unknown, never as clear** (0050). A stage that
could not reach its source says so and the restart continues. Silence is a
finding; it is not a pass.

---

## 3. The stage order, and why it is that order

The order is a rule, not a list. Each stage depends on the one before it in a
way that reverses badly.

| # | Stage | Why it sits here |
|---|---|---|
| 1 | **Estate freshness** | Every later stage reads data that could be stale. A confident answer over stale data is the failure INTENT §5 refuses everywhere else. Establish the ground before standing on it. |
| 2 | **Pending program decisions** | An unratified ruling changes what everything after it means. |
| 3 | **Pending project decisions** | Same, narrower. Program before project because a program ruling can moot a project one. |
| 4 | **Board status** | The board shows what work exists; stages 2-3 show what work is *permitted*. Reading the board first invites planning against rules that are still proposed. |
| 5 | **Inbound from beyond the operator** | The only stage that can add new obligations. Triaging new demands before knowing your own state means triaging against an unknown baseline — which is how a loud request outranks a quiet commitment. |

**Stage 5 last is the one people get wrong**, because inbound feels urgent and
freshness feels like admin. The order says otherwise, deliberately.

---

## 4. What each stage reads today

Written as it is, not as it should be. Where a surface does not exist, that is
stated and the stage degrades to a named gap (0040 clause 7) rather than to a
guess.

**Stage 1 — estate freshness.** `estate_freshness_check.py` prints exactly one
line and reads `data/estate.json`'s own `generated_at` field rather than the
file's mtime, so rewriting identical content does not read as a refresh. Over
24h reads as stale, matching the Desk's own build stamp. **The line is shown
verbatim and never re-derived into a second staleness number.** A stale reading
is not an error; it is an instruction to rebuild before trusting stages 2-4.

**Stages 2 and 3 — pending decisions. The axis does not exist yet, and this is
the honest gap.** `docs/DECISIONS.md` is **repo-scoped**. It has no program or
project field, so "pending program decisions" and "pending project decisions"
cannot be answered from it as written.

What can be read today: the log's status lines. At the time of writing, 49
accepted and 3 proposed (0051, 0052, 0053), plus whatever sits in
`data/decision_drafts/` unappended. That is *pending decisions for this repo* —
useful, and not the requested axis.

The axis exists elsewhere. 0012 defines program > project > repo and the
registry assigns every repo to a project and every project to a program
(`CONVENTION_project_registry.md`). **The join is one field away**: a ruling
carrying a registry id would let a restart group pending decisions by program
and by project across every repo that keeps a log. This convention does not
create that field — it records that stages 2 and 3 are asking for it, so that
when it is added the reason is on record.

Until then, stages 2 and 3 report **by repo**, and say plainly that they are
reporting by repo because the program axis does not exist.

**Cross-repo logs, and the wall.** Other logs exist — MCF's `wfa-` rulings,
`sfds-` — and the work-side ones are behind the wall. A restart on this rig
reads what has **crossed** as a conclusion, not the logs themselves (0051).
That is a containment fact, not a defect, and it means stages 2-3 on this rig
are structurally incomplete about work-estate rulings. Say so in the output
rather than presenting a personal-estate view as the whole picture.

**Stage 4 — board status. One board exists; it is not the one this stage
wants.** The docs board renders `docs/` as columns derived mechanically from
filenames — brief → report → walk-sheet → results log → archived — recording
nothing new and rendering a lifecycle that already exists. It is a board over
**documents**.

A board over **programs and projects** does not exist. Stage 4 therefore reads
the docs board today and reports the program/project board as absent, with the
same registry-join note as stages 2-3. Two stages wanting the same missing axis
is evidence about what to build next, and that evidence is the point of writing
the gap down rather than quietly substituting the board that does exist.

**Stage 5 — inbound.** §6.

---

## 5. The restart produces one dated artefact

**A restart that leaves no record repeats the failure it exists to prevent.**
Its conclusions would live only in the thread, which is where the lost context
was living in the first place.

**One file, dated, small.** What was stale and whether it was rebuilt; what is
pending and where; what the board showed; what came in from beyond the operator
and what was written down during the restart because it existed nowhere else;
and the one-line agenda for the round that follows.

**It is an agenda, not a report.** If it is longer than the round it introduces,
the restart has become the work.

**It records what could not be read**, by name — an unreachable source, a log
behind the wall, a stage with no surface. A restart note whose gaps section is
empty every single time is a restart note that has stopped checking.

**It is not testimony to be revised.** A later restart is a new file. A
correction is a new file that says what it corrects — the estate's standing
posture on records that travel.

---

## 6. Stage 5: the channels beyond the operator

This is the stage with the most sources, the least structure, and the only one
where §2's rule can genuinely fail.

**The channels are not alike, and the convention should not pretend they are.**

| Channel | Artefact? | Reads how |
|---|---|---|
| **Context packs** (work rig, dated and stamped) | **yes** — the purpose-built one | listed by date; selected by §6.1's *open* test, never by recall |
| `Work_Bridge/to-personal/` | **yes** — dated files, one per exchange | fetched and merged deliberately; an unmerged bundle is unread mail |
| Email, chat, tickets | yes, but **outside the estate** | read where they live; what enters the round is a written conclusion, never a copied thread |
| In-person, calls, corridor | **no artefact at all** | §2's corollary: written down during the restart, or it does not enter the round |

**Context packs are the channel this stage was waiting for.** The work rig
already builds them: dated, stamped, and deliberately produced as the place
context is dropped to be reviewed, answered, responded to or otherwise
disposed of. They are the only stage-5 source that was *designed* to be read
by a later reader, which makes them the one to measure the others against
rather than a special case to accommodate.

### 6.1 "New" is the wrong test; *open* is the right one

The obvious selection is **new** — packs the restart has not seen. It is the
wrong test, and for a reason this convention has already met twice: *new*
requires remembering what was seen, which is either a watermark file nobody
maintains or the operator's memory, and §2 refuses the second outright. A
restart that asks *what is new* has quietly reintroduced an inbox, with the
read-state living somewhere nothing can check.

**A pack is open until an artefact answers it, by name.** That is derivable
from the artefacts alone, on any machine, at any time, with no state kept
between restarts — which is exactly the property *new* lacks.

Making it work costs one field:

1. **A pack declares whether a response is owed.** Not every pack is a
   question; some are deposits. A pack that owes nothing is closed on
   arrival, and says so rather than being inferred to be harmless.
2. **A pack that owes a response is open until a dated artefact cites it by
   name.** The answering artefact names the pack; nothing else closes it.
   *"Dealt with in conversation"* does not close a pack — §2's corollary
   applies, and the conversation becomes the artefact or the pack stays open.
3. **Closure is never a status edited onto the pack.** It is the existence of
   the answer, computed at read time (0027), so an unanswered pack cannot be
   marked closed by anyone in a hurry.

**This is the estate's recurring shape, for the third time.** The bridge:
*an exchange is a dated file; if it is answered, it is answered by another
file*, and *a reply is owed* — the obligation being the price of the
arrangement. `DECISIONS.md`: a ruling is superseded by a later entry that
says so. The conversation map: a row is corrected by a later row carrying
`[status:…]` and a reason (0046). Context packs are the same mechanism
arriving at a fourth artefact, and they should not invent a fourth vocabulary
for it.

**The awkward case, named rather than smoothed.** A pack answered *partly* is
still open, and will look like neglect in the restart note for as long as it
takes. That is correct and it will be irritating. The alternative — letting a
partial answer close a pack — makes *open* mean "nobody has replied at all",
which is a much weaker claim than the one this stage needs.

**Where the packs live is a containment question, not a convenience one.**
They are built on the work rig. A restart on this rig reads what has crossed
under 0051, and names the rest as unread (§6's closing rule) rather than
omitting it.

**The bridge is the model, and the other channels should be measured against
it.** An exchange there is a dated file, it is answered by another dated file,
and *"nothing here is a queue, an inbox, or a thing anyone is expected to
poll."* A restart reads it because a person decided to, on that day.

**Stage 5 must not become an inbox.** The temptation is exactly the one 0036
ruled on: the objection to the mesh was never the transfer, it was the standing
channel that runs whether or not anyone decided it should. A restart that
subscribes to five sources and surfaces them automatically has built the thing
0036 stood down, with better manners. **Every source in stage 5 is pulled, by a
person, at restart time.**

**Containment applies at the boundary, not at the summary** (0051). A work-side
message read on the work rig may produce a conclusion that crosses; the message
itself does not. Stage 5 on this rig reads what has already crossed and what
belongs to this estate — and where it knows a channel exists that it cannot
read, it names the channel as unread rather than omitting it, because an omitted
channel is indistinguishable from a channel with nothing in it.

**A reply is owed.** The bridge's own rule — a complaint that arrives and is
never answered turns "complaint, not a patch" into "complaint, into the void" —
means stage 5 does not only *collect*. Anything inbound that is owed an answer
is named as owed in §5's note, and stays named until a file answers it.

---

## 7. A shape, not a schedule

**This convention defines what a restart is. It does not say when one happens,
and it must not.**

The operator's aspiration is to restart *more regularly*, and the morning-brief
analogy points at recurrence. That is a legitimate want and it is a **separate
decision** from this document, because a convention that mandates a cadence has
made itself a schedule — and this estate's position on things that run whether
or not anyone decided they should is 0036's.

**A scheduled restart is still a person choosing to read the output.** If a
recurring task ever fires one, what it may do is *prepare* — run stage 1, gather
what stages 2-5 will read — and what it may not do is conclude. The agenda is
written by the person the restart is for.

**Not doing one is not a failure.** A missed restart is a day nobody restarted,
which is a fact about the day and not a defect in the practice. The moment a
skipped restart reads as a violation, the restart has become a gate, and §1 says
it is not one.

---

## 8. What a restart may not do

- **It may not ratify.** Ratification is a re-read on a different day (0033).
  A restart *can be* that different day for a ruling proposed in an earlier
  restart, and that is a genuine benefit of the practice — but the reading and
  the ratifying are two acts and the second one is the operator's alone.
- **It may not rebuild silently.** Stage 1 reports staleness; rebuilding is a
  decision, and the note records that it was taken (0045).
- **It may not summarise a source it could not read.** Unknown, never fresh.
- **It may not substitute an available surface for a missing one without
  saying so.** Reading the docs board when the stage wanted a project board is
  fine; reporting it as the project board is not.
- **It may not carry content across the wall** (0051), in either direction.

---

## 9. The skill, and its name

A skill scripts this procedure and cites this file; it does not restate the
rules (0052).

**What the skill may do:** run stage 1, gather what each stage reads, report
what it could not reach, draft §5's note, and ask the operator for anything that
exists only in memory (§2's corollary — the prompt for it is the mechanism).

**What the skill may not do:** ratify, rebuild without being told, judge
priority between inbound items, or poll anything.

**A snappier name.** `muster` fits the estate's existing vocabulary — Castle,
Armory, Knight, Quartermaster, Warden, Conductor, Curator, Chronicler — and
means the right thing: a roll-call of what you actually have, taken by a person,
before committing any of it. `reveille` is the alternative if the
morning-briefing framing is the one worth keeping in the name.

---

## 10. The check, at the end of a restart

1. Did **stage 1** run, and was its line read **verbatim**?
2. Are stages 2-4 reported on the axis that actually exists, with the missing
   axis **named** rather than substituted?
3. Was anything that existed only in memory **written down**, during the
   restart?
4. Are the sources that could not be read **named as unread**?
5. Were context packs selected by the **open** test, not by what felt new
   (§6.1)?
6. Is anything **owed a reply**, and is it named as owed?
7. Does the note fit on one page, and is it shorter than the round it
   introduces?
8. Was anything **ratified**? If so, that was a second act on a different day,
   not part of the restart.
