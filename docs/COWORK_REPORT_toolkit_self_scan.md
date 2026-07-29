# Cowork report — the toolkit sees itself

**Pair:** `docs/COWORK_BRIEF_toolkit_self_scan.md`. Session 2026-07-28.
**Base commit:** `ac7710d`, working tree dirty.
**Gate:** `python verify.py` → **GREEN, 6 auditors + 53 testers** (was 50; +1:
`tester_project_root`, which locks the new root shape; the count then moved to
53 when the local-deck slice registered `tester_estate_data` and
`tester_review_preflight` before this pair was committed).
**Nothing committed. No `--apply`. No deposit. No link changed.**

**Where this ran, and why it matters.** The Cowork session's shell is an isolated
Linux sandbox with the gaming rig's `Documents/GitHub` folder mounted, not
`LucasGoonPC` itself. Every number below is measured against **the real working
tree, the real `.git`, the real `.gitignore`** — but from a local copy at
`/tmp/repo/L5GN-Tools` (the mount is too slow to walk: 38s for one `find`), on
POSIX paths, under hostname `claude`. Two consequences are recorded honestly
wherever they bite:

- The sandbox mounts `L5GN-Tools` **twice** (once standalone, once under
  `GitHub/`), which defeats the `TOOLKIT_ROOT` self-skip by accident. Every
  discovery probe below was re-run with `TOOLKIT_ROOT` corrected to the path the
  toolkit occupies **on the rig**, and only the corrected result is reported.
- The working copy carries a **5-file stand-in `.venv`** rather than the real
  one. The real `.venv` is **35,644 files** — measured on the mount, stated
  wherever it changes a total.

**`chronicler.db` is not reachable from here** (it lives at
`Documents/chronicler_dev/`, outside every mounted folder). So
`build_registry.py --report-aliases`, `build_inventory.py` and
`xref_filenames.py` could not be run. Task 4 is therefore split: everything
decidable from the registry file and the census is decided and measured here;
everything that needs the DB or a deposit is a command sheet for the rig. Per
the brief's own instruction the registry **file was not written** — the
`--report-aliases` read has not happened yet.

---

## Done vs pending

| Task | State | Note |
|---|---|---|
| 1 — add the root | **done, but not by config alone** | neither shape the brief offered works; one justified code change, one config line |
| 1 — registry binding | **proposed, not written** | exact diff below; blocked on `--report-aliases`, and the stop condition **fires without it** |
| 2 — hygiene | **done — one defect found** | `env_scanner` puts 185 gitignored `data/` paths and both gitignored config files in its output |
| 3 — self-verdicts | **done** | recorded verbatim, including three things we would rather it hadn't said |
| 4 — linking payoff | **partly measured, rest deferred** | projected inventory measured exactly; DB-side row counts need the rig |

---

## The headline

The self-scan found a real bug in the toolkit **by scanning the toolkit**, and it
found it in the scanner the brief expected to be the story. `blast_radius`'s
`git_state` label has an unreachable branch, so every uncommitted-critical file
in a git project is reported as `untracked` — including tracked-and-modified
files. The proof is this very session's edit to `l5gntools/common.py`. Details in
Task 3. **Not fixed here**: the brief puts fixing out of scope, and the findings
are the deliverable.

---

# Task 1 ▸ the root, and the registry

## Neither config shape in the brief works

The brief offered a choice: tag the parent `GitHub` folder, or add the toolkit
path specifically. The folder listing that was supposed to decide it:

```
C:/Users/timps/Documents/GitHub/
├── L5GN/                      <- the configured root; a CONTAINER of 8 projects,
│   ├── L5GN-Archive/             not a project (no .git at its own level)
│   ├── L5GN-Armory/
│   ├── L5GN-Armory_v2/
│   ├── L5GN-Castle/
│   ├── L5GN-Continuous-Ingestion-Daemon/
│   ├── L5GN-Crystal-Spire/
│   ├── L5GN_Armory_v4/
│   └── L5GN_Managed_Workspace/
├── L5GN-Tools/                <- the target
└── l5gn-mesh-vertex-3_prod/   <- a real project, currently unscanned
```

Probed against the live discovery code, with `TOOLKIT_ROOT` corrected to the rig:

| roots | `discover_projects()` returns |
|---|---|
| `[GitHub/L5GN]` (today) | the 8 real projects — correct |
| `[GitHub]` (parent) | `['L5GN', 'l5gn-mesh-vertex-3_prod']` — **L5GN-Tools absent** |
| `[GitHub/L5GN-Tools]` | `['__pycache__','auditors','chronicler','config','data','deploy','docs','l5gntools','l5gntools.egg-info','tests']` |

Three separate failures, all fatal:

1. **The parent root trips the brief's own stop condition.** It drags in `L5GN`
   as a single bogus mega-project duplicating all 8 real ones, and pulls in
   `l5gn-mesh-vertex-3_prod`, which no brief has asked for.
2. **The parent root does not even work.** `common._projects_under` carries an
   explicit `if child.resolve() == TOOLKIT_ROOT.resolve(): continue`. The toolkit
   has always refused to discover itself. A config-only change cannot undo a
   line of code.
