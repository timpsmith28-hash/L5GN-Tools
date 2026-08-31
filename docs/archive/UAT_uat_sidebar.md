<!-- gate-frozen: commit=69d1112 -->
> **ARCHIVED** 2026-08-31 · completed pair · pair `COWORK_BRIEF_uat_sidebar.md` + `COWORK_REPORT_uat_sidebar.md`, walked 2026-08-03
> Superseded by the sidebar being live, and by `CONVENTION_docs.md` §4's uat-stamp rules · Original purpose: slice 2 of two — give the *built, not walked* column a real action, so walking a sheet emits a stamped results log that advances the card itself.
> A ready-to-walk sheet, not a record. **Read the results log instead.**

# UAT walk-sheet — the UAT sidebar

**Brief:** `docs/COWORK_BRIEF_uat_sidebar.md`
**Report:** `docs/COWORK_REPORT_uat_sidebar.md`
**Built:** 2026-08-03, base commit `b9fae8d`, working tree dirty.
**Nothing committed** — walk against the working tree.
**Gate at build time:** `python verify.py` → **GREEN**, 6 auditors + 55 testers
(+1 `tester_uat_sidebar`).

**Depends on:** `docs/COWORK_BRIEF_docs_board.md` built and walked first
(`docs/UAT_docs_board_results.md`, walked 2026-08-01) — satisfied before this
slice started.

**The pleasing part, and the point of this sheet:** this slice's own walk is
done using the sidebar it built. Walking an item below means opening the
**UAT sidebar** tab, picking `uat_sidebar` as the stem, recording a verdict and
its evidence for the matching item id, and — once every item you can walk this
session has one — pressing **Emit results log**. That call writes
`docs/UAT_uat_sidebar_results.md`, staged (0028), and *that* file is the
acceptance artefact, not this sheet. **If it cannot walk itself, that is the
finding**, per the brief.

Start: `python run.py review --host 127.0.0.1`, open the **UAT sidebar** tab
(or click **Walk it** on this card from the **Docs board** tab — it opens the
sidebar with the stem pre-filled).

Mark each: `- [x]` passed · `- [~]` passed with a note · `- [ ]` not yet
walked. **The tool's own emitted results log is the evidence** for most of
these — write only a pointer here (which item id you recorded it against),
not a duplicate copy. Recording evidence only on this sheet, for an item whose
whole point is the emitted log, would reproduce the docs board's own finding
B1/B2 in the act of walking this sheet.

---

## A · reading a sheet (Task 1)

- [ ] [W] **A1** Open a real walk-sheet from `docs/` by stem (not this one — pick
      one still `built_not_walked`, or re-open this one after `A`–`E` are
      walked and a results log exists). Confirm the items shown match the
      sheet's real identifiers, text and current mark (`[ ]`/`[x]`/`[~]`).
- [ ] [W] **A2** Open `doc_provenance_coverage` or `repo_tier_producers` (the two
      cards the board flags as evidence-in-results-log). Confirm the sidebar
      shows the warning banner explaining the sheet reads 0 done because the
      evidence is in the results log instead — and does **not** present the
      sheet as untouched work.

## B · recording a verdict and evidence (Task 2)

- [ ] [W] **B1** Pick one deterministic-shaped item (a command, an exit code, a
      byte-for-byte comparison). Set its verdict to **walked** and paste real
      terminal output — multiple lines — into the evidence box. Confirm
      (after emitting, check **C1**) that the output survives verbatim, not
      paraphrased or re-wrapped.
      *(Witness suite: `tests/witness/witness_uat_sidebar.py` covers this
      DOM half against a fixture — see COWORK_REPORT_ui_witness.md Task 4.)*
- [ ] [H] **B2** Pick one judgement-shaped item (a "does this feel right" call).
      Set its verdict to **walked** and write a prose verdict. Confirm
      nothing in the UI computes or suggests a pass — the verdict box is
      never pre-filled and there is no auto-checked state.
      *(Explicitly never a witness item — see brief Task 4.)*
