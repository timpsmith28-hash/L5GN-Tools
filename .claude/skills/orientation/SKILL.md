---
name: orientation
description: Run the estate's orientation round in one repo — read the program's PROMPT_orientation_round.md and follow it, supplying only REPO and CARD. Use when asked to orientate a repo, run an orientation round, measure a repo against the conventions, or produce the first card for a project that has none. Points at the prompt file; carries no copy of it.
---

# orientation

> **DOES NOT RUN IN `L5GN-Tools`. Published here for currency, not for use.**
>
> This skill is a pointer, and **neither thing it points at exists in this
> estate**: `PROMPT_orientation_round.md` and `REGISTRY_projects.md` are work-rig
> artefacts behind the wall (**0051**). On this rig the skill's own §1 rule
> applies — *"if the file cannot be read, stop and say so"* — so it is correctly
> inert here rather than wrong. It is published so that **0057** clause 1 has a
> source of truth to point at, and so the divergence that hid it is diffable.
>
> **Two defects were corrected on arrival; a third is left open because it is a
> decision, not a typo.**
>
> **Corrected — the citations were foreign and bare.** The original cited
> *"0019 clauses 1 and 4"* and *"0011 clause 3"* with no repo. **0043** requires a
> ruling from another repo to carry its repo at every mention, and the reason is
> live here: `L5GN-Tools`'s own **0011** is *"existing `project_link` values are
> reset, not trusted"* and its **0019** is *"any LLM- or query-exposed DB path is
> structurally read-only"*. Neither is about pointers or card numbering. Read on
> this rig, those citations resolved silently to the wrong rulings — a skill
> working from authority it had misidentified, which is the failure **0052** ends
> with *stops rather than working from its own text*. Prefixed `wfa-` below.
> **The prefix is inferred** from the work rig's own usage in
> `Work_Bridge/to-personal/2026-08-27_REPLY_harness_frame.md` and should be
> confirmed before anyone relies on it.
>
> **Corrected — the absolute paths.** They named `C:\Users\tim.smith\...`, a home
> directory on another machine. The relative forms the skill already carried are
> promoted to primary.
>
> **Open, and the reason this is a round rather than a copy:** under **0057** a
> skill has one source of truth and a task force *branches* rather than copies.
> A skill published by the personal estate whose authority is a work-estate file
> either breaches **0051** or is permanently inert on the rig that publishes it.
> Which of those it should be is `CLAUDE.md`'s named debt and **0057** clause 2's
> reserved round. **Not settled here.**

**This skill is a pointer. The prompt file is the authority** (`wfa-0019`
clauses 1 and 4). It exists only so the round can be started by name instead of
by paste.

It deliberately contains no description of the round — not the measurement, not
the outputs, not the stop conditions. A summary here would be a second copy of
the spec, drifting from the first, which is the whole failure `wfa-0019` was
written to prevent. If you want to know what the round does, read the file.

**Self-test:** if this file has grown past one screen, or contains anything a
reader could mistake for the round's contents, it has drifted and needs cutting
back. That is `wfa-0019` clause 4's falsifier, written where it will be seen.
*(The block above is provenance, not round contents, and is exempt — but it is
the only exemption, and a second one would mean the self-test has stopped
working.)*

## Procedure

### 1. Read the prompt

```
<program repo>/docs/prompts/PROMPT_orientation_round.md
```

It lives in the **program** repo, not in the repo being oriented. From a project
working tree that is `..\WizForgeAnalytics\docs\prompts\`; from `sf-data-service`
it is `..\docs\prompts\`. **From `L5GN-Tools` it is nowhere** — see the header.

Read the whole file before writing anything — it says so itself, and its §2 is
the rule that stops the round's most common false finding.

**If the file cannot be read, stop and say so.** Do not run the round from this
skill's description, from memory of a previous thread, or from a reconstruction.
Ask the operator to paste the file instead.

### 2. Establish `REPO` and `CARD`

`REPO` comes from the operator. `CARD` comes from the **next card** column of

```
<program repo>/docs/REGISTRY_projects.md
```

which `wfa-0011` clause 3 makes authoritative for numbering. Read the notes
beneath that table rather than the cell alone — two repos' numbers are
conditional on a migration round that has not run, and the table says which value
applies until it does.

If the registry's row for `REPO` looks wrong in a way that changes `CARD`, stop
and ask. Do not pick a number.

### 3. Follow the prompt

Its sections are the procedure. Do not restate them back to the operator before
starting; do not ask for context the prompt says you should be reading out of the
repo.

## Anti-patterns

- Growing a summary of the round into this file.
- Proceeding when the prompt file is unreadable.
- Taking `CARD` from a thread's memory, a previous round, or arithmetic on the
  filenames in `docs/` instead of from the registry.
- Writing to `REGISTRY_projects.md`. The prompt forbids it and says why.
- Improving the round by editing this file. Improvements go in the prompt, which
  is in git and reviewable; this file is not where the round is specified.
- **Citing a foreign ruling without its repo** (**0043**). The bare `0019` and
  `0011` this file carried until 2026-08-28 both resolved to real and unrelated
  rulings in `L5GN-Tools`.