3. **The toolkit path as a plain root is nonsense by definition.** `roots` means
   "folders whose *children* are projects", so this turns `docs/` and `config/`
   into projects.

## The change: a third root shape, `is_project`

Minimal, and justified by the observed failure above rather than by preference.

```json
"roots": [
  {"path": "C:/Users/timps/Documents/GitHub/L5GN", "scope": "l5gn"},
  {"path": "C:/Users/timps/Documents/GitHub/L5GN-Tools", "scope": "l5gn", "is_project": true}
]
```

`is_project: true` means *this path is the project*, not a container of
projects. Three files touched:

| File | Change |
|---|---|
| `l5gntools/config.py` | `_root_entries` carries `is_project` through (default `False`; both old shapes unchanged) |
| `l5gntools/common.py` | `discover_projects` reads `estate_roots_tagged()` and contributes an `is_project` root *itself*; `resolve_targets` answers a bare `--target L5GN-Tools` by folder name |
| `config/machines.json` | `_is_project_comment` documents the shape (committed template) |
| `config/local.json` | the root above, on `LucasGoonPC` only — **written** |
| `tests/tester_project_root.py` | new hermetic tester, registered in `verify.py` |

**The `TOOLKIT_ROOT` skip is deliberately kept for container walks** and bypassed
only for an `is_project` entry. That preserves exactly the property 0020 wants:
the toolkit is scanned **only where a producer has said so explicitly**, never
stumbled into by someone broadening a root. The work rig and the knight are
untouched — one machine, per the brief's ruling.

`scope_for_path` needed no change: `target.relative_to(root)` succeeds when
they are the same path, so the toolkit resolves to `scope: l5gn` off its own
root entry.

## The registry — the stop condition fires, and it is decidable now

`l5gn-tools` exists as a curated project with `repos: []` and
`low_signal_body: true` (already set — no change needed there).

Reading `build_registry.assemble_tiers`, the binding rule is: **a deposited
project is claimed by a curated *repo* whose `canonical_name` matches**. With
`repos: []` nothing claims the deposit, so rule 2 fires — "deposited repos
nobody claimed become their own single-repo projects" — minting
`_slugify("L5GN-Tools")` = **`l5gn-tools`**, and appending it to `projects[]`
next to the curated entry. `assemble_tiers` itself has no id-collision guard.

**So the brief's first stop condition is not a risk to watch for; it is the
default outcome.** Deposit first and the registry gets two entries with id
`l5gn-tools`, one `provenance: manual`, one `provenance: auto`.

> **Walked 2026-07-29 — it fired, and the toolkit refused to write.** B2 was
> skipped, `run.py deposit` ran, and the next `build_registry.py
> --report-aliases` aborted with:
>
> ```
> [build_registry] duplicate registry id 'l5gn-tools' (project and project)
>  -- one id must mean exactly one thing
> ```
>
> **Correction to this report's first draft:** there *is* a guard, one layer
> down — `collect_link_targets` raises `SystemExit` on a duplicate id at any
> tier. So the failure mode is a loud abort with nothing written, not a silently
> corrupted registry. The prediction was right about the collision and wrong
> about the consequence, and the toolkit behaved better than predicted.
> The repo-tier entry has since been applied (see below); re-run to clear it.

This makes the ordering non-negotiable on the walk:

> **The repo-tier entry must exist in `config/project_registry.json` *before*
> the first `build_registry.py` run that sees the deposit.**

### The diff — **applied 2026-07-29**, after B1 read `--report-aliases`

Written to **`config/project_registry.json`** — which is `GROUPS_PATH`, the
curated manual layer, *not* the generated registry. See "Two registry files"
below; getting this wrong writes into a file the generator overwrites.

The `l5gn-tools` entry's `"repos": []` became:

```json
"repos": [
  {
    "id": "l5gn-tools-repo",
    "canonical_name": "L5GN-Tools",
    "aliases": ["L5GN-Tools", "L5GN Tools"],
    "seed_suppress": ["Tools"],
    "note": "The toolkit's own repo. Scanned from the gaming rig only (DECISIONS 0020) via an is_project root. 'Tools' is suppressed: seed_aliases() derives it by stripping the l5gn prefix token, and it is common English — the same shape as the 'Castle' false positive that auto-linked six threads on zero evidence (b7c2390)."
  }
]
```

**`seed_suppress` belongs on the repo, not the project.** `_merge_alias_lists`
reads `repo.get("seed_suppress")`; a project-tier key would be silently ignored.

**The `Tools` derivation is confirmed, not assumed** — `seed_aliases` run
directly:

```
L5GN-Tools         -> {"L5GN-Tools": "seed_canonical", "Tools": "seed_shortname"}
L5GN-Castle        -> {"L5GN-Castle": "seed_canonical", "Castle": "seed_shortname"}
```

Identical shape to the known-bad case. `PREFIX_TOKENS = {'l5gn', 'mcf'}`.

