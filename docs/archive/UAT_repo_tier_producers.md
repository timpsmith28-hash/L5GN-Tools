<!-- gate-frozen: commit=22df436 -->

> **ARCHIVED** 2026-08-31 · completed pair · pair `COWORK_BRIEF_repo_tier_producers.md` + `COWORK_REPORT_repo_tier_producers.md`, walked 2026-07-27
> Superseded by **0012**'s repo-tier implementation now being live · Original purpose: fix the evidence pass reaching only 10 of 58 targets, which left `crystal-spire` and Citadel/Armory producing zero filename evidence.
> A ready-to-walk sheet, not a record. **Read the results log instead.**

# UAT walk-sheet — repo-tier producers

**Brief:** `docs/COWORK_BRIEF_repo_tier_producers.md`
**Report:** `docs/COWORK_REPORT_repo_tier_producers.md`
**Built:** 2026-07-27, gaming rig. **Nothing committed** — walk against the staged tree.
**Gate at build time:** `python verify.py` → 6 auditors + 42 testers; all 42
testers green, 5/6 auditors green. `auditor_doc_claims` is red on 11 lines in 8
pre-existing docs from earlier rounds, unrelated to this brief's code — see the
report's "The one red auditor" section before treating this as a blocker.

Every item below is **ready to walk**, none marked passed — that is Tim's call,
and the result belongs in `docs/UAT_repo_tier_producers_results.md` with a
commit stamp, or `auditor_uat_stamp` refuses the commit. The decisive walk is
the **re-run of `apply_alignment` Task 1 on the knight** after
commit → push → knight `git pull` — everything below the fixtures is done on
the knight, against the live vault. Items ordered so a failure stops the walk
cheaply.

---

### Fixtures — rig-runnable, no knight

- [ ] **Fx1.** `python verify.py` → `tester_build_inventory`,
  `tester_build_activity`, `tester_xref_filenames`,
  `tester_extract_path_mentions` all OK.
- [ ] **Fx2.** In `tester_build_inventory`, a repo deposited as
  `L5GN-Crystal-Spire` under a repo-less concept project `crystal-spire` gets
  `file_inventory` on the **repo**; the concept entry gets none; no exception.
- [ ] **Fx3.** In `tester_build_activity`, that same concept project gets **no**
  activity block (not a fabricated `2026-07-17..27`-style window); the repo
  gets its real window; a curated `first_seen` keyed by the repo id still
  widens it.
- [ ] **Fx4.** In `tester_xref_filenames`, a unique attachment basename produces
  a `link_evidence.project` row keyed by the **repo id**, never the
  canonical_name.
- [ ] **Fx5.** In `tester_extract_path_mentions`, a message naming
  `L5GN-Crystal-Spire\world_graph.json` produces a `path_mention` row keyed by
  the repo id, whose `origin` matches the `filename_xref` origin an attachment
  of the same file would produce (run both producers against one fixture DB
  and compare the two rows directly — the tester does this).

### A — `build_inventory` on the live deposit (Task A)

- [ ] **A1.** `python pipeline/build_inventory.py` on the live deposit gives
  `L5GN-Crystal-Spire`, `L5GN_Armory_v4`, `smelt-gateway` (and the estate-infra
  repos) a `file_inventory`; the 10-of-58 becomes near-complete for
  folder-backed targets. Record the new count in the results log.
- [ ] **A2.** No concept project was handed a synthetic/invented inventory —
  spot-check `crystal-spire`, Citadel/Armory-lineage concepts, and any other
  project whose repo carries a different name.

### C — id-keyed filename evidence (Task C)

- [ ] **C1.** `world_graph.json` resolves to the Crystal Spire **repo id**, not
  `crystal-spire` the concept id and not any canonical_name string.
- [ ] **C2.** `link_evidence` is id-keyed throughout: `SELECT DISTINCT project
  FROM link_evidence` — every value resolves in the registry by id; none are
  folder-name/canonical_name strings.

### B — no fabricated activity window (Task B)

- [ ] **B1.** No concept project carries a `2026-07-17..27` (or any
  scan-date-shaped) activity window in the rebuilt registry.
- [ ] **B2.** Real threads that were at risk of being time-zeroed by the
  fabricated window (Crystal Spire, Citadel/Armory, estate-infra eras) are not
  hard-zeroed by `time_plausibility` — spot-check a handful of known-real dates
  against each project's rebuilt window.

### Then continue Step 4 (resumes the golden apply)

- [ ] **S4.1.** S4/S5 `--apply` on the live vault.
- [ ] **S4.2.** relink **DRY-RUN** as the GO/NO-GO gate — read the table
  together: Crystal Spire / Citadel / estate-infra now align, no auto-link
  rests on a single origin.
- [ ] **S4.3.** `relink --apply` on GO only.
- [ ] **S4.4.** The three verify queries.
- [ ] **S4.5.** Deposit/consume with the wall check.
- [ ] **S4.6.** **UAT stamp** on the results log
  (`docs/UAT_repo_tier_producers_results.md`), naming the commit walked.

---

## Note on the doc-claims auditor

`auditor_doc_claims` failing on **other rounds'** docs is not part of this
walk — those docs are frozen records of a past gate count and the fix is an
archiving decision (`docs-archivist`, ratified per pair), not a code change.
Do not "fix" it by editing their numbers.
