# Cowork report — the estate produces a list of its own unchecked rules

Partner to `docs/COWORK_BRIEF_conformance_reader.md`. Built 2026-09-02 on
`LucasGoonPC`, across `db149f8` and `b2a9c9c`, from `bab32cf`.

**Gate at the end of the build: `python verify.py` GREEN, 13 auditors + 82
testers.** It was 12 + 81 at `bab32cf`; this round registered one auditor and
one tester, and that movement is the answer to A9 rather than an accident.

**Read the walk-sheet's own corrections with this.** Two of the round's
findings are recorded there because they bear on checks: A9's figure was
pointed at a number the brief had withdrawn, and the sheet is now gate-frozen
at `bab32cf`.

---

## What was built

**Task 1 — already discharged, not redone.** 0060 was appended as `proposed` at
`1916fc2` and ratified at `55ce6af`; the brief's census note was corrected to
12 + 81 on 2026-08-31, as an instance rather than silently. The census was
re-derived today anyway, because the brief's header says to.

**Task 2 — `docs/CONVENTION_conformance.md`.** Authored here, so it carries no
adoption header and says so explicitly: a missing 0057 clause 7 header is
otherwise indistinguishable from a forgotten one. Its §9 maps every imperative
in the document to a clause of 0060, so A2 can be walked by reading one table
rather than the whole file. It declares its own subject and its own reader,
because a conformance convention that does not is the first thing its own
auditor should catch.

**Task 3 — `auditors/auditor_rule_subjects.py`**, registered in `verify.py`.
One class of claim: a rule bound by 0060 declares its subject, or records that
it cannot be enumerated. Declaration is field presence and nothing else — it
does not judge whether a subject is a *good* one, because that needs prose read
to it, which 0060 clause 2 resolves to `subject-not-enumerable` rather than to
a judgement made in the moment. The clause 8 carve-out is a fixed set named in
code, printed on every run rather than left in a docstring (0056 clause 1's
second half).

**Task 4 — `python run.py conformance-map` → `docs/_conformance_map.md`.** A
non-gating surface (0031, 0060 clause 7). Determinism was verified by hash
rather than by inspection: two consecutive renders of an unchanged tree are
byte-identical.

**Task 5 — `tests/tester_remedy_round_trip.py`.** One round trip, as the brief
required.

## The first render, with its denominator

**72 rule-bearing documents: 60 entries in `docs/DECISIONS.md`, counted by
their `## NNNN —` headings, and 12 files matching `docs/CONVENTION_*.md`.**
Derived at render time, never from a stored count.

| classification | count of 72 |
|---|---|
| `declared-and-checked` | 1 |
| `declared-and-unchecked` | 0 |
| `subject-not-enumerable` | 0 |
| `undeclared` | 71 |

**The one checked rule is the convention written this morning.** *"Almost
nothing is checked"* is the honest reading and is exactly what the brief's
Consequences predicted. Producing the list makes the estate look worse than it
did yesterday while being exactly as conformant.

**Zero `subject-not-enumerable` is not yet a finding.** 0060's second falsifier
reads a zero as evidence the escape hatch is being avoided, but it measures
after ten rulings and one has been written since 0060. Recorded so the reading
is available when the count is meaningful.

## What the round found, and all of it by running

**Three of the brief's own assumptions were false**, and none of the three was
visible from reading.

**1. The Task 3 stop condition cannot be satisfied without breaking 0060.**
*"The auditor passes on its first run against the real tree → stop"*, with the
attached suspicion that the clause 8 carve-out has swallowed the subject. It
did pass, and the suspicion is correct — but clause 8 *is* the carve-out. It
binds forward and forbids backdating a subject onto a frozen body, so the
auditor's live subject today is one document: the convention written this
morning to satisfy it. **Any auditor that goes red today has to break clause
8.** Overruled on the operator's call: clause 8 is an accepted ruling, the stop
condition is a prediction made before the conflict was visible.

