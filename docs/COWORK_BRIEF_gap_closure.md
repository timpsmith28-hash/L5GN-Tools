# Cowork brief — every skill gets an authority it can resolve, and the repo gets the skills

**Where you are:** `C:\Users\timps\Documents\GitHub\L5GN-Tools`, host
`LucasGoonPC`.

**Read before Task 1, in this order:** `CLAUDE.md` at the repo root — it is the
map, and it is where the environment hazards live; then this brief in full;
then `docs/UAT_gap_closure.md`, which is the walk-sheet of record and is not a
summary of what follows.

**Draft-status:** written 2026-08-27, to be built the same day. Nothing here
describes remembered code — every "already exists" claim below was checked
against the tree while drafting, and the checks are named at each task so they
can be re-run rather than trusted. **Re-verify them anyway as the round's first
act.** Two days of findings on this rig came from documents asserting things
about a tree nobody had looked at.

**Origin:** design thread, 2026-08-26/27. The work task force's
`CATALOGUE_skills_2026-08-26.md` measured seven skills configured, three
vendored, **one byte-identical to the copy that actually loads** — and its §6
asked outright what owns them. On this rig the same week produced four
conventions with no skill, four skills with no convention, and a workflow map
whose largest cluster of gaps is skills pointing at authorities that resolve to
nothing, or to the wrong estate's facts.

**Precondition — hard:** `docs/DECISIONS.md` carries entries 0054-0057,
committed and `proposed`. Check with `grep -c "^## 00" docs/DECISIONS.md` → 57.
If it returns anything else, this brief was written against a different tree.

**Depends on — this repo's rulings:** **0028** clause 3 (a commit is a human
act; a local surface may stage, never commit), **0030** (shape is generated,
rationale is authored; a generated artefact never hand-edited), **0033**
(propose, ratify, execute), **0043** (a ruling from another repo is cited with
its repo, at every mention), **0045** (verification reports and never repairs),
**0048** clause 4 (a check that cannot fail trains the eye past it), **0051**
(work-estate corpus is bounded by construction — governs what may be read from
the mirror), **0052** clauses 2, 3 and 5 (the convention lives in the repo that
owns the work; no rule may have a skill as its only home; a skill with no
convention says so and names the debt), **0057** (*proposed* — skills are
published from one source and branch rather than copy; a skill declares the kind
of authority it needs, resolves it at run time, and stops rather than working
from its own text).

**Ratify before code.** **0057 is `proposed` and is not authority.** Tasks 1, 2,
4 and 5 do not depend on it and may be built now. **Task 3 is split by it:**
3a tracks the skills unchanged and needs no ruling; **3b implements 0057 clauses
3-6 and is drafted, staged and left uncommitted until 0057 binds.** Ratification
is a re-read by the operator on a different day; this thread never ratifies
anything.

**Deliverable:** four convention documents in `docs/`, five skills tracked under
`skills/` and resolving their authority at run time rather than naming it, and
`python run.py decisions-map` writing `docs/_decisions_map.md`. The round is
finished when every skill under `skills/` either resolves its declared authority
inside this repo or stops with a named reason, and `run.py decisions-map` run
twice against an unchanged log produces byte-identical output.

---

## The thing this round exists to prevent

A skill that **half-resolves**. The catalogue named it better than we did: a
pointer that fails is a refusal you notice; a pointer that lands somewhere
plausible is a wrong answer you act on. `commit-scribe` loaded on the work rig
found its convention file — and then handed that reader ruling citations, an
architecture-regeneration instruction and a pre-commit-hook claim that were all
facts about a different repo.

So the target property is not "the skill has a convention". It is: **a skill
either reaches its authority in the repo it is standing in, or it stops.**
Anything in between is the failure.

## Working rules

