<!-- uat: commit=5a1bad9 dirty=true host=LucasGoonPC walked=2026-08-18 -->

> **ARCHIVED** 2026-08-31 · completed pair · pair `COWORK_BRIEF_pin_mechanism.md` + `COWORK_REPORT_pin_mechanism.md`, walked 2026-08-18
> Superseded by **0056** (a pin is enforced by the pattern, not an enumerated path) and by the 2026-08-31 rewrite of the auditor this round built · Original purpose: build the one pin mechanism — origin, anchor, hash, verified read-only, reported never repaired — and the auditor that checks it.
> **Asserts the round was tested**, walked 2026-08-18. **Stop trusting** any gate count quoted inside it — the live gate is **12 auditors + 81 testers**. The walk passed against an auditor that was later found unable to see half its subject; the walk was not wrong, its subject was narrower than anyone read it to be.

# Results log — pin mechanism (walked 2026-08-18, LucasGoonPC)

Partner to `docs/UAT_pin_mechanism.md`.

This log records a verdict and its evidence per item -- never a computed pass. `[EVIDENCE]` walked (with evidence) · `[DEFERRED]` deferred, with a reason · `[BLOCKED]` blocked, with a reason · `[N/A]` not applicable.

---

## Machine-verified

_No witness artefact found at `data/witness/pin_mechanism.json` for this sheet. The machine-verified section below has no witness observations to cite -- reported here, not silently omitted._

_No `[G]`/`[W]` items were recorded on this walk._

## Human ruling

- **P1** `python run.py pin bump config/mcf_conversation_map.tsv`
  [EVIDENCE] python run.py pin bump config/mcf_conversation_map.tsv -> already matches its pin ... nothing to do (same no-op path as the report). Would-write output path not separately exercised (would need a hand-edited byte or a copy), same known gap noted on the sheet.

- **P8** Read `l5gntools/pin.py` cold: no import outside stdlib
  [EVIDENCE] l5gntools/pin.py imports only stdlib (hashlib, re, dataclasses, pathlib) plus local l5gntools.common; module is read/format-only, no writes. Grepped write_text and .sha256 across l5gntools/ -- the only write_text against a pin file anywhere in the package is run.py:895 (pin bump); other write_text calls (viewer.py, consume.py, deposit.py, report.py, common.py) target unrelated JSON/HTML/manifest outputs.

- **P9** Read `docs/COWORK_REPORT_pin_mechanism.md`'s "What
  [EVIDENCE] Reviewed the "What wasn't exercised" section -- --apply never run against the real map (deliberate, per working rule); host= field's real-world value unconfirmed on this rig (documented as not a defect); full verify.py GREEN confirmed via the pre-commit hook's own run at commit time. Decision: nothing needs follow-up now -- --apply against the real map is left for a later, separate act.

- **P10** Confirm the two gate-frozen markers added to
  [EVIDENCE] Both docs gate-frozen: commit=5016eb8 markers confirmed correct -- the report and results log were archived complete pairs; the results log shows 10 of 10 items walked, with the gate reported GREEN in that historical run, not mid-edit when frozen.

---

## Not walked, and why

Everything recorded on this walk carries a `[EVIDENCE]` verdict or a witness observation.
