# Skills convention — **STUB**

> **STUB, 2026-08-29.** Sections are marked **[SETTLED]**, **[STUB]** or
> **[OPEN]**. Written from the work rig's draft of the same date and its
> originating discussion, with the corrections below applied. **Nothing here is
> enforced and nothing checks it.** Fill the `[STUB]` sections in order; the
> `[OPEN]` ones need a decision before they can be written at all.

**Status:** authored, not enforced, **new practice**, and incomplete by
declaration.

**Scope:** how skills *reach* a thread, on any rig. Not what a skill contains —
**0052** owns that.

**Cites:** 0027, 0031, 0033, 0036, 0040 cl.7, 0045, 0050, 0051, 0052,
0057 cl.1.

---

## 0. What changed from the work rig's draft, and why

**[SETTLED]** Recorded so the divergence is visible rather than silent (0052's
branch-not-copy posture applied to a convention).

- **Its §3 counts were removed.** The draft asserted "six skills", "sixteen",
  and that the repo held neither `round-closer` nor `orientation`. Measured on
  `LucasGoonPC` 2026-08-29: the tracked path holds **eight** — both of those
  included, committed `f8253c0` and `a17fda8` — and this session's load path
  holds **seventeen**. The draft was written 03:27 on the 29th against the
  28th's tree and was stale on arrival. **Counts belong in a dated measurement
  this file cites, never in the rule.** `CONVENTION_decisions.md` §2.1 and
  `CONVENTION_docs.md` §5 both carry the same lesson from the same week.
- **The employment-IP reason was restored to §1.** The discussion raised it and
  the draft dropped it.
- **"Cycle boundary" removed.** Operator's correction: it was informal phrasing,
  not a defined unit.
- **`muster`'s meaning is contested and is now `[OPEN]`.** See §6.

## 1. Where skills live [SETTLED, one addition]

**`L5GN-Tools` remains the source of truth for skills and conventions.**

Three alternatives were weighed on 2026-08-28 and are recorded with their
reasons, because a convention showing only the choice made teaches a later
reader the others were never considered.

- **Move ownership to the work estate.** Rejected on two grounds, not one.
  First: **skills and conventions cannot be separated by the wall** — 0052 makes
  a skill stop when it cannot read its convention, so moving skills alone breaks
  all of them, and moving both relocates the estate's rule set across a boundary
  it cannot be pulled back across (0051). Second, and **omitted from the work
  rig's draft**: *skills authored in a work repo on work time are the
  employer's, and the current ones were authored personally.* That reason does
  not expire when a remote arrives, so it outranks the first.
- **A third repo, hosted by neither.** Deferred, not dismissed. Likely
  destination once a proper remote exists.
- **`Work_Bridge` as canonical host.** Rejected. **The bridge is transport, not
  host** — making both rigs read it before trusting their own kit is polling
  with extra steps, which is what 0036 stood down.

**The consequence to hold:** when a remote arrives this re-opens, and the change
is one pointer rather than an unpicked dependency.

## 2. Tailoring is a branch, and it is reported [SETTLED]

A rig needing different behaviour **branches**; it does not keep an untracked
copy. A branch can be diffed; a copy cannot, and this estate has measured the
difference.

**The only obligation is the report.** A rig that changed something says so.
Nothing is built on one rig for the other's benefit and no rig owes the other a
feature. The report crosses as a dated bundle or a `Work_Bridge` message,
**written when there is something to say**.

**Not a schedule, not a queue.** Nothing polls. Silence means nothing changed.

## 3. The tracked path is not the load path [STUB]

**The claim, which holds:** 0057 clause 1 says `.claude/skills/` is tracked
**and** the load path, one directory. **That is true of this repo and not of the
Cowork interface**, which materialises its own copy. A setting can change what a
thread can reach without touching version control — demonstrated when
`decision-scribe` was disabled and physically left the load path.

**Two consequences that stand regardless of counts:**

- A skill **absent from the load path is unreachable**, whatever the repo holds.
- A skill **present in the load path and absent from the repo is not authority**,
  and a thread should say so rather than using it silently.

**TO FILL:** the measurement this section cites — a dated investigation file
recording both listings on both rigs, so this rule never carries a number.

**TO FILL:** whether **0057 clause 1 needs a correcting entry** saying the clause
is true of a repo and not of every load path. That is a `decision-scribe` round,
not an edit here.

## 4. The check reports; repair is a second act [SETTLED]

