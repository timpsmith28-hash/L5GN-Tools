# Agenda — closing the workflow gaps, 2026-08-26

A working plan for one day, not a ruling. Frozen at its date; if it is amended,
the amendment is declared at the top.

**Prefix borrowed.** `AGENDA_` is a dated-snapshot class in the work rig's
`CONVENTION_docs.md` §2. Used here ahead of adopting that convention, and noted
so the borrowing is visible rather than assumed.

**Inputs.** The five work-rig conventions and `CATALOGUE_skills_2026-08-26.md`,
received today; `docs/CONVENTION_*.md` written on this rig today; the workflow
map; `data/decision_drafts/0054-0056_proposed.md`.

---

## 0. Two corrections to yesterday's gap list

Recorded first, because a plan built on a wrong finding is worse than no plan.

**"Ratification produces no artefact" was not a new finding.** The work rig had
already named it: `CONVENTION_decisions.md` §10 — *"The different-day rule is
unobservable. A status line stamped `accepted` carries no evidence of when it
was read, and nothing would notice a same-sitting ratification."* Two estates
found it independently, which is stronger evidence that it matters and weaker
evidence that anyone has a fix.

**"Conventions have no convention" was half wrong.** `CONVENTION_docs.md` §2
governs the `CONVENTION_` class, and §2a rules the skill-versus-authority split
directly: *"the prompt file is the authority; a skill wrapping it is the
procedure… a skill that restates the spec is a second copy of the rule, and the
copy is what a thread will believe."* That is the doctrine this rig arrived at
separately today. **MCF governs its conventions; L5GN-Tools does not.** The gap
is real here and was never estate-wide.

**And one gap got worse.** `docs/Consultants/` is **retired** by `wfa-0025`
clause 6, replaced by `CONSULTANT_<YYYY-MM-DD>_<topic>.md` flat in `docs/` with
the raw capture under `context/`. So `consultant-docs` does not merely point at a
folder absent here — it points at a class the other estate has abolished.

---

## Wave 0 — decisions, this thread, before anything forks

Nothing below can start until these land. They are small and they are all
judgement.

### 0.1 Skill ownership and the branch model

Stated by the operator today and not yet ruled: **skills are the operator's IP;
`L5GN-Tools` is the source of truth for published ones; a task force may branch,
tailor and offer a merge.** This answers the work rig's §6 question and replaces
"vendored copy" with "branch", which makes drift diffable rather than invisible.

Wants a DECISIONS entry. Until it exists, every skill task below is building on
an unruled premise.

### 0.2 The three portability rules

Proposed, to be confirmed before Thread A runs:

1. A skill declares **what kind** of authority it needs, never where it lives.
2. Resolution order: this repo's `docs/` → the estate's source-of-truth repo →
   **stop**.
3. A skill that cannot read its authority **stops** — it never falls back to its
   own text.

Rule 3 is the load-bearing one. It converts `round-closer`'s baked-in *"no MCF
repo has a gate"* from a silent wrong answer into a refusal.

### 0.3 Adopt, adapt or decline, per received convention

| file | disposition | why |
|---|---|---|
| `CONVENTION_docs.md` | **adapt** | Ours is `docs/README.md`. Theirs is better-shaped and estate-scoped. Promote ours, borrow their class table and §2a. |
| `CONVENTION_decisions.md` | **adapt** | Ours has 53 entries, one log, `l5gn-` prefix. Their §2, §4, §5 and §9 transfer whole. |
| `CONVENTION_briefs.md` | **adapt** | Their card is `<NN>_<slug>` against a per-project registry; ours is `<slug>` with no registry. The `[G]`/`[H]` rules transfer unchanged. |
| `CONVENTION_gitignore.md` | **adapt** | The baseline-block mechanism transfers; the block's contents do not. |
| `CONVENTION_commits.md` | **merge back** | Ours is the origin. Take their §5 prefix table (0043 already requires it) and their §10 checklist. Leave the appendices. |

**None is a straight clone.** Every one is scoped *"every repo in the MCF
estate"* in its first line and cites `wfa-` rulings throughout.

---

## Wave 1 — parallel threads

Independent of each other. Each is written to be handed to a separate thread
with this section as its brief.

### Thread A — skills into the repo, and made portable

**Why.** The source-of-truth claim is not yet true: there is no `skills/` in the
tree, so a task force branch has nothing to diff against and a merge has nowhere
to land. `skills/dtr/` is the only one there.

**Do.**
1. Create `skills/<name>/SKILL.md` for the five house skills, from the copies
   configured today, byte-identical first — **one known baseline before any
   edit**, the same discipline the work rig used in its catalogue.
2. Commit that as its own commit. Then apply Wave 0.2's rules in a second.
3. Record a `sha256` per skill in the commit body. A fingerprint nobody
   recomputes is a comment, but one nobody wrote is not even that.

**Specifically fix.** `commit-scribe` and `docs-archivist` name L5GN-Tools in
their own descriptions; `consultant-docs` points at a retired class;
`round-closer` asserts an estate fact that is false here.

**Done when.** Five skills tracked, each resolving its authority rather than
naming it, each stopping when it cannot read it.

**Do not.** Edit and move in one commit. Touch `orientation` — it belongs to the
work rig and its absolute paths are its own problem to solve.

---

### Thread B — the decisions map generator

**Why.** Track B stage 05 is the only generated artefact in the plan that does
not exist, and three DTR stages want the view it produces.

**Do.** A command that parses `docs/DECISIONS.md` and writes
`docs/_decisions_map.md`, carrying:

