<!-- uat: commit=f5a14d2 dirty=false host=multi-rig walked=2026-08-03 -->
<!-- gate-frozen: commit=f5a14d2 -->

# Results log — scanner scope bypass (walked 2026-08-03)

Partner to `docs/UAT_scanner_scope_bypass.md` / `docs/COWORK_BRIEF_scanner_scope_bypass.md`
/ `docs/COWORK_REPORT_scanner_scope_bypass.md`. Fixed and committed as
`f5a14d2`; walked live, over one continuous session, across the gaming rig
(`LucasGoonPC`), the work rig (`10280L`) and the knight (`l5gn-castle`).

This log records **evidence**, not acceptance beyond what's stated. `verify.py`
GREEN proves the code works; only Tim ruling on it closes it.

---

## 1 — `file_census` / `workspace_scanner` skip data directories

- [x] **1.1–1.3.** Walked by hand on the gaming rig, direct scanner calls (not
  the tester) against a manual fixture (`src/real.py` + `raw_claude_files/`
  holding a JSON export and a `.py` with a planted class):
  `file_census leak: False`, `workspace_scanner leak: False`, planted
  `Leaked` class never reached `top_classes`, both scanners' `scope` block
  read `{'skipped_paths': 1, 'skipped_by_reason': {'data_dir': 1}}`.
- [x] **1.4.** Real `run.py build --fresh` on `LucasGoonPC` (personal estate,
  9 real projects): zero data-dir paths confirmed via the precise
  `is_data_dir_name`-based leak check. Required `--fresh` — see the cache-
  staleness finding below.

## 2 — the tester iterates the registry

- [x] **2.1.** `tester_scanner_scope` iterates `registry.SCANNERS` (16
  scanners) against a fixture with a planted, randomly-sentineled data
  directory across two projects. Green.
- [x] **2.2–2.3 (load-bearing).** Hand-removed `scope.skip_dir(name)` from
  `file_census` and, separately, `scope.skip(path)` from `workspace_scanner`.
  Each time: gate went **red**, naming the offending scanner exactly
  (`"... leaked the planted data directory ... scope not honoured"`).
  Restored both, diff confirmed identical to the reviewed fix, gate green
  again.
- [x] **2.4.** `python verify.py` GREEN, 6 auditors + 54 testers, on the
  gaming rig at commit `f5a14d2`.

## 3 — deposits on the knight

- [x] **3.1.** Baseline consistent with the brief's own scale (knight's local
  self-census: 2,178 `chat_threads/` matches, a separate out-of-scope
  artefact).
- [x] **3.2.** Both rigs' fresh estates measured zero real leaks before
  depositing (path-aware check, not the blunt substring count).
- [x] **3.3.** Superseded bundles removed per DECISIONS 0029 — **three**
  snapshots, not the two the brief named: `personal/estate.json` +
  `07-25` history, `work/estate.json` + `07-25` history, and a fourth,
  previously undocumented tainted snapshot found by inspecting the knight's
  `history/` directories directly rather than trusting the brief's count —
  `work/history/estate-2026-07-21.json` (5,812 matches). A fifth candidate,
  `personal/history/estate-2026-07-17.json`, was measured first and found
  **clean** — kept, not deleted on the assumption that "predates the fix"
  automatically means "tainted."
- [x] **3.4.** `consume` ran clean on both estates. Re-measured: `work` — 0
  everywhere. `personal` — a 23-substring whole-file count that resolved to
  `leaks: NONE` under the precise path-aware check (see 3.5).
- [x] **3.5.** The `Chronicler_Backup` substring hits (22, on the personal
  estate) were checked, not assumed — confirmed as `L5GN-Tools`'s own
  self-scanned docs discussing this exact round, not an unrecognised data
  directory. No `DATA_DIR_NAMES` change made or needed on this evidence.

## 4 — the disclosure boundary

- [x] **4.1–4.2.** D3/D4's ruling on `mass[]` / `outliers[]` /
  `summary.largest` / `basenames_beyond_cap` confirmed unaffected in kind —
  by construction (the fix prunes before any walk those fields draw from) and
  by the real-data checks above showing no regression in their population.

## 5 — hygiene

- [x] **5.1.** No work-estate path in any report/walk-sheet/runbook/commit
  message this round — every measurement is a count; project names shown are
  the toolkit's own repos.
- [x] **5.2.** `verify.py` GREEN at commit `f5a14d2`.

---

## Findings surfaced during the walk (not in the original brief)

- **`run.py build`'s cache is presence-based, not code-version-aware.** A
  plain `build` after the fix silently reused four projects' pre-fix
  `file_census`/`workspace_scanner` cache on the gaming rig — same `scanned
  <name>` log line whether it actually rescanned or not. `--fresh` resolved
  it; the runbook now warns about it explicitly. **Deferred** — a real gap for
  any future scanner fix, not specific to this one, worth its own look.
- **A third tainted deposit snapshot**, `work/history/estate-2026-07-21.json`,
  that the brief's "exactly two bundles" framing missed. Found by inspection,
  not assumption; removed per DECISIONS 0029.
- **Work rig's `tester_serve` diverges permanently** from an uncommitted,
  deliberate local edit to `viewer.py` (routes the Datasette invocation
  through `[sys.executable, "-m", "datasette", ...]` to work around that
  machine's endpoint policy blocking the `datasette.exe` shim). Confirmed
  isolated to the Datasette read-surface, untouched by this round's diff.
  **Deferred** — to be folded into the next round of work on `viewer.py`.
- **Work rig's `L5GN` root was briefly `(MISSING)`** in `run.py config` —
  resolved before depositing; final build carried 19 projects (up from 9).

---

## Tim's ruling

**Sections 1–5: walked and MET, in full**, on both hermetic tester evidence
(sections 1.4 excepted, which is real-data) and live, hands-on confirmation
across all three machines — including two items (1.1–1.3) walked by direct
scanner call rather than only through the automated tester.

**The two deferred findings (`tester_serve` divergence, cache-staleness gap)
are accepted as future work, not blockers for closing this pair:**
`tester_serve`'s fix waits for the next round of work on `viewer.py`; the
cache-staleness gap waits for its own look. Neither affects what this brief
set out to fix, and both are named here so they aren't rediscovered from
scratch later.

**The extra tainted snapshot and the `Chronicler_Backup` false-positive were
both treated as "go find out," not "assume and move on"** — finding a third
bad snapshot beyond the brief's count is expected texture of remotely
maintaining the knight, not a surprise or a process failure, and
`DATA_DIR_NAMES` is left unchanged on the evidence that the one nonzero
`Chronicler_Backup` reading was prose, not a leak.

**Overall: this brief's fix is confirmed landed, tested two ways (automated +
by hand), and its actual object — the two (now three) tainted deposits — is
remediated and re-measured clean on the knight.** Pair closed.