The drift check compares tracked against loaded **in both directions**, because
the two directions mean different things (§3).

**It reports. It does not repair** (0045, 0031). Three reasons:

1. Auto-repair destroys the evidence that drift occurred, which is the finding.
2. A checker that also installs cannot be run casually to ask a question.
3. **It cannot tell a stale load path from a deliberate one.** The
   `decision-scribe` case was the operator switching a skill off on purpose. A
   repairing checker would have reinstalled it and been wrong.

Repair is a **separate, confirmed act** (0033) — same posture as `commit-scribe`
handing back `git commit -F` and `docs-archivist` staging a move.

**Never overwrite a local file wholesale.** Already recorded once for
`config/local.json`.

**An unreadable load path reports as unknown, never as clean** (0050).

> **Placement note.** *"Read the load path freshly by listing it, never by
> stat'ing an expected path"* is the stale-mount hazard and **is not specific to
> skills**. Under **0052 clause 4** an environment rule belongs to the
> environment, so it belongs in `CLAUDE.md`'s hazards with the consequence cited
> here. **TO FILL:** move it, then cite it.

## 5. Agnostic base, machine overlay [STUB — foundation unverified]

**The tracked `CLAUDE.md` holds only what is true of the project.** Machine
facts — OS, shell, absolute paths, sandbox mount translation, rig identity, and
that rig's hazards — live in an **untracked local overlay**.

**A rule appearing in the overlay is in the wrong place.** The overlay holds
facts; nothing tracked can read it, so a decision there is invisible.

**The overlay carries the drift statement** (§3): tracked path and loaded path,
named separately.

**NAMED GAP, and it is the whole architecture** (0040 cl.7): **the import
mechanism is not verified.** This file deliberately names no syntax it has not
tested.

**TO FILL, in this order:** (1) test whether the tooling **already** loads a
local overlay under a conventional name — inherit rather than invent; (2) only
if it does not, design one; (3) then write this section.

## 6. The skills this implies [OPEN — a name collision]

- **`armory`** — the check in §4. Compares tracked against loaded, both
  directions, reports, drafts the overlay when absent, hands back install
  commands. **Executes nothing.** Not built. Name uncontested.
- **`muster`** — **contested, and it must be settled before either is built.**
  - `CONVENTION_design_thread_restart.md` §9 proposes `muster` as the **snappier
    name for the restart skill**, with `reveille` as its alternative. That skill
    exists and is called **`dtr`**.
  - The operator's intent is `muster` = **the skills refresh**, callable from
    `dtr`.
  - The originating discussion noticed the clash — *"`muster` is already spoken
    for by the restart practice"* — and the work rig's draft then used it for the
    restart practice anyway.

  **TO FILL:** one name, one meaning. If `muster` becomes the skills refresh, the
  restart convention §9 needs a correcting note; if it stays the restart's name,
  the refresh needs a different one. **Either way `dtr` is the built skill and
  nothing should cite `muster` as existing.**

## 7. What this convention may not do [SETTLED]

- **May not become where a skill's rules live.** 0052 stands.
- **May not make the bridge a channel.** §1, 0036.
- **May not authorise a repair.** §4.
- **May not treat an unreachable source as clean.** 0050.
- **May not carry content across the wall**, in either direction. A conclusion
  may cross; a body of work does not cross by being convenient.
- **May not carry a count.** §0.

## 8. Open, and honestly so

- **The overall process this sits inside is unwritten.** This file rules on
  delivery. How a project runs end to end is a second convention that does not
  exist, and this one must not grow into it.
- **Staleness has no trigger**, and §7's ban on standing channels constrains the
  answer without settling it. 0050's *a source declares its own staleness* is the
  likely shape: surfaces stamp themselves, the restart reads the stamps, nothing
  polls.
- **0057 clause 1's correction** — §3.
- **The third-repo option** — deferred, not closed.
- **`muster`** — §6.
- **The overlay import mechanism** — §5.

## 9. The check [SETTLED]

1. Was the **load path listed fresh**, not stat'd by expected path?
2. Is drift reported in **both directions**, with the two meanings distinguished?
3. Did the check **report only** — was every install or write separately
   confirmed?
4. Is any local file that would be overwritten **shown before** it is touched?
5. Does the overlay contain **facts only**, no rules?
6. If a rig changed a skill, is it a **branch**, and was the change **reported**?
7. Was an unreadable source recorded as **unknown** rather than clean?
8. **Does this file still carry no counts?**
