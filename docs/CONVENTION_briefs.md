# Convention — briefs, reports and walk-sheets

**Scope: this repo, `L5GN-Tools`.** It is the authority the `brief-scribe` skill
cites under **0052** clause 3. That skill's own line 12 said *"There is no
written convention for briefs yet… That gap is real and this skill is the drift
risk until it closes."* **This file closes it.** Where the skill and this file
disagree, this file wins and the skill is amended.

**Status: `proposed`.** It may be read and followed now; it is not authority to
cite until it is ratified by a re-read on a later day.

**Adopted from:** repo `WizForgeAnalytics`, file `docs/CONVENTION_briefs.md`,
read from the `wizforge-mirror-2026-08-26` snapshot on **2026-08-27** under
**0051** clause 1(b). Its §§0, 2, 3, 4, 5 and 8 transfer close to whole. Its
**§1 is replaced**, because this repo has neither per-project card numbers nor a
project registry and will not be given them to make the adaptation symmetrical.
Its **§6 is corrected**, because it asserts no repo in its estate has a gate and
this one does. Its **§7 — the orientation round — is dropped**: it is a proposed
pattern for seven migrating repos, which is not this repo's situation.

**One section is ours rather than theirs:** §3's first item, the opener. It is
marked where it appears.

---

## 0. What a brief is for

**A brief complete enough that the build is determined by it is a brief a
cheaper model can build from.** That is not a style preference. It is the
condition under which build work moves down a tier, and whether a brief clears
it is measurable: hand it to that tier and judge the output against the brief's
own checks.

So the property to optimise is not length or polish:

> Could someone who was not in the design conversation build this, and could a
> machine tell whether they had?

A brief is a **request, frozen at the moment of asking**. It is never corrected
after the fact. Correcting it destroys the record of what was actually asked,
which is the only thing a brief uniquely holds. Where a brief turns out to have
been wrong, **the report says so** — that is what the report is for.

## 1. The card and its files

A card is a `<slug>` identity shared by up to four files, living flat in
`docs/`:

```
docs/COWORK_BRIEF_<slug>.md       the request        frozen
docs/COWORK_REPORT_<slug>.md      the findings       frozen
docs/UAT_<slug>.md                the walk-sheet
docs/UAT_<slug>_results.md        the walked answer  stamped, frozen
```

- `<slug>` is `lower_snake`, descriptive of the round rather than of the repo.
- **There is no card number and no registry**, and neither is to be introduced
  to make this convention symmetrical with another estate's. The slug is the
  identity. Slugs are not reused, including for an abandoned round.
- A second cut at the same question takes a new slug that says so
  (`..._retry`, `..._part2`), not a suffix on the first.
- Every cross-repo reference to a card carries its repo, on the same terms as a
  ruling citation (`CONVENTION_decisions.md` §3).

The card's state is not recorded anywhere. **It is a function of which of the
four files exist**, which is why the filenames are a tooling contract and not a
naming preference — `docs-archivist` detects a finished pair by exactly this.

## 2. The brief and the walk-sheet are one act

The walk-sheet is the brief's acceptance section, extracted so it can be walked
and stamped. **They are written together, before the build.**

Never write the walk-sheet afterwards. By then you know which properties turned
out awkward to verify, and `[H]` checks proliferate to cover them. Written at
brief time, an awkward property forces a better design instead — which is the
entire value of writing it early.

## 3. The parts of a brief

A checklist of what a reader needs, not a template to fill. Order follows
existing practice.

1. **Where you are, and what to read first.** *(This item is this repo's, not
   adopted.)* A brief opens with the two things a cold thread cannot derive:
   **the repo and the host it is standing on**, and **what to read before
   Task 1, in order**. Everything after that is a pointer, so a brief that
   carries its own entry point can be opened without a separate instruction
   telling the thread where it is. `COWORK_BRIEF_gap_closure.md` is the worked
   example — and the evidence for the rule is that its opener was added *after*
   the brief was drafted without one.
2. **Draft-status note** — required whenever the brief is written ahead of its
   build. How far ahead, what is likely to have moved, and that re-verifying
   every "already exists" claim is **the round's first act rather than a
   formality**. A brief describing remembered code rather than the code in
   front of it is the failure this note exists to flag.
3. **Origin** — the thread, finding or ruling that produced this round.
4. **Precondition** — what must be true before the round opens, stated so it can
   be checked rather than felt. *"Phase N closed"* is checkable. *"When we're
   ready"* is not.
5. **Depends on — rulings** — cited by number with a one-line gloss each.
   Rulings from another repo carry that repo at **every** mention (**0043**). A
   cited ruling that was not opened will be glossed wrongly, and the wrong gloss
   reads authoritative.
6. **Ratify before code** — where the round needs a ruling that does not exist
   or is still `proposed`, name it, say which tasks depend on it, and say that
   those tasks may not land until it binds. A `proposed` ruling is not authority
   (`CONVENTION_decisions.md` §3).
