<!-- gate-frozen: commit=f5a14d2 -->
<!-- uat: commit=f5a14d2 dirty=false host=multi-rig walked=2026-08-03 -->

> **ARCHIVED** 2026-08-24 · completed pair · partner: `docs/archive/COWORK_BRIEF_scanner_scope_bypass.md`
> Superseded by the tree for anything about current behaviour. Original purpose: testimony for the scope-bypass round, built on `86fca68` and committed as `f5a14d2`.
> Accurate history: the walk across the gaming rig, the work rig and the knight on 2026-08-03, and the remediation re-measured live in that same session. Its gate figure — 6 auditors + **54** testers — is frozen at `f5a14d2` and already carries `gate-frozen`; it is not a claim about the gate now. The `tester_serve` failure it notes on the work rig was pre-existing and unrelated to this round, and is not evidence about that tester today.

# Cowork report — scanner scope bypass

Pair: `docs/COWORK_BRIEF_scanner_scope_bypass.md`. Built 2026-08-03 on top of
`86fca68`, committed as `f5a14d2` ("fix: file_census and workspace_scanner now
honor the Scope data-dir guard"). **Fully walked** — the code fix, the
registry-iterating tester, and Task 3's actual remediation were all executed
and independently re-measured across the gaming rig, the work rig and the
knight in the same session that produced this report. Task 3 started as a
runbook (this session's Cowork sandbox has no tailnet reach to any of the
three machines) and was then walked live, over chat, with Tim running every
command on the real rigs.

`python verify.py` — **GREEN** on the gaming rig at commit time, 6 auditors +
**54** testers. *(Frozen build-time count, written `**N**` per the estate's
convention for historical gate figures. The work rig shows one pre-existing,
unrelated `tester_serve` failure — see "Found during the live walk" below;
not caused by and not blocking this round.)*

| Task | State | What landed |
|---|---|---|
| Precondition — DECISIONS 0029 | **already ratified** | `Status: accepted` found in the working tree; not re-drafted |
| 1 — scope structural for `file_census` / `workspace_scanner` | **green, walked** | both now consult `Scope`; per-scanner import kept, reasoning below |
| 2 — the tester iterates the registry | **green, walked** | `tester_scanner_scope` now runs every `registry.SCANNERS` entry against a planted data dir; red/green verified by hand on both scanners |
| 3 — measure + remediate the knight's deposits | **done, walked live** | both estates re-measured clean on the knight after remediation; see results below |
| 4 — restate the disclosure boundary | **green** | field-by-field table below |

---

## Precondition — DECISIONS 0029

Already in the working tree, `Status: accepted`, matching the brief's draft
verbatim. Not re-drafted or re-ratified here; treated as a given per the brief's
own instruction ("draft this to Tim, get it ratified, then build" — it was
already ratified before this session started).

---

## Task 1 — scope made structural, not per-scanner (with the refusal stated)

**The brief's own question first: should the walk itself live in one shared
helper, so this defect class becomes impossible rather than merely absent?**

**Declined**, and here is why. The two unwired scanners do not share a walk
shape with each other or with the six that already route through `Scope`:

- `file_census` does its own `os.walk` with in-place directory pruning, because
  it must classify *why* a subtree is excluded (vendored / ignored / `.git`)
  and roll each reason up with exact file/byte counts — that tiering logic
  (Tier 1/2/3, the depth cap, the mass rollup) has no equivalent in the six
  `iter_files`-based scanners and can't be expressed as "skip or don't" at the
  single-file granularity `Scope.skip()` offers.
- `workspace_scanner` **does** share the exact shape of `import_scanner` — same
  `iter_files(target, suffixes=(".py",))` loop, same per-file skip-or-parse
  decision. For this one, unification was real: it now uses `Scope` in full
  (not just the data-dir slice), matching `import_scanner` exactly, so the two
  python-content scanners can no longer drift apart on what "in scope" means.

So the structural fix is not one universal walker — it is extending `Scope`
itself with a second, narrower entry point for the one caller whose walk
`Scope.skip()` genuinely can't serve:

```python
def skip_dir(self, name: str) -> bool:
    """Bare directory *name* -> data-dir or not, for callers that prune whole
    subtrees before walking them (file_census) rather than filtering
    individual file paths."""
```

`file_census` now prunes `dirnames` against `scope.skip_dir(name)` **before**
`_classify_dir` ever sees the directory — data-dir wins over vendored/ignored
classification, so a chat archive is never rolled up as mass, never tiered,
never walked at all, exactly like the six scanners' existing "data_dir wins
over gitignore" rule. The skip is counted once per pruned directory (not once
per file inside it) — counting files would mean walking the tree, which is
precisely what this guards against; the doctrine is "we did not read your chat
archive," not "we read it only far enough to count it." Both scanners now emit
a `"scope"` block identical in shape to the other six.

