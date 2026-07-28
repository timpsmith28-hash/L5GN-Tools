# Cowork brief — the docs board: the lifecycle you already run, made visible

**Origin:** design thread, 2026-07-28. Slice 1 of two; the UAT sidebar
(`COWORK_BRIEF_uat_sidebar.md`) is slice 2 and lands after this one is walked.
**Depends on:** DECISIONS **0027** (local surface reads at render time) and
**0028**, drafted below — the working-tree write.
**Deliverable:** `docs/` rendered as a board, with actions that are a function of
each card's column.

`docs/README.md` §2/§3 already defines a lifecycle: brief → report → walk-sheet →
results log → archived. Every transition is derivable **mechanically** from
filenames and existence. Nothing new needs to be recorded; it needs to be
*rendered*.

**Built from the live repo on 2026-07-28**, this is what the board shows today:

| column | cards |
|---|---|
| **In flight** (brief, no report) | `local_deck_docs_and_time`, `local_deck_evidence`, `local_deck_overlap`, `toolkit_self_scan`, this one |
| **Built, not walked** | `estate_restructure` (0 done / 11 open), `file_census` (36/19), `intent_evidence` (0/85), `scanner_bugfixes` (0/9) |
| **Walked** | `command_deck_proto` (10/5), `doc_provenance_coverage` (0/19), `repo_tier_producers` (0/17) |
| **Archived** | 12 pairs |

**Computing that already found something.** `doc_provenance_coverage` and
`repo_tier_producers` both read *0 done* despite being walked with stamped results
logs — their checkboxes were never ticked, because the evidence went into the
results log instead. `command_deck_proto` reads 10/5 because its sheet *was*
ticked. The convention is applied inconsistently and nobody noticed until
something counted it. **Expect the board's first job to be exposing that**, and do
not "fix" the affected sheets — report the inconsistency.

---

## Precondition ▸ DECISIONS 0028 must be ratified before any code

0027 authorises a local surface to **read** files at render time. This slice
**modifies the working tree** — `git mv` plus a prepended stamp. Nothing currently
authorises that, and it is a bigger step than reading: 0007 and 0024 confined
writes to the vault's own columns and tables.

**Draft this to Tim, get it ratified and committed, then build.** If he rules
against it, Task 4 falls away and the board ships read-only — still worth having.

> ## 0028 — A local surface may stage a working-tree change; it may never commit
>
> **Date:** 2026-07-28 · **Status:** proposed · **Builds on:** 0007, 0024
> (write surfaces are narrow and column-scoped), 0025 (loopback), 0027
> (render-time reads) · **Source:** design thread
>
> **Context.** Every write surface so far touches the vault and nothing else. The
> docs board's one genuine action — archiving a completed pair — is a change to
> the **source tree**: `git mv` and a prepended stamp. The `docs-archivist` skill
> already performs exactly this, by hand, under a hard rule: *never move a file
> until Tim has ratified that specific move*, and leave everything **staged,
> uncommitted**.
>
> **Decision.** A local-only surface (loopback, own estate, per 0025/0027) may
> **stage** a working-tree change, subject to all of:
> 1. the change is confined to `docs/` and is a `git mv` into `docs/archive/`
>    plus a stamp prepended above the title — **never a body edit**;
> 2. it is performed only on a per-pair ratification given in that session, never
>    in bulk and never inferred from a green gate;
> 3. **it never runs `git commit`.** The human reviews `git diff --staged` and
>    commits in a terminal. The gate runs on that commit, as it does today.
>
> **Consequences.** The mechanical layer is automated; the judgement layer is not.
> The pre-commit gate remains the last word, because a commit is still a human
> act. A surface that can stage but not commit cannot produce an unreviewed
> change — the worst case is a working tree the operator must clean up, not a
> laundered history.

---

## Working rules

- Stdlib-only for logic; the board is more views in `chronicler/review`, not a
  second service. Gate GREEN before commit.
- **The board is derived, never stored.** No board state file, no column
  assignments on disk. Recomputed from `docs/` on every load.
- Read-only until Task 4, and Task 4 stages only.
- The `docs-archivist` skill is the authority on archiving mechanics
  (`docs/README.md` §3 is the authority on the convention). **Where this brief and
  the skill disagree, the skill wins and this brief is wrong.**

---

## Task 1 ▸ derive the board

A testable function producing the card list from `docs/` and `docs/archive/`:

- **Pair up** `COWORK_BRIEF_<x>` with `COWORK_REPORT_<x>`, `UAT_<x>`, `UAT_<x>_results`.
- **Column** from what exists: no report → *in flight*; report but no results log →
  *built, not walked*; results log → *walked*; present in `archive/` → *archived*.
