# Conformance convention

**Status:** authored, **not enforced** at the moment of writing. The auditor
that reads part of it arrives in the same round (`auditor_rule_subjects`), and
what that auditor does *not* cover is named in §10 rather than left to be
discovered.

**Authored here. No adoption header, and that is a statement rather than an
omission.** **0057** clause 7 requires a convention adopted from another estate
to name origin repo, file and date in its own header. This one was written in
`L5GN-Tools` on **2026-09-02**, from **0060** and from the five worked instances
in `docs/AGENDA_conformance_instances_2026-08-31.md`. Nothing crossed the wall
to make it. Recorded explicitly because a missing adoption header is otherwise
indistinguishable from a forgotten one.

**Subject:** every rule-bearing document in this repo — `docs/DECISIONS.md`'s
entries and `docs/CONVENTION_*.md`. Declared in the form §1 demands of everything
else, because a conformance convention that does not declare its own subject is
the first thing its own auditor should catch.

**Scope:** this repo. Another repo in the estate may adopt it, and would then
carry the adoption header this one does not.

**Cites:** **0060** throughout — this file is its application and adds nothing
to it (§9). Also **0031** (a non-gating surface reports findings, never a
verdict), **0045** clause 2 (report, never repair), **0048** clause 4 (a check
that cannot fail trains the eye past it), **0050** (a source that cannot be
reached reads as unknown, never as fresh), **0052** clauses 2 and 3 (the
convention lives in the repo that owns the work; no rule may have a skill as its
only home), **0053** clauses 1 and 5, **0056** clause 1 (a check enforcing a
pattern rule is driven by the pattern, and one that narrows a pattern to a single
instance says so in its own output).

---

## 0. What this discharges

**0060** clause 7 says the rules belong in a convention this repo owns, names
`CONVENTION_conformance.md`, and states that it does not exist — declining to
discharge the debt by naming it. This is the file that clause asked for.

**It cites; it does not legislate.** Every imperative below maps to a clause of
0060, and §9 is that map, written so the mapping can be walked rather than
trusted. **If this document ever carries a rule 0060 does not contain, the
remedy is a superseding entry in the log and not a paragraph here** (0052
clause 3, inverted).

---

## 1. A declared subject, in one of three forms

**0060 clause 1.** A rule declares the subject it binds, in a form something can
enumerate. Three forms, and a rule uses whichever fits:

| form | what the rule states | worked example |
|---|---|---|
| **pattern** | the pattern itself, with any checker driven by it | 0056 clause 1's pin rule: the subject is *every conversation map*, expressed as the pattern that finds them |
| **fixed set** | the artefacts, named | a rule binding `docs/INTENT.md` and `docs/ARCHITECTURE.md` names both |
| **every X** | how X is decided, and by reading what | *every convention carrying an adoption header* is a declared subject only once something says which conventions those are |

**A subject recoverable only from prose is not a declared subject.** That is the
whole of the test, and it is deliberately blunt: if deciding whether an artefact
is in the subject requires a person to read a paragraph and form a view, the
rule has no enumerable subject and §3 applies.

**The pattern form is preferred where it fits**, because 0056 clause 1 already
requires a checker to be driven by the pattern rather than by an enumeration of
what the pattern currently matches. A fixed set that will grow is a pattern
written down at one moment in time.

## 2. A rule declares its reader, or declares that it has none

**0060 clause 4.** Both halves matter and the second is the one that gets
dropped. *No reader* is a legitimate, statable answer; **silence is not**,
because silence is indistinguishable from nobody having looked.

**The set of rules with no reader is an artefact, not an impression.** It is
generated — `docs/_conformance_map.md` — never hand-maintained, and **its being
long is information rather than an embarrassment to manage.**

## 3. `subject-not-enumerable` is an outcome, not a failure

**0060 clause 2.** A rule whose subject cannot be enumerated is recorded
*unenforceable*. This does not make the rule void: it may still be read, cited
and followed. What is refused is the third state — **a rule treated as enforced
and checked against a subject somebody chose at the moment of counting.**

**`unknown` over the right subject beats a number over the wrong one.** This is
**0050**'s posture moved from sources to subjects, and the estate has the worked
instance: *"4 of 9 conventions carry an adoption header"* counted headers against
every convention when **0057** clause 7 binds only those adopted from another
estate. A different denominator, not a rounder one — and it travelled unchallenged
for four days while the denominator itself went stale.

**The escape hatch must stay non-shameful or it produces dishonest
declarations.** A rule with no honest way to say *cannot be enumerated* gets given
a plausible subject instead of an accurate one, and 0060's own second falsifier is
watching for exactly that: **zero unenforceable rules is evidence the hatch is
being avoided**, not evidence of health.

**When classification requires reading prose to decide, the answer is
`subject-not-enumerable`.** Not a judgement call made in the moment. The instinct
to *just read it and decide* is the substitution this rule exists to refuse.

## 4. Rule, checker and remedy are three artefacts that must agree

**0060 clause 5.** Where a check names a remedy, **something asserts that running
that remedy satisfies that check.**

