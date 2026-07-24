# Cowork report — file census

Pair: `docs/COWORK_BRIEF_file_census.md`. Session 2026-07-21, on top of `03bac5d`.

**Round 1 scope: A, B and D** — the brief's own stated floor. **Round 2 (§9)
added C and E and refined the report tab against Tim's first real build**, so
**all five tasks are now green.** Nothing is committed; everything is staged for
review. §§1–8 are round 1 as written; §9 is the round-2 append and **supersedes
§3's deposit-size projection with a measured figure.**

`python verify.py` — **GREEN**, 6 auditors + 28 testers (see §9: this number
changed in round 2, and `auditor_doc_claims` caught the stale copy in this file).

---

## 1. Tasks: green vs pending

| Task | State | What landed |
|---|---|---|
| **A** — `file_census` scanner | **green** | `l5gntools/scanners/file_census.py`, registered in `registry.py` (position 2, straight after `workspace_scanner`) |
| **A** — tester | **green** | `tests/tester_file_census.py`, registered in `verify.py` |
| **B** — stop the scan touching `.git` | **green** | Both call sites fixed; `run_git` now injects the flag; `common.git_argv` extracted as the pure, testable core |
| **D** — collapsible tree in `report.html` | **green** | New **Files** tab in `l5gntools/report.py`; at-risk set above the fold; inline JS/CSS, no CDN |
| **C** — `run.py census` | **pending** | Not started. Out of agreed scope |
| **E** — `deploy/pull-report.ps1` | **pending** | Not started. Out of agreed scope |

Housekeeping: `README.md` tools table has its `file_census` row. No doc in the
core set states a tool count, so nothing went stale there — checked by hand,
since `auditor_doc_claims` polices only auditor/tester counts and would not have
told me.

---

## 2. Worked example — the census of L5GN-Tools itself

`python run.py file_census --target L5GN-Tools`, run against this tree with the
session's own edits in place:

```json
{"total_files": 890, "total_bytes": 9350891,
 "working_set": {"files": 144, "bytes": 1080258},
 "mass":        {"files": 746, "bytes": 8270633},
 "at_risk":     {"files": 2,   "bytes": 26203},
 "largest": "data/history/estate-2026-07-17.json"}
```

**The at-risk set named exactly two files** — and they are the two files this
session created and has not committed:

```
l5gntools/scanners/file_census.py   16,159 B   2026-07-21T13:09:26+01:00
tests/tester_file_census.py         10,044 B   2026-07-21T13:10:20+01:00
```

That is the scanner passing its own acceptance test in the only way that counts:
asked what was on disk and not safe in git, it named the work in progress.

The tiering, top of the mass list:

| Path | Files | Bytes | Why excluded |
|---|---:|---:|---|
| `data` | 127 | 5,742,514 | ignored |
| `.git` | 456 | 947,298 | git-internal |
| `.` (loose ignored — `report.html`) | 1 | 592,977 | ignored, partial |
| `chronicler/pipeline/__pycache__` | 24 | 312,067 | ignored |
| `tests/__pycache__` | 53 | 301,135 | ignored |

**84% of this repo by file count, and 88% by bytes, is mass.** That ratio is the
whole argument for the three tiers: a flat per-file census of L5GN-Tools would
have carried 890 entries to say what 144 entries plus 13 rollups say better.

### Three shape decisions worth ratifying or overruling

1. **`.git` is Tier 3 mass with `reason: "git-internal"`** — a third reason value
   beyond the brief's `vendored`/`ignored`. Repo storage is a real 947KB on the
   box, and "before archiving a dormant repo" is exactly when its size matters.
   It also makes `total_files` match what Windows Explorer counts, which is
   UAT check A. `git-internal` is never eligible for `at_risk`.

2. **Two git invocations per project, not one** — `ls-files -z` and
   `status -z --porcelain --ignored`. Both are O(1) per project; the brief's
   actual constraint ("do not shell out per file") holds. Untracked files are
   never enumerated because they don't need to be: anything git does not list as
   tracked and does not report as ignored is untracked by elimination. That
   deliberately leaves `--untracked-files` at its default, so a wholly-ignored
   `.venv` stays collapsed to one record instead of expanding into thousands —
   which is the cost the tiering exists to avoid.