7. **Deliverable** — one paragraph, ending in something testable. If the last
   sentence cannot be checked, the round has no finish line.
8. **Working rules** — the disciplines that hold throughout, restated at the
   point they bind rather than assumed from elsewhere.
9. **Tasks** — numbered, each naming what lands and where. A task nobody could
   tell was finished is not a task.
10. **Explicitly out of scope** — the section that most often saves the round.
    Name the specific adjacent work that will tempt whoever builds this, not
    "anything else".
11. **The one deliberate widening, named** — where the round crosses a line an
    earlier ruling drew, say so, say why, and say what still bounds it. A
    widening taken silently is the one that gets inherited.
12. **Stop conditions** — each ending `→ stop`. Tripwires a builder can notice
    mid-build, not verdicts visible only afterwards.
13. **UAT — acceptance checks** — §4, extracted to the walk-sheet per §2.
14. **Reporting** — the report path and specifically what the report must
    record. *"Record what happened"* is not an instruction; *"record what
    transferred whole, what changed and what was declined, section by section"*
    is.

**Restate nothing you can cite.** A ruling can change; a restatement of it will
not, and the copy is what a later reader will believe (**0052** clause 2).

## 4. The acceptance checks

Every check carries `[G]` or `[H]`.

- **`[G]`** — a machine, or an unambiguous procedure, decides. Someone who was
  not in the design conversation gets the same answer as someone who was.
- **`[H]`** — a human judgement is genuinely required. Legitimate, and sometimes
  the most valuable check in the round: *"was the evidence enough, or did you go
  hunting?"* cannot be mechanised and should not be.

**Every `[H]` is a cost. Count them**, and state the count in the walk-sheet's
header. For each, ask whether it is human because the property is genuinely a
judgement, or because the design made it awkward to check. **The second case is
a design finding**, and belongs in the report as one — not absorbed as a check.

The `[H]`s that earn their place ask about the operator's *experience* of the
thing rather than its behaviour. Did you trust it. Did you go back to doing it
by hand. Would you defend this on re-read.

A `[G]` check must be able to fail. **0048** clause 4: a check that cannot fail
trains the eye past it, and a walk-sheet of them is worse than a short one.

Where the round is an experiment, **state its falsifier**: the single question
whose *"no"* cancels what follows, with the consequence written down before the
answer is known.

Checks are written as `- [ ]` items so the count is derivable. `- [x]` passed,
`- [~]` passed with a caveat stated inline.

## 5. The report

Frozen testimony about a moment. Its numbers were true then and are not claims
about now.

A report records: what was built or found, against what evidence; the delta
between what the brief asked for and what landed; every `[H]` check's answer in
the operator's words rather than paraphrased; and anything the round left
outstanding. **A report may not imply a completeness the tree does not have** —
if the round left something undone, it says so, and every stop condition that
tripped is named.

**A report that contradicts its brief is the round working correctly.** Say
which one was wrong.

## 6. The results log and its stamp

`docs/UAT_<slug>_results.md` is the one document asserting *"this was tested,
here, at this commit."* It carries the uat stamp as its first line:

```
<!-- uat: commit=<sha> dirty=<bool> host=<name> walked=<YYYY-MM-DD> gate=<Na/Mt> -->
```

**This repo has a gate**, so unlike the estate this convention was adopted from,
`gate=` is a real field here and not an unbacked claim. `core.hooksPath` is
`.githooks`, `.githooks/pre-commit` runs `verify.py`, and `auditor_uat_stamp`
checks the stamp's fields and resolves `commit` against this repository.
`gate=` stays **optional**: omit it rather than assert a count you did not
observe, but where it is present it is checked against the registered counts.

The full stamp rules, the gate-frozen marker and the reason the auditor stops at
the archive door are in `CONVENTION_docs.md` §4 and are not restated here.

**Walking is a human act.** It is never inferred from a passing test, and the
results log is never written by the thread that did the build without the
operator having walked it. **0028** clause 3 keeps the commit a human act for
the same reason.

## 7. What is not enforced

Stated rather than pretended, because **0048** clause 4 says a check that cannot
fail trains the eye past it — and most of this file has no check at all:

- **Nothing checks a brief.** No hook, no auditor, no linter. This file is read
  by people and by skills that people invoke.
- **The `[H]` count is not audited.** A brief where every check is `[H]` passes
  this convention and defeats it.
- **Nothing verifies the walk-sheet matches the brief's acceptance section.**
  They are written together by discipline; they can drift by hand afterwards.
- **Nothing stops a brief being edited after it is committed.** §0 says frozen;
  git records the edit and nobody is watching the log.
- **Nothing checks that a slug is unused** before a round claims it. Two rounds
  opened on the same day can collide, and nothing will notice until both files
  exist.
- **`auditor_uat_sheet_readable` and `auditor_uat_stamp` check the walk-sheet's
  shape and the results log's provenance — never whether the walk passed.**
  That is deliberate (`CONVENTION_docs.md` §4) and it means a failed walk and an
  unwalked round are indistinguishable to the gate.