- **Open items** by counting `- [ ]` against `- [x]` / `- [~]` in the walk-sheet.
- **Handle the card types that don't fit.** `UAT_work_rig_solo` is a walk-sheet
  and results log with **no brief** — a legitimate shape, not an error. So are
  investigations, runbooks and the trinity. Anything that isn't a pair is either
  its own card type or explicitly not on the board; decide and say which.
- Surface each doc's stamp state: `gate-frozen` marker, uat stamp fields.

**Do not invent a status the filesystem cannot support.** *Archivable* is not
derivable — it requires a human saying the UAT was walked (Task 3).

## Task 2 ▸ render, with actions by column

Actions are a function of column. Nothing else appears on a card.

- **In flight** → open the brief. Nothing else; the work is elsewhere.
- **Built, not walked** → open the walk-sheet; list the open items inline.
  *Slice 2 attaches "walk it" here.*
- **Walked** → show remaining open items, and a **"UAT ratified?"** control.
- **Archivable** (ratified) → **"Prepare archive"**.
- **Archived** → read-only; show the stamp.

Document bodies render per 0027 (render-time read, nothing persisted), reusing
slice 1's containment machinery if it has landed — **do not write a second path
resolver**.

## Task 3 ▸ ratification is an input, not an inference

The one thing no tool can derive. A per-pair control recording *Tim says the UAT
was walked*, which is what moves a card from *walked* to *archivable*.

**Where does that live?** It cannot be a file the board maintains — that is a
status board, and `docs/README.md` §5 retires those by class because they rot.
Options to weigh and rule on in the report: session-scoped (ratify, archive, done
— nothing persists); or recorded in the artefact that already asserts acceptance,
the results log's uat stamp. **Recommend session-scoped**, because ratification's
only purpose is to authorise the very next action.

## Task 4 ▸ prepare and stage — the mechanics only

On an archivable card: a panel with the **`git mv` list** and a **pre-filled stamp
draft**, editable in the browser. **Stage** performs the moves and prepends the
edited stamp. Nothing is committed.

**Be honest in the UI about what the draft can and cannot contain.** The board can
generate the mechanical lines — date, disposition, pair status, file list, and a
successor path where one is derivable. It **cannot** generate the line that makes
a stamp worth writing:

> *"Stop trusting the mechanism… the report's drafted 0017 prescribes clearing
> project_link on 270 threads. None of that ran."*

That requires having read the body and knowing which later decisions overtook it,
and the skill is explicit that **a generic stamp is a failure**. So the draft
opens with the mechanical parts filled and the judgement lines **empty and
marked as required** — the board removes the typing, not the thinking. Refuse to
stage on an unedited draft.

Afterwards the UI states plainly: *staged, not committed — review `git diff
--staged` and commit.*

---

## Explicitly out of scope

- The UAT sidebar (slice 2) — but leave the *built, not walked* column's card
  detail as the obvious place it attaches.
- Committing, pushing, or any git operation beyond `mv` and the stamp write.
- Editing document bodies. Ever. The body is evidence.
- Boards for other projects' docs (MCF carries briefs too). Toolkit first.
- Any change to `docs/README.md`'s convention.

---

## UAT — acceptance checks (Tim walks these)

- **The board matches reality** — the four columns above, recomputed, with the
  same cards. Where it disagrees with this brief's table, the board is probably
  right and the brief is a day old; check which.
- **The checkbox inconsistency is visible**, not silently normalised.
- **Odd card types are handled** — `UAT_work_rig_solo` appears as itself or is
  deliberately absent, never as a broken pair.
- **Ratification is required.** A walked card offers no archive action until
  ratified, per pair.
- **Staging works and stops there.** Archive a real pair; `git status` shows the
  moves staged, the stamp prepended above the title, **the body untouched**, and
  **no commit**.
- **An unedited stamp cannot be staged.**
- **Nothing persists.** No board state file appears anywhere after use.
- `verify.py` GREEN after a staged archive — and if it goes red on a file that
  wasn't moved, that is a real finding, not something to archive around.

Mark each **ready to walk**. Results log needs a uat stamp naming the commit; do
not write a `gate=` field.

---

## Reporting

`docs/COWORK_REPORT_docs_board.md`, walk-sheet `docs/UAT_docs_board.md`, stamped
results after the walk. Record 0028's ratification, the derivation rules, how
non-pair documents were handled, the ratification-storage ruling, and the
checkbox-convention finding with the affected pairs named.
