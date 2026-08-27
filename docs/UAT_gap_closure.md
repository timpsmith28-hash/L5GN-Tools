# UAT — gap_closure

Walk-sheet for `docs/COWORK_BRIEF_gap_closure.md`. Written with the brief,
before the build (`CONVENTION_briefs.md` §2, once Task 2 lands).

**Walked by Tim.** `[G]` checks are decided by a machine or an unambiguous
procedure; `[H]` checks need a human judgement and are counted deliberately —
**six of twenty-four**, each asking about experience rather than behaviour.

Results go to `docs/UAT_gap_closure_results.md`, stamped with the commit walked.
A failed check is the walk working. Record it and do not soften it.

---

## Preconditions

- [ ] `[G]` `grep -c "^## 00" docs/DECISIONS.md` returns **57**.
- [ ] `[G]` `git config --get core.hooksPath` returns `.githooks`, and
      `.githooks/pre-commit` exists.
- [ ] `[G]` `git check-ignore -v data/git_warden` returns a rule.

## Task 1 — `CONVENTION_decisions.md`

- [ ] `[G]` `docs/CONVENTION_decisions.md` exists and contains **no** `wfa-` or
      `sfds-` citation.
- [ ] `[G]` Its header names origin repo, origin file and date.
- [ ] `[G]` It carries the five status values, and states that the freeze
      attaches at **acceptance, not commit**.
- [ ] `[H]` Reading only this file, could someone write a conforming DECISIONS
      entry — including a real falsifier — without opening the work rig's
      version?

## Task 2 — `CONVENTION_briefs.md`

- [ ] `[G]` `docs/CONVENTION_briefs.md` exists; header names the adoption.
- [ ] `[G]` It describes **this repo's** card identity (`COWORK_BRIEF_<slug>`)
      and imports no per-project numbering or registry.
- [ ] `[G]` Its statement about whether this repo has a gate matches
      `git config --get core.hooksPath`.
- [ ] `[G]` `brief-scribe`'s line-12 self-declared drift risk is now false, and
      the report says so.

## Task 3 — the skills

- [ ] `[G]` Five skills exist under `skills/`, plus `dtr`.
- [ ] `[G]` Task 3a landed as its **own commit**, and its tree is byte-identical
      to the named source once line endings are normalised.
- [ ] `[G]` The `sha256` list in 3a's commit body reproduces when recomputed.
- [ ] `[G]` `grep -rniE "L5GN-Tools|docs/Consultants|MCF" skills/*/SKILL.md`
      returns nothing outside a resolution example. Show the output.
- [ ] `[G]` Every skill states, in its own text, that it stops when its
      authority cannot be read.
- [ ] `[G]` 3b is **staged and uncommitted**, pending 0057.
- [ ] `[H]` Take one skill and imagine tailoring it for the work rig. Is there
      anything you would have to edit that should have been a convention?
- [ ] `[H]` Does `consultant-docs` now fail honestly, rather than pointing at
      something plausible and wrong?

## Task 4 — `CONVENTION_docs.md`

- [ ] `[G]` `docs/CONVENTION_docs.md` exists; `docs-archivist` cites it rather
      than a README section.
- [ ] `[G]` Every prefix in its class table matches a file that exists in
      `docs/`, or is marked unused. Spot-check three.
- [ ] `[G]` `docs/README.md` no longer holds a rule that exists nowhere else.
- [ ] `[H]` The `docs/investigation/` decision — would you defend it in a month,
      and does the reasoning survive being read cold?

## Task 5 — `CONVENTION_gitignore.md`

- [ ] `[G]` Every rule in the block was verified with `git check-ignore -v`
      against a real path, and the output is quoted in the report.
- [ ] `[G]` The document states that `check-ignore` is the only verification and
      that a file read is not evidence.
- [ ] `[G]` No baseline rule newly ignores a file git already tracks.
- [ ] `[G]` `.gitignore` itself is unchanged this round.

## Task 6 — `run.py decisions-map`

- [ ] `[G]` `python run.py decisions-map` writes `docs/_decisions_map.md`.
- [ ] `[G]` Run twice against an unchanged log, the output is byte-identical.
- [ ] `[G]` Counts reproduce: 57 entries, 23 orphans, `0025` cited ten times.
- [ ] `[G]` The output contains **no prose from any entry** beyond its title.
      Grep for a distinctive phrase from a Consequences section; expect nothing.
- [ ] `[H]` Does the orphan list read as a finding you would act on, or as
      noise you would learn to skip?

## The round

- [ ] `[G]` Nothing was committed by the thread. Every commit in
      `git log` for this round has a human at the keyboard.
- [ ] `[H]` **The round's falsifier.** How many of the five skills are stopped,
      and is your instinct to fix their conventions or to go back to editing
      them in the plugin store? Write the answer before deciding what it means.
- [ ] `[H]` Was the evidence in the report enough, or did you go hunting?