**`low_signal_body`:** the brief says consider it. It is **already `true`** on
`l5gn-tools` — nothing to add. The reasoning in the registry note ("a meta-tool
that gets name-dropped everywhere") is exactly right and this scan reinforces it:
every brief and report in the estate mentions `verify.py`.

---

# Task 2 ▸ hygiene — one real defect

Each exclusion, with the mechanism that fires and evidence it fires. `Scope` is
the shared filter; `git status_of` is the gitignore authority it reuses;
`is_ignored_dir` prunes at walk level.

| path | `Scope.reason_to_skip` | git status | `is_ignored_dir` | verdict |
|---|---|---|---|---|
| `data/estate.json` | `gitignored` | ignored | — | excluded |
| `data/history/latest.json` | `gitignored` | ignored | — | excluded |
| `data/outbox` | `gitignored` | ignored | — | excluded |
| `report.html` | `gitignored` | ignored | — | excluded |
| `.venv/pyvenv.cfg` | `vendored` | ignored | **True** | excluded twice over |
| `__pycache__` (any) | `vendored` | untracked | **True** | excluded, pruned at walk |
| `l5gntools.egg-info/` (dir) | `None` | untracked | **False** | see below |
| `l5gntools.egg-info/PKG-INFO` | `gitignored` | ignored | — | excluded |
| `chronicler/chronicler.db` | `gitignored` | ignored | — | excluded |
| `config/local.json` | `gitignored` | ignored | — | excluded by `Scope` |
| `config/project_registry.json` | `gitignored` | ignored | — | excluded by `Scope` |
| `config/machines.json` (control) | `None` | tracked | — | scanned, correct |
| `docs/DECISIONS.md` (control) | `None` | tracked | — | scanned, correct |

**One brief claim is wrong and worth correcting in the record.** The brief lists
`*.egg-info` under `is_ignored_dir`. It is not there — `IGNORE_DIRS` has
`.eggs`, not `*.egg-info`, and `is_ignored_dir("l5gntools.egg-info")` is
`False`. The directory is walked; its *files* are then caught by `Scope` as
`gitignored` (`.gitignore` line `*.egg-info/`). The outcome is right, the stated
mechanism was not. `.venv` and `__pycache__` do behave as the brief says.

`auditor_readonly` is **unaffected — confirmed by reading it, not assumed.** It
walks `SCANNERS` module `__file__` sources with `ast` looking for filesystem
writers. Its input is scanner source; a scan target never enters it. Adding a
scan target cannot change its verdict.

## The defect: `env_scanner` scans the toolkit's own exhaust

`env_scanner.scan(L5GN-Tools)` returns **190 `config_files`**:

| segment | count |
|---|---|
| `data/` | **185** |
| `config/` | 4 — including `local.json` **and** `project_registry.json` |
| `pyproject.toml` | 1 |

`"scope": {"skipped_paths": 0, "skipped_by_reason": {}}` — nothing was recorded
as skipped, because `env_scanner` passes `honor=("data_dir","vendored")` and
deliberately does **not** honour `gitignored`.

That leniency is correct and documented for its purpose: a gitignored `.env`
must still be *seen* so it can be labelled `ignored`, because that label is the
finding. But the leniency is applied to the **whole walk**, so it also lets the
generic `config_files` inventory swallow every `.json` under `data/`. On any
other project this is invisible; on the toolkit, `data/` **is** the toolkit's
output, and the scanner is listing its own exhaust back to itself.

**Severity, stated precisely:**

- It **is** the brief's stop condition — gitignored paths in the scan output.
- It is a **scope defect**, not a contents leak. `env_scanner`'s "names only"
  contract holds: `secret_suspects: []`, `credential_files: []`,
  `tracked_suspect_count: 0`. **No employer codename, no push target, no
  registry content reaches the output.** The gitignored *filenames*
  `config/local.json` and `config/project_registry.json` do.
- It does **read** both files' contents in-process (to count secret-suspect
  lines) and finds nothing worth reporting. Read, not emitted.
- The 185 `data/` entries would also be deposited and shipped to the knight —
  noise in the estate bundle, not a disclosure.

**Not fixed here.** The fix is a one-line judgement (`honor` narrowed to the
`.env`-suspect branch only, rather than the whole walk) and it belongs in its
own brief with its own tester. Recorded, sequenced, not tidied.

### What `file_census` does instead — the contrast worth keeping

`file_census` gets this right by construction. Its `files[]` working set —
**244 entries** — contains **no gitignored path at all** (the only near-match is
`config/local.json.example`, which is tracked). Gitignored bulk is aggregated
into `mass[]` at directory level with an explicit `reason`:

```
data                        189 files  32,657,146 bytes  reason=ignored
chronicler                    1 file    4,050,944 bytes  reason=ignored (partial)
.git                       1068 files   3,128,042 bytes  reason=git-internal
.                             1 file    2,037,904 bytes  reason=ignored (partial)   <- report.html
tests/__pycache__           105 files     698,640 bytes  reason=ignored
```

`outliers[]` does name individual ignored files by path (`data/estate.json`,
`report.html`, `chronicler/chronicler.db`, the `data/history/estate-*.json`
snapshots). That is disclosure **by design and labelled** — naming the large
ignored file is the entire point of a bloat outlier — and it is a different
thing from `env_scanner` listing 185 of them unlabelled in a config inventory.
Flagged so the walk can rule on it rather than discover it.

