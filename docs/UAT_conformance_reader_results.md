<!-- uat: commit=8a61aec dirty=false host=LucasGoonPC walked=2026-09-02 -->

# Results log — the conformance reader (walked 2026-09-02, LucasGoonPC) — INTERIM, one check unconfirmed

Partner to `docs/UAT_conformance_reader.md`. Walked against
`docs/COWORK_REPORT_conformance_reader.md` at `8a61aec`, working tree clean, by
Tim, with the `[G]` checks verified from the tree and from runs by the walking
thread and the `[H]` checks answered by Tim in his own words.

**No `gate=` field in the stamp, deliberately.** It is optional in
`auditor_uat_stamp`, and this round is the one that found what it costs: it
records a fact about the moment of the walk and is compared against the live
census, so every open log detonates the next time gate composition changes.
Writing one here would plant the bomb this round just defused in three other
logs. `commit=` fixes the gate state for anyone who wants it — check out
`8a61aec` and count the lists.

**Declared `INTERIM` at first writing**, under `CONVENTION_docs.md` §4's four
conditions:

1. It says so here, in the title, on the day it was first written.
2. **What it waits for, concretely:** A2's second half — one person reading
   `docs/CONVENTION_conformance.md` end to end against its own §9 table, to
   confirm the table omits no imperative. That is a read, not a judgement, and
   a reader can tell whether it has happened. It is a ten-minute job.
3. Every re-walk re-cuts the stamp above to the commit it ran against.
4. A superseded verdict is marked superseded and left standing, never deleted.

---

## The `[G]` checks

| check | verdict | evidence |
|---|---|---|
| **A1** | **verified** | `docs/DECISIONS.md` line 3684 reads `**Status:** accepted 2026-09-01`, later than its `**Date:** 2026-08-31`. `55ce6af` changed exactly two files — the log and `docs/_decisions_map.md` — and that map's status table carries `accepted 2026-09-01 \| 1`. |
| **A2** | **partial — see INTERIM above** | `docs/CONVENTION_conformance.md` exists and cites 0060 by clause throughout. §9 lists 17 imperatives, each mapped to a clause of 1-8. **The completeness half is unconfirmed:** the thread that wrote §9 checking §9 proves nothing, and nothing mechanical verifies it (`CONVENTION_conformance.md` §10 says so). |
| **A3** | **verified** | `verify.py`'s `AUDITORS` carries `auditors.auditor_rule_subjects`; every run from `db149f8` onward prints `[ OK ] auditor_rule_subjects` by name. |
| **A4** | **verified** | Two consecutive renders of an unchanged tree hash identically (`Get-FileHash`, `$h1 -eq $h2` → `True`). **Re-run after the two rendering fixes**, because the first determinism test was taken against a version that is not the one committed. |
| **A5** | **FAILED as written** | Every rule carries exactly one classification, none is blank, and the counts sum: 1 + 0 + 0 + 71 = 72. But the map carries **four** classes and A5 names three. See defects below — the check is what is wrong here, not the map. |
| **A6** | **verified** | The map's header carries "The denominator, and how it was derived": 72 rule-bearing documents = 60 entries counted by `## NNNN —` heading + 12 files matching `docs/CONVENTION_*.md`, derived at render time and not from a stored count. |
| **A7** | **verified** | Every run prints the carve-out line — naming `DECISIONS 0001-0060` and the 11 predating conventions — before its verdict, rather than leaving it in a docstring. |
| **A8** | **FAILED** | **Zero rules classify `subject-not-enumerable`.** Recorded as a failure, not softened. See defects: the check's own expected first member could not have satisfied it. |
| **A9** | **verified** | The census was re-derived at round-open three ways, none of them recollection — reading the lists, importing the module, and counting the run's 93 `[ OK ]`/`[FAIL]` lines. The brief's 82→81 correction was recorded as an instance on 2026-08-31; the walk-sheet's own misquote was corrected the same way at `dfb92be`. |
| **A10** | **verified** | Both halves. `tests/tester_remedy_round_trip.py` landed **and** the report records the search that established it — only `auditor_conversation_map_pin` and `auditor_architecture_current` print a remedy. |

**Eight verified, one partial, two failed.** Both failures are checks
discovering something, which is the walk working.

## The `[H]` checks, in Tim's words