3. **At-risk inside a Tier 3 tree is a rollup, not a truncation.** A vendored
   tree that is *not* gitignored is genuinely unprotected, but listing 8,000
   filenames would be the deposit blowout the brief warns about. It reports as
   one entry carrying the **exact** count and byte total:

   ```json
   {"path": ".venv", "files": 8421, "bytes": 214000000,
    "rollup": true, "reason": "vendored"}
   ```

   Nothing is hidden and no number is approximate. This is not the truncation the
   brief forbids — it is a different granularity, flagged as such, and "this
   entire tree is unprotected" is the more useful sentence than 8,000 paths.
   Per-file at-risk entries in the working set remain uncapped and exempt from
   `FILE_CAP`, exactly as specified.

There is a fourth, smaller one: **`at_risk` over-reports rather than
under-reports.** A file git has not claimed and has not called ignored is
classified `untracked`. A false positive costs a glance; a false negative costs a
file.

---

## 3. The deposit size — the claim, measured

`estate.json` **before: 928,120 bytes.** That is the honest measurement I can
make from this session, and here is why it is not a before-and-after pair:

**Only L5GN-Tools is reachable from this session.** The other eleven projects are
not mounted, so `python run.py build` cannot run against the real estate and I
will not report a number I did not measure. What follows is a *projection* built
from measured unit costs, and the true after-figure is UAT check F below.

Measured, on the real census of this repo:

| Component | Bytes (`indent=2`, as `write_json` emits) |
|---|---:|
| `files` (Tier 2, 144 entries) | 19,657 |
| `directories` (Tier 1, 18 entries) | 2,631 |
| `outliers` (20) | 2,079 |
| `mass` (Tier 3, 13 entries) | 1,382 |
| `summary` + `at_risk` + scalars | 541 |
| **total** | **28,971** |

Tier 2 dominates at **137 bytes per file entry**, which makes the size contract
arithmetic rather than hope:

- **Hard ceiling per project** = `FILE_CAP` × 137 ≈ **273KB**, whatever the repo
  contains. An unbounded census has no such ceiling — this is what the cap buys.
- **Projected across the seven git projects**, using each one's tracked-file
  count as a working-set proxy: **+270KB**, taking `estate.json` from 928KB to
  roughly **1.20MB (+29%)**. Largest contributors: `L5GN_Armory_v4` (~110KB),
  `L5GN-Castle` (~84KB).
- **Four projects are not git repos** (`L5GN-Archive`, `L5GN-Crystal-Spire`,
  `L5GN-server-hub-iso`, `test_folder`) so no tracked count exists to project
  from. Their working sets are bounded only by the cap, so the worst case adds
  4 × 273KB ≈ 1.1MB. **Realistic estate.json after: 1.2MB; absolute worst case:
  2.3MB.**

**My reading:** +29% for a browsable inventory of the whole estate is a fair
trade, and the cap means the number cannot run away. But the ceiling is set by
`FILE_CAP` alone, and 2000 was inherited from the brief rather than derived from
anything. If the measured after-figure lands above ~1.5MB, the lever to pull is
`FILE_CAP`, not the tiering.

One thing the numbers surfaced that is not about the census: `data/` is 5.7MB and
127 files of it, and three separate copies of a ~929KB `estate.json` snapshot are
sitting in `data/history/` and `data/outbox/personal/`. That is ignored, so it
never leaves the box — but it is worth a glance.

---

## 4. Task B — could `auditor_readonly` have caught this?

**No. Plainly no, and for two independent reasons.**

**First, it is looking at the wrong thing.** `auditor_readonly` AST-walks scanner
source for calls whose *name* mutates the filesystem — `write_text`, `mkdir`,
`unlink`, `open(...,'w')`. The offending line was

```python
run_git(target, "status", "--porcelain")
```

There is no forbidden call there. The write happens inside `git`, in another
process, several frames away from anything the AST can see. A `subprocess.run`
of an arbitrary argv is opaque to a name-based auditor by construction, and no
amount of extending the forbidden-attribute list changes that.

**Second, one of the two call sites is outside its reach entirely.** It iterates
`registry.SCANNERS`. `l5gntools/common.py:155` (`toolkit_git_info`) is not a
scanner, so that call site was never in scope — and it runs on **every single
build**, via `report.build_estate`.

