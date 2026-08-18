<!-- gate-frozen: commit=69d1112 -->

> **ARCHIVED** 2026-08-17 · completed pair (walk-sheet) · Results:
> `archive/UAT_ui_witness_results.md`
> Superseded by nothing. Original purpose: the 19 acceptance checks for the
> witness layer, marked ready-to-walk and never ticked in place.
> This sheet reads 0 done because the walk was recorded in the results log
> rather than against the sheet — a known convention split the docs board flags,
> **not untouched work**. **Item C3's instruction is stale**: it names
> `chronicler/review/static/index.html`'s `uatItemHtml`, which the `unified_app`
> round moved to `chronicler/review/static/panes/uat.js`. This sheet is
> `gate-frozen: commit=69d1112`, which predates that move.

# UAT walk-sheet — the third check layer: rendered state, deterministically

Pair: `docs/COWORK_BRIEF_ui_witness.md` + `docs/COWORK_REPORT_ui_witness.md`.

**Built:** 2026-08-03, working tree dirty. **Gate at build time:**
`python verify.py` → **GREEN**, 6 auditors + 55 testers.
**Nothing committed** — walk against the working tree.

Every check below is **ready to walk**. None is passed — only Tim walking it
makes it that.

Results go in `docs/UAT_ui_witness_results.md` with a `uat` stamp naming the
commit. **Do not write a `gate=` field.**

Before walking C6/C7, run the witness suite once on a machine with
Playwright's Chromium installed (`python -m playwright install chromium`,
then `python -m tests.witness.run_witness uat_sidebar`) — it was not run
end-to-end in the build sandbox (network policy blocks the browser
download); see COWORK_REPORT_ui_witness.md's Verification section.

---

## A — the assignment rule and the counts

- [ ] **A1.** The assignment rule places every item on
      `docs/UAT_local_deck_docs_and_time.md` and `docs/UAT_uat_sidebar.md`
      without argument, and the counts (18 gate / 40 witness / 2 human / 1
      unplaceable) are reported in `COWORK_REPORT_ui_witness.md` Task 1.
- [ ] **A2.** Both sheets render their `[G]`/`[W]`/`[H]` markers correctly —
      open each in the UAT sidebar tab and confirm the markers do not break
      item parsing (ids, text, sheet notes all still show).

## B — a mis-marked item shows up as a finding

- [ ] **B1.** On a copy of a marked sheet, mis-mark a `[G]` item as `[W]` (or
      vice versa) and confirm the sidebar still renders it — the marker is
      read, not validated against anything, so a wrong marker is silent at
      parse time.
- [ ] **B2.** Give that item a verdict and emit. In the emitted results log,
      confirm a `[G]`/`[W]` item with **no matching witness observation**
      prints `[no witness observation] not present in the cited witness
      artefact for this item id` inline — this is the finding surfacing, per
      the report's Task 2 note. It does not sit quietly as if walked.

## C — the witness suite

- [ ] **C1.** `python -m tests.witness.run_witness uat_sidebar` runs and
      writes `data/witness/uat_sidebar.json` with `outcome` values only from
      `matched`/`diverged`/`error` — never `passed`, `ok`, or `result`
      anywhere in the file.
- [ ] **C2.** Run it twice with nothing changed. Both runs report the same
      outcomes for every item id.
- [ ] **C3.** **Break the UI deliberately** — remove the refusal message
      element (`.verr`) from `chronicler/review/static/index.html`'s
      `uatItemHtml`, or comment out where it's populated in `uatEmit` — and
      re-run the suite. Confirm `B3`/`B4` report `outcome: "diverged"` naming
      the missing message, and that nothing in the output or this suite's
      code claims the underlying code is broken (only that the surface
      didn't render what was expected). Restore afterwards.
- [ ] **C4.** `python verify.py` is GREEN and unchanged in runtime; confirm
      by inspection that neither `AUDITORS` nor `TESTERS` in `verify.py`
      names anything under `tests.witness`, and that no module `verify.py`
      imports (transitively) imports `tests.witness` either.
- [ ] **C5.** Try to use a witness result to close a UAT item: open
      `docs/UAT_uat_sidebar.md` and confirm nothing in the sidebar's item
      view or emit flow reads `data/witness/*.json` to auto-tick, pre-fill,
      or suggest a verdict for any item. The only place a witness result is
      read is the results-log citation at emit time, after a human (or, for
      `[G]`/`[W]` items, nobody) already decided what's on the log.
- [ ] **C6.** *(needs a real Chromium — see the note above.)* Run the suite
      for real against the fixture and confirm all five observations
      (`B1`, `B3`, `B4`, `B6`, `B7`) come back `matched` on an unmodified
      checkout.
- [ ] **C7.** *(needs a real Chromium.)* Repeat C3 for real: remove the
      message element, re-run, confirm `B3`/`B4` come back `diverged` with a
      detail naming what was missing.

## D — the sidebar's own sheet is shorter

- [ ] **D1.** Re-open `docs/UAT_uat_sidebar.md` in the sidebar. Of its 18
      items, confirm 6 read `[G]` (gate — never walked here), 11 read `[W]`
      (witness-eligible), and only 1 (`B2`) reads `[H]` — the human queue for
      this sheet is now exactly one item.

## E — the results log splits by layer

- [ ] **E1.** Walk `UAT_uat_sidebar.md`'s one `[H]` item (B2) for real, and
      emit. Confirm the emitted log has a `## Machine-verified` section
      **above** a `## Human ruling` section, and that Human ruling contains
      only B2.
- [ ] **E2.** With `data/witness/uat_sidebar.json` present (from C1), confirm
      the Machine-verified section's citation line names the artefact path,
      fixture, commit and `ran_at` — as **visible body text**, not inside the
      `<!-- uat: ... -->` stamp comment at the top of the file.
- [ ] **E3.** **The citation re-derives.** Follow it to
      `data/witness/uat_sidebar.json`, note the `commit` and `fixture`
      fields, re-run the witness at that commit against that fixture, and
      confirm the same observations come back.
- [ ] **E4.** `auditor_uat_stamp` is unchanged and green — confirm by running
      `python verify.py` and checking the `[ OK ]` line for it, and by
      diffing `auditors/auditor_uat_stamp.py` against the pre-round commit
      (no changes).
- [ ] **E5.** **Delete `data/witness/uat_sidebar.json` and emit again** (any
      new entry, e.g. re-walk B2). Confirm the Machine-verified section now
      reads *"No witness artefact found at `data/witness/uat_sidebar.json`
      for this sheet"* — visibly, not a blank section that could be misread
      as "nothing to check."
- [ ] **E6.** `data/witness/` (after re-running C1) contains no file with a
      `passed`, `ok`, or `result` field anywhere in it —
      `grep -r '"passed"\|"ok"\|"result"' data/witness/` returns nothing.

## F — a legacy sheet is unaffected

- [ ] **F1.** Open a walk-sheet with no `[G]`/`[W]`/`[H]` markers at all
      (any sheet not touched this round) and emit a real verdict. Confirm
      the emitted log keeps its original flat-by-section shape — no
      Machine-verified/Human ruling split appears for a sheet nobody has
      marked.

---

## Findings

Anything that fails, surprises you, or reads wrong goes in the results log
with the check number.