**2. The brief's three-way classification omits a state clause 8 mandates.**
Existing rules *"acquire declared subjects when something next touches them"* —
which describes a rule that has not yet declared, and is none of the three.
**`undeclared` is a backlog; `subject-not-enumerable` is a finding.** Merging
them would record seventy-one rules as unenforceable because nobody has written
a `Subject:` line, reporting the estate as principled where it is merely
behind. The map carries four classes. **A5 says "exactly one of the three" and
was left untouched** — adjusting an acceptance check mid-build is what the stop
conditions exist to prevent.

**3. Task 5's no-code branch did not apply.** It asked whether any check
besides the conversation-map pin prints a remedy, and said to record the finding
and write nothing if none did. One other does: `auditor_architecture_current`
prints *"regenerate with `python run.py render-architecture` and commit it"*,
and its round trip was unasserted — `tester_architecture_current` checks the
commit-line mask and that the auditor is green *now*, never that running the
remedy makes it so.

## The finding that came from outside the five tasks

**Registering one auditor turned three green documents red.**
`auditor_uat_stamp` failed on `UAT_conductor_results.md`,
`UAT_desk_stale_card_results.md` and `UAT_scanner_bugfixes_results.md` — the
three INTERIM logs, all claiming `gate=12a/81t`.

**That check compares a historical fact to a live count.** It has two stable
outcomes over time: the gate goes red whenever gate composition changes, or
historical stamps get re-cut to match. The second is laundering a number into a
document to satisfy a check, which is verbatim the incident that auditor's own
docstring says it was built to catch.

**It has not happened here.** `git log` shows one commit against
`UAT_conductor_results.md`, so its stamp was never re-cut. The mechanism
permits the failure; the estate has not taken that path. Stated because the
suspicion was raised during the build and the evidence refutes it.

`gate=` is optional in that auditor and duplicates what `commit=` already
fixes. It was removed from the three stamps, each carrying a dated correction
note rather than a silent edit — permitted because all three are INTERIM and
revisable.

## Not built, and named rather than skipped

- **`auditor_uat_stamp` is not fixed.** Resolving `gate=` against the census at
  the stamped commit would make the field mean something again. A code change,
  outside these five tasks, and it wants its own card.
- **A second claim class for `auditor_rule_subjects`** — clause 8's other limb,
  a pre-0060 rule that has been *touched* since 0060 and must then acquire a
  subject. Lawful, and empty today because no convention has been edited since.
  Not added: the brief says one reader, one claim class.
- **`report.write_architecture_shape` emits CRLF on Windows**, calling
  `dest.write_text(text, encoding="utf-8")` with no `newline=`, while
  `.gitattributes` mandates LF. That is the *"CRLF will be replaced by LF"*
  warning every `git add` of the shape doc prints. Harmless to the round trip,
  since both sides read through universal newlines. Named, not fixed in passing.
- **Everything in the brief's out-of-scope section**, unchanged: whether any
  rule is *obeyed*, 0051 clause 2's containment auditor, retrofitting subjects
  onto 0001–0059, and `CLAUDE.md`'s estate-scale debt.

**One out-of-scope item was done, and not by this round.** The
two-draft-directory hazard was resolved during the 2026-09-02 restart —
`data/decisions_draft/` deleted, `data/decision_drafts/` kept, because
`CONVENTION_design_thread_restart.md` §4 is the only rule-bearing document
naming either. Recorded in `AGENDA_restart_2026-09-02.md`, before the build
opened, so the brief's exclusion was not breached.

## What the walk still owes

**The round falsifier is unanswered and is the operator's to answer.** *Does
the generated list name at least one rule the estate believed was enforced and
is not?* The candidate is 0057 clause 7 — the estate published *"4 of 9
conventions carry an adoption header"* against a rule that binds only
conventions adopted from another estate, and that rule sits in the map as
`undeclared`. **Whether that counts as *believed enforced* is a reading, not a
derivation**, which is why it is a walk question and why it was written down
before the answer was known.

**A5** expects three classifications and the map produces four. **A9** asks
whether `12 + 81` survived contact; it did not, and this round is what moved
it. Both go to the walk as they stand.
