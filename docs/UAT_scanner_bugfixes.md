<!-- gate-frozen: commit=6d09eb3 -->

# UAT walk-sheet — scanner bug fixes

Pair: `docs/COWORK_BRIEF_scanner_bugfixes.md` → `docs/COWORK_REPORT_scanner_bugfixes.md`.
Built on `23b5ffa`. Gate at build time: `python verify.py` **GREEN**, 6 auditors
+ **30** testers (frozen build-time count). Mark each check **ready to walk**,
never "passed" — the walk is Tim's.

Nothing is committed. These check staged changes.

## A — scope discipline

- [ ] **A1.** A full-estate `python run.py build` that includes Chronicler
  produces a `todo_adr` marker count in the **low tens, not the hundreds**, on
  the TODO/ADR tab. *(Ready to walk — needs the work rig where Chronicler lives.)*
- [ ] **A2.** The report never lists a path under `raw_*`, `chat_threads/`,
  `vault_staging/`, `Takeout/` or `*_files/` — search the report for
  `raw_claude_files` and expect nothing.
- [ ] **A3 (doctrine).** No chat-transcript text appears anywhere in the report
  or in any `data/**/*.json`.
- [ ] **A4.** Each content scanner's per-project JSON carries a `scope` block with
  `skipped_paths` and `skipped_by_reason`; on a project with a chat archive,
  `data_dir` appears there with a non-zero count.

## B — the report polices itself

- [ ] **B1.** `data/estate.json` and the `DATA` block inside `report.html` both
  parse as JSON after a build (open the report; it renders without a blank page).
- [ ] **B2.** Force an oversize case (or point at Chronicler pre-fix) and confirm
  `run.py build` **either** caps honestly (`truncated: true` + true count) **or**
  exits non-zero naming the culprit — never leaves a truncated report that reads
  as complete.
- [ ] **B3.** When any scanner payload is oversized or capped, the report shows a
  **payload-anomaly banner** at the top naming the scanner and project.
- [ ] **B4.** `python verify.py` is GREEN and reports 6 auditors + **30** testers
  at this build; `tester_scanner_scope` and `tester_report_selfcheck` listed OK.

## C — recorded only

- [ ] **C1.** Confirm Task C (count `## Open questions` toward PENDING) is on the
  governance run and **not** expected in this pair.

---
*Ready-to-walk sheet. The results log you produce needs a uat stamp
(`docs/README.md` §3) before the pair can close.*
