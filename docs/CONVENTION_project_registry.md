# Project registry convention

**Status:** authored, not enforced. Unlike `CONVENTION_config.md`, most of this
describes something that already works -- the registry is real, populated and
in use. What is missing is that **the convention governing it lives inside the
artefact it governs**, in four comment keys of a gitignored file (§1). This
document is that content lifted out, plus the four gaps lifting it out
revealed.

**Scope:** this repo. The registry is consumed by Chronicler and by relink; a
consumer repo may read the generated registry but does not author the seed.

**Companion:** `CONVENTION_config.md` §7 argues this artefact out of `config/`
on the grounds that it is curated data with a review lifecycle, not
configuration. This file states what that lifecycle is.

**Cites:** 0010 (`project_link` is estate- and account-agnostic), 0011
(pre-registry links are reset, not trusted), 0012 (three tiers: program,
project, repo), 0031 (a non-gating surface reports, never verdicts), 0040
clause 4 (a curated artefact carries a committed fingerprint), 0042 clause 2
(the wizard allowlist is a reviewed edit), 0045 (a pin is origin, anchor,
hash -- reported, never repaired), 0048 clause 4 (a field with one possible
value trains the eye past it), 0051 (containment by construction), 0052 (a
convention lives in the repo, because it does not migrate with whoever is
typing).

---

## 1. What this fixes, measured

Read from `config/project_registry.json` on 2026-08-25.

| | |
|---|---|
| programs | **4** (3 `l5gn`, 1 `mcf`) |
| projects | **31** (21 `l5gn`, 10 `mcf`) |
| projects carrying curated aliases | **30** |
| projects carrying repo incarnations | **19** |
| projects carrying a human note | **22** |
| auditors covering the file | **0** |
| committed fingerprint | **none** |

**The convention is currently inside the artefact.** Four keys --
`_comment`, `_schema`, `_id_scheme`, `_low_signal_body` -- carry roughly a
page of rules: what the three tiers mean, why the id scheme won, what
`low_signal_body` does and the evidence for it, how the generator merges, how
to ship the file and how to confirm the destination path. All of it is good.
All of it lives in a **gitignored** file, which means a machine that does not
have the registry also cannot read the rules for building one, and the rules
cannot be reviewed, diffed or cited independently of the data they describe.

That is 0052's finding -- *a convention that lives in whoever happens to be
typing is not a convention* -- with a file in the role of the person. The
remedy is the same one 0052 prescribed: the convention lives in the repo, and
the artefact cites it.

**Two different files are called `project_registry.json`.** The curated seed
at `config/project_registry.json`, and the generated registry
`build_registry.py` writes to relink's `REGISTRY_PATH`. They have different
authors, different lifecycles and different edit rules, and §4 exists because
the names do not say so. Both are also resolved by two independent code paths
under two different environment variables (`CHRONICLER_REGISTRY_PATH`,
`CHRONICLER_REGISTRY_GROUPS`), recorded in `CONVENTION_config.md` §1.

**Nothing verifies it.** No auditor reads it, no fingerprint is committed
beside it, and it carries no stamp saying when it was authored or on which
host. The conversation map -- the same class of artefact -- has all three
(0040 clause 4, `auditor_conversation_map_pin`), so the mechanism exists and
was simply never applied here. §5.

---

## 2. What the registry is

**The join surface between the filesystem world and the conversation world.**
Repo folders on one side, Chronicler threads on the other; the registry is
what says a folder and a conversation are about the same effort.

**Three tiers (0012): program > project > repo.** A program is a portfolio
identity. A project is a coherent effort. A repo is a physical folder that is
*one incarnation* of a project. `v1 proto` -> `L5GN_Armory_v4` ->
`smelt-gateway` are three incarnations of one project, not three projects.

That was settled by evidence, not taste, and the reasoning is worth keeping
because it is the test to re-apply next time: those three repos carry 10, 58
and 123 evidence threads. One project with aliases would not produce three
separate substantial clusters. Had one carried 123 and the others 2 each, the
data would have said *flatten* -- it did not.