## The reflexive case: `docs/archive/` and `docs/investigation/`

Both are **scanned**, and both **should be**. Neither is gitignored;
`docs/investigation/` is untracked, `docs/archive/` is tracked.

They are not exhaust — they are the estate's decision history — but the brief is
right that they move the numbers a long way:

| slice | docs |
|---|---|
| `docs/archive/` | **45** |
| `docs/investigation/` | **5** |
| everything else | 52 |
| **total** | **102** |

**Decision: scan them, count them, and say so.** Excluding them would be the
`data/` argument applied to content that is genuinely authored, and it would
make the toolkit's doc count a fiction chosen to look normal. It does change the
`out_of_band` verdict — with them the toolkit trips the flag at 102, without
them (52) it would not — and that is exactly why the exclusion would have been
a thumb on the scale. Measured both ways in Task 3 so the choice is visible.

---

# Task 3 ▸ what the toolkit says about itself

Every scanner run directly against the working tree. `run.py build` was **not**
used from the sandbox: it writes `data/` and overwrites `report.html`. `DATA_DIR`
was redirected out of the tree; nothing was written into the repo.

### Confirmed on the rig, 2026-07-29

Tim then ran the real `run.py build` on `LucasGoonPC`. The sandbox measurements
held:

| measure | sandbox prediction | rig actual | |
|---|---:|---:|---|
| `file_census.total_files` | ~37,382 | **37,388** | ✓ (the `.venv` estimate) |
| `working_set.files` | 244 | **246** | ✓ +2 = this report and its walk-sheet |
| `blast_radius.hit_count` | 270 | **270** | ✓ exact |
| `blast_radius.tier` / rank | raw-write / 3 | **raw-write / 3** | ✓ |
| `git_state` on a tracked-modified file | `untracked` (bug) | **`untracked`** | ✓ dead branch reproduced |
| `decisions_count` | 28 | **28** | ✓ |
| `doc_count` | 102 | **104** | ✓ +2, same two docs |
| `out_of_band` median / threshold | 27 / 81 | **27 / 81** | ✓ exact |
| `out_of_band` flagged | CID, Armory_v4, Crystal-Spire, **L5GN-Tools** | **the same four** | ✓ 4 of 9 |
| `env_scanner.secret_suspects` | `[]` | **`[]`** | ✓ no committed secret |

Two things the rig showed that the sandbox could not:

- **`largest` is `.venv/Lib/site-packages/torch/lib/torch_cpu.dll`.** The
  toolkit's virtualenv carries PyTorch — 1.08 GB of the toolkit's 1.08 GB mass
  is `.venv`. Correctly excluded from the working set, and a fair answer to
  "why is a stdlib-only tool a gigabyte on disk": the *wall* is stdlib-only,
  the *venv* is not (`sentence_transformers` pulls torch).
- **`todo_adr_scanner.marker_count` rose 28 → 33.** The five new markers are in
  this report and this walk-sheet — documents written *about* the reflexive
  false-positive class, which then joined it. The finding grew by being
  reported.

## `blast_radius` — the tier ladder is saturated, and there is a bug

```
tier                    : raw-write
tier_rank               : 3
hit_count               : 270
by_family               : {"db-writes": 204, "shell-os": 48, "salesforce-dml": 13,
                           "cloud-read": 2, "salesforce-read": 2, "cloud-infra": 1}
truncated               : false   (cap 300)
has_uncommitted_critical: true
uncommitted_critical    : [{"path": "l5gntools/common.py", "tier": "raw-write",
                            "git_state": "untracked"}]
scope                   : {"skipped_paths": 0, "skipped_by_reason": {}}
```

**The brief expected the toolkit to be the highest-tier result in the estate. It
is not — because nothing can be.** Every project is already at the ceiling:

| project | tier | rank | hits | uncommitted_critical |
|---|---|---:|---:|---|
| **L5GN-Tools** | raw-write | 3 | **270** | true |
| L5GN-Castle | raw-write | 3 | 29 | true |
| L5GN-Archive | raw-write | 3 | 22 | true |
| L5GN-Armory_v2 | raw-write | 3 | 14 | true |
| L5GN_Armory_v4 | raw-write | 3 | 14 | false |
| L5GN-Armory | raw-write | 3 | 12 | true |
| L5GN_Managed_Workspace | raw-write | 3 | 8 | false |
| L5GN-Continuous-Ingestion-Daemon | raw-write | 3 | 3 | false |
| L5GN-Crystal-Spire | raw-write | 3 | 3 | false |

(Toolkit row from this scan; the other eight from the rig's last real build,
`data/estate.json`.)

**9 for 9 at `raw-write`.** `tier` carries no information at project level — one
`subprocess.run` anywhere maxes it out. The discriminating axis is `hit_count`,
where the toolkit is **270 against a next-highest 29: a 9.3× margin, and 68% of
the estate's total.** That is the true picture the brief asked for, and it is
louder than "highest tier" would have been. It also says the *ladder* needs
re-examining, not the toolkit.

