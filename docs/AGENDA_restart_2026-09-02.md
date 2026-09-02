# Restart — Wednesday 2026-09-02

Run against `CONVENTION_design_thread_restart.md`, all five stages, on
`LucasGoonPC`. **It is an agenda, not a report** (§5). Everything below was read
today; nothing is carried from the 2026-09-01 sitting except where a commit is
cited.

**It also stands in for the note 2026-09-01 never produced.** That sitting
ratified 0060 and committed it at `55ce6af`, having run stages 2 and 3 only —
stage 1 was skipped, stage 4 was taken from a restart prompt rather than
derived, and stage 5 was not run at all. A restart that leaves no record
repeats the failure it exists to prevent, so the gap is named here rather than
quietly closed.

---

## Stage 1 — estate freshness

```
0.1h old (generated_at=2026-09-02T13:06:52+01:00) -- fresh
```

Verbatim, and not re-derived into a second staleness number. **Fresh, so no
rebuild was needed and no rebuild decision was taken.**

## Stages 2 and 3 — pending decisions

**Reported by repo, and only by repo.** `docs/DECISIONS.md` carries no program
or project field, so the axis §4 asks for cannot be answered from it. The
registry join that would supply it is one field away and unbuilt. This is the
third consecutive restart to record that.

`DECISIONS.md` held **60 entries, of which 2 were proposed** — 0058 and 0059,
both drafted 2026-08-28. **Both were re-read and ratified in this sitting**,
stamped `accepted 2026-09-02`. 0060 was ratified yesterday at `55ce6af`.
**Nothing now stands at `proposed`.**

**Every draft on disk is appended.** Both draft directories were checked file by
file against the log; no draft was orphaned. The two-directory hazard 0060's own
header named — `data/decision_drafts/` and `data/decisions_draft/` — is resolved
below rather than merely reported again.

**Work-estate rulings are unread, by construction.** MCF's `wfa-` log and
`sfds-` sit behind the wall; this rig reads what has crossed as a conclusion
(0051) and never the logs themselves. Stages 2 and 3 here are structurally
incomplete about them, and that is a containment fact rather than a defect.

## Stage 4 — board

**The program/project board does not exist.** The docs board is what was read,
and it is a board over documents. It is not being reported as the board the
stage wanted.

Derived from `docs/` rather than recalled: **11 briefs with no report, 8 reports
with no results log, 6 pairs with all three files present.**

**The derivation answers "do three files exist", not "is the round finished",
and the six were read.** None of the six is closed:

| pair | why not |
|---|---|
| `conductor` | INTERIM results log, and a task not built |
| `desk_stale_card` | INTERIM results log, and "flagged, not implemented" |
| `scanner_bugfixes` | INTERIM results log, and Task C recorded, not built |
| `conductor_governor` | Task 2 not built |
| `curator_tab` | Task 4 deliberately not built |
| `curator_correction` | a "Not built" section |

**Six of six**, where 2026-08-31 recorded three carrying INTERIM logs and three
with unbuilt tasks. The two conditions overlap on three pairs rather than
partitioning the six, which is what a filename-derived board cannot show.

**This is one question, not six.** *Does a deliberately-deferred task close a
pair, and does an INTERIM log?* It is a candidate ruling, it is worth making
once, and it is **not blocking this week's build.**

## Stage 5 — inbound

**Nothing.** The operator reports no outside updates today: nothing across
`../WizForge/Work_Bridge/to-personal/`, no context pack open under §6.1's test,
and nothing owed a reply.

**Nothing existed only in memory that had to be written down**, with one
exception, recorded in the next section because it was decided during the
restart rather than before it.

## What could not be read, by name

- **The live vault.** Not reachable from a Cowork sandbox; vault figures read as
  **unknown** (0050) unless the operator runs the probe.
- **Work-side decision logs.** Behind the wall (0051), named as unread.
- **`git`, from the sandbox.** Every git fact in this note came from the
  operator's own shell.
- **The auditor and tester census.** A naive parse of `verify.py`'s `AUDITORS`
  and `TESTERS` lists from the sandbox returned nothing, so the count is
  **unknown to this thread** and is the build's first act rather than a figure
  quoted here.

## Decided during the restart, because it existed nowhere

**The draft directory is `data/decision_drafts/`.** `data/decisions_draft/` was
deleted. The choice is not arbitrary: `CONVENTION_design_thread_restart.md` §4
names `data/decision_drafts/` as what stage 2 reads for unappended drafts, and
it is the only rule-bearing document naming either path — everything naming the
other is an agenda, a completed brief task, or 0060's descriptive header.

**Deleting the directory is not the fix.** Nothing tells the next thread where a
draft goes; §4 names the path in passing while describing something else, which
is how a second name grew. `CONVENTION_decisions.md` is the authority on the log
and says nothing about where drafts live. **Until it does, this will regrow.**

## Agenda for the round that follows

**Clear three pre-build items, then build the conformance reader (S4) and walk
it (S5).** The three: re-derive the auditor and tester census, which the brief's
own header demands as the round's first act; rule on
`UAT_conformance_reader.md`'s stale census figure, which A9 tests against;
and correct `CLAUDE.md`, whose skill-citation footnote and hand-copy debt were
made false by `99784e8`.