**One identifier scheme across all three tiers.** Every program, project and
repo has a registry `id`, and `threads.project_link` always holds an id --
never a `canonical_name`, never a folder name. The id wins because it is
**stable under rename**: `L5GN-Armory` -> `smelt-gateway` is a rename this
estate has actually performed, and `canonical_name`-keyed links would have
been orphaned by it. A ruling may be made at any tier; the hierarchy rolls up
for display. `project_link` is estate- and account-agnostic by design (0010),
and values predating the registry are reset rather than trusted (0011).

**`scope` is a config tag on the producer's root, never folder nesting**
(0012). The layout differs on every machine, so nesting has never been a
reliable signal. This is the one place where the registry and configuration
genuinely touch: config declares the scope of a root, the registry inherits it.

---

## 3. It is built from local knowledge, and cannot be derived

**The generator seeds; a human decides.** `build_registry.py` reads deposited
estate snapshots and attaches derivable facts -- path, git dates, scope, which
estates saw each repo. It cannot decide that three folders are one project. It
cannot know that a name is a portfolio rather than an effort. It cannot know
that an alias is a false friend.

Those came from somewhere specific, and the file records it: a 78-URL scrape's
title sheet, an era-map TSV, a doctrine document and live Datasette queries,
drafted 2026-07-18 and moved to three tiers on 2026-07-20. **None of that is
recoverable from a folder walk**, which is exactly why the registry exists and
why it is authored rather than generated.

**Why a folder walk is the wrong shape anyway**, restated from the generator
so it is not lost with it: producers scan their own estate and deposit facts;
the consumer reads deposited facts and never reaches back to a producer's
disk. A consumer-side folder walk can only see the machine it runs on, which
is precisely the machine whose projects it least needs to discover. The knight
learns about the work rig's MCF projects because the work rig told it.

**A registry that has seen only some estates is legitimate**, and reports
exactly which estates it saw. Re-run when another producer deposits. Partial
is a stated condition, not a degraded one (0031: report the finding, do not
issue a verdict).

---

## 4. The curated / generated boundary

**One rule, in both directions:**

> The generator never removes or rewrites what a human wrote. A human never
> edits the generated registry.

The generator's side of that is already implemented and should be cited rather
than re-derived:

- **Manual-provenance aliases are never auto-removed or rewritten.**
  `alias_sources` records where each alias came from -- `manual`,
  `claude_project`, `vocabulary_extract` -- and `merge_entry` re-adds any old
  alias whose source is one of those, every run.
- **`first_seen` is preserved**, so the registry remembers when it first saw a
  project.
- **Downstream signal blocks are carried forward untouched**: `vocabulary`,
  `activity`, `file_inventory`, `trail`, `link_evidence_ids`.
- **`seed_suppress` beats a prose note.** A repo may list short-name aliases
  the seeder would otherwise re-derive from the canonical name every run --
  `Castle` off `L5GN-Castle`, which collides with the knight's own hostname in
  shell transcripts. A note explaining the problem does not stop the
  regeneration; the key does. **Any human judgement the generator can undo
  needs a key, not a sentence.** That is the transferable rule.
- **Whole-file write, loud failure**: tmp-file plus `os.replace`, never a
  half-updated registry; any problem raises and writes nothing.

**`low_signal_body` is a judgement with evidence attached, and that is the
standard.** It means an alias found only in a message *body* is near-worthless
as a link signal for this entry, because the name gets dropped inside
conversations about other things -- *"I'll log this in Chronicler"*. relink
demotes body-only hits from 0.60 to 0.15. The umbrella case is stated in the
entry itself: a program name is by nature mentioned in passing inside
conversations about its children, so without the flag the umbrella outscores
the specific project it contains.

**A curated entry carries its reasoning.** 22 of 31 projects have a `note`,
and those notes are the reason the registry can be re-derived by a person who
was not there. Adding an entry without one is allowed and is a small debt.

---

## 5. Currency: the registry has none, and should

The registry is hand-carried, untracked and consumed on machines other than
the one that authors it. That is precisely the class of artefact 0040 clause 4
addressed for the conversation map, and the mechanism generalises without new
code -- `l5gntools/pin.py` already supports a pin file carrying
`origin=`, `anchor=`, `date=` and `host=`, verified read-only and **reported,
never repaired** (0045).

