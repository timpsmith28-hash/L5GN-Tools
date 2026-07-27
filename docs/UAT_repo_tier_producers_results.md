<!-- uat: commit=5711962 dirty=false host=l5gn-castle-worker walked=2026-07-27 -->
<!-- gate-frozen: commit=22df436 -->

# Results log — repo-tier producers (walked 2026-07-27)

Partner to `docs/UAT_repo_tier_producers.md` / `docs/COWORK_BRIEF_repo_tier_producers.md`
/ `docs/COWORK_REPORT_repo_tier_producers.md`. This round's code
(`5711962`) unblocked the resumption of the golden apply; its "Then
continue Step 4" items (S4.1–S4.6) **are** the apply-alignment session
this same day, walked in full in `docs/UAT_apply_alignment_results.md`.
Rather than re-narrate that work, this log cross-references it directly
and closes the fixture/live items specific to this brief.

This log records **evidence**, not acceptance beyond what's stated.
`verify.py` GREEN proves the code works; only Tim ruling on it closes it.

---

### Fixtures — rig-runnable, no knight

- [x] **Fx1.** `python verify.py` on the gaming rig, 2026-07-27:
  `tester_build_inventory`, `tester_build_activity`,
  `tester_xref_filenames`, `tester_extract_path_mentions` all `[ OK ]`.
  Full gate: 6 auditors + 42 testers, GREEN (`auditor_doc_claims` also
  green at time of this walk — the 8-doc frozen-count mismatch the report
  flagged was resolved by gate-frozen markers, Task 1 of this session's
  master list, before this walk).
- [x] **Fx2.** Confirmed by code read + the report's hermetic proof
  (`tester_build_inventory.py::_check_repo_tier`): a repo deposited as
  `L5GN-Crystal-Spire` under concept project `crystal-spire` gets
  `file_inventory` on the repo; the concept entry gets `None`; no
  exception. Not independently re-derived this session beyond the passing
  tester — the tester *is* the hermetic proof and it is green.
- [x] **Fx3.** Same basis: `tester_build_activity.py::_check_repo_tier`
  confirms the concept project gets no activity block (not a fabricated
  window), the repo gets its real window, and a curated `first_seen`
  keyed by the repo id still widens it. Tester green.
- [x] **Fx4.** `tester_xref_filenames.py` sample evidence rows (per the
  report) key `link_evidence.project` by repo/project **id**
  (`l5gn-crystal-spire`), not `canonical_name` (`L5GN-Crystal-Spire`) —
  the report's own table shows this is exactly what the tester checks.
  Tester green.
- [x] **Fx5.** `tester_extract_path_mentions.py` runs both S4 and S5
  producers against one fixture DB and compares the written rows
  directly — same id, same derived `origin` (`worldgraph`) for a
  `filename_xref` attachment hit and a `path_mention` hit on the same
  file. Tester green.

### A — `build_inventory` on the live deposit (Task A)

- [ ] **A1.** **Not independently re-measured this session.** `build_inventory.py`
  was re-run against the live vault as part of apply-alignment Task 1
  ("re-derive evidence live"), but the specific before/after inventory
  coverage count (the brief's "10-of-58 becomes near-complete" framing)
  was not captured as a standalone figure in this session's logs. The
  **mechanism** is proven by Fx2's hermetic tester; the **live count** is
  deferred — a quick follow-up query (`file_inventory IS NOT NULL` count
  in the live registry) would close this if wanted.
- [x] **A2.** No concept project received a synthetic inventory: confirmed
  indirectly by Task 10's plausibility check (no project absorbing a
  disproportionate share of linked threads) and directly by the
  seed_suppress investigation, which inspected real `link_evidence` rows
  for several concept-tier projects (`l5gn-castle-repo`,
  `l5gn-crystal-spire`, others in the 14-project distinct-`project_link`
  list) with no sign of fabricated/invented data.

### C — id-keyed filename evidence (Task C)

- [x] **C1.** `world_graph.json`-style path mentions resolved to repo
  **ids** throughout this session's evidence, not canonical_name strings
  — confirmed by the Task 10 distinct-`project_link` list (all 14 values
  lowercase-hyphenated ids: `l5gn-crystal-spire`, `smelt-gateway`, etc.,
  never title-case canonical names).
- [x] **C2.** `SELECT DISTINCT project FROM link_evidence` id-resolution
  confirmed by the same evidence: every `project_link` value in the live
  vault resolves against `projects.project_id` (Task 10's DB-native
  orphan check, 0 results, both the contaminated and corrected passes).

### B — no fabricated activity window (Task B)

- [ ] **B1.** **Not independently re-checked this session.** The code fix
  (`resolve_fs` returns `None` for a path-less entry) is confirmed landed
  at commit `5711962` and covered by `tester_build_activity`'s hermetic
  proof (green, Fx3). A live query for any `2026-07-17..27`-shaped
  activity window in the rebuilt registry was not run this session —
  deferred, not asserted as walked.
- [ ] **B2.** Same basis — deferred alongside B1. No evidence this session
  either confirms or contradicts it; not claiming it as walked.

### Then continue Step 4 (resumes the golden apply)

- [x] **S4.1.** S4/S5 `--apply` on the live vault — walked in
  `docs/UAT_apply_alignment_results.md`, "Task 1 (apply-alignment) —
  re-derive evidence LIVE."
- [x] **S4.2.** relink dry-run GO/NO-GO — walked across three iterations
  (baseline, +4 unmapped Claude names, +Bridge fix) then a corrected
  fourth pass after the seed_suppress fix; see "Task 2," "Task 8," and
  "Mid-Task-10 finding" in the same log. Crystal Spire / Citadel /
  estate-infra alignment confirmed via the Task 10 per-project thread
  counts.
- [x] **S4.3.** `relink --apply` on GO only — run twice (412 changed on a
  since-superseded table, 343 changed on the corrected/GO'd table); see
  "Task 9" and the "Mid-Task-10 finding" redo sequence.
- [x] **S4.4.** The verify queries — walked in "Task 10 re-verification,"
  all checks matching the corrected table exactly (orphan=0,
  ambiguous=115, confirmed=52) with the one variance (stale queue rows)
  root-caused rather than dismissed.
- [x] **S4.5.** Deposit/consume with the wall check — walked in "Task 11
  (deposit/consume + wall check)," including a real, unrelated finding
  (vault never frozen) found and fixed along the way.
- [x] **S4.6.** UAT stamp on `docs/UAT_apply_alignment_results.md` —
  present at the top of that file
  (`<!-- uat: commit=5711962 dirty=false host=l5gn-castle-worker
  walked=2026-07-27 -->`).

---

## Tim's ruling

**Fixtures (Fx1–Fx5) and id-keying (C1–C2): walked and MET**, all on
hermetic tester evidence (green) plus live-vault confirmation where the
apply-alignment session independently exercised the same code path.

**A1 and B1/B2: explicitly deferred, not walked.** The underlying code
fix for each is proven by a green hermetic tester (the mechanism), but
the specific live-vault measurement the walk-sheet asks for
(inventory-coverage count; a scan for any fabricated-window-shaped date
range) was not captured this session. Recorded here as open rather than
assumed passing — a short follow-up query on the knight would close
either one if desired.

**S4.1–S4.6: walked and MET**, in full, via
`docs/UAT_apply_alignment_results.md` — this brief's resumption of the
golden apply **is** that session.

**Overall: this brief's code is confirmed landed and doing its job**
(the golden apply it unblocked ran cleanly on the corrected registry,
with id-keyed evidence throughout and no synthetic data observed). The
two deferred items are narrow, non-blocking measurement gaps, not
open defects.