The concentration is where it should be: `chronicler/pipeline/relink.py` (14),
`group_fallback.py` (15), `finalize_db.py` (7), `chronicler/review/core.py` (8),
`deploy/pull-report.ps1` (8). `db-writes` at 204 of 270 is the honest shape of a
tool whose job is a SQLite vault. Nothing important is missing.

### The bug, found by the toolkit on itself

`uncommitted_critical` reports `l5gntools/common.py` as `git_state: "untracked"`.
It is not untracked — it is tracked and modified, by this session. The cause,
`blast_radius.py:205-209`:

```python
uncommitted = (changed is None) or (p in changed)
if not uncommitted:
    continue
state = "no-git" if changed is None else ("untracked" if p in changed else "dirty")
```

Reaching line 208 with `changed is not None` guarantees `p in changed`, so the
`"dirty"` branch is **unreachable**. Every uncommitted-critical file in every git
project in the estate has been labelled `untracked` since the alarm was written,
whatever its real state. The `has_uncommitted_critical` alarm itself is correct;
only the state label is wrong.

This is the self-scan paying for itself on the first run: the toolkit is the only
repo whose in-flight modifications the toolkit itself was editing at scan time.

## The build defect found on the walk: estate-level scanners never invalidate

**Symptom (Tim, 2026-07-29):** after a clean `run.py build` over 9 projects,
`L5GN-Tools` is missing from the report's git-summary page.

**It is not missing from the scan.** `data/estate.json` from that build carries a
complete, correct `L5GN-Tools` entry — `scope: l5gn`, `git_summary` fully
populated (branch `main`, `ac7710d`, 76 commits, 9 dirty). The per-project half
is right.

**The estate half is stale.** In the same file:

```
projects[]                      : 9 entries, including L5GN-Tools
estate.estate_status            : project_count = 8, no L5GN-Tools row
estate.duplicate_finder         : no L5GN-Tools
```

`report.build_estate` caches per-project scans under a **project-keyed** name,
`<scanner>/<project>.json` — so a new project is a cache miss and gets scanned.
Estate-level scanners are cached under a **project-independent** name,
`<scanner>.json`:

```python
for mod in estate_level:
    rel_name = f"{mod.NAME}.json"
    data = _cached(rel_name) if resume else None
    if data is None:
        data = mod.scan_estate(projects)
```

There is nothing in that key to invalidate when the project *set* changes.
`data/estate_status.json` and `data/duplicate_finder.json` already existed from
the 8-project era, so `resume` (the default) served them unchanged. The emitted
artifact therefore states `project_count: 8` and lists 9 projects **in the same
file**, and `tester_report_selfcheck` does not catch the contradiction.

This is not specific to the toolkit — **any** project added to any estate would
have hit it. It took the first new project in a while to expose it.

**Unblock without a code change** (cheap — keeps every per-project cache):

```bat
del data\estate_status.json data\duplicate_finder.json
python run.py build
```

`python run.py build --fresh` also works but rescans everything, including
`L5GN_Armory_v4` at 2.8 GB.

**Consequence for this report:** the estate-wide `duplicate_finder` comparison
below is still the 8-project baseline — it never re-ran. Its 9-project numbers
are pending that rebuild, as F5 on the walk-sheet says.

**Not fixed here.** The fix is a keyed or project-set-hashed cache name plus a
self-check assertion (`estate_status.project_count == len(projects)`), and it
belongs in its own brief.

## `doc_census` — trips `out_of_band`, as predicted

```
doc_count        : 102        authored_count : 101      generated_count : 1
classified_count : 88         classified_pct : 87.1
type_tally       : {"uat": 26, "brief": 23, "report": 16, "unclassified": 13,
                    "runbook": 10, "readme": 5, "intent": 4, "plan": 2,
                    "decisions": 1, "architecture": 1}
adr_files        : 0          has_readme : true
has_claude_md    : false      has_glossary : false
```

The brief's figures (~84 authored, 74 classified) came from the doc round's own
measurement; the count has grown to 102/88 with this week's briefs. Classified
share is **87.1%**, well above the round's target.

**`out_of_band`, before and after** (`MULTIPLIER = 3.0`, `MIN_PROJECTS = 3`):

| | doc counts | median | threshold | flagged |
|---|---|---:|---:|---|
| **before** (8) | 1, 9, 19, 25, 27, 97, 288, 358 | 26.0 | 78.0 | CID 358, Armory_v4 288, Crystal-Spire 97 — **3 of 8** |
| **after** (9, toolkit in) | +102 | **27.0** | **81.0** | the same three **+ L5GN-Tools 102** — **4 of 9** |

**Does the rule still discriminate?** Yes — the toolkit did not break it. The
median barely moves (26 → 27) because the toolkit lands above it, and 5 of 9
projects stay under the line.

**But the honest answer is that the rule was already weak before the toolkit
arrived.** An anomaly flag firing on **3 of 8** projects (37.5%), now **4 of 9**
(44.4%), is not identifying anomalies — it is splitting the estate roughly in
half. The problem is the population: doc counts run 1 → 358, and a median-based
3× rule on a distribution that skewed will always flag its upper third. The
toolkit is a legitimate 102-doc project and *should* be above the line; that it
sits alongside `L5GN_Armory_v4` (288 docs, only **2 authored** — the rest are
generated) shows the flag is answering "big" rather than "odd". Recommend
re-examining `OUT_OF_BAND_MULTIPLIER` against `authored_count` rather than raw
`doc_count`, in its own brief.

