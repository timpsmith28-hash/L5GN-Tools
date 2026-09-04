# Cowork brief — what Cowork actually loads, and the gap 0057 clause 1 says cannot exist

**Where you are:** `C:\Users\timps\Documents\GitHub\L5GN-Tools`, host
`LucasGoonPC`.

**Read before Task 1, in this order:** `CLAUDE.md` at the repo root — its
**Skills** row is the claim under test, not background; then **0057** in
`docs/DECISIONS.md`, clauses 1, 2 and 8 in particular; then **0052** clauses 2
and 3; then `docs/CONVENTION_skills.md`, which exists, is declared STUB, and is
where any rule this round produces belongs; then this brief; then
`docs/UAT_skill_load_path.md`.

**Draft-status:** written 2026-09-04, in the session that found the defect, to
be built the same day or the next. Every measurement below was taken that day
and is named with how it was taken, so it can be re-run rather than trusted.
**Re-run them as the round's first act** — and note that four skills were
refreshed during the finding session (see *The one act already taken*), so the
divergence this brief describes should no longer be present. **If it is still
present, that is the round's most important result and Task 1 has already
answered the falsifier.**

**Origin:** the cleanup session of 2026-09-04. `docs-archivist`, invoked in a
Cowork thread, loaded with the line *"Read `docs/README.md` §3 first — it is the
authority on the convention."* That is the exact stale citation corrected at
`99784e8` on 2026-08-31, and which `CLAUDE.md` records as **discharged**. The
same session had already worked around `brief-scribe` loading with *"There is no
written convention for briefs yet"* — false since 2026-08-27 — without
recognising the pattern.

**Measured, not inferred.** Six skills compared, line-endings normalised first
per **0057** clause 8 (`sed 's/\r$//' | md5sum`), between the tracked repo copy
and the directory the Cowork session actually loaded from:

| skill | loaded | tracked | |
|---|---|---|---|
| `docs-archivist` | 109 lines | 119 | **differs** |
| `brief-scribe` | 142 | 155 | **differs** |
| `decision-scribe` | 152 | 164 | **differs** |
| `round-closer` | 101 | 114 | **differs** |
| `commit-scribe` | 158 | 158 | identical |
| `consultant-docs` | 137 | 137 | identical |

**The four that differ are exactly the four corrected on 2026-08-31**, and each
is missing precisely the block that correction added — the *"Corrected
2026-08-31"* note and the convention citation beside it. The two that match were
untouched by that work. This is not random drift; it is one snapshot, taken
before a known date.

**Precondition — hard, and checkable:**

- **`docs/CONVENTION_skills.md` exists.** `test -f docs/CONVENTION_skills.md`.
  This round amends it or records why not; it does not write a new convention
  for a subject that already has one (**0052** clause 2).
- **`python verify.py` GREEN** before the first edit.
- **Task 1 is a read and may run immediately.** Tasks 2–4 wait on its result,
  because what Cowork loads after a refresh decides which of them are needed.

**Depends on — this repo's rulings:**

- **0057** — clause 1 (a skill's one source of truth is the repo's own load
  path; **the account or plugin store a skill is synced into is a deployment,
  never the source**), clause 2 (a task force branches, never copies; an
  untracked copy is the divergence the entry exists to stop), clause 5 (a skill
  that cannot read its authority stops rather than working from its own text —
  the clause a stale skill silently defeats, because it *can* read an authority,
  just the wrong one), clause 8 (a drift check over hand-carried text normalises
  line endings first — followed here).
- **0052** — clause 2 (the convention lives in the repo that owns the work and
  the skill cites it), clause 3 (no rule may have a skill as its only home).
- **0060** — clause 2 (a rule whose subject cannot be enumerated is recorded
  **unenforceable**, and that is a permitted outcome), clause 4 (a rule declares
  its reader, or declares that it has none).
- **0045** — report, never repair.
- **0030** — an authored file carries rationale; a generated one carries shape.

## The thing this round exists to name

**0057 clause 1's identity claim is true of Claude Code and false of Cowork.**
Its words: *"`L5GN-Tools` publishes every skill this estate authors from
`.claude/skills/`, which is tracked and is also where Claude Code loads project
skills from. **That identity is the point**: what is published is what runs, so
there is no gap for a publish-versus-load divergence to live in."*