**Read the mirror narrowly.** Three tasks below read a convention file from
`…\wizforge-mirror-2026-08-26_Unpacked\WizForgeAnalytics\docs\`. Read **only the
named file** in each case. The rest of that tree is contained work-estate corpus
under 0051 and is not this round's to read, quote or summarise.

**Normalise line endings before concluding anything changed.** A byte, size or
hash comparison across a Windows tree and a synced store reports every file as
different, on every run, forever. Five skills that looked adapted were
byte-identical once normalised. `docs/DECISIONS.md` is LF on disk; most of the
tree is CRLF.

**Ask git for anything about git.** Never run plain git against the mounted
Windows repo from a sandbox, and never treat a read of `.gitignore` as evidence
of what git ignores — a mount served a truncated copy stably across three
consecutive reads on the work rig and sent a thread in circles.

**Prefer append over rewrite.** Where a rewrite is unavoidable, compare the
read length against `stat` before writing anything back.

**Cite, never restate.** A rule copied into a second file is the copy a later
reader will believe (0052 clause 2).

**Name every adoption.** A convention adapted from another estate states its
origin repo, origin file and date in its own header (0057 clause 7). Method that
crosses a boundary and leaves no trace is the defect the work rig's census
named.

**Stage, hand back, never commit** (0028 clause 3). Draft each commit message to
`data/git_warden/<slug>-<n>.msg` and hand back the exact `git commit -F`
command. `data/` is gitignored wholesale — confirm with
`git check-ignore -v data/git_warden`, which returns a rule or the path is
tracked.

**A partial round is a real result.** If a stop condition trips, stop, report
where, and hand back what is done. A round that pushed past a tripwire is worth
less than one that halted at it.

---

## Task 1 ▸ `docs/CONVENTION_decisions.md`

**Checked while drafting:** no `CONVENTION_decisions.md` exists in `docs/`.
`decision-scribe` carries the format in its own text and names no convention
file. Re-verify both.

Adapt the work rig's `CONVENTION_decisions.md`. Read that file and no other.

**Transfers essentially whole:** its §2 (the entry shape — metadata line and
four sections, including *"What would show this wrong"* as mandatory and
concrete), §4 (append-only, and the freeze attaching at **acceptance, not
commit**, so a `proposed` entry may still be corrected in place), §5 (the five
status values — `proposed`, `accepted <date>`, `superseded by NNNN`,
`withdrawn`, `recovered`), §7 (superseding, and stating which clauses of the old
entry survive), §9 (propose and ratify; a thread never ratifies).

**Must change:**

- **Scope.** Theirs opens *"every repo in the estate"*, meaning MCF. This is
  L5GN-Tools.
- **Prefix** is `l5gn-`. Remove or replace every `wfa-` and `sfds-` citation. A
  citation nobody can resolve here is worse than none (0043).
- **Their §6** rules on a living register in a repo that does not exist here.
  Drop it and say in the header that it was dropped.
- **Their §0** recounts how the convention was found missing on their side. Ours
  was found missing differently — by the workflow map on 2026-08-26. State ours.

**Lands:** `docs/CONVENTION_decisions.md`.

## Task 2 ▸ `docs/CONVENTION_briefs.md`

**Checked while drafting:** `brief-scribe` line 12 reads *"There is no written
convention for briefs yet… That gap is real and this skill is the drift risk
until it closes."* Re-verify the line is still there; closing it is this task's
point.

Adapt the work rig's `CONVENTION_briefs.md`. Read that file and no other.

**Transfers essentially whole:** its §0 (a brief is a request frozen at the
moment of asking; correcting it destroys the record of what was asked), §2 (the
brief and walk-sheet are one act, written before the build), §3 (the parts of a
brief), §4 (`[G]`/`[H]`, and *"every `[H]` is a cost, count them"*, and that an
`[H]` forced by an awkward design is a **design finding** rather than a check),
§5 (the report).

**Must change:**

- **Card identity.** Theirs is `<NN>_<slug>`, numbered per project from a
  `REGISTRY_projects.md`. **This repo has neither a per-project number nor a
  registry.** Ours is `COWORK_BRIEF_<slug>.md`. Do not import their numbering.
- **Their §6** asserts *"no MCF repo has a gate"*. This repo has one. Confirm
  with `git config --get core.hooksPath` (expect `.githooks`) and state what is
  true here.
- **Their §7** proposes an orientation-round pattern for seven migrating repos.
  Not our situation. Drop it.

**Add, and it is ours rather than theirs.** In the parts-of-a-brief list: **a
brief opens with the two things a cold thread cannot derive — where it is
(repo and host), and what to read first.** Everything after that is a pointer,
so the brief carries its own entry point and opening a round needs no separate
instruction. This brief's own header is the worked example, and it was added
after the brief was drafted without one — which is the evidence for the rule.

**Lands:** `docs/CONVENTION_briefs.md`.

## Task 3 ▸ the skills

**Checked while drafting:** `skills/` contains `dtr` and nothing else. Five
skills are configured and shared with the work rig: `brief-scribe`,
`commit-scribe`, `consultant-docs`, `decision-scribe`, `docs-archivist`.

### 3a — track them, unchanged

Copy the five in **byte-identical, defects included**, to
`skills/<name>/SKILL.md`. This is the known baseline the branch model needs; a
repository recording what we *wish* loaded is not a currency check, and it is the
discipline the work rig used in its own catalogue.

Source is the configured copies. The mirror's
`…\WizForgeAnalytics\skills\<name>\SKILL.md` were verified byte-identical to the
configured set on 2026-08-26 **once line endings were normalised**, so they are a
valid fallback. **Record which source you used.**

Record a `sha256` per file in the commit body. A fingerprint nobody recomputes
is a comment; one nobody wrote is not even that.

**This is its own commit.** No edits ride with it.

### 3b — make them resolve, not name

**Held until 0057 binds.** Draft, stage, hand back; do not commit.

Apply 0057 clauses 3-6 to each of the five. `skills/dtr/SKILL.md` is the
reference shape — it declares the kind of authority it needs, resolves
most-specific-first, and stops rather than falling back.

Specifically:

- `commit-scribe` says *"for L5GN-Tools"* in its own description;
  `docs-archivist` says *"in L5GN-Tools"*. Both name an estate in prose.
- `consultant-docs` points at `docs/Consultants/` — a class the work rig
  **retired** (`wfa-0025` clause 6) and which does not exist here.
- `brief-scribe` and `decision-scribe` should, after Tasks 1 and 2, resolve to
  real files. Confirm that they do rather than assuming it.

**A skill whose authority still does not exist is left stopping.** That is
clause 5 working. Do not invent a convention to satisfy it.

**Lands:** `skills/{brief-scribe,commit-scribe,consultant-docs,decision-scribe,docs-archivist}/SKILL.md`,
in two commits.

## Task 4 ▸ `docs/CONVENTION_docs.md`

**Checked while drafting:** `docs/README.md` carries §1 the core set, §2 doc
classes, §3 the archiving convention, §4 `investigation/`, §5 do not recreate,
§6 what isn't enforced. It is `docs-archivist`'s authority and it is a filing
document doing a convention's job.

Promote §2 and §3 into `docs/CONVENTION_docs.md`, and reduce `docs/README.md` to
a pointer. Read the work rig's `CONVENTION_docs.md` — that file and no other —
and borrow, naming the adoption:

- their **§0**: *"a document earns its place by holding something that cannot be
  derived"*, which states 0030 better than we state it;
- their **§2 class table**, adjusted to the prefixes actually in use here;
- their **§2a entire** — a skill is the procedure, the file is the authority, and
  a skill that restates the spec is a second copy of the rule. This is 0057
  clauses 3-6 with reasoning behind it;
- their **§6** — no status boards, no handoff or priming documents.

**Decide and record:** whether `docs/investigation/` survives. The work rig
retired theirs in favour of a gitignored `context/` at the repo root for inbound
material. State the decision either way; **migrate nothing.**

**Lands:** `docs/CONVENTION_docs.md`, and an edited `docs/README.md`.

## Task 5 ▸ `docs/CONVENTION_gitignore.md`

**Checked while drafting:** `.gitignore` line 2 is `/data/`; line 7 is
`/config/local.json`; line 25 is `/config/project_wizard.allow.json`; line 32 is
`/config/*conversation_map.tsv`. Re-verify **through git**, not by reading the
file.

Derive a baseline block for this repo, with two marker lines and the rule that
nothing above the lower marker is edited locally. Read the work rig's
`CONVENTION_gitignore.md` — that file and no other — and carry across the
**mechanism, not the contents**: block first, repo-specific rules below the
line, and exceptions expressed as a **negation below the line** with a comment
saying what it re-admits and why, because git applies patterns in order and a
negation above its pattern silently does nothing.

Carry their reasoning on secrets: extensions and exact names only, **not**
`*secret*`-style substring patterns, which match anywhere in a path and would
swallow a `CONVENTION_secrets.md` or a `token_parser.py`. State the cost they
state: a file named `salesforce_credentials.txt` passes the baseline.

**Lands:** `docs/CONVENTION_gitignore.md`. **`.gitignore` itself is not edited
this round.**

## Task 6 ▸ `run.py decisions-map`

**Checked while drafting:** `run.py` registers subcommands with
`sub.add_parser(...)` — `pin bump` at line 886 is the nearest model.
`docs/_architecture_shape.md` exists and is produced by `run.py architecture`
then `run.py render-architecture`.

Write a command that parses `docs/DECISIONS.md` and writes
`docs/_decisions_map.md`.

Each entry's citations run from `**Builds on:**` to `**Source:**` or
`**Context.**`; extract four-digit numbers and exclude self-citations. Emit four
views:

- **Threads** — chains followed through citations. The deepest today is
  `0010 → 0025 → 0027 → 0033 → 0037/0040 → 0042/0044 → 0050-0053`.
- **Spine** — most-cited. Today `0025` (×10), then `0007`, `0013`, `0032`,
  `0033`, `0040` (×5 each).
- **Orphans** — entries citing nothing. Today **23**, including `0029`, `0030`,
  `0036` and `0043` — all load-bearing and unreachable by following citations.
- **Status** — counts, and a list of what is `proposed`.

The file's header states it is generated, names the command, and says never
hand-edit it (0030).

**The one prohibition that matters: never summarise, condense or paraphrase an
entry.** Titles and numbers only. **Link to the falsifiers; never restate them.**
"What would show this wrong" and the uncomfortable half of Consequences are the
first things a condensing pass eats, and they are the reason the log is worth
keeping.

**Lands:** a `decisions-map` subcommand in `run.py`, its implementation, and
`docs/_decisions_map.md`.

---

## The one deliberate widening, named

**`skills/` is a new top-level directory that no ruling names.** 0057 clause 1
makes this repo the published source for the estate's skills, which requires
somewhere for them to live, and the tree has no convention covering its own root
layout. The work rig hit the same thing from the other side and catalogued it as
debt rather than resolving it.

Taken knowingly, bounded three ways: `skills/` holds `SKILL.md` files and
nothing else; no skill is executed by anything in this repo; and a convention
covering the repo's root layout is a later round, not this one.

## Explicitly out of scope

- **`orientation` and `round-closer`.** Both were authored on the work rig, both
  bind to MCF paths or MCF facts, and both want their own round under the branch
  model. Their absence here is a decision, not an oversight.
- **Editing `.gitignore`.** Task 5 writes the convention; the file is not
  touched, and `git rm --cached` on anything already tracked is a different
  round entirely.
- **Migrating any document** into or out of `docs/investigation/`, or creating
  `context/`. Task 4 decides; it does not move.
- **Inventing a card-numbering scheme or a project registry** to make Task 2's
  adaptation symmetrical with the work rig's.
- **Wiring `_decisions_map.md` into `CLAUDE.md`**, or into DTR. Later.
- **Ratifying anything.** Including 0057, which half this round implements.
- **Amending `dtr`.** It is the reference shape; if it is wrong, that is a
  finding for the report, not an edit.

## Stop conditions

- `grep -c "^## 00" docs/DECISIONS.md` does not return 57 → **stop.** This brief
  was written against a different tree.
- The mirror is unreadable, or a named convention file is not where this brief
  says → **stop** for that task; the others continue.
- A configured skill and its mirror copy differ **after normalising line
  endings** → **stop.** That is a real divergence and wants recording, not
  resolving.
- Task 3a and 3b would land in one commit → **stop** and split them.
- A skill's authority does not exist after Tasks 1, 2 and 4 → **do not invent
  one.** Leave the skill stopping and record it.
- An adaptation requires importing the work rig's card numbering or its registry
  → **stop** and report.
- A baseline rule in Task 5 would newly ignore a file git already tracks →
  **stop** and name the file.
- The generator finds a duplicate entry number → **stop.** Unrecoverable in an
  append-only log, and it must not be papered over.
- You find yourself summarising a DECISIONS entry to make the map read better →
  **stop.** That is the one thing Task 6 forbids.

## The round's falsifier

**Does resolve-or-stop leave the skills usable?**

If, at the end of this round, three or more of the five skills are permanently
stopped and the operator's response is to go back to editing them in the plugin
store, then 0057 clause 5 has produced refusals rather than reliability, and the
clause wants replacing with a **currency stamp on a named path** rather than
restating more firmly. Write the answer down before deciding what it means.

## UAT — acceptance checks (Tim walks these)

Extracted to `docs/UAT_gap_closure.md`, which is the walk-sheet of record.

## Reporting

`docs/COWORK_REPORT_gap_closure.md`. It must record:

1. **Per convention adapted: what transferred whole, what changed, and what was
   declined** — section by section, not "adapted from theirs".
2. **The `sha256` list from Task 3a**, and which source the copies came from.
3. **Per skill: what its declared authority now is, and whether it resolves** in
   this repo today. A skill that stops is a result; name it and say why.
4. **The `docs/investigation/` decision and its reasoning**, whichever way it
   went.
5. **The `git check-ignore -v` output** for every rule Task 5's block contains.
6. **The generator's four counts**, and any dangling citation it found.
7. **Every stop condition that tripped**, and what was left undone.
8. **Anything this brief got wrong about the tree.** The draft-status note says
   the claims were checked; where one was stale by the time you read it, that is
   the most valuable line in the report.
