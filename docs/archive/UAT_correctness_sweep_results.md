<!-- uat: commit=5a1bad9 dirty=true host=LucasGoonPC walked=2026-08-18 -->

> **ARCHIVED** 2026-08-31 · completed pair · pair `COWORK_BRIEF_correctness_sweep.md` + `COWORK_REPORT_correctness_sweep.md`, walked 2026-08-18
> Superseded by the fixes themselves being live, and by `CONVENTION_docs.md` §4 for the archiving rules its walk-sheet exercised · Original purpose: a sweep of correctness defects found across the deck panes and the gate, fixed one at a time with a commit each.
> **Asserts the round was tested**, walked 2026-08-18. **Stop trusting** any gate count quoted inside it — the live gate is **12 auditors + 81 testers**.

# Results log — correctness sweep (walked 2026-08-18, LucasGoonPC)

Partner to `docs/UAT_correctness_sweep.md`.

This log records a verdict and its evidence per item -- never a computed pass. `[EVIDENCE]` walked (with evidence) · `[DEFERRED]` deferred, with a reason · `[BLOCKED]` blocked, with a reason · `[N/A]` not applicable.

---

## Machine-verified

_No witness artefact found at `data/witness/correctness_sweep.json` for this sheet. The machine-verified section below has no witness observations to cite -- reported here, not silently omitted._

_No `[G]`/`[W]` items were recorded on this walk._

## Human ruling

- **A1** Open a sheet with mixed `[G]`/`[W]`/`[H]`/unmarked items in
  [EVIDENCE] Opened the UAT sidebar tab on a mixed sheet; all three badges ([G] gate, [W] witness, [H] human) rendered correctly and matched the sheet.

- **E1** Run `pip install -e .[review]` (or `pip install httpx2`
  [EVIDENCE] pip install -e .[review] confirms httpx2 already satisfied; python verify.py GREEN (12 auditors, 81 testers), no StarletteDeprecationWarning printed anywhere in the run.

---

## Not walked, and why

Everything recorded on this walk carries a `[EVIDENCE]` verdict or a witness observation.
