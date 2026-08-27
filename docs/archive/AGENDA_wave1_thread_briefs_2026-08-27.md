> **ARCHIVED** 2026-08-27 · superseded · no report — a handover plan, not a round
> Superseded by `docs/COWORK_BRIEF_gap_closure.md` and `docs/UAT_gap_closure.md` · Original purpose: five separate briefs for five parallel Sonnet threads, written before the round was scoped as a single card.
> Read as accurate history of the task order and the stop conditions, most of which carried into the brief unchanged. Do **not** read the five-thread split as current — the round is one sequential card, and Thread A's dependency on Thread E is expressed there as task ordering rather than as a run-order note. Two things this file gets wrong by omission: it has no counterpart to the brief's Task 3 split (3a tracks the skills unchanged and needs no ruling; 3b implements 0057 and is held until that entry binds), and it states no falsifier for the round.

# Wave 1 — thread briefs, 2026-08-27

Five briefs, one per thread, each written to be handed to a **cold thread with
no prior context**. Frozen at date.

**A deviation, declared.** These are compressed house briefs — origin,
preconditions, cited rulings, deliverable, tasks, out of scope, stop conditions,
`[G]`/`[H]` checks, reporting — but they are **not cards** and carry no separate
walk-sheet. They govern handover, not a build round. If any grows into real
build work, it earns a proper card.

**Run E before A.** 0057 clause 5 makes a skill stop when it cannot read its
authority, and Thread E is what gives two of them one to read. A and B, C, D
are otherwise independent of each other.

---

## Preamble — binds every thread below

**Read first, in this order:** `CLAUDE.md` at the repo root, then the convention
for whatever you are touching. `CLAUDE.md` is a map: it points, it does not
decide. Where it and the thing it points at disagree, the thing it points at
wins.

**Repo:** `C:\Users\timps\Documents\GitHub\L5GN-Tools` on host `LucasGoonPC`.

**Environment hazards — these have all bitten in the last two days.**

- **Never run plain git against the mounted Windows repo from a sandbox.** For
  anything about what git holds, ask git, on Windows.
- **Normalise line endings before concluding anything changed.** A byte, size or
  hash comparison across a Windows tree and a synced store reports every file as
  different, forever. Five skills that looked adapted were byte-identical once
  normalised. `docs/DECISIONS.md` is LF on disk; most of the tree is CRLF.
- **A sandbox mount serves stale, byte-truncated content deterministically and
  without error.** A second read confirms a false answer. Prefer append over
  read-modify-write; where a rewrite is unavoidable, compare the read length
  against `stat` before writing anything back.
- **`git bundle verify` needs a repository context**; from a plain directory it
  fails with *"need a repository to verify a bundle"*.
- **Commit with `git commit -F <file>`**, never a multi-line `-m`.

**Working rules, all threads.**

1. **Propose; never execute the last step.** Draft, stage, hand back. **The
   commit is a human act** (0028 clause 3). No thread runs `git commit`.
2. **Cite, never restate.** A rule copied into a second file is the copy a later
   reader will believe (0052).
3. **A convention adopted from another estate names the adoption in its own
   header** — origin repo, origin file, date (0057 clause 7, proposed).
4. **Report what you could not do**, by name. An omitted step is
   indistinguishable from a step that found nothing.
5. **Draft the commit message** to `data/git_warden/<slug>-<n>.msg` and hand
   back the exact `git commit -F` command. `data/` is gitignored wholesale.

**Status of the rulings you will be citing.** 0051-0057 are **`proposed`**. They
may be read and followed; they are not authority to cite as settled. Say so
where a deliverable leans on one.

---

# Thread E — `CONVENTION_decisions.md` and `CONVENTION_briefs.md`

**Run this first.**

**Origin.** `decision-scribe` and `brief-scribe` cite conventions that do not
exist in this repo. `brief-scribe` line 12 declares the gap itself and names
itself the drift risk. Both conventions now exist on the work rig, written
during the week that task force trialled the process.

