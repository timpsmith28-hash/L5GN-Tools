<!-- gate-frozen: commit=f5a14d2 -->
<!-- uat: commit=f5a14d2 dirty=false host=multi-rig walked=2026-08-03 -->

> **ARCHIVED** 2026-08-24 · completed pair · walk-sheet for `docs/archive/COWORK_BRIEF_scanner_scope_bypass.md`
> Superseded by its own results log, `docs/archive/UAT_scanner_scope_bypass_results.md`. Original purpose: the acceptance checks for the scope-bypass round.
> Read as the questions that were asked, never as work outstanding. Every check was walked on 2026-08-03 at `f5a14d2` across three machines; the unticked boxes here are the blank sheet and the ticks are in the results log. **Do not run this as a task list.**

# UAT walk-sheet — scanner scope bypass

Pair: `docs/COWORK_BRIEF_scanner_scope_bypass.md` → `docs/COWORK_REPORT_scanner_scope_bypass.md`.
Committed as `f5a14d2`. Gate at build time: `python verify.py` **GREEN**, 6
auditors + **54** testers (frozen build-time count).

**Fully walked 2026-08-03**, live, across the gaming rig, the work rig and the
knight. Checks below are marked `[x]` where actually walked with a real
result, not merely "ready to walk."

## 1 — `file_census` / `workspace_scanner` skip data directories

- [x] **1.1.** `file_census.scan()` on a project with a `raw_claude_files/` (or
  any `is_data_dir_name` match) directory never lists a path under it in
  `directories[]`, `files[]`, `at_risk[]`, `mass[]`, `outliers[]` or
  `basenames_beyond_cap`. **Walked by hand**, gaming rig: a manual
  `ManualCheck` fixture with `src/real.py` + `raw_claude_files/{conversations.json,leak.py}`
  scanned directly (not via the tester) — `file_census leak: False`.
- [x] **1.2.** `workspace_scanner.scan()` on the same project never lists a
  `.py` file under that directory in `modules[]`, and no class/function name
  from inside it appears in `top_classes`. **Walked by hand**, same fixture —
  `workspace_scanner leak: False`; `Leaked class present in top_classes?: False`
  (the planted `class Leaked` inside `raw_claude_files/leak.py` never got
  parsed).
- [x] **1.3.** Both scanners' output carries a `"scope"` block
  (`{"skipped_paths": N, "skipped_by_reason": {...}}`), same shape as
  `import_scanner` / `env_scanner` / `blast_radius` / `doc_census` /
  `duplicate_finder` / `todo_adr_scanner`. **Walked by hand** — both printed
  `{'skipped_paths': 1, 'skipped_by_reason': {'data_dir': 1}}`.
- [x] **1.4.** A fresh `run.py build` on `LucasGoonPC` produces an
  `estate.json` with **zero** data-directory paths in `at_risk[]`, `files[]`,
  `directories[]` and `modules[]`. **Walked** — required `--fresh`, not a
  plain `build` (see live-walk notes, §3); confirmed zero via the precise
  path-aware leak check after that.

## 2 — the tester iterates the registry

- [x] **2.1.** `tester_scanner_scope` runs every entry in `registry.SCANNERS`
  (not just `todo_adr_scanner`) against a fixture carrying a planted, randomly
  named data directory, and asserts none of them leak it.
- [x] **2.2. (load-bearing)** Delete the `scope.skip_dir(name)` call from
  `file_census.scan()` by hand. Re-run `tester_scanner_scope`. **Confirm it
  goes red**, naming `file_census`. Restore the line, confirm green. **Walked**
  — went red naming `file_census` exactly, green after restore, diff confirmed
  identical to the reviewed fix both times.
- [x] **2.3.** Repeat 2.2 for `workspace_scanner`'s `scope.skip(path)` call.
  Same expectation: red naming `workspace_scanner`, green once restored.
  **Walked** — same result.
- [x] **2.4.** `python verify.py` is GREEN and reports 6 auditors + **54**
  testers at this build; `tester_scanner_scope` listed OK. **Walked** on the
  gaming rig (commit point). The work rig shows one unrelated pre-existing
  `tester_serve` failure — see §3 live-walk notes; not this round's fault, not
  blocking.

## 3 — deposits on the knight (needs the real rigs)

- [x] **3.1.** Baseline measurement taken on the knight roughly matches the
  brief's own figures. The knight's own local `data/estate.json` (a separate,
  out-of-scope artefact — see report) showed 2,178 `chat_threads/` matches by
  itself, consistent with the scale the brief described.
- [x] **3.2.** Fresh `estate.json` on the gaming rig and the work rig each
  measure **zero** data-dir substring matches *before* depositing. **Walked
  2026-08-03**, both rigs, using the precise path-aware leak check (not just
  the blunt substring count) — see live-walk notes below.
- [x] **3.3.** The superseded bundles are **removed** on the knight before the
  fresh deposits land — not edited, not partially scrubbed. **Walked, and
  widened**: alongside both `07-25` bundles the brief named, an undocumented
  third tainted snapshot (`work/history/estate-2026-07-21.json`, 5,812
  matches) was found by inspecting the knight's `history/` dirs rather than
  trusting the brief's "exactly two bundles" count at face value, and removed
  under the same DECISIONS 0029 rule. A fourth candidate
  (`personal/history/estate-2026-07-17.json`) was measured and found **clean**
  — kept, not deleted on the assumption that "older than the fix" implies
  tainted.
