---
name: dtr
description: Run a design thread restart — re-enter a design thread from the artefacts rather than from memory, in five stages, and write the dated restart note. Use when asked to restart a design thread, run a DTR or a muster, re-orientate before a round, pick up where a thread left off, or check what is pending and what has come in. Reads its convention; never ratifies, never rebuilds unbidden.
---

# dtr — design thread restart

**The convention is the authority. This skill carries no copy of it.**

Resolve `CONVENTION_design_thread_restart.md`, most-specific first:

1. `docs/CONVENTION_design_thread_restart.md` in the repo you are standing in
2. the estate's source-of-truth repo, if this repo is a consumer
3. **stop and say so**

**If the convention cannot be read, stop.** Do not run a restart from this
file's description, from memory of an earlier thread, or from a reconstruction.
Ask the operator to point at the file. A restart run from recall is the exact
failure the convention's §2 exists to prevent, and running one anyway would make
this skill the first thing it warns about.

**Self-test:** if this file has grown to contain the stage definitions, the
selection rules, or the restart note's shape, it has drifted into being a second
copy of the convention and needs cutting back (0052 clause 2).

---

## What this skill is for

Stages 1-5 in the convention's order, then the dated note. The order is a rule
and reverses badly — read §3 before deciding to skip ahead.

**This skill gathers and reports. It decides nothing.**

## Procedure

### 1. Read the convention, then the pointers

Read the convention in full. Then read `CLAUDE.md` if the repo has one — it says
where things are, and a restart that guesses paths is already off-convention.

### 2. Stage 1 — estate freshness

Run the repo's freshness command and **show its output verbatim**. Do not
re-derive a second staleness number from it; the convention says one line, shown
as printed.

A stale reading is **not an error** and not a licence to rebuild. Report it, say
that stages 2-4 will be read over data of that age, and ask. Rebuilding is the
operator's decision (0045 — report, never repair).

### 3. Stages 2 and 3 — pending decisions

Read the decision log's status lines and the drafts folder. Report:

- what is **proposed** and not yet ratified, by number and title
- what is **drafted and not appended**
- anything whose ratification is now available because the drafting day has
  passed (0033 — a re-read on a different day)

**Report on the axis that exists, and name the axis that does not.** Where the
log has no program or project field, say so rather than substituting repo
grouping silently. Where other logs sit behind a wall, name them as unread
(0051) rather than presenting one estate's view as the whole.

### 4. Stage 4 — board status

Read whatever board the repo actually has, and say which board it is. Where the
stage wanted a program or project board and only a document board exists,
**report the substitution**. Reading the available surface is fine; presenting
it as the missing one is not.

### 5. Stage 5 — inbound from beyond the operator

Per channel, in the convention's table. Two rules do the work:

- **Context packs are selected by the *open* test, not by what looks new.** A
  pack that owes a response is open until a dated artefact cites it by name.
  Never ask the operator what they have already seen — that is the watermark the
  convention refuses.
- **A source you cannot read is named as unread**, never omitted. An omitted
  channel is indistinguishable from an empty one.

Then the part that asks something of the operator rather than of a tool:

> **Ask what has reached them that exists nowhere as a file** — a conversation, a
> call, a decision taken away from the keyboard. Write down what they say, in
> their words, as an artefact. Anything they cannot or will not write down does
> not enter the round.

That prompt is the mechanism for the convention's §2 corollary. Skipping it
because nothing seems outstanding is how the corollary quietly stops applying.

### 6. Check the generated pairs are current

For each authored/generated pair the repo declares, report whether the generated
file is behind its source, and **hand back the command** rather than running it.
Where a generated file has moved, ask whether the map's pointers still resolve.

### 7. Write the note

One dated file, per the convention's shape. It is an **agenda, not a report** —
if it is longer than the round it introduces, the restart has become the work.

It must carry, by name: what could not be read, what is owed a reply, and what
was written down during the restart because it existed nowhere else. **A gaps
section that is empty every time is a restart that has stopped checking.**

Hand the note back. Do not commit it.

## What this skill may not do

- **Ratify anything.** A restart can *be* the different day for a ruling
  proposed in an earlier one, but the reading and the ratifying are two acts and
  the second is the operator's (0033).
- **Rebuild without being told**, or repair anything it finds (0045).
- **Summarise a source it could not read.** Unknown, never fresh (0050).
- **Substitute an available surface for a missing one without saying so.**
- **Judge priority between inbound items.** Report them; the operator ranks them.
- **Poll, watch, or subscribe to anything.** Every source is pulled, once, at
  restart time. A restart that acquires a standing channel has rebuilt the thing
  0036 stood down.
- **Carry content across a wall** (0051), in either direction.

## Anti-patterns

- Opening with *"where were we"*, or with a summary of an earlier session.
- Running the stages out of order because inbound feels urgent.
- Asking the operator which packs are new instead of computing which are open.
- Turning "not answered" into a pass, anywhere.
- Reporting the docs board as the project board.
- Growing the convention's contents into this file.
- Writing a note with an empty gaps section and treating that as a clean bill.
