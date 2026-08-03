# Prompt — ARCHITECTURE drift audit

**Date:** 2026-08-02 · **Model:** Claude (Cowork, design thread) · **Machine:**
`LucasGoonPC` · **Tree:** working tree at the docs-board commit.

Captured per `docs/README.md` §4. This is the ask as it was made, not a
reconstruction.

---

## The ask, in Tim's words

> whilst we have done a fairly thorough job of this build I'm sure there's
> probably lots of housekeeping and other tasks we can funnel into this 20%
> window. Help me review some high token use methods that would be beneficial to
> the build (trying to think of things other than writing more code to back up in
> my UAT stack. we'll pick a few ideas and then we can run some investigation
> brief and report pairs.

Selected from the options offered: **the ARCHITECTURE drift audit** and **the
knight roles design** (this file covers the first). Output ruled to
`investigation/` only, findings appended at the end, with a new acknowledgement
stamp to be designed so an investigation can record that something was actioned
as a result of it.

## The task as scoped

Read `docs/ARCHITECTURE.md` in full against every entry in `docs/DECISIONS.md`
(0001–0028) and against the current code, and report where the document that
`docs/README.md` §1 calls *"the authoritative shape reference"* no longer
describes the system.

Constraints set on the work:

- **Every claim must cite a real file, line or entry number**, checked against
  the working tree. No finding asserted from a report or from memory.
- **No code changes.** The output is findings.
- **No new UAT debt.** This lands in `investigation/`, which §4 places outside
  the maintained lifecycle — never maintained, never graduates, never walked.

## Why this target

`ARCHITECTURE.md` was last written at `c1c81ee`, **2026-07-18**. It cites
decisions 0002, 0004, 0005, 0006 and 0008 and nothing after. Twenty entries have
been ratified since. In that window the estate gained the deposit wall's project
axis (0010), the three-tier registry (0012), the snapshot read surface (0013),
structural single-writer (0014), the review write endpoint, the command deck,
estate-scoped visibility (0025), knowledge documents (0026), render-time reads
(0027) and staged working-tree writes (0028).

The stakes are set by `docs/README.md` §1: *"Where a brief, a report or an
archived doc disagrees with the trinity, the trinity wins."* A stale shape
reference does not fail quietly under that rule — it wins arguments it should
lose.
