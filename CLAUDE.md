# L5GN-Tools — map

A table of contents, not a manual. Nothing is decided here; everything points
somewhere that decides it. **If this file and the thing it points at disagree,
the thing it points at wins and this file is the defect.**

This repo is the **source of truth for the estate's skills and conventions**. A
task force may branch and tailor, and offers changes back as a merge — so a
divergence is a branch that can be diffed, never an untracked copy that cannot.

---

## Read first, in this order

1. **`docs/INTENT.md`** — what this is for. §5 is the standing constraints every
   other document assumes.
2. **`docs/ARCHITECTURE.md`** — the shape, authored. §5 is key decisions and why.
3. **`docs/_decisions_map.md`** — the rule set, generated. Threads, spine,
   orphans, and what is still proposed.
4. **The convention for whatever you are about to touch** (below).

## Where things live

| | |
|---|---|
| Rulings | `docs/DECISIONS.md` — append-only; clause numbers frozen once accepted |
| Conventions | `docs/CONVENTION_*.md` — one per subject |
| Rounds | `docs/COWORK_BRIEF_*.md` → `COWORK_REPORT_*.md` → `UAT_*.md` → `UAT_*_results.md` |
| Procedures | `docs/RUNBOOK_*.md` |
| Outside material | `docs/Consultants/` *(does not exist yet — see Debts)* |
| Raw exchanges | `docs/investigation/` |
| Retired | `docs/archive/` |
| Configuration | `config/` — start at `config/README.md`, then `CONVENTION_config.md` |
| Generated data | `data/` — gitignored wholesale; never source |
| Skills | `.claude/skills/` — tracked **and** the load path; one directory, deliberately (**0057** cl.1) |
| Correspondence | `../WizForge/Work_Bridge` — its own repo, its own README |

## Authored and generated pairs

An authored file carries rationale; a generated file carries shape (**0030**).
Never hand-edit a generated file. Regenerate it **in the same commit as the
change that caused it**, never in a tidy-up afterwards
(`CONVENTION_commits.md` §6).

| authored | generated | command |
|---|---|---|
| `docs/ARCHITECTURE.md` | `docs/_architecture_shape.md` | `python run.py render-architecture` |
| `docs/DECISIONS.md` | `docs/_decisions_map.md` | `python run.py decisions-map` |

`docs/INTENT.md` has **no generated twin, deliberately** — purpose is not
derivable from the tree, and nobody should try to build one.

## Conventions, and the skills that cite them

A convention owns a rule; a skill scripts a procedure and cites it (**0052**).
**A skill never houses a rule**, and a skill that cannot read its convention
stops rather than working from its own text.

| subject | convention | skill |
|---|---|---|
| commits | `CONVENTION_commits.md` | `commit-scribe` |
| `.gitignore` baseline | `CONVENTION_gitignore.md` | — |
| configuration | `CONVENTION_config.md` | — |
| project registry | `CONVENTION_project_registry.md` | — |
| conversation map | `CONVENTION_conversation_map.md` | — |
| design thread restart | `CONVENTION_design_thread_restart.md` | `dtr` |
| decisions | `CONVENTION_decisions.md` | `decision-scribe` |
| briefs and walk-sheets | `CONVENTION_briefs.md` | `brief-scribe` |
| doc lifecycle and archiving | `CONVENTION_docs.md` | `docs-archivist` |
| outside material | *(none — and the class it names is retired; see Debts)* | `consultant-docs` |
| closing a round | *(none here — see Debts)* | `round-closer` |
| orientating a repo | *(prompt file, not a convention)* | `orientation` |

## Commands you will actually need

```
python run.py config          # this machine, as resolved -- run before assuming anything
python run.py build           # rebuild data/estate.json
python verify.py              # every auditor and tester; this is the gate
python run.py render-architecture   # rebuilds the census JSON *and* the shape doc, one scan
python run.py decisions-map         # docs/DECISIONS.md -> docs/_decisions_map.md
python run.py pin bump              # only on the host that authors the artefact (0053 cl.5)
```

`.githooks/pre-commit` runs `verify.py`. The commit itself stays a human act
(**0028** clause 3).

## Environment hazards

These bind every thread, not only the one that discovered them (**0052**
clause 4). They are rules rather than pointers, and they are here because the
environment is what they are about.

- **Never run plain git against a mounted Windows repo from a sandbox.** For
  anything about what git holds, ask git, on Windows.
- **Normalise line endings before concluding anything changed** — but the
  hazard is at this repo's boundaries, not inside it. `.gitattributes` sets
  `* text=auto eol=lf`, so the tree here is LF throughout. Measured 2026-08-26:
  five skills that looked "adapted" were byte-identical to their synced copies
  once normalised, and `Work_Bridge` — which carries no such `.gitattributes` —
  reported a 757-line phantom rewrite of three unchanged files.
- **A sandbox mount serves stale, byte-truncated content deterministically and
  without error.** A second read confirms a false answer rather than catching
  it. Hash on Windows.
- **`config/local.json` is untracked and is written at runtime** by
  `governor.set_profile` and `curator_control.set_curator_model`. Never
  overwrite it wholesale from another rig — that silently destroys machine-side
  state on both ends.
- **`git bundle verify` needs a repository context.** From a plain directory it
  fails with *"need a repository to verify a bundle"*; `git init` a scratch repo
  and verify from there.
- **Commit with `git commit -F <file>`**, never a multi-line `-m`
  (`CONVENTION_commits.md` §2). Every corrupted message in the log came from
  doing otherwise on Windows.

## Debts, named rather than hidden

Listed here because a map that shows only what exists teaches a reader that
nothing is missing.

- **`consultant-docs` has no authority it can reach.** It points at
  `docs/Consultants/`, which does not exist here and which the work rig has
  **retired** as a class. The skill is left stopping rather than pointed at a
  substitute; naming what replaces it is a round of its own.
- **`round-closer` has no convention here**, and asserts an estate fact
  (*"no MCF repo has a gate"*) that is false in this repo.
- **`orientation` binds to absolute paths on another machine.** Authored on the
  work rig; wants its own round under the branch model (**0057** cl.2).
- **Ratification produces no artefact.** A status line changes and nothing
  records that the re-read happened, when, or by whom. Found independently on
  both rigs.
- **Nothing checks any convention in this file.** No auditor reads them; the
  conformance reader both estates want first does not exist.

## What this file may not become

Rules that live nowhere else, rationale, or the only copy of anything — the
environment hazards above excepted, and those exist here because 0052 clause 4
says an environment rule belongs to the environment. **The moment a reader needs
this file to know *why*, it has stopped being a map.**

**Self-test:** if this file has grown past two screens, or if deleting it would
lose information rather than convenience, it has drifted and needs cutting back.
