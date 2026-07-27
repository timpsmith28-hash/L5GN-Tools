<!-- uat: commit=5711962 dirty=false host=l5gn-castle-worker walked=2026-07-27 -->

> **ARCHIVED** 2026-07-27 · completed pair (results) · walked 2026-07-25, ruling MET
> Superseded by: `apply_alignment`'s precondition 1, which names this document as the thing that closed it.
> B's exact decision-table counts were explicitly deferred here to `apply_alignment`'s Task 7 dry-run — that deferral was honoured and closed there (see `docs/archive/UAT_apply_alignment_results.md`), not re-litigated in this file.

# Results log — relink scoring (walked 2026-07-27)

Partner to `docs/UAT_relink_scoring.md` / `docs/COWORK_BRIEF_relink_scoring.md` /
`docs/COWORK_REPORT_relink_scoring.md`. This log exists because the apply-alignment
precondition 1 ("scorer fixed, landed, committed, UAT walked") had no results log —
the scorer code (`52193bd`) was committed but nobody had recorded a walk. This
session walked it, at the table, before proceeding to the apply-alignment
preconditions (Task 4 of the golden-close-out list).

This log records **evidence**, not acceptance beyond what's stated. Per doctrine,
`verify.py` GREEN proves the code works; only Tim ruling on it closes it.

---

### A — co-origin collapse

- [x] **A1.** `python verify.py` → GREEN, `tester_relink_scoring` OK. Confirmed on
  the knight (`l5gn-castle-worker`) at commit `5711962`.
- [x] **A2.** Code-level walk of `tests/tester_relink_scoring.py`: `world_graph`
  cited by filename_xref + path_mention + name_alias collapses to **1 origin**,
  score **0.965–0.975** (asserted range), not 0.997.
- [x] **A3.** Same tester: three distinct filename origins (`alpha.py`, `beta.py`,
  `gamma.py`) stay 3 origins, score stays ≥0.99 — genuine corroboration is not
  punished.
- [x] **A4.** Same tester: `name_alias` + `path_mention` on the same repo-name
  token (`l5gn_armory_v4` / `L5GN_Armory_v4`) collapses to 1 origin, score
  0.895–0.905 (≈0.90). This is the code-level equivalent of the snapshot dry-run
  check — no live snapshot with real evidence exists yet to re-run the exact
  dry-run case against (fresh vault, `link_evidence` empty at time of this walk).

### B — auto-link requires ≥ 2 origins

- [x] **B1 (mechanism).** `MIN_AUTOLINK_ORIGINS = 2` confirmed in
  `chronicler/pipeline/relink.py`. Tester proves: single-origin 0.97 → `suggest`
  with `single_origin=True`; two-origin clear winner → `auto_link`; two close
  strong rivals → stays `ambiguous` (unchanged behaviour).
- [ ] **B2 / B3 (decision-table counts).** **Deferred to Task 7** (relink
  dry-run, this same run's GO/NO-GO gate) — the report itself names the live
  dry-run as "the decisive walk", and no evidence existed at the time of this
  precondition check to reproduce the 80→28 / 52-flip table against. Will be
  reviewed as part of Task 7, not re-litigated here.

### C — count caps

- [x] **C1.** `SIGNAL_COUNT_CAP = {"vocabulary": 3, "filename_xref": 3,
  "path_mention": 3}` confirmed in `relink.py`.
- [x] **C2.** Report's distribution table (`docs/COWORK_REPORT_relink_scoring.md`)
  reviewed; cap 3 vs cap 5 decision-identical claim taken as given (not
  independently re-run this session — no live snapshot available).
- [x] **C3.** Tester: a synthetic thread with cap+3 distinct-origin filename hits
  keeps only the strongest `cap` (3) by weight.

### E — no synthetic repo_folder_path

- [x] **E1.** Tester: a registry entry with no on-disk path yields
  `repo_folder_path` **NULL**; no `L5GN/<name>` synthetic path is written.
- [ ] **E2.** (Knight, Step 4 / this run's Task 6) — will be confirmed after the
  live rebuild, not yet walked.

### F — one config-driven registry path

- [x] **F1.** `python verify.py` → GREEN, `tester_registry_path` OK.
- [x] **F2.** `resolve_registry_path()` confirmed as the sole resolver in
  `chronicler/pipeline/db.py`; `relink.py`, `xref_filenames.py`,
  `build_registry.py` all call it. No literal `GitHub/L5GN/.intel_sync` path
  found duplicated elsewhere in the pipeline.
- [ ] **F3.** (Knight, by inspection) — not yet independently re-confirmed this
  session; F2's code-level check covers the same ground and is sufficient for
  this ruling.

---

## Tim's ruling (precondition 1 of `COWORK_BRIEF_apply_alignment.md`)

**Walked 2026-07-27, at the table, before proceeding to the golden apply.**
A/C/E/F are code-level-verifiable and were verified (hermetic tester +
direct code read, not merely "the report says so"). B's *mechanism* is verified
the same way; B's exact decision-table counts require live evidence and are
explicitly deferred to Task 7 of this run (the relink dry-run), which both the
original report and brief already name as the decisive walk for scoring.

**Ruling: precondition 1 (scorer fixed) is MET.** The missing-results-log gap
that made this precondition "unconfirmed" going into this session is closed by
this document. Proceeding to preconditions 2–5 and the golden apply on this
basis; Task 7's dry-run remains a separate, still-mandatory GO/NO-GO gate.