**Task 2 is what actually makes this structural**, not Task 1's per-scanner
`skip`/`skip_dir` call: a scanner that calls neither one now fails a gate that
runs on every registered scanner, every build, forever — including one that
doesn't exist yet. That is the honest answer to "how do we make this
impossible rather than absent": not a single walker, but a single verifier that
iterates the same list every scanner is already registered in.

**A circular import, found and worked around.** `_scope.py` imports
`_git_lookup` / `status_of` from `file_census` (reusing its one `.gitignore`
implementation, per the original bugfix brief). A module-level
`from ._scope import Scope` inside `file_census.py` would therefore be
circular. Deferred to a function-local import inside `scan()` — noted in a
comment at the call site so a future reader isn't left to rediscover why.

---

## Task 2 — the tester now iterates the registry

Before: `tester_scanner_scope` imported exactly one scanner
(`todo_adr_scanner`) plus the `Scope` primitive. Green meant "todo_adr_scanner
respects scope," not "scanners respect scope" — and had no way to fail for
`file_census` or `workspace_scanner`, because nothing in it ever ran them.

Now: the tester plants a data directory named `raw_<random-sentinel>_files`
(a fresh random token per run, so a match can only be the fixture — never a
coincidence against this repo's own real `data/`, which genuinely does carry
the literal string `raw_claude_files` today) into a two-project fixture, runs
**every** `mod` in `registry.SCANNERS` (`scan_estate(projects)` for
estate-level scanners, `scan(proj)` for the rest, matching the existing
`tester_scanners.py` convention), and asserts the sentinel never appears
anywhere in any scanner's JSON-shaped output — recursively, across every key,
list and nested dict, not just the fields the brief already knows about.

This generalises correctly to scanners that never touch a file tree at all
(`git_summary`, `bloat_audit`, `drift`, `estate_diff`, `vault_reader`,
`project_trail`, `estate_status`): they trivially pass, because they never see
a path in the first place. That is the right behaviour, not a gap in the
check — the assertion is "no scanner leaks this," which subsumes "scanners
that don't walk trees can't leak it."

**Verified both directions by hand**, per the brief's own UAT instruction:
removing `scope.skip_dir(name)` from `file_census` (and separately,
`scope.skip(path)` from `workspace_scanner`) turns the gate red, naming the
offending scanner exactly:

```
1 violations
 - workspace_scanner: leaked the planted data directory ('raw_scopeleak...') into its output -- scope not honoured
```

Restoring the call returns the gate to green. `python verify.py` is GREEN with
both fixes in place, 6 auditors + 54 testers.

---

## Task 3 — measured, remediated, re-measured clean

Started as `docs/RUNBOOK_scope_bypass_remediation.md` (this Cowork sandbox has
no tailnet route to any of the three rigs), then walked live: Tim ran every
step on the gaming rig, the work rig and the knight, pasting output back for
each check before the next step ran. The runbook held up with two amendments,
both real findings the brief didn't anticipate.

### Finding: `run.py build` without `--fresh` silently ships stale scans

`report.py`'s `_scan_one_project` reuses a per-project, per-scanner cache file
(`data/<scanner>/<project>.json`) **whenever one already exists on disk**, with
no check on whether the scanner's code changed since it was written — and the
`scanned <name>` progress line prints identically whether it actually re-ran
the scanner or silently served the cache. On the gaming rig, the first
post-fix `build` (no `--fresh`) looked clean by the blunt substring count but
still carried real data-dir paths from four projects' pre-fix caches, caught
only by re-running the precise path-aware leak check (below). `--fresh` on
both rigs resolved it; the runbook now calls this out explicitly so it isn't
rediscovered the hard way on a future round.

### Finding: an undocumented third tainted snapshot

The brief's dating — "exactly two bundles, one commit, one morning, no
deposit since" — was accurate for the *current* deposits but missed an older
history snapshot. Before deleting anything, the knight's `history/` dirs were
inspected rather than trusted to match the brief:

| snapshot | disposition | measured |
|---|---|---|
| `personal/history/estate-2026-07-17.json` | **kept — clean** | 0 matches |
| `personal/history/estate-2026-07-25.json` | removed (brief's finding) | not re-measured before delete; superseded per 0029 regardless |
| `work/history/estate-2026-07-21.json` | **removed — newly found, tainted** | 5,812 matches (`raw_gemini_files` 993, `chat_threads` 2410, `vault_staging` 1404, `Takeout` 993, `raw_claude_files` 12) |
| `work/history/estate-2026-07-25.json` | removed (brief's finding) | not re-measured before delete; superseded per 0029 regardless |

Three snapshots removed, not two; one older one kept because it measured
genuinely clean rather than being deleted on the assumption that "older than
the fix" automatically means "tainted." DECISIONS 0029 was applied identically
to the newly-found snapshot — replaced/removed, not edited.

### Before/after, both estates

| estate | before (personal deposit table, brief's own count) | after remediation, on the knight |
|---|---:|---|
| `estates/personal/estate.json` | **9,159** matches | **0** real leaks — see caveat below |
| `estates/work/estate.json` | **2,328** matches | **0** |

**Personal estate caveat, checked rather than assumed:** the whole-file
substring count on the fresh personal deposit read `23 total
(raw_claude_files: 1, Chronicler_Backup: 22)`, not zero. Re-run through the
precise, path-aware check (parses the JSON, walks every `path` field, tests
each with `is_data_dir_name` — the same check that cleared a false alarm on
the work rig's whole-file count earlier in this round) returned `leaks: NONE`.
`L5GN-Tools` is confirmed present in the personal estate's own project list
(self-scanned, `is_project` root per DECISIONS 0020) — its own docs
(`DECISIONS.md`, this brief/report/runbook) now discuss `raw_claude_files` and
`Chronicler_Backup` extensively as their subject matter, correctly read by
`doc_census`/`blast_radius`/`todo_adr_scanner`. No `Chronicler_Backup`-named
directory was found outside a recognised `raw_*`/`*_files` ancestor on either
estate, so `DATA_DIR_NAMES` needs no widening from this round's evidence —
noted as checked, not assumed.

### Two rig-specific findings, neither a regression from this round

- **Work rig, `run.py config`:** the `L5GN` root briefly showed `(MISSING)` —
  resolved before depositing; the rebuild went from 9 to 19 projects once
  fixed.
- **Work rig, `tester_serve` RED, permanently, until reconciled separately:**
  an uncommitted, deliberate local edit to `l5gntools/viewer.py` on that
  machine (confirmed via `git diff`, not a shadow import — `__file__` points
  at the correct repo path) routes the Datasette invocation through
  `[sys.executable, "-m", "datasette", ...]` instead of a bare `datasette`
  call, working around that endpoint's policy blocking the `datasette.exe`
  shim while `-m` still runs. Isolated to the Datasette read-surface
  (DECISIONS 0007/0013); confirmed untouched by this round's diff and by
  `git log` on `viewer.py` (last touched in `48ce16d`, long before this
  round); does not affect `file_census`, `workspace_scanner`, `build`,
  `deposit` or `consume`. **Not fixed here** — worth its own small follow-up
  (teach `datasette_argv`/`datasette_available` to prefer `-m` when the shim
  isn't runnable, or update `tester_serve` to accept both shapes) so this rig
  stops carrying a permanent uncommitted diff and a permanently-red gate.

### Confirmed, not merely claimed

Final measurement on the knight, post-`consume`: `work/estate.json` — 0;
`work/history/estate-2026-08-03.json` — 0; `personal/estate.json` — 23
substring / 0 real (see caveat above); `personal/history/estate-2026-07-17.json`
— 0 (kept); `personal/history/estate-2026-08-03.json` — 23 substring / 0 real.
Both `deposit_manifest.json`s report `manifest_verified: true` implicitly via
successful `consume` (sha256 match). Task 3 is closed.

---

## Task 4 — the disclosure boundary, field by field

D3/D4 (`UAT_toolkit_self_scan_results.md`) ruled labelled `outliers[]` /
`mass[]` disclosure-by-design. That ruling is about *labelled outlier paths in
a scanned repo* — never about walking data directories — and this round must
not blur the two by accident while fixing the second.

| field | scanner | disposition | why |
|---|---|---|---|
| `directories[].path` | `file_census` | **scope bypass — fixed** | Tier 1 rollup of the working-set tree; a data dir pruned before this loop runs can never contribute an entry. |
| `files[].path` | `file_census` | **scope bypass — fixed** | Tier 2 per-file working set; same pruning applies before the file loop. |
| `at_risk[].path` | `file_census` | **scope bypass — fixed** | Named in the brief explicitly; an untracked file inside a data dir could previously appear here. Impossible now — the directory is never entered. |
| `mass[].path` | `file_census` | **deliberate disclosure — unaffected** | Design bias 2 in the module docstring: an unprotected vendored/ignored tree is reported as one rollup entry with an exact count, "so a reader can see the mass without paying for it." Data dirs never routed through mass before or after this fix (pre-fix they fell into Tiers 1/2 as ordinary directories, which was the bug) — this field's disclosure contract is untouched. |
| `outliers[].path` / `summary.largest` | `file_census` | **deliberate disclosure — ruling restated, population now clean** | D3/D4's exact ruling. Before this fix, the 20-largest-files heap drew from *whatever the walk touched*, which could include a large file inside a data dir if the pruning bug let the walk reach it — a scope-bypass instance riding on a ratified mechanism, not a flaw in the mechanism itself. The fix prunes data dirs before any walk, including the outlier heap's, so the ratified disclosure now provably can never surface a data-dir path. The ruling is restated, not revoked or widened. |
| `basenames_beyond_cap` | `file_census` | **deliberate disclosure — unaffected in kind, population now clean** | Basenames only (S4's filename cross-reference), drawn from the same working-set population as `files[]` — a data-dir basename could previously leak here for the same reason as the outlier heap; now excluded by the same pruning. |
| `modules[].path` | `workspace_scanner` | **scope bypass — fixed** | Named in the brief explicitly. A `.py` file inside a bulk export (unlikely but possible — export tooling, a saved script) would have been AST-parsed and its path emitted; `scope.skip(path)` now excludes it before `ast.parse` ever runs. |
| `top_classes` / `classes` (content, not a path field) | `workspace_scanner` | **scope bypass — fixed, noted for completeness** | Not path-bearing, but content-bearing: a class name from a data-dir `.py` file could previously enter this list. The same `scope.skip` prevents the file from ever being parsed, so this is fixed as a side effect rather than a separate change. |

**Two honest caveats carried forward from the brief, unchanged by this round:**
`todo_adr_scanner.markers[].text` matching twice on prose *mentioning*
`raw_claude_files` (not a path) is a detection-heuristic looseness in an
already-correct, already-wired scanner — out of this round's scope, noted so
it isn't lost. And the `outliers[]` / `summary.largest` ruling above is
restated, not re-litigated.

---

## Files touched

Build:

- `l5gntools/scanners/_scope.py` — new `Scope.skip_dir(name)` for directory-
  pruning callers.
- `l5gntools/scanners/file_census.py` — consults `scope.skip_dir` before
  `_classify_dir`; emits a `scope` block; `git` now comes from `scope.git`
  (one `_git_lookup` call, not two).
- `l5gntools/scanners/workspace_scanner.py` — adopts `Scope` in full (matching
  `import_scanner`); `vendored_py_files_excluded` now reads from
  `scope.skipped["vendored"]`; emits a `scope` block.

Tests:

- `tests/tester_scanner_scope.py` — rewritten to iterate `registry.SCANNERS`
  against a planted, randomly-sentineled data directory across two fixture
  projects (the second so estate-level cross-project scanners like
  `duplicate_finder` get a fair chance to leak too). The prior `is_data_dir_name`
  predicate checks and the non-git `Scope` checks are kept.

Docs (this pair):

- `docs/COWORK_REPORT_scanner_scope_bypass.md` — this file.
- `docs/UAT_scanner_scope_bypass.md` — walk-sheet.
- `docs/RUNBOOK_scope_bypass_remediation.md` — new. Copy-paste remediation
  sequence for a machine with tailnet access to the knight.

Not touched: `docs/DECISIONS.md` (0029 was already in the working tree,
`Status: accepted`, before this session started).

---

## What was deliberately left alone

- **The knight's stale local `data/estate.json`** — explicitly out of scope
  per the brief (it never travels; fixed by a re-census after the scanners
  are, which this session's fix now enables). Still 8 days stale; not
  rebuilt as part of this round.
- **No `DATA_DIR_NAMES` change.** `Chronicler_Backup` was checked, live,
  against both estates post-remediation (see Task 3) and did not name an
  unrecognised top-level directory on either — the substring hits were
  `L5GN-Tools`'s own prose. `DATA_DIR_NAMES` is left as-is on the evidence
  gathered; the question is closed for this round, not left open.
- **`tester_serve`'s work-rig divergence** — real, understood, deliberately
  not fixed here (see Task 3). Isolated to a different subsystem.
- **The `run.py build` cache-staleness gap** (no invalidation on toolkit
  version/commit) is noted in the runbook and in Task 3 above, but not fixed
  in this round — it's a correctness hazard for *any* future scanner fix, not
  specific to this one, and deserves its own look rather than a patch bolted
  on under this brief's scope.

---

## UAT

Walk-sheet: `docs/UAT_scanner_scope_bypass.md`, fully walked 2026-08-03.
Results log stamp: `<!-- uat: commit=f5a14d2 dirty=false host=multi-rig
walked=2026-08-03 -->` (no `gate=` field, per the brief). An acknowledgement
line belongs on
`docs/investigation/2026-08-02_knight-roles_claude_2-response.md` (K3/K4) once
this lands.
