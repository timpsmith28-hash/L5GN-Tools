<!-- gate-frozen: commit=86fca68 -->

# Cowork report — scanner scope bypass

Pair: `docs/COWORK_BRIEF_scanner_scope_bypass.md`. Session 2026-08-03, on top of
`86fca68`. **BUILD, then STOP — nothing committed; everything staged for Tim's
review.** Ran in a Cowork sandbox with the git clone only — no tailnet reach to
the knight, gaming rig or work rig, so Task 3's actual remediation is a runbook,
not an executed remediation. See "What this session could not do" below.

`python verify.py` — **GREEN**, 6 auditors + **54** testers at this build.
*(Frozen build-time count, written `**N**` per the estate's convention for
historical gate figures.)*

| Task | State | What landed |
|---|---|---|
| Precondition — DECISIONS 0029 | **already ratified** | `Status: accepted` found in the working tree; not re-drafted |
| 1 — scope structural for `file_census` / `workspace_scanner` | **green** | both now consult `Scope`; per-scanner import kept, reasoning below |
| 2 — the tester iterates the registry | **green** | `tester_scanner_scope` now runs every `registry.SCANNERS` entry against a planted data dir |
| 3 — measure + remediate the knight's deposits | **runbook only** | `docs/RUNBOOK_scope_bypass_remediation.md` — needs a machine with tailnet access |
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

## Task 3 — measured on paper, not executed here

**This Cowork session has the git clone only.** `hostname` inside its sandbox
is `claude`, not `LucasGoonPC`, `10280L` or `l5gn-castle` — there is no tailnet
route to the knight from here, so the actual measure-rebuild-redeposit-remove
sequence cannot run in this session.

Per the answer given when this was raised: **`docs/RUNBOOK_scope_bypass_remediation.md`**
is written so the sequence is copy-paste ready on whichever machine has the
access. It carries:

- a **before** measurement command (the brief's own substring-count technique,
  extended to include `Chronicler_Backup` per the diagnosis table, with an
  explicit instruction to flag — not silently absorb — a nonzero count that
  isn't already nested under a recognised data-dir ancestor);
- rebuild-on-fixed-producer steps for both rigs, each gated on a **local**
  zero-count check before depositing anything;
- the DECISIONS 0029 deletion step on the knight (`estate.json`,
  `deposit_manifest.json`, and the single `history/estate-2026-07-25.json` per
  estate — **exactly two bundles, exactly one snapshot each**, matching the
  brief's own dating: both from one commit, one morning, and no deposit since);
- deposit + consume, then the **same** measurement re-run against the fresh
  landing, so the remediation is confirmed clean rather than merely claimed.

The dated exposure is not re-derived here (brief's own instruction): `6d09eb3`
(scope discipline) landed 09:32:56; `1951cfe` (carrying the guard, but not in
the two unwired scanners) is 09:35:22; the two violating deposits followed 25
and 48 minutes later. No deposit has happened since (rig built on `a202ba0`,
never pushed), so remediation is bounded and small, not a backlog.

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

## What this session could not do

- **No deposit was measured, rebuilt or removed.** This sandbox has the git
  clone and nothing else — no `LucasGoonPC`, `10280L` or `l5gn-castle` reach.
  The runbook exists so that gap doesn't become a blocker; the actual
  before/after counts still need to come from a walk on the real machines.
- **The knight's stale local `data/estate.json`** — explicitly out of scope
  per the brief (it never travels; fixed by a re-census after the scanners
  are, which this session's fix now enables).
- **No `Chronicler_Backup` code change.** It appears in the brief's own
  diagnosis table as a substring match; whether it names a top-level directory
  outside the `raw_*`/`*_files` families that `DATA_DIR_NAMES` should also
  recognise is a question the runbook asks the operator to check with real
  data, not something this session had evidence to decide either way.

---

## UAT

Walk-sheet: `docs/UAT_scanner_scope_bypass.md`. The results log needs a `uat:`
stamp naming the commit once walked (`docs/README.md` §3) — no `gate=` field,
per the brief. An acknowledgement line belongs on
`docs/investigation/2026-08-02_knight-roles_claude_2-response.md` (K3/K4) once
this lands.