**A checker demanding what no sanctioned writer produces is strictly worse than
an unenforced rule.** It converts a green gate into a permanently red one with a
documented fix that does nothing. The worked instance is `154afbd`: an auditor
required 0056 clause 3's metadata, `run.py pin bump` short-circuited on hash
equality and refused to write it, and the printed remedy ran, reported success
and changed nothing.

**This extends 0053 clause 5 rather than restating it.** That clause required a
remedy to be *safe* wherever the check can fire. **A remedy can be perfectly safe
and inert, and inert passed it.**

**Mode 5 was found by running, not by reading** — four of the five instances came
from careful reading and this one did not. A conformance sweep can enumerate
subjects by reading. It cannot discover an inert remedy that way.

## 5. A published count carries its denominator

**0060 clause 3.** Any count of the form *"N of M"* published in this estate
carries what M is and how M was derived.

**A figure whose M is not the rule's own subject is withdrawn, not adjusted.**
Withdrawal is the expensive half: an agenda that cited such a figure becomes
wrong rather than imprecise, and there is no correcting arithmetic that rescues
it. That is the intended cost.

**This binds the conformance map's own output first.** The generated map states
its denominator in its own header, and is the first place the rule is tested.

## 6. A shared invariant lives in the gate, not in either component

**0060 clause 6.** Where a rule's subject spans two components that must not know
about each other, the reader lives in the gate.

**A code comment keeping two implementations in step is not a mechanism.** The
worked instance is `db.resolve_registry_path` and `review/core.resolve_registry_path`,
whose independence is a property something relies on. **The independence is
preserved; the drift is not** — the assertion moved to a tester (`709721a`)
rather than the two being merged.

## 7. A conformance reader is a reader

**0060 clause 7, with 0045 clause 2 and 0031.** It reports; it never repairs. It
does not add a subject line to a ruling, does not edit a convention, and does not
touch an accepted entry's body under any circumstance.

**It emits a verdict only where it is in the gate** (0053 clause 1). The
generated map is a non-gating surface and reports findings; the registered
auditor is the only thing in this arrangement that may go red.

**A reader that cannot go red is worse than no reader** (0048 clause 4). If the
carve-out in §8 has swallowed the subject so completely that nothing can ever
fail, the reader is training the eye past itself.

## 8. What binds from when

**0060 clause 8.** This binds rules made from 2026-08-31 forward. **It does not
retroactively invalidate anything.** Existing rulings and conventions acquire
declared subjects when something next touches them, or when the sweep in §2
reaches them.

**Backdating a subject onto an accepted entry would edit its body**, which
`CONVENTION_decisions.md` §4 forbids. **The subject is declared in the sweep's
output, never in the entry.**

**The cost is a long tail**, during which the log holds two classes of rule that
look identical in it. Only the generated map distinguishes them, and a reader who
reads only `DECISIONS.md` will not know which is which.

## 9. Every imperative here, against its clause

Written so **A2 of `UAT_conformance_reader.md`** can be walked by reading one
table instead of the whole file. **Nothing in this document should be absent from
this map.** If something is, it is a rule invented here, and §0 says what happens
then.

| § | imperative | 0060 clause |
|---|---|---|
| 1 | a rule declares an enumerable subject, in one of three forms | 1 |
| 1 | prose-only subjects do not count as declared | 1 |
| 1 | prefer the pattern form; a checker is driven by the pattern | 1, and 0056 cl.1 |
| 2 | a rule declares its reader, or declares it has none | 4 |
| 2 | the no-reader set is generated, never hand-maintained | 4 |
| 3 | an unenumerable subject is recorded unenforceable | 2 |
| 3 | the rule stays readable and citable; only the third state is refused | 2 |
| 3 | unknown over the right subject beats a number over the wrong one | 2, and 0050 |
| 3 | prose-reading classification resolves to not-enumerable | 2 |
| 4 | a named remedy has its round trip asserted | 5 |
| 5 | a published count carries its denominator | 3 |
| 5 | a wrong-subject figure is withdrawn, not adjusted | 3 |
| 6 | a cross-component invariant is read in the gate | 6 |
| 7 | the reader reports and never repairs | 7, and 0045 cl.2 |
| 7 | verdicts only in the gate; the map does not gate | 7, and 0031, 0053 cl.1 |
| 8 | binds forward; no retroactive invalidation | 8 |
| 8 | the subject is declared in the sweep, never in the entry | 8 |

**Seventeen imperatives, all eight clauses.** The denominator is 0060's clauses
1-8, and the count is over this file's own section headings — stated because §5
applies to this document as much as to anything it governs.

## 10. What is not enforced

**Stated rather than pretended** (0048 clause 4).

- **Only §1 is read by anything.** `auditor_rule_subjects` classifies subjects.
  **§2's reader declaration, §4's round trip, §5's denominators, §6's placement
  and §7's report-never-repair are unchecked** as of this file's writing.
- **§9's own completeness is unchecked.** Nothing verifies that the table lists
  every imperative in the document. A2 is walked by a person, once.
- **§5 is unchecked except for one claim shape.** `auditor_doc_claims` matches
  *"N auditors + M testers"* and nothing else. Every other count in every
  convention here is unguarded, including the one in §9.
- **Nothing detects a rule that declares a subject dishonestly.** A plausible
  subject that is not the rule's real one passes §1 mechanically, which is the
  risk 0060's own first falsifier is set to measure.
