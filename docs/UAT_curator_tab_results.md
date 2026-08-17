<!-- uat: commit=174e57e dirty=true host=LucasGoonPC walked=2026-08-17 -->

# UAT results — the Knowledge Curator tab (`COWORK_BRIEF_curator_tab.md`)

Sheet: `docs/UAT_curator_tab.md`. Pair:
`docs/COWORK_BRIEF_curator_tab.md` + `docs/COWORK_REPORT_curator_tab.md`.

**Walked:** 2026-08-17 on `LucasGoonPC`, against `174e57e`.
`dirty=true` — Grand Walk results logs were uncommitted at walk time; no code
was.

**Gate:** `python verify.py` GREEN, and green via the pre-commit hook across
`13fef34..174e57e`.

---

## This is a partial walk, and the board will overstate it

**2 of the sheet's 6 open items are walked. 4 are deferred to `10280L`** and
recorded below as deferred with a named cause — not as passed, and not as
untouched.

The docs board has no representation for this state: a results log existing
moves the card to *Walked* wholesale (see `docs/UAT_ui_witness_results.md`
finding 5, and the proposed `walking` lane). **A reader of the board will see
`curator_tab` as Walked. This document is the correction to that.**

The four deferred items share one cause: this is the gaming rig. Its declared
estate is `personal`, it holds no MCF corpus, no curated sheet and no work
Cowork transcript store, and the Curator pane correctly renders a stated
absence rather than data. **Nothing about them can be answered here, and
answering them here would be inventing evidence.**

---

## Walked

- [x] **1.** `[H]` **0033 is ratified and committed before any code lands.**
  **Passed.** `e987d1a` — *"docs(decisions): 0033 ratified — path allowlist
  replaces docs/-only staging clause"*, dated **2026-08-08**. `DECISIONS.md`
  records 0033 with **Status: accepted**, amending 0028 without superseding it.
  The curator-tab code lands after that date.

  The sheet keeps this `[H]` deliberately, noting it is machine-checkable but
  worth the walker's own eyes because it is the round's precondition. Walked on
  that basis: the ruling exists, is accepted, and predates the code.

- [x] **21.** `[H]` **Does anything on the surface read as a verdict?**
  **Passed.** Tim, on the rendered surface: *"no it does not."*

  This is the item the round most needed a human for. The build's own check —
  `grep` for `"passed"`/`"clean"`/`"complete"`/`✓` across the round's code —
  returned nothing, but that only proves the *vocabulary* is absent. Whether a
  rendered page **reads** as a verdict (a green `.ok` class on a successful
  stage outcome, say) is a judgement no grep can make, which is why the sheet
  held it at `[H]` rather than downgrading it once the grep came back clean.

  Recorded with its limit stated: this was walked against the Curator pane in
  its **absent** state on this rig, where it renders a stated absence rather
  than stage data. **A populated Curator surface has not been judged for verdict
  vocabulary.** Item 19 covers that and is deferred.

## Deferred to `10280L` — named, not guessed

- [ ] **5.** `[H]` **Ratify the map.** Read the highlighted evidence, not the
  answers. — **Deferred.** Needs a real curated sheet and a reachable work
  Cowork transcript store. Neither exists on this rig.

- [ ] **19.** `[H]` **Is run health impossible to miss?** Look at the tab as if
  you had not built it: could you mistake a thin run for a clean one? —
  **Deferred.** Needs a real run rendered. The pane is in its stated-absence
  state here, so there is no run health to fail to notice.

- [ ] **20.** `[H]` **Does the evidence display actually help you ratify?** —
  **Deferred.** Needs real evidence text to read. The sheet's own bar is the
  right one and cannot be met with synthetic data: *"If you find yourself
  trusting the pass label instead of reading the spans, the display has failed
  at its one job."* Trusting a label is only tempting when the spans are real.

- [ ] **22.** `[H]` **Is the tab worth it over the markdown report?** Answered
  plainly, including if the answer is "only for K0." — **Deferred.** Needs real
  use, not a demonstration.

---

## A note on when these become walkable

All four are currently gated by this machine's estate, and **that gate is
itself under review.** Draft DECISIONS 0044 would settle the question 0039 left
open (whether `data/knowledge_curator/` sits inside the deposit contract) and
correct `curator_estate_gap`, which today enforces 0032's MCF-only rule that
0039 amended.

If 0044 is ratified and the Curator runs against this repository's own
conversations, **items 19, 20 and 22 become answerable on this rig** — with
better ground truth than MCF offers, because the material being curated is in
`DECISIONS.md` where a claim can be checked rather than remembered.

Item 5 stays a work-rig item: it ratifies the *MCF* map specifically.

## Carried findings

1. **The Curator's estate gate implements a superseded ruling.** `app.py`'s
   `curator_estate_gap` gates on *"declared estate is not work/MCF"*, reason
   string `not_work_mcf_estate`, citing **0032** — the clause 0039 amended on
   2026-08-11, before this round's code was written. `curator_data
   .RATIFIED_MAP_PATH` is likewise hardcoded to
   `config/mcf_conversation_map.tsv`, the fixed estate name 0039 clause 1
   forbids and the per-source pattern 0040 clause 2 replaced.

   Found while walking item 21 — the absence message the pane renders is
   correct about *what* it does and cites the wrong entry for *why*.
   Addressed by draft 0044.

2. **Item 21 was walked against an absent pane.** Recorded above rather than
   left implicit, so a later reader does not treat it as covering the populated
   surface. Item 19 is where that gets tested.
