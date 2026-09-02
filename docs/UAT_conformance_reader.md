# UAT walk-sheet — the conformance reader

<!-- gate-frozen: commit=bab32cf -->

Pair: `docs/COWORK_BRIEF_conformance_reader.md` → `docs/COWORK_REPORT_conformance_reader.md`.

> **Why this sheet is gate-frozen, added 2026-09-02 during the build.** The
> count below is a **build-time** count — the state the build starts from, which
> is what A9 tests against. Task 3 registers a thirteenth auditor, so from that
> commit onward the live census disagrees with this sheet **by design**, and
> `auditor_doc_claims` would read a frozen stamp as a live claim and go red.
> The marker is the mechanism that auditor already provides for exactly this,
> and it names `bab32cf` — the commit in `Built on:` below, so the exemption
> and the baseline are the same fact stated once.

**Written 2026-08-31, at brief time, before the build.** That is deliberate
(`brief-scribe`): a walk-sheet written afterwards fills up with `[H]` checks
covering whatever turned out awkward to verify. Three `[H]`s here, all chosen.

Built on: `bab32cf`. Gate at build time: `python verify.py`
**GREEN**, **12** auditors + **81** testers — **the frozen build-time count, and
A9 is about whether the brief's figure of 12 + 81 survived contact.**

> **Corrected 2026-09-02, before the build, and recorded rather than fixed
> silently.** This line read *"the brief's figure of 12 + 82"*. That was never
> the brief's figure: the brief itself carried 82 briefly on 2026-08-31, caught
> it the same day by counting, and corrected to **12 + 81** while recording the
> error as an instance. The walk-sheet kept the withdrawn number, so A9 was
> pointed at a figure the brief does not publish.
>
> The build-time count above was derived three ways on 2026-09-02, none of them
> recollection: reading `verify.py`'s `AUDITORS` and `TESTERS` lists; importing
> the module and taking `len()` of each, which is the derivation
> `auditor_doc_claims` treats as authoritative; and counting the run's own
> `[ OK ]` / `[FAIL]` lines, which came to **93** — one per registered gate,
> since `_run_group` has no silent path. **A9 stands unchanged.** A number
> corrected twice is not thereby trustworthy either, and the round still
> re-derives the census and still reports whether this figure survived.

Mark each check **ready to walk**, never "passed" — the walk is Tim's. Nothing
is committed; these check staged changes.

---

## Round falsifier — answer this one first

- [ ] **F.** **Does the generated list name at least one rule the estate believed
  was enforced and is not?**

  A "no" is not a failed build. It means the reader produced a tidier rendering
  of `AGENDA_design_gaps_2026-08-28.md`, the round bought bookkeeping, and 0060's
  own third falsifier has fired early — the consequence being that the 08-28
  deferral was right and Cards C and D were the better week. **Written down
  before the answer is known.**

## A — the ruling and the convention

- [ ] **A1 [G].** 0060 appears in `docs/DECISIONS.md` with status
  `accepted <date>`, the date is **later** than its `Date:` line, and
  `docs/_decisions_map.md` was regenerated in the same commit and reflects it.
- [ ] **A2 [G].** `docs/CONVENTION_conformance.md` exists, cites 0060 by clause,
  and **introduces no rule absent from 0060** — checked by listing every
  imperative in the convention against 0060 clauses 1-8.

## B — the reader

- [ ] **A3 [G].** `auditors/auditor_rule_subjects.py` is registered in
  `verify.py`'s `AUDITORS` and `python verify.py` reports it by name.
- [ ] **A7 [G].** The auditor's output **states the 0060 clause 8 carve-out
  explicitly.** A reader that silently excludes pre-0060 rules fails this check
  even if its numbers are right (0056 clause 1's second half).

## C — the map

- [ ] **A4 [G].** `python run.py conformance-map` writes
  `docs/_conformance_map.md`, and running it twice with no intervening change
  produces a **byte-identical** file.
- [ ] **A5 [G].** Every rule in the map carries **exactly one** of the three
  classifications — declared-and-checked, declared-and-unchecked,
  subject-not-enumerable. None is blank and the counts sum to the total.
- [ ] **A6 [G].** The map's header states **the denominator it counted over and
  how it was derived** (0060 clause 3).
- [ ] **A8 [G].** **At least one rule classifies as `subject-not-enumerable`.**
  If none does, clause 2's state is unreachable in practice and this check is
  what says so. *(0057 clause 7 is the expected first member; this check does not
  require it to be that one.)*

## D — the round's own rules, applied to itself

- [ ] **A9 [G].** The brief's draft-status census (**12 auditors / 82 testers**)
  was re-derived at round-open and either confirmed or corrected in the report,
  **with the correction recorded as an instance rather than as a fix.**
- [ ] **A10 [G].** Task 5 either lands a round-trip tester, **or** the report
  records — with the search that established it — that no other check in the
  estate prints a remedy.

## E — worth, which only a person can answer

- [ ] **A11 [H].** Read `_conformance_map.md` cold. **Did it tell you something
  about this estate you did not already know**, or did you recognise every line?
- [ ] **A12 [H].** Having seen the list's length — **would you rather not have
  it?** An honest yes is a real finding about whether naming gaps drives closure
  or just produces a wall of red nobody reads (0048 clause 4 from the other
  direction). This check is written so that "not worth building" is an easy
  answer to give.
- [ ] **A13 [H].** Did writing `CONVENTION_conformance.md` feel like **citing**
  0060, or like **re-deciding** it? If the second, the brief's one deliberate
  widening was not as bounded as it claimed and the convention should be cut back
  before it lands.

---

**Three `[H]`s, and the count is deliberate.** All three ask about the operator's
*experience* of the artefact rather than its behaviour — the only thing a machine
cannot reach here. Everything about the map's structure is `[G]`; only its worth
is `[H]`.

**If the `[H]` count rises during the build, stop** (brief, Stop conditions). It
means a property turned out awkward to check mechanically and the design is being
adjusted to fit the test.

---
*Ready-to-walk sheet. The results log it produces needs a uat stamp
(`auditor_uat_stamp`), and a results log may be marked INTERIM
(`CONVENTION_docs.md`).*
