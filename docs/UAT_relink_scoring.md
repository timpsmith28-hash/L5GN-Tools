<!-- gate-frozen: commit=d1a1b76 -->

# UAT walk-sheet — relink scoring

**Brief:** `docs/COWORK_BRIEF_relink_scoring.md`
**Report:** `docs/COWORK_REPORT_relink_scoring.md`
**Built:** 2026-07-25, gaming rig. **Nothing committed** — walk against the staged tree.
**Gate at build time:** `python verify.py` → GREEN (6 auditors + 40 testers).

Every item below is **ready to walk**, none marked passed — that is Tim's call, and
the result belongs in `docs/UAT_relink_scoring_results.md` with a commit stamp, or
`auditor_uat_stamp` refuses the commit. The decisive walk is on the knight against
the live vault (Step 4 / apply brief); here it is the snapshot dry-run + testers.
Items ordered so a failure stops the walk cheaply.

---

### A — co-origin collapse

- [ ] **A1.** `python verify.py` → GREEN, `tester_relink_scoring` OK.
- [ ] **A2.** In the hermetic tester, `world_graph` cited as filename_xref +
  path_mention + name_alias combines to **≈0.97 with 1 origin**, not 0.997.
- [ ] **A3.** Three *distinct* owned files still combine high (3 origins) — the fix
  does not punish genuine corroboration.
- [ ] **A4.** On the snapshot dry-run, a `name_alias` + `path_mention` on the same
  repo-name token (e.g. an `L5GN_Armory_v4` thread) reports **origins=1**.

### B — auto-link requires ≥ 2 origins

- [ ] **B1.** No auto-link in the dry-run rests on a single origin (spot-check the
  top 10 — each `summary` shows `origins≥2`).
- [ ] **B2.** Spot-check three former lone-signal auto-links now read as
  suggestions: `SolConfig` "Code base audit…", `L5GN_Armory_v4` "Demo phase
  rollout", and one more of the 52 flips.
- [ ] **B3.** The old→new decision table matches the report: auto-links 80 → 28,
  52 single-origin flips to suggest, ambiguous/downgrade unchanged.

### C — count caps

- [ ] **C1.** `SIGNAL_COUNT_CAP` carries `filename_xref: 3` and `path_mention: 3`.
- [ ] **C2.** The report's distribution justifies the value, and the dry-run at
  cap 3 vs cap 5 is decision-identical (the defended, decision-neutral choice).
- [ ] **C3.** A thread with > 3 distinct-origin filename hits uses only the
  strongest 3 (`tester_relink_scoring` C case).

### E — no synthetic repo_folder_path

- [ ] **E1.** `tester_relink_scoring` E case: a target with no on-disk path yields
  `repo_folder_path` **NULL**, and no `L5GN/<name>` synthetic path appears.
- [ ] **E2.** (Knight, Step 4) after a rebuild, a concept project reads
  `repo_folder_path` NULL in the vault, not a constructed guess.

### F — one config-driven registry path

- [ ] **F1.** `python verify.py` → GREEN, `tester_registry_path` OK.
- [ ] **F2.** `CHRONICLER_REGISTRY_PATH` set → `relink` / `xref_filenames` /
  `build_registry` all resolve that exact path; unset → the same derived per-host
  path for all. No literal `GitHub/L5GN/.intel_sync` remains in the five modules.
- [ ] **F3.** (Knight, by inspection) the writer and the four readers resolve one
  location on the box; the dead literal is gone.

---

Mark each **ready to walk**, never "passed". Record the walk in
`docs/UAT_relink_scoring_results.md` with a uat stamp
(`<!-- uat: commit=<sha> dirty=<bool> host=<name> walked=<YYYY-MM-DD> -->`).