Without `docs/archive` + `docs/investigation` the toolkit would sit at 52 and not
trip. It is counted at 102. See Task 2.

**Minor finding:** the one `generated` document is
`.claude/skills/docs-archivist/SKILL.md` — a hand-authored Cowork skill,
classified `generated` by the directory-segment provenance rule and
`unclassified` by type. Correct by the rule, wrong about the file.

## `todo_adr_scanner` — `decisions_count` fires for the first time

```
decisions_count : 28
decision_tiers  : {"accepted": 27, "other": 1}
adr_count       : 0      adrs : []
marker_count    : 28     markers_by_tag : {"TODO": 27, "XXX": 1}
open_questions  : {"sections": 0, "items": 0}
scope           : {"skipped_paths": 189, "skipped_by_reason": {"gitignored": 189}}
```

**`decisions_count = 28`, non-zero on a real scan for the first time in the
counter's life** — and it is exactly right: `DECISIONS.md` runs `## 0001` to
`## 0028`. 27 accepted, 1 other. `adr_count: 0` is also correct — the toolkit
keeps decisions in one file, not one-per-ADR.

Note `skipped_paths: 189` — `todo_adr_scanner` honours gitignore properly and
skipped all of `data/`. Direct contrast with `env_scanner`'s 0.

**And the counter that fires is immediately embarrassing about the marker half.**
Of the 28 TODO/XXX markers, **the substantial majority are the toolkit talking
about markers, not markers**:

- `todo_adr_scanner.py` matches **itself four times**, including line 30 — its
  own regex literal `|FIXME|HACK|XXX)\b[:\s-]*(.{0,120})")`.
- `tests/tester_scanner_scope.py` matches **five times** — the fixture strings
  written to prove the scanner ignores TODO-shaped noise.
- 14 of 28 are in `docs/`, all prose *about* the scanner
  (`COWORK_BRIEF_scanner_bugfixes.md`, `DECISIONS.md:910`, the archived
  governance report).

Genuine markers: roughly `chronicler/scrape_gemini_share.py:104`
("normalize to ISO 8601 UTC") and the `tests/_fixture.py` stub. **The toolkit's
own TODO count is ~2 real and ~26 reflexive.** That is a false-positive class no
other project could have exposed, because no other project's source *is* the
matcher.

## `import_scanner` — first-party siblings reported as third-party

```
py_files_scanned : 127
third_party      : {"db": 27, "relink": 6, "build_inventory": 4,
                    "normalize_md_transcript": 2, "yaml": 2, "local_transcripts": 2,
                    "build_registry": 2, "build_activity": 2, "playwright": 1,
                    "reconcile_gemini": 1, "normalize_claude": 1,
                    "normalize_gemini_personal": 1, "extract_path_mentions": 1,
                    "parse_gemini_export": 1, "sentence_transformers": 1,
                    "render_md": 1, "fastapi": 1, "uvicorn": 1, "pydantic": 1,
                    "finalize_db": 1, "xref_filenames": 1, "set_substantive": 1,
                    "coherence_check": 1, "run_pipeline": 1,
                    "ingest_local_transcripts": 1, "backfill_candidate_project": 1,
                    "intake": 1}
top_imports      : pathlib 103, __future__ 100, tempfile 42, l5gntools 40,
                   json 40, sys 35, os 33, db 27, argparse 25, re 25,
                   datetime 22, sqlite3 22, subprocess 17, hashlib 13
```

**Only 6 of those 27 "third-party" names are third-party** (`yaml`,
`playwright`, `sentence_transformers`, `fastapi`, `uvicorn`, `pydantic`). The
other 21 — `db`, `relink`, `build_inventory`, `xref_filenames`, `intake`,
`finalize_db` … — are the toolkit's **own** `chronicler/pipeline` modules,
imported by bare name because those scripts run as a flat directory rather than a
package. The classifier can only see "not stdlib, not a local package", so
sibling-by-bare-name reads as external.

Consequence worth naming: the scanner reports the toolkit's *stdlib-only wall* as
if it were breached 27 ways. The wall is intact — `auditor_stdlib` is green in
the same gate run. Anything embarrassing is a finding.

## `env_scanner`

Covered in Task 2. Clean on the half that matters —
`credential_files: []`, `secret_suspects: []`, `tracked_suspect_count: 0`. **No
committed secret in the toolkit.**

## `file_census`

```
total_files  : 1,743      total_bytes : 46,120,093
working_set  : 244 files, 2,355,784 bytes
mass         : 1,499 files, 43,764,309 bytes
at_risk      : 1 file, 3,627 bytes  -> tests/tester_project_root.py
largest      : chronicler/chronicler.db
file_count   : 244        truncated : false  (cap 2000)
```

**The working set is 5% of the files and 5% of the bytes.** 95% of the toolkit
by mass is exhaust, cache and history. Nothing is truncated, so the census — and
therefore the file inventory in Task 4 — is complete.

