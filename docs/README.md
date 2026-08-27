# docs/ — what lives here, and what doesn't

The map of this folder. **It decides nothing.** Every rule this file used to
carry now lives in `CONVENTION_docs.md`, which is the authority; if this file and
that one disagree, that one wins and this file is the defect.

The governing rule, in one line so a reader knows what the convention is for:
**a document earns its place by holding something that cannot be derived.**
Rationale cannot be derived — it lives here. Status can be derived from
`verify.py`, `git log` and the DB — so it does not.

---

## What is here

| | |
|---|---|
| The trinity | `INTENT.md`, `ARCHITECTURE.md`, `DECISIONS.md` — maintained, and they win against anything that disagrees |
| Conventions | `CONVENTION_*.md` — one per subject |
| Reference | `RUNBOOK_*.md`, `SPEC_*.md` |
| Rounds | `COWORK_BRIEF_*.md` → `COWORK_REPORT_*.md` → `UAT_*.md` → `UAT_*_results.md` |
| Dated snapshots | `AGENDA_*.md` |
| Generated | `_*.md` — never hand-edited (**0030**) |
| Retired | `archive/` — stamped, read-only history |
| Raw exchanges | `investigation/` — evidence, born frozen, never graduates |

Two subdirectories, and no others. Everything else in `docs/` is a file.

## Where the rules are

**`CONVENTION_docs.md`** is the authority for this folder, and the file
`docs-archivist` cites:

- §1 the core set · §2 doc classes and the prefix that carries them · §2a why a
  skill is the procedure and the document is the authority
- §4 the archiving convention — when a doc is archivable, the archive stamp, the
  uat stamp, the gate-frozen marker, and why `auditor_doc_claims` stops at the
  archive door
- §5 `investigation/` — what it holds, how files are named, and the
  acknowledgement stamp
- §6 the two classes that are permanently retired — **no status board, no
  handoff or priming document** — and why
- §7 what none of it enforces

**`CONVENTION_briefs.md`** owns the round: what a brief must contain, how the
walk-sheet is written with it rather than after it, and `[G]` / `[H]`.

**`CONVENTION_decisions.md`** owns the entry format, numbering, citation and the
five status values.

## Before you add a doc

Read `CONVENTION_docs.md` §2 and pick the prefix first. The prefix is the class,
and a file named without one is invisible to every tool and every reader scanning
by class — which §7 names as this folder's single point of failure.