Claude Code does load from `.claude/skills/`. **Cowork does not.** It loads from
a per-install plugin cache under
`AppData\Roaming\Claude\local-agent-mode-sessions\skills-plugin\`, which is
0057's own **deployment** — and clause 1 says a deployment is never the source.
The clause is right; what is wrong is the sentence after it, because the gap it
says cannot exist is exactly where four stale skills lived for four days.

**`CLAUDE.md` repeats the claim without the qualifier**, in two places:

- its table — *"Skills | `.claude/skills/` — tracked **and** the load path; one
  directory, deliberately (**0057** cl.1)"*;
- and its discharged-markers paragraph — *"All three now cite the convention in
  the row beside them — read on 2026-09-02, not inferred."* True of the tracked
  copies. **False of what a Cowork session loads**, which is what a Cowork
  session acts on.

**And the cost is not hypothetical.** Both stale skills that fired on 2026-09-04
sent a thread to the wrong authority. One was caught because the repo obviously
had the convention the skill denied; the other was not caught at all, and this
brief exists because the second one happened to be noticed afterwards. **0057
clause 5 makes a skill stop when it cannot read its authority. A stale skill
never stops** — it reads an authority, confidently, and it is the wrong one.

**The one thing 0057 clause 2 got exactly right, and it is why this was
findable:** the entry calls an out-of-git copy *"an untracked divergence"* and
contrasts it with a branch, *"a divergence that can be diffed."* The Cowork cache
is the untracked copy. It was diffable here only because a Cowork sandbox happens
to mount both paths at once — an accident of this environment, not a mechanism.

## The one act already taken, named rather than buried

**On 2026-09-04, before this brief existed, all four diverged skills were
refreshed** — the tracked `SKILL.md` bodies pushed into the account via Cowork's
`save_skill` with `overwrite`. That closes the *instance*. It does not close the
*mechanism*, and it was a change written into a deployment, which is the
direction 0057 clause 1 governs.

It is recorded here rather than in a report because it happened before the round
opened, and because **it changes what Task 1 measures**: Task 1 is no longer
"is there drift" but "did the refresh hold, and through what". If the refresh did
not persist, `save_skill` is not the mechanism and Tasks 2–4 are answering the
wrong question.

## Working rules

- **Report, never repair** (0045). This round establishes what loads and where
  the authority is; it does not build a sync.
- **Every comparison normalises line endings first** (0057 clause 8). A raw hash
  across a Windows tree and a synced store is not evidence of change, and this
  estate has a measured instance of five skills that looked adapted and were
  byte-identical once normalised.
- **The deployment is never edited to fix a divergence, except to restore it to
  the source.** Restoring is what happened above; authoring there is what 0057
  clause 1 forbids.
- **No rule this round produces lives in a skill** (0052 clause 3). It goes in
  `CONVENTION_skills.md` or nowhere.
- **An accepted entry's body is not edited.** 0057 stands as written; if clause
  1's second sentence needs qualifying, that is a superseding entry, not a patch.

## Tasks

1. **Establish what Cowork loads, and whether the refresh held.** In a **fresh**
   Cowork thread — not this one — invoke each of `docs-archivist`,
   `brief-scribe`, `decision-scribe` and `round-closer`, and record the first
   authority line each reports, verbatim. Compare against the tracked copies.
   **This is a read and it is the whole round's pivot**: if all four now cite
   their conventions, the refresh held and Tasks 2–4 are about preventing
   recurrence; if any is still stale, `save_skill` is not the mechanism and the
   round's finding is that this repo cannot fix it from inside.

2. **Decide whether the drift is checkable, and record which.** A reader would
   compare tracked `.claude/skills/*/SKILL.md` against the deployment. The
   deployment path is per-install, per-machine and outside the repo, so it may
   be **`subject-not-enumerable`** in 0060 clause 2's sense — *a permitted
   outcome, not a failure*. **The task is to determine which, not to force a
   checker into existence.** A checker that can only run on one machine, or that
   goes red on a fresh clone, is worse than a recorded `unenforceable`.

3. **Correct `CLAUDE.md`.** Its Skills row asserts an identity that holds for
   Claude Code and not for Cowork, and its discharged-markers paragraph asserts a
   present-tense fact about what skills cite that was false in a Cowork session
   on 2026-09-04. Both are corrections to a map, which is what `CLAUDE.md`'s own
   self-test says it is for — *"if this file and the thing it points at disagree,
   the thing it points at wins and this file is the defect."*

4. **Amend `CONVENTION_skills.md`, or record why not.** It is declared STUB and
   it is the home 0052 clause 2 gives this. The rule the round has to offer is
   small: **a skill's source is the tracked file; every other copy is a
   deployment; a deployment can lag, and a thread that suspects it should read
   the tracked file rather than trust what loaded.** If that is already there,
   say so and change nothing.

## Explicitly out of scope

- **Building a sync, a publisher, or anything that writes into the deployment on
  a schedule.** Report, never repair.
- **Refreshing skills by hand as a routine.** The 2026-09-04 refresh was a
  one-off restoration; making it a habit is a rule with no home but somebody's
  memory, which INTENT §5 and 0052 clause 3 both refuse.
- **Editing 0057.** Clause 1's second sentence may want qualifying; that is a
  superseding entry drafted by `decision-scribe`, and it is not this round.
- **The two skills that matched.** `commit-scribe` and `consultant-docs` are
  evidence, not work.
- **Anything about the work rig's skill deployment** (0051, 0036).
- **A second tracked skills directory**, under any justification. 0057 clause 1
  calls it a defect by name.

## Stop conditions

- Anything writes to the deployment other than the restoration already recorded
  → stop; that is authoring in a deployment (0057 cl.1).
- A second tracked skills directory appears → stop (0057 cl.1, verbatim).
- A checker is built that can only pass on `LucasGoonPC` → stop; record
  `subject-not-enumerable` instead (0060 cl.2).
- A rule from this round lands in a skill rather than in the convention → stop
  (0052 cl.3).
- 0057's body is edited → stop; supersede it or leave it.
- A comparison is made without normalising line endings → stop (0057 cl.8).
- Task 1 is skipped or answered from this brief's table rather than from a fresh
  thread → stop; the table is four hours old at best and is the thing under test.

## UAT — acceptance checks (Tim walks these)

**Falsifier for this round:** *did the refresh hold?* If a fresh Cowork thread —
today, and again a week from now — loads any of the four with its pre-2026-08-31
text, then `save_skill` is not the mechanism, the fix is upstream of this repo,
and **the consequence, written before the answer is known:** this round produces
a recorded `unenforceable` and a `CLAUDE.md` correction, and nothing else. No
checker, no sync, no habit. The estate would then know it cannot guarantee what
its own skills say when they run, and that is a finding worth having plainly.

- `[G]` In a fresh Cowork thread, each of the four skills reports the tracked
  authority line: `docs-archivist` → `docs/CONVENTION_docs.md` §4;
  `brief-scribe` → `docs/CONVENTION_briefs.md`; `decision-scribe` →
  `docs/CONVENTION_decisions.md`; `round-closer` → its 2026-08-28 publication
  note. Recorded verbatim, one line each.
- `[G]` The line-ending-normalised comparison between tracked and deployment is
  re-run and its result recorded, whichever way it falls.
- `[G]` Task 2's answer exists in the tree as one of exactly two things: a reader
  that can go red on more than one machine, **or** a recorded
  `subject-not-enumerable` naming why. Not silence.
- `[G]` `CLAUDE.md`'s Skills row no longer asserts an identity that is false in
  Cowork, and its discharged-markers paragraph no longer asserts a present-tense
  fact about what loads.
- `[G]` `CONVENTION_skills.md` either carries the source-versus-deployment rule
  or the report says why it does not.
- `[G]` No rule introduced by this round exists only in a skill file — grep the
  four skills for any sentence not present in a convention.
- `[G]` `python verify.py` → GREEN.
- `[H]` **Had you noticed?** Two stale skills fired at you on 2026-09-04 and
  neither was caught as a pattern until the third. Reading the four refreshed
  ones now — is the difference visible to you in use, or only in a diff? If only
  in a diff, this class of defect is invisible at the point it does harm, and
  that is the argument for whatever Task 2 concludes.
- `[H]` **Is `save_skill` a mechanism you would rely on?** It restored four
  deployments in one session, from a Cowork thread, with no record in the repo
  that it happened except this brief. Would you rather it left a tracked
  artefact — and if so, that is a card, not a line here.

**`[H]` count: 2.** The first asks whether the defect is perceptible in use,
which no assertion can answer. The second asks whether a mechanism is one the
operator would trust, which is a judgement about reliance and not about
behaviour.

## Reporting

`docs/COWORK_REPORT_skill_load_path.md`, walk-sheet
`docs/UAT_skill_load_path.md`, stamped results
`docs/UAT_skill_load_path_results.md`.

Record: Task 1's four verbatim lines and the date they were taken; whether the
refresh held; Task 2's answer and, if `subject-not-enumerable`, the exact reason;
what `CLAUDE.md` said before the correction, quoted, so the defect is legible
after the fix; whether `CONVENTION_skills.md` already held the rule; and — named
rather than absorbed — **that this round was found by accident**, because a
Cowork sandbox happens to mount both the tracked copy and the deployment, and
nothing was looking.