- [ ] [W] **B3** Set an item's verdict to **deferred** and leave the evidence box
      empty. Press **Emit results log**. Confirm the emit is refused, the
      item is flagged in place, and the refusal names *why* (missing reason)
      rather than a generic error.
      *(Witness-covered, see B1's note.)*
- [ ] [W] **B4** Same as B3, for **blocked**. *(Witness-covered.)*
- [ ] [W] **B5** Reload the UAT sidebar tab (or switch to a different stem and
      back) without emitting first. Confirm every verdict and evidence box
      is gone — session-scoped means a lost session loses the notes, as the
      pane's sub-line says.
- [ ] [W] **B6** Open a sheet whose results log already exists (this one, after
      C1 below has run once). Confirm the "results log already exists"
      banner is impossible to miss — not a footnote in a counts line — and
      that each item already recorded shows an "already recorded: …" badge
      even before you press anything. *(Witness-covered, see B1's note.)*
- [ ] [W] **B7** Press **Resume** on that banner. Confirm previously recorded
      verdicts and evidence populate the form, and that emitting right after
      (with nothing else changed) does **not** re-print those untouched items
      into a new section — only genuinely new or edited items should appear
      in the appended section. Then edit one resumed item's evidence and
      confirm it now *does* appear in the new section. *(The resume-populates
      half is witness-covered; the dedup-on-append half is backend logic,
      already covered by `tests.tester_uat_sidebar`.)*

## C · emitting the stamped results log (Task 3)

- [ ] [W] **C1** With B1/B2 given real verdicts, emit. Open the emitted
      `docs/UAT_uat_sidebar_results.md` (or whichever stem you walked) and
      confirm: the pasted multi-line output from B1 is verbatim; the prose
      verdict from B2 reads as written, with no computed pass/fail language
      anywhere in the file. Also confirm the log now splits into
      **Machine-verified** / **Human ruling**, with a visible citation line
      (not an HTML comment) above the machine section.
- [ ] [G] **C2** Check the stamp comment on the first line: `commit=` matches
      `git rev-parse --short HEAD` on this machine, `host=` matches this
      machine's hostname, `dirty=` matches whether `git status --porcelain`
      is non-empty right now, and there is **no `gate=` field** anywhere in
      the stamp. *(Backend-testable via `TestClient`; already covered by
      `tests.tester_uat_sidebar`.)*
- [ ] [G] **C3** Emit a second time (any stem with an existing results log —
      re-emit onto the one C1 just created). Confirm it is **refused**, not
      silently overwritten, and the refusal explicitly offers to append
      instead. *(Already tester-covered — see C2's note.)*
- [ ] [G] **C4** Choose to append. Confirm the file's **original** stamp line at
      the top is unchanged, and a new dated "Additional walk" section is
      added below rather than the old content being edited. *(Already
      tester-covered — see C2's note.)*
- [ ] [G] **C5** Confirm `git status` shows the results log as staged
      (`git diff --staged` shows it), and confirm nothing was committed —
      `git log -1` is unchanged.

## D · closing the loop with the board (Task 4)

- [ ] [W] **D1** Before emitting for a real *built, not walked* card, note its
      column on the **Docs board** tab. After emitting that card's results
      log, reload the Docs board tab (no other action) and confirm the card
      moved to **Walked** by itself.
- [ ] [W] **D2** Confirm nothing else on the board changed — no new finding
      appeared, no other card moved, no board state file was written
      (`git status` before/after the emit shows only the one new/staged
      results log, nothing else new).

## E · the gate and the reversible part

- [ ] [G] **E1** `python verify.py` → **GREEN** after everything above.
- [ ] [G] **E2** `git status` after the whole walk shows only staged additions
      (new/modified results logs from this walk) — nothing committed, and no
      file outside `docs/` touched.

---

## Windows note

`python run.py review --host 127.0.0.1` binds loopback only, port `8002`
(`REVIEW_DEFAULT_PORT`). Use `curl.exe` (never bare `curl`) if you want to
drive `/api/uat/sheet` or `/api/uat/emit` directly rather than through the UI.