So the auditor's promise is broader than its reach, and that is worth knowing:
its docstring says *"Scanners must not write to disk"*, but what it actually
enforces is *"scanner source must not contain a call whose name is a known
filesystem mutator."* Those are very different guarantees, and the gap is exactly
where this bug lived. Two honest options, neither built here:

- **Narrow the docstring** to what it enforces. Cheap, and stops the auditor
  claiming a guarantee it cannot make.
- **Add a sibling auditor** — say `auditor_subprocess` — that checks argv-building
  `subprocess`/`run_git` calls against an allowlist. Now feasible *because* of
  this session's change: `common.git_argv` is a pure function, so the invariant
  "every read-only git invocation carries `--no-optional-locks`" is checkable
  without spawning git. `tester_file_census._check_no_optional_locks` already
  asserts it for `git_argv` itself; an auditor would extend that to call sites.

**An accidental live demonstration.** Late in the session I ran a bare
`git status --porcelain` by hand to list the staged changes. It left a
`.git/index.lock` behind that it could not clean up, and that stale lock would
have blocked the next git operation in this repo. (Removed; `git status` is clean
again.) The same command a scanner used to run, doing the same thing, in this
repo, today. Every scanner invocation immediately before and after it — including
a full `file_census` and `git_summary` pass — left `.git/index` untouched. The
flag is not theoretical.

**What was built instead** (the brief's "build it only if it stays simple" —
it stayed simple, ~20 lines):

```python
READ_ONLY_GIT_SUBCOMMANDS = frozenset({"status", "diff", "ls-files", "log", ...})

def git_argv(path, args):
    """--no-optional-locks is a GLOBAL option, so it goes before the subcommand."""
```

An **allowlist, not a denylist**: a subcommand nobody has considered gets no
injection and behaves exactly as it does today, so adding one is a decision
rather than an accident. Injection is idempotent, so the two fixed call sites
still pass the flag explicitly — the intent stays greppable where the risk is,
and `run_git` catches whoever forgets next time. Four behaviours are asserted:
injection happens, the flag lands *before* the subcommand (git rejects it after),
an explicit flag is not duplicated, and the allowlist does not leak into
`commit`.

---

## 5. Task D — the tree

New **Files** tab, between *Code Inventory* and *Docs*. Self-contained: native
`<details>`/`<summary>` does the collapsing, so there is no toggle script to go
wrong, no framework and no CDN. ~90 lines of JS and ~20 of CSS, in the existing
generator's style.

- **The at-risk set renders first**, in a bordered panel above every project, with
  the project name against each path. It is visible without scrolling. Rollup
  entries render as *"whole vendored tree: 8,421 files"* so a rollup can never be
  mistaken for a single file.
- **Every directory row carries its subtree file count and size**, so the mass is
  visible while collapsed. Totals are computed in the browser from Tier 1's
  *direct* counts, which is why no byte is counted twice.
- **Tier 3 rows are one line, dimmed, with a reason pill, and cannot expand** —
  there is nothing behind them.
- Depth-collapsed directories say so. A truncated project says so, and says the
  directory totals and the at-risk set are still complete.
- **Trees build on first expand.** Eleven full trees up front is a lot of DOM for
  a page whose whole point is that it opens instantly from a `file://` URL.