**Preconditions.** The work rig's files are readable at
`…\wizforge-mirror-2026-08-26_Unpacked\WizForgeAnalytics\docs\`. **Read only
`CONVENTION_briefs.md` and `CONVENTION_decisions.md` from there.** The rest of
that tree is contained work-estate corpus under 0051 and is not yours to read.

**Deliverable.** Two files in `docs/`, adapted rather than cloned, each naming
its origin in the header.

**Transfers essentially whole.** From decisions: §2 (the entry shape and the
four sections), §4 (append-only, and the freeze attaching at **acceptance, not
commit**), §5 (the five status values — `proposed`, `accepted <date>`,
`superseded by NNNN`, `withdrawn`, `recovered`), §7 (superseding), §9 (propose
and ratify; a thread never ratifies). From briefs: §0 (a brief is a request
frozen at the moment of asking), §4 (`[G]`/`[H]`, and *"every `[H]` is a cost,
count them"*), §5 (the report).

**Must change.**

- **Scope line.** Both open *"every repo in the MCF estate"*. This is L5GN-Tools.
- **Prefix** is `l5gn-`. Drop or replace every `wfa-` and `sfds-` citation; a
  citation nobody can resolve here is worse than none.
- **Card identity.** Theirs is `<NN>_<slug>` numbered per project from
  `REGISTRY_projects.md`. **This repo has neither.** Ours is
  `COWORK_BRIEF_<slug>.md`. Do not import their numbering, and do not invent a
  registry — that is a separate round.
- **Their briefs §6** asserts *"no MCF repo has a gate"*. This repo has one:
  `.githooks/pre-commit` runs `verify.py`. Confirm the hook path yourself with
  `git config core.hooksPath` rather than trusting this line, and state what is
  true here.
- **Their decisions §6** (living registers) binds a repo that does not exist
  here. Drop it.

**Out of scope.** Their §3 numbering machinery. Their `REGISTRY_projects.md`.
Amending `decision-scribe` or `brief-scribe` — that is Thread A.

**Stop conditions.**
- The mirror is unreadable, or the two files are not where stated → stop.
- An adaptation would require inventing a card-numbering scheme → stop, say so.
- You find a third convention you think should be adopted → report it, do not
  adopt it.

**Acceptance.**
- `[G]` Both files exist in `docs/`, and neither contains a `wfa-` or `sfds-`
  citation.
- `[G]` Each header names origin repo, origin file and date.
- `[G]` Every claim about this repo's tree was checked against the tree, not
  carried over. List what you checked.
- `[H]` Reading only the adapted file, could someone write a conforming
  DECISIONS entry without opening the work rig's version?
- `[H]` Does anything read as borrowed rather than adopted — a rule that fits
  their estate and not this one?

**Report.** What transferred whole, what changed and why, and anything you
declined to adopt.

---

# Thread A — skills into the repo, then made portable

**Depends on Thread E.**

**Origin.** This repo is the declared source of truth for the estate's skills
and there is no `skills/` in the tree — so a task force branch has nothing to
diff against and a merge has nowhere to land. `skills/dtr/` is the only one
present. 0057 rules the ownership and the portability; this thread is its first
application.

**Preconditions.** 0057 read. The five skills configured today:
`brief-scribe`, `commit-scribe`, `consultant-docs`, `decision-scribe`,
`docs-archivist`. Thread E has landed, or you know it has not.

**Source of truth for the copy.** The configured copies. The mirror's
`…\WizForgeAnalytics\skills\<name>\SKILL.md` were verified byte-identical to
the configured set on 2026-08-26 **once line endings were normalised**, so they
are a valid fallback — but normalise before you compare, and record which source
you used.

**Deliverable.** `skills/<name>/SKILL.md` for five skills, in **two commits**.

**Tasks.**

1. **Commit one — byte-identical.** Copy the five in unchanged, defects
   included. This is the known baseline the branch model needs; a repository
   recording what we *wish* loaded is not a currency check. Record a `sha256`
   per file in the commit body.
2. **Commit two — portability**, per 0057 clauses 3-6:
   - a skill declares the **kind** of authority it needs, never where it lives;
   - resolution at run time: this repo's `docs/` → the estate source repo →
     **stop**;
   - a skill that cannot read its authority **stops**; it never works from its
     own text, from memory, or from a reconstruction;
   - **no estate-specific fact in a skill's prose.**
3. **Fix specifically.** `commit-scribe` says *"for L5GN-Tools"* and
   `docs-archivist` says *"in L5GN-Tools"* in their own descriptions.
   `consultant-docs` points at `docs/Consultants/` — a class the work rig
   **retired** (`wfa-0025` clause 6) and which does not exist here.
4. **Use `skills/dtr/SKILL.md` as the reference shape.** It resolves rather than
   names, and stops rather than falling back.

**Out of scope.** `orientation` and `round-closer`. Both were authored on the
work rig, both bind to MCF paths or MCF facts, and both want their own round
under the branch model. Named here so their absence is a decision.

**Stop conditions.**
- The configured copy and the mirror copy differ after normalising → stop; that
  is a real divergence and wants recording, not resolving.
- A skill's authority does not exist in this repo after Thread E → **leave it
  stopping.** That is clause 5 working. Do not invent a convention to satisfy it.
- Commit one and commit two would land together → stop and split them.

**Acceptance.**
- `[G]` Five skills tracked under `skills/`.
- `[G]` Commit one's tree is byte-identical to the source; the `sha256` list in
  its body reproduces.
- `[G]` No skill names a repo, a path or an estate fact in its prose. Grep and
  show the result.
- `[G]` Each skill states its stop-on-unreadable-authority rule.
- `[H]` Would a task force branching one of these be able to tailor it without
  editing anything that should have been a convention?
- `[H]` Does `consultant-docs` now fail honestly rather than half-resolving?

**Report.** Which source you copied from, the `sha256` list, what each skill's
authority now resolves to, and which skills stop today and why.

---

# Thread B — the decisions map generator

**Independent.**

**Origin.** `ARCHITECTURE.md` has a generated twin; `DECISIONS.md` does not.
Three DTR stages want the view it would produce, and the citation graph that
produces it already exists in every entry's `Builds on:` field and is read by
nothing.

**Preconditions.** 0030 (shape is generated, rationale is authored) read.
`docs/DECISIONS.md` holds 57 entries.

**Deliverable.** `python run.py decisions-map` writing `docs/_decisions_map.md`.

**Tasks.**

1. Parse `## NNNN — <title>` headings and each entry's `**Builds on:**` segment
   — the citations run from that marker to `**Source:**` or `**Context.**`.
   Extract four-digit numbers; exclude self-citations.
