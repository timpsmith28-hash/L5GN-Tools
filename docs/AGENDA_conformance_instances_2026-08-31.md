# Seed instances for the conformance ruling — 2026-08-31

Session 1 of the week set out in `AGENDA_running_order_2026-08-31.md`. **This
file is the session's real deliverable**: the worked instances S3's ruling
generalises from, written down in one shape so the ruling is derived from cases
rather than from a theory.

**Frozen at its date.** It records what was found and what was done. It rules
nothing, and 0060 is not drafted here.

**Shape of each entry:** what the rule says · what the code or artefact says ·
why nothing noticed · what was done today · what it tells the ruling.

---

## 1. 0054 clause 6 — authorship, and a tracked file that declared itself empty

**The rule.** `authors` is estate policy and **lives in the tracked file only**.
An untracked declaration makes *"no host declares this artefact"* and *"the
declaration has not been shipped here yet"* the same input with two meanings.

**What the tree said.** `config/machines.json` declared itself, in its own
`_comment`, a *"TEMPLATE (committed, no real machine data)"*. Every host key in
it was a `RENAME-ME-` placeholder. All four real hosts existed only in the
gitignored `config/local.json`. The `authors` key sat under
`RENAME-ME-GAMING-RIG`, which no hostname ever matched, so **it was never read**;
authorship resolved entirely from the untracked overlay.

**The two contracts were mutually unsatisfiable.** Not "the code violates the
clause" — the clause required authorship in a file whose own declared contract
forbade holding it. Either had to give way.

**Why nothing noticed.** No auditor and no tester reads the real
`config/machines.json`. Every config tester is hermetic against a temp fixture —
correctly, for the properties they test, and the effect is that **the shipped
file is read by no check at all**.

**What was done.** The operator ruled that `machines.json` gives way. A real
`LucasGoonPC` section now carries `authors` **and nothing else**; the template
`_comment` is amended to state the exception and its reason;
`_authorship_exception_comment` records the collision and its date.
`config.authored_artefacts` and `config.authoring_hosts` now resolve authorship
through `_tracked_entry` — the layer stack with `local.json` removed — so a
declaration in the overlay **cannot** supply or override authorship rather than
merely being asked not to. `local.json`'s now-inert key is replaced by a note
saying re-adding it would be inert. `tester_config` asserts all four cases.
Recording folded into S3's 0060 on the operator's instruction.

**What it tells the ruling.** A clause naming a file is not checkable until
something reads that file's **own declared contract** too. Two documents can
each be internally consistent and jointly impossible, and the estate currently
has no way to notice — 0056's shape, one level up: not a rule with no reader,
but **two rules whose conflict has no reader.**

---

## 2. 0056 gap 1 — the check that could not see its own subject

**The rule.** 0056 clause 1: a check enforcing a pattern rule is driven by the
pattern. Clause 2: a map that exists without a pin is a violation, not an
absence. Clause 3: a pin carries origin, anchor where one exists, date, host.

**What the tree said.** `auditor_conversation_map_pin` bound `ARTEFACT` and
`PIN_FILE` to `config/mcf_conversation_map.tsv` as module-level constants.
`config/personal_conversation_map.tsv` existed with no pin. The auditor
**structurally could not see the instance that violated the rule it enforces**,
and the gate was green over it. Separately, the MCF pin carried a hash line and
nothing else — a third of what clause 4 undertook to keep.

**Why nothing noticed.** The gate was green, and green is what people check.
0056 diagnosed this precisely in its own Context and its Consequences predicted
today: *"the day this lands `verify.py` fails on this rig until a pin is
written. That is the ruling working."*

**What was done.** The auditor is now driven by `PATTERN = "*conversation_map.tsv"`
— the same glob `.gitignore` already carries, copied rather than paraphrased.
`subjects()` enumerates the union of maps and pins on disk, so a second map
inherits the check by existing. Clause 3's completeness check is layered in the
auditor rather than in `pin.py`, because `pin.py`'s contract that a comment line
is optional is the *mechanism's* view and 0052 puts a rule's enforcement in the
checker that cites it. `anchor` is demanded only where a resolver is available.
`tester_conversation_map_pin` gained the pattern cases — a directory with two
maps, one pinned and one not — because a tester that only ever hands `check()`
one pair reproduces the original blind spot exactly.