**What a registry pin would give**, in the terms the estate already uses: the
repo records *that* a registry was ratified, when, on which host and against
what content, while carrying none of the project names. A consumer holding an
older copy then reads as **not current** rather than as fine, and 0050's rule
-- a source declares its own staleness; one that cannot be reached reads as
unknown, never as fresh -- becomes true of the registry as well.

**Not built.** Recorded here as the named gap, not as an apology. The cost of
not having it is measured elsewhere in the estate: a hand-carried, untracked,
unpinned config file diverged between two rigs for days and was found by a
human comparing documents (`CONVENTION_config.md` §1).

---

## 6. Containment

**The registry carries real project names and employer codenames**, which is
why it is gitignored and why it travels by hand. 0051's line holds: the file
belongs on the machines that need it, and a copy of it is estate content, not
a conclusion.

**What may cross a boundary**: counts, scope distribution, the shape of the
schema, the *fact* that a project has N incarnations. **What may not**: the
names, the aliases, the notes, and any excerpt that carries them. A summary of
the registry is publishable; a redacted registry is not, because a redaction
that leaves the ids intact leaves the join intact.

**A generated registry inherits the containment of its seed.** Shipping the
generated file to a consumer is shipping the names.

---

## 7. The procedure, for the skill that will script it

A skill scripts the procedure and cites this file; it does not carry its own
copy of the rules (0052). The procedure a registry skill would script:

1. **Confirm the destination before shipping.** The seed and the generated
   registry resolve by different paths on different machines. Check with
   `relink.REGISTRY_PATH` on the target host rather than assuming.
2. **Run the generator dry first.** `--dry-run` prints and writes nothing;
   `--report-aliases` adds the human-in-the-loop report, including
   **DEPOSIT GAPS -- what the estate data could not tell us**: repos whose root
   carried no scope tag, repos whose deposit carried no git dates, and the
   whole-file case where no curated seed was found at all. Read that section
   first: it is the list of things the generator declined to guess.
3. **Read the alias report as a proposal.** Every new alias is a candidate,
   not a decision. A false friend gets `seed_suppress`, not a note.
4. **Decide at the right tier.** A new folder is usually a repo incarnation of
   an existing project. Ask the evidence-cluster question from §2 before
   creating a project.
5. **Write the note.** What the entry is, and why it is at that tier.
6. **Re-stamp currency in the same act as the change** (§5, once it exists).
7. **Ship deliberately**, and never by whole-file overwrite onto a machine
   that may have written to its own copy -- the failure `CONVENTION_config.md`
   §1 measured.

**A skill may propose every step above. It ratifies none of them.**

---

## 8. Not a gate -- and what a gate would cost

Nothing checks the registry. The two cheap, mechanical checks available:

1. **Schema and referential integrity** -- every `program` referenced by a
   project exists; every id unique across all three tiers; every entry carries
   a `scope`; no `canonical_name` used where an id is required. All decidable
   from the file alone.
2. **Fingerprint drift**, once §5's pin exists, on the same
   reported-never-repaired footing as `auditor_conversation_map_pin`.

Neither can check whether a project is at the right tier, and neither should
pretend to. That judgement is §2's evidence test, made by a person.

**Both report; neither gates.** A registry complaint on a consumer that has
simply not been re-handed is the state 0053 identified -- a check that can go
red without a defect -- and it belongs outside the gate for the same reason.

---

## 9. The check, before you change the registry

1. Is this a **new project**, or another **incarnation** of one? Apply §2's
   evidence test.
2. Is the identifier an **id**, everywhere? Never a `canonical_name`, never a
   folder name.
3. Does the entry carry a **`scope`** and a **`note`**?
4. Is a judgement being recorded that the generator could undo? Then it needs
   a **key** (`seed_suppress`, `low_signal_body`), not a sentence (§4).
5. Did the generator run **dry** first, and was the alias report read as a
   proposal?
6. Does anything leaving this machine carry **names** rather than counts (§6)?