2. Emit four views:
   - **Threads** — chains followed through citations. The deepest today is
     `0010 → 0025 → 0027 → 0033 → 0037/0040 → 0042/0044 → 0050-0053`.
   - **Spine** — most-cited. Today `0025` (×10), then `0007`, `0013`, `0032`,
     `0033`, `0040` (×5 each).
   - **Orphans** — entries citing nothing. Today **23 of 57**, including `0029`,
     `0030`, `0036` and `0043`, all load-bearing and unreachable by citation.
   - **Status** — counts and a list of what is `proposed`.
3. Header states it is generated, names the command, and says never hand-edit.

**Out of scope.** Cross-repo citations (`wfa-`, `sfds-`). Editing any entry.
Wiring into `CLAUDE.md` — Wave 2.

**Stop conditions.**
- A duplicate entry number → stop and report. Unrecoverable in an append-only
  log, and the generator must not paper over it.
- A cited number that does not exist → report it in the output as a dangling
  citation; do not drop it silently.

**Acceptance.**
- `[G]` Running twice against an unchanged log produces a byte-identical file.
- `[G]` Counts reproduce the four numbers above.
- `[G]` The output contains **no prose from any entry** beyond its title.
- `[H]` Does the orphan list read as a finding rather than as noise?

**Do not, and this is the one that matters.** **Never summarise, condense or
paraphrase an entry.** Link to the falsifiers; never restate them. The "What
would show this wrong" sections and the uncomfortable half of Consequences are
the first things a condensing pass eats, and they are the reason the log is
worth keeping.

**Report.** The command, the four counts, and any dangling citations found.

---

# Thread C — `CONVENTION_docs.md`

**Independent.**

**Origin.** This repo's doc lifecycle rules live in `docs/README.md` §3 — a
filing document doing a convention's job, and the authority `docs-archivist`
cites. It is the one row of the workflow map sitting in the wrong column.

**Preconditions.** `docs/README.md` read in full. The work rig's
`CONVENTION_docs.md` is readable in the mirror at
`…\WizForgeAnalytics\docs\CONVENTION_docs.md` — read that file only.

**Deliverable.** `docs/CONVENTION_docs.md`, with `docs/README.md` reduced to a
pointer.

**Tasks.**

1. Promote `docs/README.md` §2 (doc classes) and §3 (the archiving convention,
   the stamps, why the auditor stops at the archive door).