**Scale caveat, stated plainly.** These totals carry the **5-file stand-in
`.venv`**. On the rig, with the real 35,644-file `.venv`, `total_files` will read
approximately **37,382** and `mass` will grow by the venv's bytes. Working set,
`files[]`, `at_risk` and `outliers` are unaffected — `.venv` is pruned at walk
level. **Expect a much larger `total_files` on the rig; that is not a
discrepancy.**

`at_risk` flagging `tests/tester_project_root.py` is the scanner correctly
noticing this session's own untracked work.

## `git_summary` / `git_deep_history`

```
branch ......... main            commit_count ..... 76
latest ......... ac7710d 2026-07-28T23:16:30+01:00
dirty_files .... 7               first_commit ..... 2026-07-10T16:44:05+01:00
remote ......... https://github.com/timpsmith28-hash/L5GN-Tools.git
commits_by_author: {"L5GN": 76}   author_aliasing: {"timpsmith28-hash": "L5GN"}
commits_by_day  : 07-10:2, 07-17:17, 07-18:7, 07-20:5, 07-21:2, 07-24:1,
                  07-25:10, 07-26:2, 07-27:15, 07-28:15
```

76 commits in 18 days, single author, alias folding working. The 7 dirty files
are this session's.

## `workspace_scanner`

```
py_files : 127    classes : 9    functions : 662    vendored_py_files_excluded : 0
top_classes : DeckSchemaNotMigratedError, GeminiExportParseError, ... (9 total)
```

662 functions across 9 classes — a resolutely functional codebase, and the class
list is dominated by exception types. Consistent with the stdlib-only wall.

## `bloat_audit`

```
tracked_files : 243   tracked_bloat_paths : 0   large_tracked_files : []   flags : []
```

Clean. Nothing bulky has been committed — the 43MB of mass is all correctly
ignored.

## `duplicate_finder` — not measurable from one project

`duplicate_finder.scan_estate([L5GN-Tools])` returns all zeros: it is a
**cross-project** scanner and needs at least two. The rig's current estate-wide
baseline, **without** the toolkit, is `identical_content_groups: 25`,
`shared_filename_groups: 39`, `shared_filename_divergent: 27`. Adding the
toolkit will very likely raise all three — `chronicler/` code and `deploy/`
scripts share names with material in `L5GN-Castle`. **Unmeasured here; it needs
the rig's full build.** Recorded as pending, not as zero.

---

# Task 4 ▸ the linking payoff

## What is measurable now, and it is a lot

`file_inventory` is built from the census's `files[]` and
`basenames_beyond_cap` (`build_inventory.build_from_census`). The census is
complete and untruncated, so the inventory the deposit *will* produce is
computable exactly:

```
file_inventory (projected, l5gn-tools):
  file_count        : 244
  paths             : 244        (truncated: false)
  extra_basenames   : 0
  DISTINCT BASENAMES: 235
```

Applying `xref_filenames`' own rules to those basenames:

```
suppressed as GENERIC_BASENAMES (9):
  .gitattributes  .gitignore  README.md  __init__.py  app.py
  config.py  index.html  pyproject.toml  run.py
viable carriers: 226
```

**226 basenames that can carry `filename_xref` evidence, where today there are
zero.** The brief's named carriers all survive:

| basename | in inventory | generic-suppressed | collides |
|---|---|---|---|
| `verify.py` | yes | no | no |
| `relink.py` | yes | no | no |
| `DECISIONS.md` | yes | no | no |
| `SOLO_PLAYBOOK.md` | yes | no | no |
| `build_registry.py` | yes | no | no |
| `xref_filenames.py` | yes | no | no |
| `finalize_db.py` | yes | no | no |
| `deposit.py` | yes | no | no |

**One suppression worth knowing about: `run.py` is in `GENERIC_BASENAMES`.** The
toolkit's dispatcher — "run `run.py build`" is in half the transcripts in the
vault — can never produce evidence. That is the stoplist working as designed
(`run.py` is boilerplate across the estate), but it means the single most-typed
toolkit filename is not a carrier. `verify.py` and `relink.py` carry the load.

## Two registry files, and why "zero inventories" was the wrong reading

The brief's premise is that `l5gn-tools` uniquely lacks a `file_inventory`.
Checked directly, no entry at any tier in either registry file on this rig
carries one — which the first draft of this report flagged as a possible
estate-wide hole. **The walk gave the real answer, and it is more mundane and
more useful.** There are two files:

| role | path | state |
|---|---|---|
| `GROUPS_PATH` — the **curated manual layer** (programs, projects, repo groupings, aliases, `low_signal_body`, `seed_suppress`). Hand-authored, read by the generator, never overwritten. | `L5GN-Tools/config/project_registry.json` | present, 31 projects |
| `REGISTRY_PATH` — the **generated registry** every downstream reader consumes (`build_inventory`, `build_activity`, `xref_filenames`, `relink`). | `…/GitHub/L5GN/.intel_sync/project_registry.json` | **does not exist on the gaming rig** |