- **Threads** — chains derived from `Builds on:`. The current deepest is
  `0010 → 0025 → 0027 → 0033 → 0037/0040 → 0042/0044 → 0050-0053`.
- **Spine** — most-cited. Today: `0025` (×10), then `0007`, `0013`, `0032`,
  `0033`, `0040` (×5 each).
- **Orphans** — entries citing nothing. Today **23 of 53**, including `0029`,
  `0030`, `0036` and `0043`, all load-bearing and unreachable by citation.
- **Status** — accepted, proposed, superseded, with counts.

**Done when.** `python run.py decisions-map` writes the file, and running it
twice on an unchanged log produces an identical file.

**Do not.** Summarise, condense, or paraphrase any entry. **Link to the
falsifiers; never restate them.** The "What would show this wrong" sections and
the uncomfortable half of Consequences are the first things a condensing pass
eats and the reason the log is worth keeping.

---

### Thread C — `CONVENTION_docs.md`

**Why.** Our doc lifecycle rules live in `docs/README.md` §3, which is a filing
document doing a convention's job — the one row in the workflow map that sits in
the wrong column. It is also `docs-archivist`'s authority.

**Do.** Promote `docs/README.md`'s §2 and §3 into `docs/CONVENTION_docs.md`,
adapted to this repo. Borrow from the work rig's version:

- **§0's governing rule** — *"a document earns its place by holding something
  that cannot be derived"* — which is 0030 stated better than we state it.
- **§2's class table**, adjusted to the prefixes actually in use here.
- **§2a entire.** The skill/authority split. This is Wave 0.2 with a citation
  behind it.
- **§6 do-not-recreate**, which forbids status boards and handoff documents.

**Also decide.** Whether `docs/investigation/` survives — the work rig retired
theirs (`wfa-0024` clause 10) in favour of `context/` at the repo root for
inbound material. We have both problems and neither rule.

**Done when.** `docs-archivist` can cite a `CONVENTION_` file, and
`docs/README.md` is reduced to a pointer.

---

### Thread D — `CONVENTION_gitignore.md`

**Why.** Their `wfa-0014` was accepted and conformance was **1 of 9 by the end
of the same day**. That is the strongest evidence either estate has produced
that a written rule decays without a reader, and it is worth having the same
baseline here so the same measurement is possible.

**Do.** Write the baseline block for L5GN-Tools from the current `.gitignore`,
with the marker line and the below-the-line rule. Keep their clause-4 negation
mechanism — it is the good part.

**Carry across unchanged.** The `data/git_warden/` rule, the export extensions
including `*.xlsm`, and the secrets list. Their §5 note on why
`*secret*`-style substring patterns are excluded is reasoning worth keeping
rather than re-deriving.

**Done when.** `.gitignore` opens with the block and `git check-ignore -v` is the
stated verification, never a read of the file. Our own evening proved why: a
sandbox mount served a byte-truncated `.gitignore` stably across three reads.

---

### Thread E — `CONVENTION_decisions.md` and `CONVENTION_briefs.md`

**Why.** Two skills here cite conventions that do not exist on this rig, and
both now exist on the other one. Adapting is cheaper than authoring and the
texts are good.

**Do.** Two files, adapted. Transfers whole: their decisions §2 (the entry
shape), §4 (append-only, and the freeze attaching at acceptance not at commit),
§5 (the five status values including `withdrawn` and `recovered`), §9 (propose
and ratify). Their briefs §4 (`[G]`/`[H]`, and *"every `[H]` is a cost, count
them"*) and §5 (the report).

**Change.** Card identity — theirs is `<NN>_<slug>` against
`REGISTRY_projects.md`; ours is `<slug>` with no registry, and inventing one is
out of scope for today. Prefix is `l5gn-`. Drop every `wfa-` citation or
replace it with ours.

**Note honestly in both.** These are adaptations of documents authored by the
work task force, and say so in the header. Method crossing the bridge and
leaving no trace is the defect their census named; this is the correction.

**Done when.** `decision-scribe` and `brief-scribe` each cite a file in this
repo, and `brief-scribe`'s line 12 self-declared drift risk can be deleted
because it has closed.

---

## Wave 2 — after Wave 1

**Wants Thread A:** `architecture-scribe` + `CONVENTION_architecture.md`. Its
judgement boundary is *read the diff of the generated files and decide which
authored text now lies* — not running the commands, which is 0052 clause 1's
line between a skill and a script.

**Wants Threads A and C:** the build skill. The operator's shape, and it is the
right one: finds the next brief and runs it, carrying only top-level reminders,
because **the brief is the rules** and the specifics belong in each brief. Thin,
per `CONVENTION_docs.md` §2a. This is what closes the workflow map's Build gap —
not by governing the build, but by naming where its governance already lives.

**Wants everything:** `CLAUDE.md` refresh. Point at the conventions that have no
skill — config, registry, conversation map — so an important rule without a
procedure is still reachable from the map. That was the operator's answer to the
four-conventions-no-skill gap and it is better than inventing four skills.

**Operator only, and not today's work:** append `0054-0056`, ratify on a
different day, and draft `0057` on the hook-versus-standing-channel question the
work rig put to us.

---

## What this agenda does not close

- **Observe still has nowhere to land.** A finding lives in a thread until
  someone decides it is worth a convention. Unchanged by any thread above.
- **Ratification still produces no artefact**, on either rig. §0 above.
- **Nothing checks any of it.** Every convention written today is read by people
  and by skills people invoke. The conformance reader the work rig asked for
  first is not on this plan, and it is the thing both estates say they want most.
- **Two documents that claim to be walkable and are not** — the mirror runbook
  and the bridge README — are recorded and not fixed.