2. Borrow, with the adoption named in the header:
   - their **§0** — *"a document earns its place by holding something that
     cannot be derived"* — which states 0030 better than we state it;
   - their **§2 class table**, adjusted to the prefixes actually in use here;
   - their **§2a entire** — a skill is the procedure, the file is the authority,
     and a skill that restates the spec is a second copy of the rule. This is
     0057 clauses 3-6 with a citation behind it;
   - their **§6** — no status boards, no handoff or priming documents.
3. **Decide and record:** whether `docs/investigation/` survives. The work rig
   retired theirs in favour of `context/` at the repo root for inbound material,
   gitignored. State the decision either way; do not migrate anything.

**Out of scope.** Moving or renaming any existing document. Amending
`docs-archivist` — Thread A. Creating `context/`.

**Stop conditions.**
- Adopting their class table would require renaming existing files → stop.
  Record which files and why; the rename is its own round.
- You cannot tell whether a rule in `docs/README.md` is a rule or a description
  → leave it in the README and say so.

**Acceptance.**
- `[G]` `docs-archivist` can cite a `CONVENTION_` file rather than a README
  section.
- `[G]` Every prefix in the class table matches a file that actually exists in
  `docs/`, or is marked as unused.
- `[G]` `docs/README.md` no longer holds a rule that exists nowhere else.
- `[H]` Is the `docs/investigation/` decision one you would defend in a month?

**Report.** What was promoted, what was borrowed, the investigation decision and
its reasoning, and any rename the class table would demand.

---

# Thread D — `CONVENTION_gitignore.md`

**Independent.**

**Origin.** The work rig's equivalent ruling was accepted and **conformance was
1 of 9 by the end of the same day.** That is the strongest evidence either
estate has that a written rule decays without a reader. Having the same baseline
here makes the same measurement possible.

**Preconditions.** The current `.gitignore` read **via git, not via a file
read** — a sandbox mount served a byte-truncated `.gitignore` stably across
three consecutive reads on the work rig and sent a thread in circles. Their
`CONVENTION_gitignore.md` is in the mirror; read that file only.

**Deliverable.** `docs/CONVENTION_gitignore.md`, with the baseline block for
this repo.

**Tasks.**

1. Derive the baseline block from the current `.gitignore` — the rules true of
   any repo in this estate, with the two marker lines.
2. Carry across the mechanism, not their contents: the block first, nothing
   edited above the marker, repo-specific rules below it, and **exceptions
   expressed as a negation below the line** with a comment saying what it
   re-admits and why. Their worked example is worth reading; the ordering
   argument is the whole point.
3. Carry their reasoning on secrets: extensions and exact names only, and **not**
   `*secret*`-style substring patterns, which match anywhere in a path and would
   swallow a `CONVENTION_secrets.md` or a `token_parser.py`. State the cost they
   state: a file called `salesforce_credentials.txt` passes the baseline.
4. Record what this repo's `.gitignore` already carries that the baseline does
   not, and leave it below the line.

**Out of scope.** Editing `.gitignore`. Propagating to any other repo.
`git rm --cached` on anything already tracked.

**Stop conditions.**
- A proposed baseline rule would newly ignore a file git is already tracking →
  stop and name it. An ignore rule has no effect on a tracked file, and pretending
  otherwise is how a repo gets a rule it believes is working.
- The current `.gitignore` cannot be read through git → stop.

**Acceptance.**
- `[G]` Every rule in the block is verified with `git check-ignore -v` against a
  real path, and the output is quoted.
- `[G]` The document states that `check-ignore` is the only verification and a
  file read is not evidence.
- `[G]` Nothing in the block newly ignores a tracked file.
- `[H]` Would you be able to tell, in a month, whether this repo had drifted
  from the block?

**Report.** The block, the `check-ignore` output per rule, and what this repo
carries below the line.

---

## What Wave 1 does not close

Recorded so no thread reads its own scope as the whole job.

- **Nothing checks any convention any of these threads writes.** The conformance
  reader both estates say they want first is not in Wave 1.
- **Ratification still produces no artefact**, on either rig.
- **Observe still has nowhere to land** — a finding lives in a thread until
  someone decides it deserves a convention.
- **`architecture-scribe`, the build skill and the `CLAUDE.md` refresh** are
  Wave 2 and depend on A and C.