So `file_inventory` is absent from the curated layer **by design** — it is an
input, and inventories are written to the generated file. And it is absent from
the generated file because **that file has never been produced on this rig**:
`--report-aliases` is a dry-run ("31 entries *would be* written"), and the first
real write aborted on the duplicate id.

That reframes the payoff measurement rather than weakening it. The 226 viable
carrier basenames stand. What is now known is that **the whole S4 chain —
`build_inventory` → `xref_filenames` → `relink` — has nothing to read on the
gaming rig at all**, for any project, until `build_registry.py` completes a
non-dry run. That is a precondition for F1/F2 on the walk, not a finding about
`l5gn-tools`.

**`config/project_registry.json` is the file to hand-edit.** Editing
`.intel_sync/project_registry.json` would be writing into the generator's
output.

## Deferred to the rig — command sheet

Deposit-dependent and DB-dependent; **no `--apply`, no relink**, per the brief.

```bash
# 0. registry FIRST -- the auto-id collision is the default outcome otherwise
python3 chronicler/pipeline/build_registry.py --report-aliases   # read it
#    then apply the repo-tier diff above to config/project_registry.json

# 1. scan + deposit, on LucasGoonPC only
python run.py build
python run.py deposit                    # no --push needed to measure

# 2. registry, again -- confirm ONE l5gn-tools, provenance manual
python3 chronicler/pipeline/build_registry.py --report-aliases

# 3. the payoff
python3 chronicler/pipeline/build_inventory.py
python3 chronicler/pipeline/xref_filenames.py        # DRY-RUN (the default)
```

Record from step 3: `l5gn-tools` (or `l5gn-tools-repo`) `file_count` and
basename count — **expect 244 / 235**, and treat a mismatch as a scope change
worth explaining — and the `filename_xref` row count the dry-run reports.

---

## Stop conditions — status

| condition | status |
|---|---|
| registry generates a second identity | **FIRED on the rig, 2026-07-29** — deposit landed before the repo-tier entry, `build_registry` aborted with `duplicate registry id 'l5gn-tools'`. **Nothing was written.** Repo-tier entry now applied; re-run to clear. |
| anything gitignored in scan output | **FIRED** — `env_scanner`, 185 `data/` paths + both gitignored config files. Scope defect. **Not a disclosure defect**: names only, no contents, `secret_suspects: []`. |
| root pulls in unrelated siblings | **avoided** — that is precisely why the parent-root option was rejected and `is_project` built |

Neither firing condition was worked around. Both are reported with the mechanism
and left for ratification.

## What was changed, and what was not

**Written:** `l5gntools/config.py`, `l5gntools/common.py`, `config/machines.json`,
`config/local.json`, `tests/tester_project_root.py`, `verify.py`, this report,
the walk-sheet.

**Also written, and it needs a sentence.** `auditor_doc_claims` went red the
moment the tester count moved 50 → 51, on two finished docs
(`UAT_doc_provenance_coverage.md`, `..._results.md`) whose quoted gate count was
true when written. The correct remedy is the mechanism the auditor
already provides — a `<!-- gate-frozen: commit=… -->` marker, at `87253c8` and
`dec7dc5` respectively — **not** rewriting a stamped historical count. Two
marker lines added; no historical claim altered.

(Then `auditor_doc_claims` promptly went red a second time — on **this report**,
for quoting the old count in the sentence above. Rephrased, not exempted. The
auditor is working.)

**Written after the walk (2026-07-29):** `config/project_registry.json` — the
`l5gn-tools-repo` repo-tier entry with `seed_suppress: ["Tools"]`, once B1 had
read `--report-aliases` as the brief requires.

**Not written:** any `--apply`, any link. `env_scanner`, `blast_radius`'s dead
branch, `import_scanner`'s classifier, the `out_of_band` multiplier,
`is_ignored_dir`'s missing `*.egg-info` and the estate-level cache
invalidation are all **left broken on purpose** — measure first; the findings
are the deliverable.

## Findings ledger — six defects, none fixed

| # | where | defect | severity |
|---|---|---|---|
| 1 | `blast_radius:208` | `"dirty"` branch unreachable; every uncommitted-critical file reads `untracked` | wrong label on a live alarm, estate-wide |
| 2 | `report.build_estate` | estate-level scanners cached under an unkeyed name — a changed project set never invalidates; emitted artifact self-contradicts (`project_count: 8`, 9 projects) | **stale governance artifact**, estate-wide |
| 3 | `env_scanner` | `honor` narrowed for the whole walk, not just the `.env` branch — 195 gitignored `data/` paths + both gitignored config files in `config_files` | scope defect; names only, no contents |
| 4 | `import_scanner` | bare-name sibling imports classified third-party — reports the stdlib wall as breached 21 ways when it is intact | misleading, cosmetic |
| 5 | `doc_census.out_of_band` | 3× median flags 4 of 9 projects; answers "big", not "odd" | weak discriminator |
| 6 | `todo_adr_scanner` | ~26 of 33 markers are the toolkit's own regex, fixtures and prose *about* markers | reflexive false-positive class |

Defect 2 is the one that touches the deposit the knight consumes. Recommend it
gets the next brief.