Verified headlessly: the tab's render function was executed under a DOM stub in
Node against two *real* censuses (this repo, and the tester's synthetic repo).
Eleven assertions green, including *"`.venv` appears as a mass row"*, *"`.venv` is
not expandable"*, *"no per-file entry from inside `.venv`"* and *"`<details>` tags
balance"*.

---

## 6. Assimilation list

- **`SKIP_PROJECT_NAMES` in `chronicler/pipeline/build_registry.py:78`** —
  `{"outputs", "uploads", "test_folder"}`. Noted, not changed, as instructed. The
  census sharpens the point: `test_folder` shows up as a full project in
  `estate.json` with its own census, so the junk is being scanned and deposited
  and then filtered at the *registry* end. The fix belongs in the scan path
  (roots config), not in a name denylist downstream.
- **`auditor_readonly`'s docstring overclaims** — see §4. Either narrow it or
  build `auditor_subprocess`.
- **`data/` holds three ~929KB copies of the same `estate.json` generation** across
  `history/` and `outbox/personal/`. Ignored, so harmless; still worth a look.

---

## 7. Files touched

**New**

- `l5gntools/scanners/file_census.py`
- `tests/tester_file_census.py`
- `docs/COWORK_REPORT_file_census.md` (this file)
- `docs/UAT_file_census.md`

**Modified**

- `l5gntools/common.py` — `NO_OPTIONAL_LOCKS`, `READ_ONLY_GIT_SUBCOMMANDS`,
  `git_argv()`; `run_git` routed through it; `toolkit_git_info` explicit
- `l5gntools/scanners/git_summary.py` — explicit flag on the `status` call
- `l5gntools/registry.py` — `file_census` imported and registered
- `l5gntools/report.py` — Files tab, tree renderer, census CSS
- `verify.py` — `tests.tester_file_census` registered
- `README.md` — tools table row

**Nothing is committed.** No results log is written: `docs/UAT_file_census.md`
carries the stamp template, and the log is Tim's to write once he has walked it.

---

## 8. UAT walk-list

Full sheet: `docs/UAT_file_census.md`. Six checks, all **ready to walk**:

| | Check |
|---|---|
| **A** | `run.py file_census --target L5GN-Tools`; `total_files` vs Explorer; at-risk names files Tim recognises |
| **B** | `.git/index` mtime unchanged across a full `build` |
| **D1** | Files tab: expand a tree, find a file by clicking |
| **D2** | At-risk set visible without scrolling; `.venv`-class row shows mass and does not expand |
| **F** | `estate.json` bytes before and after — the real after-figure this session could not measure |
| **G** | Any project reporting `at_risk_note` (not a git repo) is one Tim genuinely intends to leave outside git |

C and E have no checks, because C and E were not built. **Superseded by §9** —
they were built in round 2 and have checks now.

---

# 9. Round 2 — the real build, plus C and E

Tim ran `python run.py build` on the gaming rig (`LucasGoonPC`, estate
`personal`, 11 projects) and handed back the resulting `report.html`. Everything
below is measured from **that** feed, not from a fixture.

`python verify.py` — **GREEN**, 6 auditors + **26** testers.

## 9.1 The deposit size — I was wrong, and by a lot

| | Bytes |
|---|---:|
| `estate.json` **before** | 928,120 |
| `estate.json` **after** (measured) | **3,350,576** |
| §3's projection | 1,197,972 |
| `report.html` on disk | 2,393,421 |

**The measured figure is 3.6× the starting size and 2.8× my own projection.**
Not a rounding error — a wrong model, and worth saying plainly rather than
burying.

Where the census payload actually goes (2,110,371 bytes, **63% of the whole
feed**):

| | Bytes | Share of census |
|---|---:|---:|
| Tier 2 per-file entries | 1,126,392 | 53% |
| **`at_risk`** | **791,152** | **37%** |
| Tier 1 directories | 38,623 | 2% |
| Tier 3 mass + the rest | ~154,000 | 7% |

**What I got wrong:** §3 modelled Tier 2 from tracked-file counts and treated
`at_risk` as a rounding error — L5GN-Tools' at-risk block was 234 bytes, so I
never modelled it at all. On the real estate `at_risk` is the **second largest
component of the entire census**, and 784,789 of its 791,152 bytes come from one
project.

The lesson is not "the cap was too high". It is that I projected the *bounded*
part of the output and ignored the *unbounded* one — and the unbounded one is
unbounded on purpose, because the brief was right that a truncated at-risk list
is worse than none. `FILE_CAP` did its job: only L5GN-Castle hit it (3,805
working-set files capped to 2,000, `truncated: true`, honest). The cap is not
the lever here.

## 9.2 The one project driving all of it

| Project | Census bytes | Tier 2 | at_risk | At-risk files |
|---|---:|---:|---:|---:|
| **L5GN-Castle** | **1,341,094** | 476,046 | 784,789 | **3,624** |
| L5GN-Crystal-Spire | 354,739 | 326,659 | 728 | 7 |
| L5GN_Armory_v4 | 165,063 | 142,857 | 1,840 | 11 |
| *(eight others)* | 249,475 | 180,830 | 3,795 | 27 |

**L5GN-Castle is 64% of the census payload**, and **3,599 of its 3,624 at-risk
files are in one directory: `data/`** — untracked, and not matched by any
`.gitignore` pattern. Across the whole estate that single directory is 98% of the
at-risk set.

You've said `data/` is on the roadmap for a reorg, so this is reported rather
than acted on. But the size of the prize is worth stating, and it is not a guess:
I re-derived Castle's census with `data/` moved into Tier 3, exactly as the
scanner would emit it if the directory were ignored.

| | Now | With `data/` ignored |
|---|---:|---:|
| Castle's census | 1,341,094 | **26,934** |
| `estate.json` | 3,350,576 | **1,857,316** |

**One `.gitignore` line takes the feed from 3.35MB to 1.86MB** and removes the
only truncation in the estate — and, more to the point, it is the difference
between "3,599 files are unprotected" and "3,599 files are deliberately
transient". The census is not asking for a code change; it is asking a question
about `data/`.

Second-order: `report.html` is now **2.39MB**, and it is the thing you open from
a phone on the tailnet. Same fix halves it.

## 9.3 The at-risk panel, refined

Both requested changes are in, plus the grouping you asked for.

- **The panel is a `<details open>`** — open on load, so it is still the first
  thing you see, but one click gets it out of the way.
- **Grouped by project + top-level directory**, sorted by size of the problem.
  The 3,673-row table became **20 rows**; the Castle group reads
  `L5GN-Castle / data/ — 3,599 files · 1.4 GB` and expands to every path,
  largest first. Group bodies render on expand, so the 3,599 rows cost nothing
  until asked for.
- **Nothing is truncated.** Grouping is presentation only. Verified by
  reconciliation, not by eye: the renderer's expanded rows were counted against
  the feed and came to **3,672 vs 3,672**.
- **Rollup entries stay as their own top-level rows**, since a whole unprotected
  tree is not a directory group.
- **`.git` unchanged** — ratified as-is. It renders as one non-expandable mass
  row with its size, which is how it already worked. Asserted both ways now: it
  appears as a mass row in 10 project trees, and as an expandable node in none.
  Worth seeing, given L5GN_Armory_v4's `.git` is **87.1MB** and Castle's
  **47.3MB**.

Verification for D was re-run against **Tim's real feed** rather than a fixture:
the tab's render function executed under a DOM stub in Node, every project tree
and every at-risk group expanded for real, 11 assertions green.

## 9.4 Task C — `run.py census`

New `l5gntools/census.py`, wired into `run.py` as `census`. A **writer**, so it
is deliberately not a scanner and is never registered in `registry.py`; it writes
through `write_json`, which confines it to the machine's own `data/`.

- **Producer domain** — the configured `roots`, via `file_census` unchanged.
  There is no second implementation of the walk, the tiering or the at-risk rule.
- **Consumer domain** — two roots. **Code root** (config `code_root`, falling
  back to the toolkit the command is running from, which *is* the deploy —
  resolution, not a hardcode) and **vault root** (`CHRONICLER_HOME`, then
  `chronicler_home`, then the DB's parent; raises rather than guessing).
- **Named vault components**, because a single 4GB rollup would not answer any
  operational question: `chronicler.db`, its `-wal`/`-shm` sidecars (absent
  reports as *absent*, not as zero), `chat_threads/vault_staging/`, `backups/`,
  `serve-snapshot/`, and `estates/` broken down per bundle.
- `--target PATH` bypasses role routing entirely — the escape hatch for "just
  tell me about this folder" without arguing with config.

**On the wall.** The knight's census necessarily names `estates/personal` and
`estates/work` side by side with their sizes. That is a machine report, not a
deposit: both already sit in a directory the knight owns, and nothing is read
*inside* either bundle. It is said in the module docstring **and asserted in the
tester** — `_check_wall` fails if a bundle entry ever carries a key beyond
name/path/exists/files/bytes, which is what a future "improvement" that started
reading across the two would look like. It is checked rather than trusted
precisely because it is the thing most likely to be "fixed".

`tests/tester_census.py` is hermetic: a synthetic `CHRONICLER_HOME` with a fake
vault, WAL sidecars, backups, a serve-snapshot and two estate bundles, driven
with an injected machine dict. It asserts role routing, that resolvers land on
the injected paths (a hardcode would break the match), that empty config raises
rather than guesses, that a missing vault degrades to a stated error rather than
a silent empty report, and that the writer stays under `DATA_DIR`.

**`code_root` documented** in `config/machines.json`'s knight template. It is
optional; the fallback is correct on a machine nobody has configured.

## 9.5 Task E — `deploy/pull-report.ps1`

The mirror of `push-exports.ps1`, same conventions: `-WhatIf`, list-before-you-
transfer, loud failure, scp over the existing ssh alias, `.part`-then-rename so a
half-pulled report never sits there looking whole.

- One `ssh` round trip probes what actually exists on the knight first, so the
  `-WhatIf` listing is **observed rather than assumed** — sizes and ages for
  `report.html`, `data/census.json` and `data/estate.json`.
- **Lands in `data\knight\`, not the repo root.** Pulling the knight's
  `report.html` over this rig's own would destroy the local build, and the two
  answer different questions.
- **Warns when the knight's newest file is over 24h old.** A stale report passing
  for current state is the failure this pull exists to prevent.
- Anything missing is named; a failed `scp` throws and exits non-zero rather than
  reporting success on a partial pull.

**Not executed.** There is no PowerShell in this build environment, so E is
written and reviewed but unrun — UAT check E is its first real execution, and
should be treated as such. Reviewing it did surface two real bugs, both fixed:
`SupportsShouldProcess` propagates `-WhatIf` to every cmdlet in the script, so
the dry run would have skipped its own `mkdir` and then died on `Resolve-Path`
(a dry run that fails is not a dry run); and `Write-Error` under
`$ErrorActionPreference = "Stop"` terminates before the following `exit 1` ever
runs, so the failure paths are `throw` now.

## 9.6 The gate caught me

Adding `tester_census` moved the registered count from 25 to 26 testers, and
`auditor_doc_claims` promptly failed the gate on **this document** and on the UAT
sheet, both of which still asserted the old gate of `6a/25t` at their heads.

Both corrected, and the UAT stamp template is now `gate=6a/26t`. Noted because §1
said no doc stated a *tool* count and nothing would catch a stale one — that
remains true, and this is the neighbouring class of claim that **is** policed,
doing its job on a doc written four hours earlier.

**Then it did it again, for a worse reason.** This section originally quoted the
auditor's failure message verbatim — and the quoted message contains the very
pattern the auditor scans for, so quoting the error inside a scanned doc *caused
the error*. Two more violations, on the two lines that were describing the fix.

That is funnier than it is serious, but it is a real limitation and belongs on
the list. `auditor_doc_claims`' docstring claims narrative mentions of a past
count are safe because *"only a present-tense assertion of BOTH counts together
trips it"*. That is not what it does: it is a bare regex over prose with no
notion of tense, quotation, code fences or context. A doc discussing a gate
count — a report, an archived brief, a runbook quoting real output — is
indistinguishable to it from a doc *making* the claim. The narrow-and-mechanical
design is right, but the docstring again promises more than the code delivers,
which is the same shape of gap as §4. Cheapest honest fix: skip fenced code
blocks and narrow the docstring. Not built here; §9.7.

## 9.7 Assimilation list — additions

- **`L5GN-Castle/data/` is 98% of the estate's at-risk set** and 45% of
  `estate.json`. Already on the reorg roadmap; the census now quantifies it.
- **`report.html` is 2.39MB** and embeds the whole feed. It is the phone-facing
  artefact. If the Castle fix does not bring it down enough, the split worth
  considering is embedding summaries and lazy-loading per-project detail — but
  that breaks the single-file offline guarantee, so it is a real trade, not an
  obvious win.
- **`auditor_doc_claims` cannot tell a quoted gate count from a claimed one** —
  see §9.6. Its docstring says it only matches present-tense assertions; it is a
  context-free regex. Skipping fenced code blocks would let a report quote real
  output, which is a thing reports need to do. Same overclaiming-docstring shape
  as `auditor_readonly` in §4.
- **Three `.git` directories exceed 20MB** (Armory_v4 87.1MB, Castle 47.3MB,
  Crystal-Spire 20.7MB) against working sets of 702, 3,805 and 1,740 files. Now
  visible, and relevant to the archive-a-dormant-repo question the census was
  built for.

## 9.8 Files touched in round 2

**New:** `l5gntools/census.py`, `tests/tester_census.py`,
`deploy/pull-report.ps1`

**Modified:** `l5gntools/report.py` (collapsible + grouped at-risk panel),
`run.py` (`census` command, help, tool list), `verify.py` (`tester_census`),
`config/machines.json` (`code_root` on the knight template, documented),
`docs/UAT_file_census.md` (checks C/E, refinement checks, `gate=6a/26t`)

**All five brief tasks are green. Nothing is committed.**