**Left for the operator, on Windows:** the two pins. The gate is red until they
are written, by design.

**What it tells the ruling.** The failure was not a wrong answer. It was a
**correct answer about the wrong subject**, and no amount of testing the answer
would have found it. A reader must be able to state what its subject set is, and
something must be able to check that set against the rule's own wording.

---

## 3. The two registry resolvers — an invariant that was only ever a comment

**The rule.** None, and that is the finding. `chronicler/review/core.py` says in
a code comment *"Mirror relink.REGISTRY_PATH"* and recomputes the derivation by
hand.

**What the tree said.** Two resolvers. `chronicler/pipeline/db.py:52` has two
steps and documents *deliberately* having no repo fallback — *"the defect F
removes is the silent fallback to a different literal."*
`chronicler/review/core.py:247` has three, the third being
`config/project_registry.json`. **Measured today on this rig with no env set:**

| | resolves to | exists |
|---|---|---|
| `db.resolve_registry_path()` | `…/L5GN/.intel_sync/project_registry.json` | **no** |
| `core.resolve_registry_path()` | `…/L5GN-Tools/config/project_registry.json` | yes |

So the pipeline silently **skips** linking (`has_registry()` false — Card B's
defect 1) while the review endpoint silently **succeeds** against a different
registry, and neither reports which it used. The file `core` falls back to is
the one **0055** rules is corpus rather than configuration, and whose migration
is undone (design-gaps gap 3).

**Why nothing noticed.** The duplication is deliberate and documented:
`review/core.py`'s docstring states the module *"stays independent of
pipeline.db."* That invariant is real and merging the two would break it. What
was never written down anywhere executable is that the two must **derive the
same location**. A comment is not a mechanism.

**What was done.** Not merged — the independence is a property, not an
oversight. `tester_registry_path` now asserts the agreement the comment stood in
for: both honour an explicit `CHRONICLER_REGISTRY_PATH` identically, and the two
derived formulas are compared as formulas rather than as answers. The check
lives in `tests/`, which may import both tiers, so it couples nothing.
**The step-3 divergence is deliberately not fixed** — making it loud is a call
about 0055's migration, and taking it here would have been a restructure inside
a session that promised commits.

**What it tells the ruling.** Some invariants are **between** two components
that must not know about each other. The reader for those cannot live in either
one, and the ruling should say where it does live — this estate's answer today
is the gate, and that answer should be explicit rather than incidental.

---

## 4. 0057 clause 7 — a rule whose subject cannot be enumerated

**The rule.** *"A convention adopted from another estate names the adoption in
its own header — origin repo, origin file, date."*

**What the tree said.** **4 of 11** conventions carry a real `Adopted from:`
header: `briefs`, `decisions`, `docs`, `gitignore`, all from
`WizForgeAnalytics`. Two more mention adoption only in prose about other repos
adopting *this* estate's work — outbound, not inbound.

**The count was never the finding.** Clause 7 binds *conventions adopted from
another estate*, and **nothing determines which conventions those are.** The
answer is recoverable only by reading prose: `CONVENTION_skills.md` says
*"Written from the work rig's draft of the same date"*;
`CONVENTION_project_process.md` says *"Paired with the work rig's stub of the
same date"*; `CONVENTION_design_thread_restart.md` says it is new practice
authored here and correctly carries no header. **A conformance figure cannot be
computed for a rule whose subject set is prose.**

**Why nothing noticed.** Because a count was reported instead. "4 of 9" was
carried into two agenda files as a conformance figure; it was a count of headers
against a denominator of *all* conventions, which is not what the rule asks. The
denominator had also gone stale — 11, not 9 — within three days.

**What was done.** Headers added to `CONVENTION_skills.md` and
`CONVENTION_project_process.md`, both marked **origin repo and file
unconfirmed** — the drafts crossed as content, not as citable locations, and
0050 says an unreachable source reads as unknown. A fabricated origin would be
worse than a named gap. `project_process`'s header additionally records that its
adoption is *weaker* — written alongside rather than from — and that if clause
7's subject turns out to be "adopted whole", that header is over-declaring and
should be cut.

**What it tells the ruling.** This is the sharpest of the four. A rule can have
a reader only if its **subject set** is mechanically enumerable. Clause 7's is
not, and the estate has been reporting a conformance figure against a
substituted subject for four days without noticing. **0060 should require that
a rule declaring itself checkable also declares how its subject is
determined** — otherwise the first thing a reader does is silently choose one.