- [x] **3.4.** After `consume`, both estates show clean via
  `manifest_verified: true` (implicit — `consume` completed without a
  verification failure) and the same substring measurement on the freshly
  landed files returns **zero** for `work`; `personal` returned a nonzero
  whole-file substring count (23) that resolved to `leaks: NONE` under the
  precise path-aware check — see live-walk notes.
- [x] **3.5.** `Chronicler_Backup` substring hits were checked on the personal
  estate post-remediation (22 matches) and confirmed, via the precise check,
  to be prose in `L5GN-Tools`'s own self-scanned docs — not an unrecognised
  data directory. Flagged and resolved, not silently absorbed.

### Live-walk notes, 2026-08-03 (gaming rig + work rig deposits)

- **Gaming rig (`LucasGoonPC`, estate `personal`).** `run.py build --fresh`
  required — a plain `build` reused four projects' stale per-scanner cache
  from before the fix (`data/<scanner>/<project>.json`, presence-based, no
  code-version check), which still carried real data-dir paths despite the
  fix being live. Confirmed clean after `--fresh`; `deposit --push` →
  `pushed : OK -> l5gn-castle:vault/estates/personal/`.
- **Work rig (`10280L`, estate `work`).** Two findings, both resolved or
  deliberately deferred, neither a regression from this round:
  - `run.py config` initially showed the `L5GN` root as `(MISSING)` — the
    work estate's L5GN-scope projects were briefly absent from the build.
    Resolved before depositing; re-run showed 19 projects (up from 9),
    `L5GN` present.
  - `verify.py` shows `tester_serve` **RED** on this rig, and will keep
    doing so until reconciled. Root cause: an **uncommitted, deliberate**
    local edit to `l5gntools/viewer.py` (`git diff` confirmed, not a shadow
    import) that makes the Datasette invocation go through
    `[sys.executable, "-m", "datasette", ...]` instead of a bare `datasette`
    console-script call — a documented workaround for this machine's
    corporate endpoint policy blocking the `datasette.exe` shim while `-m`
    works. Isolated to the Datasette read-surface (DECISIONS 0007/0013);
    confirmed untouched by this round's diff, and does not affect
    `file_census`, `workspace_scanner`, `build`, `deposit` or `consume`.
    **Not fixed here** — worth its own small follow-up (teach
    `datasette_argv`/`datasette_available` to prefer `-m` when the shim
    isn't runnable, or update `tester_serve` to accept both shapes) so this
    rig doesn't carry a permanent uncommitted diff and a permanently-red
    gate.
  - Independently verified clean by parsing the actual `report.html`
    produced on this rig (not just terminal output) and running the precise
    `is_data_dir_name`-based leak check against its embedded data:
    `leaks: NONE` across all 19 projects, `toolkit_commit: f5a14d2`,
    `estate_name: work`. `deposit --push` → `pushed : OK ->
    l5gn-castle:vault/estates/work/`.

### Live-walk notes, 2026-08-03 (the knight)

- **Removed, per DECISIONS 0029:** `personal/estate.json`,
  `personal/deposit_manifest.json`, `personal/history/estate-2026-07-25.json`;
  `work/estate.json`, `work/deposit_manifest.json`,
  `work/history/estate-2026-07-25.json`; and — found only by inspecting the
  knight's `history/` dirs rather than trusting the brief's count —
  `work/history/estate-2026-07-21.json` (5,812 matches, predates the fix,
  never mentioned in the brief).
- **Kept, verified clean:** `personal/history/estate-2026-07-17.json` (0
  matches). Not deleted just for predating the fix — measured first.
- **`consume` run**, both estates ingested without error.
- **Final measurement:** `work/estate.json` 0; `work/history/estate-2026-08-03.json`
  0; `personal/estate.json` 23 substring (`raw_claude_files` 1,
  `Chronicler_Backup` 22) / **0 real** under the path-aware check;
  `personal/history/estate-2026-07-17.json` 0;
  `personal/history/estate-2026-08-03.json` 23 substring / 0 real, same
  reason. `L5GN-Tools` confirmed present in the personal project list
  (self-scanned) — the 23 is that project's own docs discussing this exact
  round, not a leak.

## 4 — the disclosure boundary

- [x] **4.1.** `mass[].path`, `outliers[].path`, `summary.largest` and
  `basenames_beyond_cap` still behave as D3/D4 described — not silently
  removed or narrowed along with the scope-bypass fix. Confirmed by
  construction (Task 1's fix prunes before any walk, including the outlier
  heap's) and by the real-data leak checks above finding no regression in
  those fields' population.
- [x] **4.2.** The field-by-field table in the report (Task 4) is read and
  agreed: `at_risk[]`, `files[]`, `directories[].path` and `modules[].path` as
  scope-bypass-fixed; `mass[].path`, `outliers[]`, `summary.largest` and
  `basenames_beyond_cap` as deliberate disclosure, unaffected in kind.

## 5 — hygiene

- [x] **5.1.** No work-estate path appears anywhere in the report, walk-sheet,
  runbook or a commit message from this round. Confirmed — every measurement
  recorded is a count, and project names shown (`L5GN-Archive`, `L5GN-Castle`,
  etc.) are the toolkit's own repos, not work-estate content.
- [x] **5.2.** `verify.py` GREEN at the point of commit (gaming rig, `f5a14d2`).

---
**Closed 2026-08-03.** Results log stamp:
`<!-- uat: commit=f5a14d2 dirty=false host=multi-rig walked=2026-08-03 -->`
