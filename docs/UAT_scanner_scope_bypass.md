<!-- gate-frozen: commit=86fca68 -->

# UAT walk-sheet — scanner scope bypass

Pair: `docs/COWORK_BRIEF_scanner_scope_bypass.md` → `docs/COWORK_REPORT_scanner_scope_bypass.md`.
Built on `86fca68`. Gate at build time: `python verify.py` **GREEN**, 6 auditors
+ **54** testers (frozen build-time count). Mark each check **ready to walk**,
never "passed" — the walk is Tim's.

Nothing is committed. These check staged changes. Task 3 (deposit remediation)
was not executed in this session — it needs a machine with tailnet access to
the knight; see the runbook.

## 1 — `file_census` / `workspace_scanner` skip data directories

- [ ] **1.1.** `file_census.scan()` on a project with a `raw_claude_files/` (or
  any `is_data_dir_name` match) directory never lists a path under it in
  `directories[]`, `files[]`, `at_risk[]`, `mass[]`, `outliers[]` or
  `basenames_beyond_cap`.
- [ ] **1.2.** `workspace_scanner.scan()` on the same project never lists a
  `.py` file under that directory in `modules[]`, and no class/function name
  from inside it appears in `top_classes`.
- [ ] **1.3.** Both scanners' output carries a `"scope"` block
  (`{"skipped_paths": N, "skipped_by_reason": {...}}`), same shape as
  `import_scanner` / `env_scanner` / `blast_radius` / `doc_census` /
  `duplicate_finder` / `todo_adr_scanner`.
- [ ] **1.4.** A fresh `run.py build` on `LucasGoonPC` produces an
  `estate.json` with **zero** data-directory paths in `at_risk[]`, `files[]`,
  `directories[]` and `modules[]`. *(Ready to walk — needs the gaming rig.)*

## 2 — the tester iterates the registry

- [ ] **2.1.** `tester_scanner_scope` runs every entry in `registry.SCANNERS`
  (not just `todo_adr_scanner`) against a fixture carrying a planted, randomly
  named data directory, and asserts none of them leak it.
- [ ] **2.2. (load-bearing)** Delete the `scope.skip_dir(name)` call from
  `file_census.scan()` by hand. Re-run `tester_scanner_scope`. **Confirm it
  goes red**, naming `file_census`. Restore the line, confirm green.
- [ ] **2.3.** Repeat 2.2 for `workspace_scanner`'s `scope.skip(path)` call.
  Same expectation: red naming `workspace_scanner`, green once restored.
- [ ] **2.4.** `python verify.py` is GREEN and reports 6 auditors + **54**
  testers at this build; `tester_scanner_scope` listed OK.

## 3 — deposits on the knight (needs the real rigs)

- [ ] **3.1.** Baseline measurement taken on the knight (Step 1 of
  `docs/RUNBOOK_scope_bypass_remediation.md`) roughly matches the brief's
  own figures (9,159 / 2,328 substring matches). *(Ready to walk — needs the
  knight.)*
- [ ] **3.2.** Fresh `estate.json` on the gaming rig and the work rig each
  measure **zero** data-dir substring matches *before* depositing.
- [ ] **3.3.** The superseded `estate.json` / `deposit_manifest.json` /
  `history/estate-2026-07-25.json` for both estates are **removed** on the
  knight before the fresh deposits land — not edited, not partially scrubbed.
- [ ] **3.4.** After `consume`, both estates show `manifest_verified: true`,
  and the same substring measurement on the freshly landed files returns
  **zero**.
- [ ] **3.5.** If a `Chronicler_Backup` substring surfaces outside a
  `raw_*`/`*_files` ancestor path during 3.1 or 3.4, it is flagged in the
  results log rather than silently absorbed.

## 4 — the disclosure boundary

- [ ] **4.1.** `mass[].path`, `outliers[].path`, `summary.largest` and
  `basenames_beyond_cap` still behave as D3/D4 described — not silently
  removed or narrowed along with the scope-bypass fix.
- [ ] **4.2.** The field-by-field table in the report (Task 4) is read and
  agreed: `at_risk[]`, `files[]`, `directories[].path` and `modules[].path` as
  scope-bypass-fixed; `mass[].path`, `outliers[]`, `summary.largest` and
  `basenames_beyond_cap` as deliberate disclosure, unaffected in kind.

## 5 — hygiene

- [ ] **5.1.** No work-estate path appears anywhere in the report, walk-sheet,
  runbook or a commit message from this round.
- [ ] **5.2.** `verify.py` GREEN at the point of commit.

---
*Ready-to-walk sheet. The results log you produce needs a `uat:` stamp
(`docs/README.md` §3) before the pair can close — no `gate=` field, per the
brief.*