---

## 5. The remedy that could not fire — found by running it

**Not found by reading. Found because the operator ran `verify.py` and it went
red on a pin the printed remedy had just reported success on.**

**The rule.** 0056 clause 3, as newly enforced by instance 2 above. The auditor's
finding names its own remedy: `python run.py pin bump <artefact> --apply`.

**What happened.** The remedy ran to completion and changed nothing:

> `pin bump: config/mcf_conversation_map.tsv already matches its pin … — nothing to do.`

`run.py`'s writer short-circuited on **hash equality alone** (`existing.sha256 ==
digest`). The MCF pin's hash was correct; only its metadata line was missing.
So the only sanctioned writer of clause 3's fields declined to write them on the
grounds that the part it did check was fine, and **a hash-only pin was
permanently unfixable through the sanctioned path.** The gate stayed red, the
documented fix reported success, and the two facts did not meet.

**Why nothing noticed.** Because the checker and the writer were written by
different rounds against the same rule, and **nothing asserted the round trip**
— that whatever `pin bump` writes must satisfy the check that demands it.
`tester_pin` tested the writer. `tester_conversation_map_pin` tested the checker.
Neither tested the pair, and the pair is where the rule actually lives.

**This one is ours.** The auditor of instance 2 was written in this session and
demanded a field its own printed remedy could not produce. It shipped that way
for the length of one `verify.py` run.

**What was done.** 0056 clause 3's field list now lives once, in
`l5gntools/pin.py` as `REQUIRED_FIELDS` and `missing_metadata()` — the read-only
mechanism both sides already import. The auditor reads it; `run.py pin bump`
reads it to decide whether there is anything left to write. *"Nothing to do"* now
means *the pin records everything it should*, not *the hash agrees*. Completing a
correct pin and re-pinning a drifted one print different sentences, because they
are different acts with different risks. `tester_pin` asserts the round trip in
both directions, including that an incomplete pin must never report "nothing to
do" — the sentence that was true about the hash and wrong about the pin.

**What it tells the ruling.** 0053 clause 5 requires a remedy to be **safe**
wherever it can fire. This one was safe and **inert**, which is a weaker test
than that clause thought to set. **A rule, its checker and its remedy are three
artefacts, and conformance means all three agree** — a checker that demands what
no sanctioned writer produces converts a green gate into a permanently red one
with a documented fix that does nothing, which is strictly worse than leaving the
rule unenforced. **0060 should require that a rule declaring itself checkable
also names the writer that can satisfy it, and that something asserts the round
trip.**

---

## What the five have in common

The 08-28 aggregate said: *an accepted rule with no reader, or a reader that
structurally cannot see what its rule is about.* Five worked cases refine that
into **five distinct failure modes**, and a ruling that only addresses the first
will leave four live:

| | failure mode | instance | found by |
|---|---|---|---|
| 1 | two rules that cannot both hold, and no reader of the conflict | 0054 cl.6 vs `machines.json`'s template contract | reading |
| 2 | a reader whose subject is narrower than its rule's | 0056 cl.1, the hardcoded pin path | reading |
| 3 | an invariant between components that must not know about each other | the two registry resolvers | reading |
| 4 | a rule whose subject set is not enumerable at all | 0057 cl.7 | reading |
| 5 | a rule whose checker and whose remedy disagree | 0056 cl.3, `pin bump` vs its own auditor | **running it** |

**Mode 4 is the one to design against first.** Modes 1-3 and 5 are checkable
once someone decides what to check; mode 4 cannot even be counted, and it is the
mode that produced a wrong conformance figure that then travelled into two
planning documents unchallenged.

**Mode 5 is the one to be most humble about.** Four instances were found by
careful reading. The fifth was found because the operator ran the gate, and it
was introduced *by this session*, in the act of fixing instance 2 — a checker
that demanded a field its own printed remedy could not produce. **Reading found
the rules with no readers; only running found the reader with no remedy.** Any
sweep S4 builds should assume the same about itself.

**A sixth, noted but not worked:** `CLAUDE.md`'s standing Debt — *"nothing
checks any convention in this file"* — is mode 2 at estate scale. It is the
scope S4 should be careful not to accept by accident.