**F — round falsifier.** *Does the generated list name at least one rule the
estate believed was enforced and is not?*

> only shows 1 rule enforced which I think passes not fails.

**Recorded partial.** The verdict — *passes not fails* — is given and stands.
It rests on the count of enforced rules rather than on F's own test, which asks
whether the list **names a rule the estate believed enforced**. No such rule was
named at the walk. The report offered 0057 clause 7 as the candidate; it was not
adopted, and this log does not adopt it on the operator's behalf.

**A11.** *Did it tell you something about this estate you did not already know,
or did you recognise every line?*

> honestly yes - but more as a reminder of what we have previously decided -
> does show that the projects been a victim of target scope creep - I've moved
> the goal posts a few times as we've been getting the idea in place - although
> I hope the plan as L5GN-Tools as the harness for my work projects is going to
> stick - it has thus far XD

**A12.** *Having seen the list's length — would you rather not have it?*

> length is ok right now although not particularly informative - everything but
> 1 is a not declared.

**A13.** *Did writing `CONVENTION_conformance.md` feel like citing 0060, or like
re-deciding it?*

> it's close but not identical - it's a fine line between a convention and
> decision - and if I'm honest about it most of the conventions we've written
> have probably originated as a decision first.

**A13 does not trigger its own remedy.** The check said that *re-deciding*
means the convention is cut back before it lands. The answer is "close but not
identical" rather than the second, so nothing is cut. **The observation
underneath it is larger than the check** — that most conventions here began as
decisions — and belongs to the estate rather than to this round.

## Defects the walk found in the brief and the walk-sheet, not in the repo

**This section is the round's most valuable output and has nowhere else to
live.** Four of the five are collisions between the round's own instructions
and the ruling it was applying.

**1. A5 names three classifications; 0060 clause 8 mandates four.** Clause 8
says existing rules *"acquire declared subjects when something next touches
them"* — a rule that has **not yet declared**, which is none of the three.
`undeclared` is a backlog; `subject-not-enumerable` is a finding. Merging them
would record 71 rules as unenforceable because nobody has written a `Subject:`
line. The map carries four and A5 was left untouched during the build, because
adjusting an acceptance check mid-build is what the stop conditions exist to
prevent. **The check is the defect.**

**2. A8's expected first member could not have satisfied it.** A8 names 0057
clause 7 as *"the expected first member"* of `subject-not-enumerable`. For it to
classify that way, something must declare it so — and 0060 clause 8 forbids
editing 0057's accepted body, while the map declares nothing on its own
initiative. So 0057 clause 7 lands in `undeclared`, correctly, and **A8 was
structurally unreachable from the moment it was written.** This is the same
clause-8 collision as the Task 3 stop condition, arriving at a different check.

**3. Task 3's stop condition cannot be satisfied without breaking clause 8.**
*"The auditor passes on its first run → stop"*, suspecting the carve-out has
swallowed the subject. It did, the suspicion is right, and clause 8 **is** the
carve-out. Overruled on the operator's call during the build, recorded in
`db149f8`.

**4. Task 5's no-code branch rested on a false premise.** It offered "record it
and write no code" if no other check prints a remedy. One does.

**5. The walk-sheet is internally inconsistent about A9's figure, and the
walking thread caused it.** Line 11 was corrected on 2026-09-02 from *"the
brief's figure of 12 + 82"* to `12 + 81`. A9's own body still reads *"(12
auditors / 82 testers)"*. Both readings are defensible — A9's parenthetical
names the brief's **original** draft-status figure, which is what A9 asks to
have been re-derived — but the sheet now states the brief's figure two ways in
one document. **The half-correction is the thread's, not the sheet author's**,
and it is recorded here rather than fixed, because the sheet is frozen at walk
time.

## What is not closed

- **A2's completeness**, per the INTERIM condition above.
- **A8 failed and nothing follows from it automatically.** Whether zero
  `subject-not-enumerable` means clause 2's state is unreachable, or merely that
  one rule has been written since 0060, is a reading nobody made at this walk.
  0060's own second falsifier measures it after ten rulings; there has been one.
- **F's own test is unanswered**, per the partial above.
- **A12's finding is not acted on.** *"Not particularly informative - everything
  but 1 is a not declared"* is a real result about the map's present worth, and
  no card exists to address it.

**The card is walked and not closed.** It re-walks when A2's read happens.
