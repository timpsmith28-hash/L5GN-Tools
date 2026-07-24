# COWORK REPORT — intent evidence: connecting the file inventory to the chat vault

**Brief:** `docs/COWORK_BRIEF_intent_evidence.md`
**Session:** 2026-07-21, Cowork on the gaming rig (`LucasGoonPC`)
**Gate:** `python verify.py` → **GREEN** (6 auditors + 28 testers)
**Nothing committed in L5GN-Tools.** Everything staged for review.

---

## Headline

The join works. `build_inventory` now reads the deposited census instead of a
folder layout that exists on no machine, and **all 11 projects get a
`file_inventory` where previously all 11 resolved missing**. With inventories
populated, S4's dry-run produces **2,246 evidence rows across 321 threads and
all 11 projects**, and S5 adds **104 rows across 84 threads**.

Task 0 is settled and executed: Crystal Spire's history was rebuilt on your
ruling, with the old history preserved as a clonable git bundle.

Four findings materially revise the brief's premises. They are in
[Corrections](#corrections-to-the-briefs-premises) and they matter more than the
task-by-task detail.

## Task status

| Task | State | Notes |
|---|---|---|
| **0** — Crystal Spire git position | **green, executed** | Backed up, history rebuilt in 6 chunked commits, no remote |
| **A** — `build_inventory` reads deposits | **green** | 11/11 projects, hermetic tester added |
| **B** — folder-walk audit | **green** | 2 remaining instances found, +2 the brief did not anticipate |
| **B2** — the `is_git` contradiction | **green, already fixed** | Mechanism identified; it is the same bug |
| **C** — run S4 | **green, dry-run only** | Real run against a vault snapshot; **not applied** |
| **D** — run S5 | **green, dry-run only** | Watermark verified; **not applied** |
| **E** — the origin query | **green** | Table delivered; every project's earliest evidence **precedes its first commit** |
| **F** — delve index harvest | **green, with a null result** | Index harvested; producers score **0.000/0.000** — and that is the finding |
| *(extra)* `build_activity` refactor | **green** | S3 activity windows build for the first time; tester added |

**Second pass additions:** after you re-ran `run.py build --fresh`, Tasks E and F
were completed, `build_activity` was refactored, and a real bug in the
beyond-cap basename set was found and fixed. Gate is **GREEN at 28 testers**.

---

## Corrections to the brief's premises

### 1. S4 is not dark — it ran once, against an estate that no longer exists

The brief states S4 "has never had anything to join against." The vault
disagrees: `link_evidence` already holds **568 `filename_xref` rows** across 213
threads and 8 projects, producer `xref_filenames/1.1`, all stamped
**2026-07-16T08:10:43Z**.

The projects those rows name are the tell:

> `Chronicler`, `DesktopsAndDungeons`, `GemToPairs`, `SolConfig`,
> `smelt-gateway`, `v1 proto`, `L5GN-Crystal-Spire`, `L5GN_Armory_v4`

Only the last two exist in the current 11-project estate. S4 ran successfully
**before the estate restructure**, when the nested layout it assumed was real.
The restructure flattened the estate and the producer went dark.

**So the correct statement is not "S4 has never worked" but "S4's existing
evidence is stale and points at project names that no longer exist."** That is a
different problem with a different fix, and it is squarely the DECISIONS 0011
reset — which this brief puts out of scope. Flagging, not acting.

The same applies to the brief's expectation that `L5GN-Archive`,
`L5GN-Crystal-Spire` and `L5GN-server-hub-iso` would "gain their first evidence
ever": Crystal Spire already had 75 rows across 15 threads. Archive and
server-hub-iso genuinely gain their first.

### 2. The sandbox mount no longer truncates large files

`DRIVE_ID_SCAN.md` records that the Linux mount silently truncated
`world_graph.json` and `world2.json` at ~12–13 MB, and that every count in it
was therefore taken host-side. **That defect does not reproduce.** Measured
today, through the mount:

| File | Bytes read | Structure |
|---|---|---|
| `world_graph.json` | 13,428,214 | parses; **1,602 zones** |
| `world2.json` | 12,536,206 | parses; **1,601 `"floor"` records** |

Both match the host-side figures in your scan exactly. A truncated JSON could
not parse at all, so this is decisive. **Task F's counts can be taken
sandbox-side**, which removes the constraint that made it the most awkward task
in the brief.

### 3. There are two non-git projects, not four

The brief expects "the four non-git projects" to carry a `source_signature`.
Only **two** are genuinely non-git: `L5GN-Archive` and `L5GN-server-hub-iso`.
The other two — `L5GN-Crystal-Spire` and `test_folder` — *were* misreported as
non-git, which is precisely the B2 contradiction, and are now correctly
detected. The count reconciles: 4 = 2 real + 2 misreported.

### 4. A vault snapshot exists on this rig

`L5GN-Castle/data/Chronicler_Backup/chronicler.db` (88 MB, 2026-07-17) holds
1,171 threads, 22,004 messages, 2,836 attachments. Tasks C and D were run
against a **read-only copy** of it rather than being deferred to runbooks.

> **Caveat carried into every C/D number below:** this is a 4-day-old snapshot,
> not the live vault. The figures are indicative and the runs must be repeated
> on the knight before anything is applied.

---

## Task 0 — Crystal Spire's git position

### Facts established

| Question | Answer |
|---|---|
| Remote configured? | **None** |
| Ever pushed? | **No** — all 11 commits returned by `log --branches --not --remotes`; reflog shows 11 plain commits, no clone/fetch/push |
| Which commits introduced the three world files? | **All three in `e7de409`, the initial commit.** `world_graph.json` and `canon_index.json` rewritten again in `8cb6798` |
| Working tree state | **1,677 uncommitted changes**, including deletions under `modules_v3/` |
| Git identity | Unset in-repo |

Because the first affected commit *was* commit #1, `filter-repo` would have
rewritten every hash anyway — its "surgical" advantage did not apply. It also
refuses to run against a dirty tree.

### Exposure is wider than the three world files

A coarse shape-match over tracked content found ID-shaped tokens in **61 files**,
concentrated as:

| Group | Files | Shape-matched tokens |
|---|---|---|
| `_archive/pipeline_data/*.tsv` | 3 | 382 |
| The 3 world files | 3 | 35 |
| `modules_v3/*.md` | 52 | 34 |
| Root docs | 3 | 6 |

Your `DRIVE_ID_SCAN.md` is the authority and is better work: **33 entropy-filtered
genuine live IDs**, with 176 in-fiction tokens correctly rejected. My 35 in the
world files agrees with your 33 closely enough to validate the method; the other
numbers are unfiltered shape-matches and will contain false positives. The
directional point stands: **a purge scoped to three files would have left most
of the exposure in place.**

### Executed, on your ruling

1. **Backup**, verified end to end — gzip-intact, extracts, 11 commits restore,
   `fsck` clean, HEAD matches, 1,601 `modules_v3` files present, 1,677 dirty
   changes preserved.
   `Backups\L5GN-Crystal-Spire_pre-surgery_20260721.tar.gz` (33 MB)
2. **History record** — `Backups\L5GN-Crystal-Spire_history_pre-reset_20260721\`
   containing a **complete clonable `git bundle`**, plus full log, reflog and a
   per-commit tree listing for all 11.
3. **Fresh init**, then six chunked commits by stratum:

   | Commit | Contents |
   |---|---|
   | `a027a61` | scaffolding — setup, manifest, packaging, new `.gitignore` |
   | `77da1c5` | engine, shells, game data |
   | `bc39960` | design corpus, era digests, audit reports |
   | `593b2ae` | superseded material under `_archive/` |
   | `492619a` | session logs and remaining scratch |
   | `30cc7e4` | `HISTORY_RESET.md` |

4. **Untracked** on your ruling: the 3 world files, the 3 `_archive` TSVs, and
   `modules_v3/`. Tracked files fell **1,738 → 134**. All content remains on disk.
5. **No remote exists.** None was added. Nothing was pushed.

`HISTORY_RESET.md` in the repo records all of this for a future reader.

### Two things to decide

1. **The scan reports are now the exposure.** `DRIVE_ID_SCAN.md` and
   `HYGIENE_SWEEP.md` are the *only* tracked files still carrying live Drive
   IDs — they quote all 33 verbatim with context, which is what a scan report
   is for. Decide whether they belong in the repo.
2. **`modules_v3/` is now version-controlled nowhere** — 1,601 files, 8.5 MB,
   on disk and in the 2026-07-21 tape only.

**The scrub has not happened and was not attempted**, per the brief.

### The knock-on, noted and not compensated for

Crystal Spire's census changes: working set shrinks (1,740 → ~134 tracked, though
the census counts the working set, not the index) and its at-risk count rises as
untracked-not-ignored files become ignored. `file_inventory` will no longer carry
`world_graph.json`, `world2.json` or `canon_index.json` as basenames for S4 to
match on. Correct behaviour; left alone.

---

## Task A — `build_inventory` reads the deposited census

### What changed

`resolve_fs()` reconstructed `GITHUB_ROOT_FS / <scope-root> / <canonical_name>`.
That is the third instance of the folder-walk defect. Replaced with deposit-driven
resolution that **reuses `build_registry`'s own discovery** — `resolve_estates_dir`,
`find_estate_snapshots`, `read_estate_snapshot` — rather than adding a second path.

- `paths` and `file_count` come from the deposited census.
- `source_commit` preserved for git projects (from `git_summary.latest_hash`),
  `source_signature` for non-git ones. Never collapsed into one field.
- Local-disk fallback retained for a producer running against its own tree;
  deposits win wherever both exist.
- New `source` field records which path produced the block.

### Result against the real deposit

All 11 projects build. **Previously all 11 resolved missing.**

| Project | files | listed | source |
|---|---|---|---|
| L5GN-Archive | 420 | 420 | signature |
| L5GN-Armory | 36 | 36 | `488df20` |
| L5GN-Armory_v2 | 88 | 88 | `2b44083` |
| **L5GN-Castle** | **3805** | **2000** | `96d099a` — truncated |
| L5GN-Continuous-Ingestion-Daemon | 459 | 459 | `f0861f8` |
| L5GN-Crystal-Spire | 1740 | 1740 | `77045a5` |
| l5gn-mesh-vertex-3_prod | 60 | 60 | `be2b0d2` |
| L5GN-server-hub-iso | 8 | 8 | signature |
| L5GN_Armory_v4 | 702 | 702 | `0e21976` |
| L5GN_Managed_Workspace | 45 | 45 | `4247770` |
| test_folder | 16 | 16 | `36806ae` |

### The truncation decision — basenames beyond the cap

**Decided: carry basenames past the cap. Implemented.**

Only `L5GN-Castle` trips the 2000-file cap. The three options were: raise the cap,
carry basenames beyond it, or accept the blind spot.

**Reasoning.** S4 matches on basename *alone* — it never reads a path, size or
mtime. Raising the cap would inflate every deposit with full per-file records
that nothing consumes, to fix one project. Accepting the blind spot means 1,805
of Castle's files are silently unmatchable by the strongest automatic signal in
the system, and "silently" is the objectionable word. Carrying just the
basenames costs a few KB and closes it completely.

**Implementation.** `file_census` now emits `basenames_beyond_cap`; `build_inventory`
surfaces it as `extra_basenames`; consumers call **`basename_set(inv)`**, which
unions both. `file_count` remains the true count, so `file_count > len(paths)`
stays the honest signal that `paths` is a subset. A change confined to files
beyond the cap still moves the signature — tested, because otherwise those edits
would be invisible to change detection forever.

**Confirmed against the refreshed deposit.** After you re-ran `run.py build
--fresh`, `L5GN-Castle` reports `files=3805, listed=2000, +names=1764` and the
`<- SHORT` flag is gone. All other projects sit under the cap.

### Two bugs found in the second pass

**1. The `<- SHORT` flag was wrong.** It tested `file_count == listed + extra`,
comparing a *file* count against a *deduplicated basename set*. Castle's 3,805
files yield 2,000 listed + 1,764 unique beyond-cap names — short by exactly the
41 duplicate basenames. The flag now means what it should: *files exist for which
we hold no basename at all*, which is the only condition that is actually a blind
spot.

**2. `basenames_beyond_cap` was redundantly large — a real bug my own tester
should have caught.** It recorded every basename past the cap, including the
1,627 already present in `files[]`. The tester asserted "no repeats" and passed
only because the fixture gave every file a unique basename, which real repo trees
never do. Both fixed: the census now subtracts what `files[]` already carries,
and the fixture creates `src/pkg_NNNNN/mod.py` so basenames genuinely repeat.

| | Before | After |
|---|---:|---:|
| Castle `basenames_beyond_cap` | 1,764 | **137** |
| `basename_set()` coverage | 1,980 | **1,980 (unchanged)** |

A 92% reduction for identical information.

> **Outstanding:** the deposits now on disk still carry the pre-fix, redundant
> version of the field. It is harmless — coverage is identical — but one more
> `run.py build --fresh` per rig will shrink it.

### Coverage

New `tests/tester_build_inventory.py`, registered in `verify.py` (27 testers).
Hermetic: synthetic deposit in, correct `file_inventory` out. Covers a git
project, a **non-git** project, a **truncated** project, `basename_set()` union,
skip-if-unchanged, `--force`, a change confined to beyond the cap, dry-run
writing nothing, and loud failure when no deposits exist.
`tester_file_census.py` extended to assert the basename set is complete.

---

## Task B — the folder-walk class

### Remaining instances

| Location | Pattern | Does the census supply what it needs? |
|---|---|---|
| **`build_activity.py:237–241`** | `resolve_fs()` → `GITHUB_ROOT_FS / root / canonical_name` | **Yes.** Deposits carry `first_commit_date` / `latest_date` |
| **`build_vocabulary.py:358`** | calls `resolve_fs` (imported from `build_inventory`) | **Partly.** Needs file *contents*, which the census does not carry |

### Two the brief did not anticipate

3. **`relink.py:189`** writes `repo_folder_path` as `f"{SCOPE_TO_ROOT[scope]}/{canon}"`
   — it **encodes the dead layout into the vault**. The `projects` table already
   holds `L5GN/Chronicler`, `MCF/SolConfig`, `L5GN/L5GN-Crystal-Spire`,
   `L5GN/v1 proto`. These paths exist on no machine. This is the only instance
   that has written bad data into a durable store.

4. **`REGISTRY_PATH = GITHUB_ROOT_FS / "L5GN" / ".intel_sync" / "project_registry.json"`**
   in **four** files (`build_registry:68`, `build_activity:60`, `relink:84`,
   `xref_filenames:46`). `GitHub/L5GN/` **does not exist on this rig**. Since
   `write_json_atomic` does `mkdir(parents=True)`, running `build_registry` here
   would *create* a spurious `GitHub/L5GN/.intel_sync/` folder rather than fail.
   Task A's demonstration used a temp registry specifically to avoid this.

**Recommendation: fix the class at `REGISTRY_PATH` and `relink.py:189` before
fixing more instances of `resolve_fs`.** The registry location is shared by four
modules, and `relink` is actively writing wrong paths into the vault.

### `build_activity.py` — not attempted

Round 3 judged the refactor "small, contained." It is — the deposits carry the
dates. But it was not done: Task 0 and the four corrections consumed the budget,
and the brief is explicit that "a second task done badly costs more than a first
task done well." The change is straightforward and is the natural first item next
session.

### B2 — the `is_git` contradiction: resolved, and it is the same bug

`is_git_repo` is `(path / ".git").exists()` — a pure filesystem predicate. It
cannot return false for a directory that has `.git`. Therefore the fault was
never in the predicate; it was in **the path handed to it**.

`estate_status.scan_estate(projects: list[Path])` maps `git_summary.scan` over
paths its caller supplies. When those paths were reconstructed as
`<root>/<scope>/<name>`, they did not exist, `.git` was not found, and every
project so resolved reported `is_git: false`. The census reported `true` because
the census is invoked with a real path. **The `is_git` contradiction and the
folder-walk defect are one bug observed from two directions.**

Verified live today — all four disputed projects now report correctly:

| Project | `.git` exists | `is_git_repo` | `git_summary.scan` |
|---|---|---|---|
| L5GN-Crystal-Spire | True | True | **True** |
| test_folder | True | True | **True** |
| L5GN-Archive | False | False | False (correct) |
| L5GN-server-hub-iso | False | False | False (correct) |

`estate_status.json` now reports **9 git repos**, not 7. No fix was required —
the working tree's uncommitted scanner changes already resolved it. The registry
takes `first_seen` / `last_activity` from these facts, so those dates are now
available for the previously-misreported projects.

---

## Task C — S4 dry-run

Run against the vault snapshot with real inventories. **Nothing applied.**

Basename index: **4,816 distinct basenames**, with 263 export-artifact basenames
excluded. Before Task A this index was empty and the producer aborted.

| Project | unique (1.0) | multi (1/n) |
|---|---|---|
| L5GN_Armory_v4 | **404** | 309 |
| L5GN-Crystal-Spire | **71** | **0** |
| L5GN-Armory_v2 | 68 | 229 |
| L5GN-Castle | 66 | 191 |
| l5gn-mesh-vertex-3_prod | 43 | 205 |
| L5GN_Managed_Workspace | 39 | 60 |
| L5GN-Continuous-Ingestion-Daemon | 36 | 66 |
| L5GN-Archive | **22** | 152 |
| L5GN-Armory | 11 | 204 |
| L5GN-server-hub-iso | **2** | 38 |
| test_folder | 0 | 30 |

**2,246 rows across 321 threads.** Crystal Spire's 71-unique / 0-multi split is
the cleanest signal in the estate.

### Projects gaining their first evidence

`L5GN-Archive` (22 unique) and `L5GN-server-hub-iso` (2 unique) gain evidence for
the first time — both were thin in the registry precisely because they lack usable
git history, and filename evidence is the route the brief predicted. Crystal Spire
**already had** 75 rows from the 2026-07-16 run (see Correction 1).

### The stoplist

41 basenames stoplisted; **11 distinct basenames / 166 attachment rows suppressed**.

The brief's candidates, checked:

| Basename | Stoplisted? | Projects owning | Attachments |
|---|---|---|---|
| `main.py` | yes | 6 | 56 |
| `README.md` | yes | 9 | 27 |
| **`handover_schema.py`** | **no** | **3** | **15** |
| **`citadel_archetypes.json`** | **no** | **5** | **16** |

**The brief was right on both.** They currently produce 15 rows at weight 1/3 and
16 rows at weight 1/5. **Recommend extending the stoplist to include both.**

**A finding in the other direction:** `index.html` and `style.css` are stoplisted
but owned by **exactly one project each** — stoplisting them discards a legitimate
unique hit. The stoplist is a static list where the multi-owner test is already
computed per-run; consider suppressing on *measured* ownership count rather than
on a hardcoded name.

---

## Task D — S5 dry-run

**104 rows across 84 threads**, 9 projects, from 21,795 messages scanned.

| Project | rows | threads |
|---|---|---|
| L5GN_Armory_v4 | 34 | 34 |
| L5GN-Castle | 18 | 18 |
| L5GN-Armory | 16 | 16 |
| l5gn-mesh-vertex-3_prod | 11 | 11 |
| L5GN-Armory_v2 | 10 | 10 |
| L5GN_Managed_Workspace | 5 | 5 |
| L5GN-Continuous-Ingestion-Daemon | 4 | 4 |
| L5GN-Crystal-Spire | 4 | 4 |
| L5GN-server-hub-iso | 2 | 2 |

**`L5GN-Archive` scores zero path mentions.** Worth noting as the project whose
name is most likely too generic to match safely — "archive" appears constantly in
ordinary prose, and the producer is right to be conservative, but it means Archive
depends entirely on filename evidence.

**Watermark verified.** Run 1 scanned rowids `(0, 22004]` → 104 rows. Run 2
scanned `(22004, 22004]` → **0 rows**. UAT item D is satisfied on this snapshot.

### The double-count question — the answer is "compound", and it is worse than feared

`relink.combine()` groups signals by type, applies `SIGNAL_COUNT_CAP` — which
contains **only** `{"vocabulary": 3}` — and multiplies the survivors:

```
score = 1 - Π(1 - min(weight_i, 0.97))
```

`filename_xref` and `path_mention` are distinct types, so **both survive and
compound**:

| Evidence | Score | vs. `AUTO_LINK_THRESHOLD` = 0.90 |
|---|---|---|
| one `filename_xref` @ 1.0 | **0.970** | **already auto-links alone** |
| one `path_mention` @ 0.9 | 0.900 | at threshold |
| **both, from one sentence** | **0.997** | far above |
| three *independent* signals @ 0.6 | 0.936 | below the pair |

**Flagged as the brief instructed.** A single sentence mentioning
`L5GN-Crystal-Spire\world_graph.json` produces both signals and scores 0.997 —
outvoting three genuinely independent sources at 0.936.

Two aggravating factors the brief did not anticipate:

1. **A lone unique filename hit already auto-links** (0.970 > 0.90) with no
   corroboration at all.
2. **`filename_xref` has no count cap**, so N filename hits in one thread all
   compound. Crystal Spire's 71 unique hits across 15 threads means several
   threads carry many hits each, saturating toward 1.0.

**Recommendation:** add `filename_xref` and `path_mention` to `SIGNAL_COUNT_CAP`,
and treat the two as one evidence family for scoring — a filename hit and a path
mention derived from the same message are not independent observations, and the
independent-combination formula assumes they are. **This is a `relink` scoring
change, out of scope here, and should be settled before `relink --apply` is ever
run against this evidence.**

---

## Task E — the origin query

**Delivered.** Computed in memory from the S4+S5 dry-run votes scored through
`relink.combine()`, with the floor set at `AUTO_LINK_THRESHOLD` (0.90) — the same
bar relink itself would use. **Nothing was written.**

| Project | Earliest evidenced | Score | Signal | Threads ≥ floor | Account | Thread |
|---|---|---|---|---|---|---|
| L5GN-Castle | **2026-05-20** | 0.999 | filename | 63 | gemini-personal | `Function GetNeighborContext(currentCoord As String)…` |
| L5GN_Managed_Workspace | **2026-05-23** | 0.970 | filename | 25 | gemini-personal | `ok yeah let's queue those updates as well…` |
| l5gn-mesh-vertex-3_prod | **2026-05-30** | 0.970 | filename | 51 | gemini-personal | `ok help me out here - here's the current contents of the chr…` |
| L5GN_Armory_v4 | **2026-05-31** | 0.970 | filename | 93 | gemini-personal | `first batch of 50 is running now. see file census attached` |
| L5GN-Crystal-Spire | **2026-06-07** | 0.970 | filename | 14 | gemini-personal | `when I run docker compose exec gateway mount \| grep /data` |
| L5GN-server-hub-iso | **2026-06-08** | 0.999 | filename | 3 | gemini-personal | `I had to create and add to files which I think I've done rig…` |
| L5GN-Archive | **2026-06-13** | 1.000 | filename | 15 | gemini-personal | `errr seems we didnt get it quite right XD` |
| L5GN-Armory | **2026-06-13** | 0.900 | path | 25 | gemini-personal | `before I go just adding .py files what other setup should I…` |
| L5GN-Armory_v2 | **2026-06-15** | 0.995 | filename | 30 | gemini-personal | `Morning - Turns out we have quite the harvest to collect fro…` |
| L5GN-Continuous-Ingestion-Daemon | **2026-06-18** | 0.958 | filename | 8 | claude-personal | `Prompt engineer IDE codebase audit and consolidation` |
| **test_folder** | **— none —** | | | 0 (30 below floor) | | |

### The result the brief was actually after

**Every project's earliest evidenced thread precedes its first commit.**

| Project | 1st commit | 1st evidence | Lead |
|---|---|---|---:|
| L5GN_Armory_v4 | 2026-06-17 | 2026-05-31 | **−17 d** |
| L5GN-Castle | 2026-05-29 | 2026-05-20 | **−9 d** |
| L5GN-Continuous-Ingestion-Daemon | 2026-06-26 | 2026-06-18 | **−8 d** |
| L5GN_Managed_Workspace | 2026-05-28 | 2026-05-23 | −5 d |
| l5gn-mesh-vertex-3_prod | 2026-06-04 | 2026-05-30 | −5 d |
| L5GN-Armory | 2026-06-13 | 2026-06-13 | 0 d |
| L5GN-Armory_v2 | 2026-06-15 | 2026-06-15 | 0 d |
| L5GN-Crystal-Spire | *2026-07-21 (reset)* | 2026-06-07 | n/a |

This is the brief's founding thesis, measured: **the conversation reliably comes
first, by up to two and a half weeks.** The two zero-lead projects are the two
whose first commit is same-day as their earliest thread — plausible for a project
scaffolded in the same session it was discussed.

### The caveats, stated rather than buried

- **File mtime is weak evidence of origin.** A copy, zip extraction or folder
  move resets it, and this estate has done all three. Every date above is a
  **chat timestamp**, not a file date. The `first commit` column is git, which is
  reliable; no mtime was used to establish any origin.
- **Earliest evidenced ≠ where the idea started.** The vault's earliest thread is
  **2026-05-02**, so nothing before that date can appear regardless of truth.
  `L5GN-Castle`'s earliest evidence (2026-05-20) is only 18 days after the vault
  begins — **its true origin may well predate the vault's coverage entirely** and
  this row should not be read as "where Castle started".
- **An empty row is ambiguous, not a finding.** `test_folder` shows no evidence
  above the floor, but it also has 30 rows below it. And per Correction 1, a
  project could have evidence filed under a pre-restructure name. Until the
  DECISIONS 0011 reset lands, an empty row cannot be read as "no origin exists".

### One row is demonstrably wrong, and it is instructive

`L5GN-Crystal-Spire`'s earliest evidenced thread is
*"when I run `docker compose exec gateway mount | grep /data`"* — a Docker
question with nothing to do with a text adventure.

**Cause:** it attaches an `engine.py`, and `engine.py` exists in exactly one
project's inventory in this estate — Crystal Spire's `_archive/pipeline_v1/`. A
sole owner means weight **1.0**, which alone clears the 0.90 auto-link bar.

The same applies to `tui.py`, `repl.py` and `world.json` — all sole-owner, all
weight 1.0. **Uniqueness within an 11-project estate is not distinctiveness.**
See the stoplist recommendation in Task C; this is its concrete cost.

---

## Task F — the delve index

**Delivered, with a null result that is itself the finding.**
Full write-up: `docs/investigation/2026-07-21_crystal-spire-delve-index_2-response.md`

### Harvested

**1,601 floors across 111 delves in 10 eras**, keyed `delve_<era>_<NNNN>_f<N>`
exactly as the brief described, plus one `citadel_gate` entry room. Era
breakdown in the investigation doc; the ten eras match the ten `ERA_DIGEST_*.md`
files.

**Counts were taken sandbox-side** and that is now safe — see Correction 2.

### The volume/Drive-ID chain does not exist

- 13 volume names are mentioned anywhere in the corpus.
- **Exactly one delve — 92 — binds volumes to Drive IDs** (11 IDs). Every other
  delve names volumes at most in passing.

This corroborates `DRIVE_ID_SCAN.md` independently: delve 92 is the hotspot
holding 18 of the 33 genuine IDs, because it *is* the manifest conversation.
**A lineage present for 1 of 111 delves cannot support scoring.**

Volume names also drift — `TheManifestoRebornVol01` / `ManifestoRebornVol01`, and
`ManifestationRebornVol02` is a corruption of `ManifestoRebornVol02`. Any future
join must normalise first.

**No Drive IDs were reproduced in `docs/`.** They are live, and Task 0 has just
finished removing that class of content from one repo; copying them into
L5GN-Tools would recreate the exposure in a second.

### Delve → vault thread: 111 / 111

The `modules_v3/` **filenames** carry the source title
(`module_<Era>_<NNNN>_<TitleSlug>`). De-camel-cased and fuzzy-matched against
`threads.title`, **all 111 delves match a vault thread at ≥ 0.75**, many at 1.00.

**This settles the brief's first caveat decisively.** The world was forged from
Drive-hosted stitched volumes while the vault holds chat threads — but they are
the same conversations, and the titles survived the round trip.

### Scoring — 0.000 / 0.000, and why that is not a producer failure

| Metric | Value |
|---|---|
| Ground truth (delve threads) | 110 |
| Predicted (S4+S5 ≥ 0.90) | 14 |
| True positives | **0** |
| Precision / Recall | **0.000 / 0.000** |

Read the sets, not the metric.

**Linked but not delve threads:** *building a mobile delve menu browser* ·
*help me apply the fix to the attached `tui.py`* · *building a terminal-based
d&d world for discord* · *l5gn crystal spire*

**Delve threads not linked:** *google sheets audit tool development* ·
*activity statement logic context* · *sovereign os handshake & mission brief*

The first list is threads **about building Crystal Spire**. The second is threads
**whose content was harvested into** its world. A Google Sheets audit conversation
became a delve because the forge turned it into a dungeon floor, not because it
was ever about the game.

**They are disjoint by construction.** S4/S5 answer *"which conversation built
this?"*; the delve index answers *"which conversation became this?"* The perfect
zero is what makes the conclusion strong rather than ambiguous.

**Consequence:** the brief's ambition — precision and recall on real data for the
first time — is **not delivered and cannot be from this dataset.** The estate
still has no labelled dataset for *project linkage*. What it now has is a labelled
dataset for *content provenance*, which is a different and arguably more
interesting relation, and one the schema has nowhere to put.

The 14 linked threads are a small, tractable set for a human to adjudicate if you
want a real linkage ground truth.

---

## Extra — `build_activity` refactored (the fourth folder-walk instance)

Round 3 judged this "small, contained." It held up.

`git_deep_history` in each deposit already carries the **full commit list** with
dates — which is what burst clustering needs, not just the first/last pair. The
refactor reads that, falls back to `commits_by_day`, then to `git_summary`'s date
pair, and uses census mtimes for non-git projects. `resolve_fs` remains as a
local-disk fallback reading the deposit's recorded path.

**S3 activity windows now build for all 11 projects — the first time this has
worked anywhere.**

| Project | Precision | Bursts | Window |
|---|---|---:|---|
| L5GN-Archive | mtime | 2 | 2026-05-30 .. 2026-06-22 |
| L5GN-Castle | commit | 1 | 2026-05-29 .. 2026-06-04 |
| L5GN-Continuous-Ingestion-Daemon | commit | 1 | 2026-06-26 .. 2026-07-13 |
| L5GN_Armory_v4 | commit | 1 | 2026-06-17 .. 2026-06-24 |
| **L5GN-Crystal-Spire** | commit | 1 | **2026-07-21 .. 2026-07-21** |
| *(and six others)* | | | |

New `tests/tester_build_activity.py` (28 testers), asserting the full commit list
drives burst clustering, thin-deposit degradation, non-git mtime precision, and
that a truncated commit list is **flagged** — git log is newest-first, so the
dates lost are the *earliest* ones and the window would silently narrow.

### ⚠ A consequence of Task 0 that must not be missed

Crystal Spire's activity window is now a **single day**, because the history
reset gave it one day of git history. `relink` computes
`adjusted = score × time_plausibility`, and `time_plausibility` hard-zeroes any
thread more than 14 days before a project's first commit:

| Thread date | Crystal Spire `time_plausibility` |
|---|---:|
| 2026-06-07 (its earliest evidence) | **0.000** |
| 2026-07-10 | 0.724 |
| 2026-07-21 | 1.000 |

**Every Crystal Spire thread older than about two weeks now scores zero,
annihilating all 71 of its filename hits.**

**In fairness, the reset did not create this — it deepened it.** With the
pre-reset first commit of 2026-07-11, a 2026-06-07 thread already scored 0.000.
Crystal Spire's git history never covered its real lifespan: the world was forged
from conversations going back to May, but the repo was only initialised in July.
The reset moved the recovery point from 2026-07-11 to 2026-07-21.

**Recommended fix:** record a manual `first_seen` for Crystal Spire in
`config/project_registry.json` — the curated layer `build_registry` reads and
never overwrites, which exists precisely for facts the generator cannot derive.
Its true origin is somewhere in the delve corpus, well before any commit. **This
is a registry data decision, not a code change, and it is yours to make.**

---

## Unrun — stated plainly

| What | Why | Fix |
|---|---|---|
| S4 / S5 against the **live** vault | Only the 2026-07-17 snapshot was reachable from here | Runbook below |
| `xref_filenames --apply` / `extract_path_mentions --apply` | Requires your GO and `run.py backup` first | Runbook below |
| Task E table against **applied** evidence | The table above is computed from dry-run votes in memory | Re-run after applying; expect the same numbers |
| One more `run.py build --fresh` | Deposits carry the pre-fix, redundant `basenames_beyond_cap` (harmless — coverage identical) | Next routine build |
| `relink.py:189` and the shared `REGISTRY_PATH` | Out of scope; the highest-value remaining fixes | Next brief |
| A manual `first_seen` for Crystal Spire | A registry data decision, yours to make | `config/project_registry.json` |

### Runbook — knight, in order

```bash
# 0. On EACH producer rig (Windows), regenerate deposits with the new field
python run.py build --fresh
python run.py deposit --push

# 1. On the knight — back up before any write
cd ~/L5GN-Tools
.venv/bin/python run.py backup

# 2. Rebuild registry then inventories from the deposits
.venv/bin/python chronicler/pipeline/build_registry.py
.venv/bin/python chronicler/pipeline/build_inventory.py --force
#    EXPECT: 11 built, 0 missing; L5GN-Castle shows a non-zero '+names'
#            and NO '<- SHORT' flag.

# 3. S4 dry-run — compare against the table in this report
.venv/bin/python chronicler/pipeline/xref_filenames.py
#    Spot-check three threads before going further (UAT item C).

# 4. S5 dry-run, twice. The second MUST add nothing.
.venv/bin/python chronicler/pipeline/extract_path_mentions.py
.venv/bin/python chronicler/pipeline/extract_path_mentions.py

# 5. ONLY on Tim's GO, and only if 3 and 4 are clean:
.venv/bin/python chronicler/pipeline/xref_filenames.py --apply
.venv/bin/python chronicler/pipeline/extract_path_mentions.py --apply
```

**Do not run `relink --apply`.** The double-count finding above should be settled
first.

---

## Changed files — staged, uncommitted

| File | Change |
|---|---|
| `chronicler/pipeline/build_inventory.py` | Rewritten: deposit-driven, `basename_set()`, truncation handling, `resolve_fs`/`current_signature` retained as documented fallbacks for `build_vocabulary` |
| `l5gntools/scanners/file_census.py` | Emits `basenames_beyond_cap` |
| `tests/tester_build_inventory.py` | **New** — hermetic, 13 behaviours |
| `tests/tester_file_census.py` | Asserts the basename set is complete past the cap |
| `chronicler/pipeline/build_activity.py` | **Refactored**: deposit-driven; S3 windows build for the first time |
| `tests/tester_build_activity.py` | **New** — hermetic, gates the refactor |
| `docs/investigation/2026-07-21_crystal-spire-delve-index_2-response.md` | **New** — Task F |
| `verify.py` | Registers both new testers (28) |
| `docs/COWORK_REPORT_file_census.md`, `docs/UAT_file_census.md` | Tester count 26 → 28, required by `auditor_doc_claims` |
| `docs/COWORK_REPORT_intent_evidence.md`, `docs/UAT_intent_evidence.md` | **New** |

In **L5GN-Crystal-Spire** (a separate repo, committed on your ruling): history
rebuilt, `.gitignore` extended, `HISTORY_RESET.md` added.

**The results log still needs a UAT stamp or the gate refuses the commit.**
