# Restart — Monday 2026-08-31

**Host:** `LucasGoonPC` · **HEAD at open:** `f59ac18` · **Working tree:** clean,
3 commits ahead of `origin/main` · **Governed by:**
`CONVENTION_design_thread_restart.md` (§2 read, never recall; §5 one dated
artefact; §10 the closing check).

**This is not a report and not a ratification** (§1, §8). It establishes state.
Every figure below was read from the tree today. Where the prompt that opened
this thread carried a figure, that figure was re-derived rather than accepted,
and the corrections are marked **[was]**.

---

## Task 0 — what happened after `f8253c0`

Eight commits, none of which the opening prompt knew about. From the operator's
`git log` on Windows:

| commit | subject |
|---|---|
| `a17fda8` | `feat(skills)`: orientation published as pending, not as working |
| `d03cf35` | `docs(conductor)`: walk the Task 1 sheet — three G verified, one W open |
| `bd55428` | `docs(decisions)`: 0058 and 0059 appended as proposed |
| `d7a7336` | `docs(scanners)`: walk scanner_bugfixes — A2 fails on its own evidence |
| `0fe9ef5` | `docs(investigation)`: the fable prompt, pairing a response that had none |
| `6953df8` | `docs(convention)`: CONVENTION_skills as a stub, with counts stripped out |
| `5d3a03a` | `docs(convention)`: CONVENTION_project_process, stubbed and paired |
| `f59ac18` | `docs(convention)`: CONVENTION_project_process, stubbed and paired |

**Two pairs of commits in this log carry byte-identical subjects** — `5d3a03a`
/ `f59ac18` above, and `562a43d` / `386d764` further back. **Unresolved:** git
cannot be asked from this sandbox, so whether the second of each pair is an
amend-and-recommit, a genuine follow-up, or a duplicate is **unknown**. It is
named here rather than assumed benign. `CONVENTION_commits.md` has nothing to
say about it, which is itself the finding.

---

## Stage 1 — estate freshness

```
71.9h old (generated_at=2026-08-28T10:05:27+01:00) -- STALE
```

Read verbatim from `estate_freshness_check.py`; **not re-derived into a second
number** (§4). **Not rebuilt** — §8 forbids a silent rebuild, and rebuilding is
the operator's call. **Every figure in stages 2-4 below comes from `docs/` and
`config/` directly, not from `data/estate.json`**, so none of them inherits this
staleness. Any coverage figure would.

**Caveat on the reading itself:** it was taken in the Cowork sandbox against the
mounted repo, and `CLAUDE.md` records that a sandbox mount serves stale content
deterministically and without error. The line is reported as read. If it matters,
re-run it on Windows.

---

## Stages 2 and 3 — pending decisions, **by repo**

The program/project axis **does not exist** and was not substituted (§4, §8).
`docs/DECISIONS.md` is repo-scoped; 0012's program > project > repo axis is one
registry-id field away and that field has not been added. Reported by repo,
because that is what can be read.

- **59 entries. 57 accepted, 2 proposed.** Every entry carries a status.
- **Proposed: 0058 and 0059.** **[was]** the opening prompt said 0058 was
  *drafted and unappended*; `bd55428` appended both, and **0059 did not exist
  when the prompt was written**. Both are the first thing the prompt's own board
  figures got wrong in the operator's favour.
- **Both draft directories still exist** — `data/decision_drafts/` (0054-0056,
  0057) and `data/decisions_draft/` (0058, 0059). All four drafts are now
  appended, so all four are spent. The two-directory hazard the prompt names is
  **still live**, and now demonstrably so: 0058 and 0059 were written into the
  directory that is *not* the one the earlier drafts used.

**Behind the wall, named as unread** (§4, 0051): MCF's `wfa-` rulings and the
`sfds-` log are not readable from this rig. Stages 2-3 are **structurally
incomplete** about work-estate rulings, and this is a containment fact rather
than a defect.

---

## Stage 4 — board status

The **program/project board does not exist**. What follows is the **docs board**,
derived mechanically from filenames in `docs/`, reported as the docs board.

| | count |
|---|---|
| briefs | 31 |
| reports | 21 |
| walk-sheets | 24 |
| results logs | 14 |

- **Briefs with no report — 10:** `conversation_grain`, `curator_linking`,
  `dispatcher`, `distillation_extraction`, `hermetic_gate`, `ledger_migration`,
  `model_bench`, `staleness_feeds`, `validation_ratify`, `wizard_tiers`.
- **Reports with no results log — 8:** `estate_restructure`, `file_census`,
  `gap_closure`, `intent_evidence`, `knowledge_curator`,
  `local_deck_docs_and_time`, `project_wizard`, `quartermaster_frame`.
  **[was]** the prompt implied more; `d03cf35` and `d7a7336` walked `conductor`
  and `scanner_bugfixes` and closed two of them.
- **Walk-sheets with no results log — 10**, the eight above plus
  `conversation_grain` and `hermetic_gate`, whose sheets exist ahead of their
  reports.
- **No results log exists without its walk-sheet.**

**Conventions: 11**, not 9 **[was]**. `CONVENTION_project_process.md` and
`CONVENTION_skills.md` landed on 2026-08-29, both declared **STUB**, neither
enforced, and **neither carries 0057 clause 7's adoption header**. Five of
eleven carry one.

---

## Stage 5 — inbound

**`Work_Bridge/to-personal/` — 4 files**, all four cited by name somewhere in
`docs/`:

| file | cited in |
|---|---|
| `TOOLKIT_notes_2026-08-23.md` | `DECISIONS.md`, `COWORK_BRIEF_hermetic_gate.md`, `UAT_hermetic_gate.md`, `RUNBOOK_wizforge_mirror.md` |
| `2026-08-25_REPLY_harness_census.md` | `DECISIONS.md`, `CONVENTION_config.md` |
| `2026-08-26_NOTE_ecosystem_and_gates.md` | `DECISIONS.md` |
| `2026-08-27_REPLY_harness_frame.md` | `COWORK_BRIEF_conversation_grain.md`, `AGENDA_running_order_2026-08-28.md` |

**By §6.1's literal test all four are closed, and the test is too weak to trust
here.** §6.1 clause 2 says a pack is open until a dated artefact *cites it by
name* — but a citation records that something was **read**, not that it was
**answered**. `2026-08-27_REPLY_harness_frame.md` is closed on this test by
`COWORK_BRIEF_conversation_grain.md`, **a brief that has never been built**.
That is a pack answered by a promise. **§6.1 cannot distinguish "cited as read"
from "answered", and this is the first restart where the difference bites.**
Named, not resolved.

**Named as unread:**

- **Context packs** — built on the work rig, behind the wall, none has crossed.
  Not "none exist"; **unread**.
- **The live Chronicler vault** — outside the connected folders, unreachable
  from a Cowork sandbox. Reads as **unknown** (0050), never as fresh.
- **Email, chat, tickets** — not read today. Nothing entered the round from them.
- **`to-work/2026-08-27_REQUEST_harness_frame.md`** was answered by
  `to-personal/2026-08-27_REPLY_harness_frame.md`. Nothing is **owed outbound**
  on the bridge as far as this rig can see.

---

## Written down during the restart, because it existed nowhere tracked (§2 corollary)

**The countable test for whether something was a decision at all.** The
operator's framing, from 2026-08-28: *"if you can provide all of those points
around a decision it is barely an actual decision at that point — it becomes the
definition of the next logical step forward (a forced decision)."*

The response, and the part that is testable: **after assembly, count how many
options remain _defensible_.** One means it was a discovery, not a decision, and
should be **promoted** rather than put to a human. More than one means a genuine
trade-off, and the assembly made the judgement cheap rather than making it.

**The worked example is D9 on 2026-08-28** — fully assembled, four defensible
answers, and the operator chose one the assembling thread had ranked lower. That
is the case that shows the test is not vacuous.

Until now this lived in a conversation and in `data/restart_prompts/`, which is
**gitignored** — that is, nowhere. It belongs in `quartermaster_frame`'s walk at
Q2 and possibly in `AGENDA_running_order_2026-08-28.md` §2a, **which may not be
amended a fourth time**. It is written here so it exists in a tracked file, and
finding it a permanent home is a round, not a line in this note.

---

## Verified against code today, not taken from the prompt

- **Card B defect 1 — confirmed, and worse than documented.**
  `run_pipeline.has_registry()` is `_relink.REGISTRY_PATH.is_file()`; with
  `CHRONICLER_REGISTRY_PATH` unset, `db.resolve_registry_path()` returns
  `<github_root>/L5GN/.intel_sync/project_registry.json`, which does not exist
  here. The stage then prints **`[relink] skipped (no input available)`**
  (`run_pipeline.py:204`) — the same line every input-gated stage prints — and
  the chain finishes green. **Its own docstring claims the skip is "clean and
  loud". It is neither**; `relink.py:174-176`'s loud `SystemExit` is never
  reached. A docstring asserting a loudness the code does not implement is
  0048 clause 4's failure with a comment attached.
- **Card B defect 2 — confirmed.** `summarize_from_log` sums `ingestion_log`
  rows; `relink.py` contains **zero** references to `ingestion_log`. So a relink
  that linked forty threads prints **`[relink] ok — no new rows`**
  (`run_pipeline.py:232`). Not merely vacuous — **actively wrong in the
  reassuring direction.**
- **New, and adjacent to Card B: there are two registry resolvers and they
  disagree.** `chronicler/pipeline/db.py:52` has **two** steps (env, then the
  derived path) and documents having deliberately no repo fallback.
  `chronicler/review/core.py:247` has **three** — env, the derived path, then
  `config/project_registry.json`. So the review endpoint validates against a
  registry the pipeline would have skipped over. Card B should scope this or
  say why not.
- **Card B's prerequisite is a live violation, not an ambiguity.** 0054 clause 6
  is **accepted** and says `authors` "is estate policy and lives in the tracked
  file only". `authors` is present in **both** `config/machines.json` (tracked)
  **and** `config/local.json` (untracked), and `run.py:900` documents the
  untracked one as where it lives. **The code and an accepted clause say opposite
  things, and nothing checks it.**
- **0056 gap 1 — confirmed.** `config/personal_conversation_map.tsv` exists
  (695 bytes) with **no `.sha256`**. `auditors/auditor_conversation_map_pin.py`
  binds `ARTEFACT`/`PIN_FILE` to `config/mcf_conversation_map.tsv` at module
  level and **structurally cannot see the second map**. The gate is green over a
  live violation of an accepted ruling.

---

## Could not be read

- Git history beyond the log the operator pasted — **no git from this sandbox**.
  The duplicate-subject commits stay unresolved.
- The **live Chronicler vault** — unreachable; unknown, never fresh.
- **Work-estate rulings** (`wfa-`, `sfds-`) and **context packs** — behind the
  wall.
- **`.claude/`** is write-protected from here; any skill change this round must
  be written to outputs and copied in by hand.

---

## The agenda for the round that follows

**Settle 0054 clause 6 against the code, then build Card B** — make `relink`'s
skip loud and its success line answer for what relink actually did. Nothing
built anywhere else moves the coverage figure until it lands.
