<!-- uat: commit=5a1bad9 dirty=true host=LucasGoonPC walked=2026-08-18 -->

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
