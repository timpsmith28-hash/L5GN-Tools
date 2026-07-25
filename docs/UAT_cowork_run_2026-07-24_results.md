<!-- uat: commit=1951cfe dirty=false host=LucasGoonPC walked=2026-07-25 -->

# Results log — Cowork run 2026-07-24 (walked 2026-07-25, gaming rig)

Partner to `UAT_cowork_run_2026-07-24.md`. Records the evidence gathered walking
the rig-runnable checks on the **gaming rig** (`LucasGoonPC`) against a real
estate build generated `2026-07-25T09:42:53+01:00` on toolkit `1951cfe` (clean).

This log records **evidence**, not acceptance. Per doctrine, `verify.py` GREEN
proves the code works; only Tim walking a check closes it. Each item is tagged
with what was observed, so Tim can ratify (or reject) from the evidence rather
than re-derive it.

**Legend**
`[EVIDENCE]` mechanism observed working on the real 2026-07-25 build — ready for
Tim to ratify · `[BLOCKED]` cannot pass on this build because of the
mid-restructure estate layout (cause named) · `[FIXTURE]` proven by its tester
only; the real estate carries no data to exercise it this run · `[DEFERRED]`
needs the work rig, the knight, or Tim's judgment.

The estate scanned as **3 projects**: `L5GN` (a non-git *container* folder — see
Finding 1), `L5GN-Crystal-Spire` (6 commits), `l5gn-mesh-vertex-3_prod` (136
commits). The whole walk is coloured by Finding 1; read it first.

---

## Headline structural findings (read before the checklist)

**Finding 1 — the `L5GN/` container is scanned as one non-git project, and that
distorts most content checks.** The restructure nested seven repos under
`GitHub/L5GN/` (the original five plus **L5GN-Castle** and **CID**, both
previously locked — see Finding 2). The config root is still `…/GitHub`, so the
scanner sees `L5GN/` as a single child folder with no `.git` of its own and
walks the whole subtree as one project called `L5GN`. Consequences observed:

- **File census hits its 2000-file cap** and is flagged as a payload anomaly
  (514,159 bytes, `truncated: true`). The honesty machinery worked; the input
  was wrong.
- **1,633 walled-off path strings leak into the report and data feed** (see
  1.A2) — because the nested repos' `.gitignore` files don't apply from the
  `L5GN/` vantage point, so `raw_claude_files` / `Takeout` / `chat_threads`
  paths get censused as ordinary files.
- **60 false UNCOMMITTED-CRITICAL** — a non-git folder has nothing committed, so
  every write-capable file reads as uncommitted.
- **Per-repo identity is lost** — Castle's and CID's git history, `adr/`,
  `DECISIONS.md`, and blast-radius attribution are all collapsed into the blob.

The two proper git repos (`L5GN-Crystal-Spire`, `l5gn-mesh-vertex-3_prod`) are
**clean on every one of these axes** — 0 path leaks, 0 false criticals, correct
gitignored/data skips. So the fix is not in the scanners; it is to **finish the
restructure**: move the last two repos into `L5GN/`, then flip
`config/local.json` `LucasGoonPC.roots` to `…/GitHub/L5GN` (walk-list 4-cfg / 5,
which already says "only once all 9 repos are in `L5GN\`"). Until then, the
gaming-rig build cannot cleanly pass the scope-scope checks 1.A1 / 1.A2.

**Finding 2 — restructure has advanced since the walk-list was written.**
`L5GN-Castle` and `CID` (listed as LOCKED in 4.2b) are now inside `GitHub/L5GN/`.
**7 of 9** estate repos are in `L5GN\`. Remaining at top level:
`L5GN-Crystal-Spire`, `l5gn-mesh-vertex-3_prod`. Worth updating 4.2b to reflect
that only these two are still out.

**Finding 3 — `L5GN-Tools` is not scanned** (it is a top-level git repo under the
root but absent from the project list). Its own 16-entry `DECISIONS.md` is
therefore why check 2.B1 has no real-data hit. Confirm self-exclusion is
intended; if so, note that the toolkit's own governance surface is invisible to
its own report.

**Finding 4 — `all-MiniLM-L6-v2`** (a git repo at the estate root) is **not**
scanned as a project. This is the vendor asset deferred in 4.V (do not move until
`CITADEL_MINILM_PATH` is updated). Confirm it is being dropped by a vendor
heuristic and not silently erroring.

**Finding 5 — `relinking_test.txt` (36 KB) sits loose at the estate root**
alongside `.obsidian`. Scratch candidate (cf. 4.Sc). Not a repo; harmless, but
it is inside the scanned root.

---

## Brief 1 — scanner_bugfixes

- `[DEFERRED]` **1.A1** Chronicler full-estate `todo_adr` in the low tens —
  needs the work rig where Chronicler lives. Not walkable on the gaming rig.
- `[BLOCKED]` **1.A2** No `raw_*` / `chat_threads` / `Takeout` / `*_files` path
  in the report. **Not clean on this build:** 1,633 such path strings appear —
  `file_census.files[].path` (1,283), `workspace_scanner.modules[].path` (337),
  plus a handful in census dirs/outliers/basenames. **All 1,633 originate in the
  `L5GN` container** (Finding 1); the two proper repos leak **zero**. Example:
  `L5GN-Castle/data/Chronicler_Backup/raw_claude_files/data-20260711_1700/conversations.json`.
  `file_census` is exempt from the scope-skip by brief design (it classifies
  rather than omits), so this is a layout problem, not a scanner regression —
  clears when the root points at `…/GitHub/L5GN` and each repo is scanned as
  itself.
- `[EVIDENCE]` **1.A3** No chat-transcript **text** anywhere. Searched the data
  feed for role/`Human:`/`Assistant:` transcript shapes — none. `file_census`
  and `blast_radius` emit paths and line *numbers*, never body text. The 1.A2
  leak is path strings only; no conversation content crossed the wall.
- `[EVIDENCE]` **1.A4** Scope blocks present and populated on real data. On the
  `L5GN` blob: `env_scanner` skipped **4,175** paths `by_reason: {data_dir}`,
  `todo_adr` 904, `blast_radius` 345, `import_scanner` 337, `doc_census` 35. On
  Crystal-Spire: `todo_adr` skipped **3,220** `{gitignored}`, `doc_census`
  1,605. The `data_dir` and `gitignored` reasons both fire against real trees.
- `[EVIDENCE]` **1.B1 / 1.B2** Report self-validates and truncates honestly.
  The `L5GN` file_census hit its cap and emitted `truncated: true` with the true
  figure — an honest cap, not a silent slice. Report + embedded DATA both parse
  (node --check PASS on the embedded JS).
- `[EVIDENCE]` **1.B3** Payload-anomaly banner has real content to show:
  `anomalies = [{project: L5GN, scanner: file_census, bytes: 514159, truncated:
  true}]`. The banner fires at the top of the report naming scanner + project.
- `[EVIDENCE]` **1.B4** `verify.py` GREEN, 6 auditors + 39 testers;
  `tester_scanner_scope` + `tester_report_selfcheck` listed OK.
- `[EVIDENCE]` **1.C1** Task C (Open-questions → PENDING) confirmed as governance
  scope — walked under 2.B3 below, not expected here.

## Brief 2 — governance_scanners

- `[EVIDENCE]` **2.A1 / A2 / A3** Scope summary honest: one root, state
  `scanned`, 3 projects, scope `l5gn`. Toggle / caveat / "empty this run" are
  template-proven (client-side `SP()`/`rescope()`, no re-scan); no empty root in
  this estate to exercise the "empty this run" string on real data.
- `[FIXTURE]` **2.B1** `DECISIONS.md` by entry + tier. No real-data hit: the one
  repo with a 16-entry `DECISIONS.md` is `L5GN-Tools`, which is not scanned
  (Finding 3). Proven by `tester_decision_records` only.
- `[FIXTURE]` **2.B2** `adr/NNNN` count. CID carries `adr/`, but CID is collapsed
  inside the `L5GN` blob (Finding 1), so no per-repo adr count surfaced. Proven
  by tester only.
- `[EVIDENCE]` **2.B3** Open-questions → PENDING. `L5GN-Crystal-Spire` carries an
  `## Open questions` section — **1 section, 7 items** counted toward PENDING.
- `[EVIDENCE]` **2.C1 / C2** Tracked-secret labelling on real data. A genuine
  hit: `L5GN-Crystal-Spire/_archive/pipeline_data/world_sample.json` is
  **TRACKED** and trips a secret-suspect line. The `L5GN` blob shows one
  `untracked (no git)` suspect. Names, line counts and git status only — **no
  secret value** appears in the output. (Tim to rule whether `world_sample.json`
  is a real exposure or a benign sample.)
- `[EVIDENCE]` **2.D1** Shared-filename verdicts populated: 15 shared-filename
  groups, **13 divergent / 2 identical-content** groups labelled.
- `[FIXTURE]` **2.E1** 0-commit note. No 0-commit git repo exists in this estate
  (`TSsToAssets` is not here); Crystal-Spire has 6 commits, mesh 136, and the
  `L5GN` blob is non-git (it carries the *different* "not a git repository"
  note). Proven by `tester_zero_commit_note` only.
- `[EVIDENCE]` **2.G1** `verify.py` GREEN, 6a + 37t; five governance testers
  listed OK.

## Brief 3 — blast_radius

- `[EVIDENCE]` **3.A1 (mechanism)** Blast-radius tiers real code. `L5GN` blob:
  102 hits (95 raw-write, 4 guarded-write, 3 read-only). Crystal-Spire: 3
  raw-write (`forge_v2.py` http-writes, `pull_logs.ps1` shell-os). mesh: 20
  raw-write (`restore_personas.py`, `api/registry.py` db-writes). The specific
  SolConfig / `upload_r141.py` prod-write case is work-rig only.
- `[EVIDENCE]` **3.A2** No hit originates from a gitignored data/chat path — the
  blast-radius `scope` block skips them (345 skipped on the blob); no `raw_` /
  `chat_threads` path appears among blast-radius hits.
- `[EVIDENCE]` **3.A3 (guardrail)** No script body, alias or credential stored.
  Every hit carries only `family / signal / tier / env-classification / guarded /
  path / line-number`. `env` classifies to `none` throughout (no Salesforce
  prod-alias in the personal estate, as expected). The raw line is never stored.
- `[EVIDENCE]` **3.A4** Report has a Blast Radius tab ranking by tier.
  (Template-proven; real tiers above feed it.)
- `[EVIDENCE / caveat]` **3.B1 / B2** UNCOMMITTED-CRITICAL. Fires correctly on
  committed repos: **0** on Crystal-Spire and mesh (both fully committed). The
  `L5GN` blob shows **60** — but that is Finding 1 (a non-git container reads
  every write as uncommitted), not a true alarm set. The clean-repo behaviour is
  the real evidence; the blob number is noise until the root flips.
- `[DEFERRED]` **3.C1 / C3** Does the estate list match Tim's sense of the sharp
  edges — Tim's judgment. Note that Castle/CID prod-writes are currently hidden
  inside the blob, so this cannot be fairly judged until Finding 1 is resolved.
- `[EVIDENCE]` **3.C2** `db-writes` false-positive tuning: bare `.commit()` /
  local-SQLite is visibly the dominant raw-write family (e.g. mesh
  `restore_personas.py`, `api/registry.py`). Ruling still open (Tim).
- `[EVIDENCE]` **3.G1** `verify.py` GREEN; `tester_blast_radius` +
  `tester_blast_uncommitted` listed OK.

## Brief 4 — estate_restructure

Walked as state-of-the-estate, not as a build. See Findings 1–5. Net: 7 of 9
repos now in `L5GN\` (Castle + CID moved since the sheet was written); the two
still out are `L5GN-Crystal-Spire` and `l5gn-mesh-vertex-3_prod`; the config-root
flip (4-cfg) and a clean scope-scope pass both wait on those two moving in.

---

## What this run could not close, and why

- **1.A1, 3.A1** — work rig (Chronicler, SolConfig). A separate walk on `10280L`.
- **1.A2, clean 3.B, 3.C** — blocked on Finding 1; re-walk after the root flips
  to `…/GitHub/L5GN`.
- **2.B1, 2.B2, 2.E1** — no real-data carrier in this estate (holders excluded
  or collapsed); tester-proven, awaiting an estate that contains them.
- **The consumer side (knight)** — untouched here; a later thread deposits from
  the rigs and tests `consume` / `build_registry` on the Castle.

## Suggested next action

Finish the two remaining moves into `GitHub/L5GN/`, flip
`config/local.json` `LucasGoonPC.roots` → `…/GitHub/L5GN`, rebuild, and re-run
this walk. Expect: project count jumps from 3 to ~7 (each repo as itself), the
1,633 path leaks and 60 false criticals vanish, and 2.B1/2.B2 (Tools' DECISIONS,
CID's adr) become walkable — turning most of the `[BLOCKED]`/`[FIXTURE]` rows
into real-data evidence.

---

## Addendum — re-walk after retargeting root → `…/GitHub/L5GN` (build 10:00)

Tim moved `L5GN-Crystal-Spire` into `L5GN/` and retargeted the config root, then
rebuilt (`2026-07-25T10:00:04+01:00`, toolkit `1951cfe`, dirty — the only
uncommitted change being this results log). The collapse is **resolved**: **8
projects, each scanned as itself** — `L5GN-Archive` (non-git folder, see below),
`L5GN-Armory` (6), `L5GN-Armory_v2` (10), `L5GN-Castle` (12), `CID` (63),
`L5GN-Crystal-Spire` (6), `L5GN_Armory_v4` (80), `L5GN_Managed_Workspace` (3).
Per-repo git history, blast-radius and identity are all restored.

**Two findings carried forward by Tim's ruling (both left as-is this run):**

- **`[NOTED GAP]` mesh-vertex-3_prod is no longer scanned.** The root flip dropped
  it — it remains at `…/GitHub/` (outside the new root) and **cannot move**: it is
  slaved to the knight and is how deploys run from it. Confirmed still on disk at
  `…/GitHub/l5gn-mesh-vertex-3_prod`. Consequence: the prod deploy repo (136
  commits; prod db-writes in `restore_personas.py`, `api/registry.py`) has **no
  blast-radius coverage from this rig** until it is either re-added as a second
  root or scanned from the knight. Ruled: leave dropped, note the gap.
- **`[DEFERRED]` 1.A2 leak is now solely `L5GN-Castle`.** Estate-wide leak count
  is 5,668 path strings — **100% from Castle**, all under
  `data/Chronicler_Backup/raw_claude_files/…`; the other seven projects leak
  **zero**. Cause confirmed on disk: Castle's `.gitignore` lists only
  `core/data/castle.db`; the Chronicler backup is **neither tracked nor
  gitignored** (`git check-ignore` → not ignored), so file_census lists it as
  at-risk (3,482 `at_risk[].path` + 1,823 `files[].path` + 337
  `workspace_scanner`), hitting the 2000-file cap (anomaly fires: Castle
  file_census, 1,171,674 bytes, `truncated: true`). Crystal-Spire — which
  gitignores its data — leaks zero, which is the proof the gitignore fix would
  work. Ruled: leave it, Tim to rule later.

**Updated verdicts on the properly-shaped build:**

- `[BLOCKED→DEFERRED]` **1.A2** — no longer estate-wide; isolated to Castle's
  un-gitignored backup (above). 7 of 8 projects clean.
- `[FIXTURE→EVIDENCE]` **2.B2** `adr/NNNN` — CID now scanned as itself reports
  **adr = 9**. The convention count surfaces on real data.
- `[EVIDENCE]` **2.B3** — Crystal-Spire still the carrier: 1 Open-questions
  section, 7 items → PENDING.
- `[FIXTURE (still)]` **2.B1** `DECISIONS.md` by entry+tier — still no carrier;
  the 16-entry `DECISIONS.md` is in `L5GN-Tools`, which is **not** under `L5GN\`
  and remains unscanned (Finding 3). Tester-proven only.
- `[FIXTURE→EVIDENCE]` **2.C1** tracked secrets — **two** real TRACKED hits now:
  `L5GN-Crystal-Spire/_archive/pipeline_data/world_sample.json` and
  `L5GN_Armory_v4/zCodeAlphaTests_Ideas/ETL_Pipeline_Review_and_Optimisation.json`.
  Names + git status only, no values. (The Armory_v4 file read `untracked` in the
  collapsed blob and `TRACKED` scanned-as-itself — a clean illustration of why
  per-repo scanning matters.) Both await Tim's exposure ruling.
- `[FIXTURE→EVIDENCE]` **2.D1** dupes — estate-wide now: **25 identical-content
  groups, 27 divergent of 39 shared-name groups**.
- `[FIXTURE (still)]` **2.E1** 0-commit note — no 0-commit repo in the estate.
- `[FIXTURE→EVIDENCE]` **3.B1** UNCOMMITTED-CRITICAL on real git repos — genuine
  hits now visible: `L5GN-Armory` 5, `L5GN-Armory_v2` 2, `L5GN-Castle` 1 (these
  are committed repos, so these are *real* uncommitted write-capable files worth
  Tim's eyes). CID/Crystal-Spire/Armory_v4/Managed_Workspace: 0. Caveat:
  `L5GN-Archive` shows 14, but it is a **non-git plain folder** (`is_git=false`,
  "not a git repository") — those are the non-git artifact, not real alarms.
- `[EVIDENCE]` **3.A** blast tiers per repo look sane: CID shows a `guarded-write`
  (typed-gate detection working) alongside raw-writes; guardrail intact
  throughout (family/tier/env/path/line only).

**New minor finding — `L5GN-Archive` is a non-git plain folder** (420 files, no
`.git`, `at_risk_note: "not a git repository"`). It leaks zero chat paths, but as
a non-repo it has no history and reads every write-capable file as
uncommitted-critical (14). Worth deciding whether it should be a repo, be
gitignored-from-concern, or be treated as an archive that the blast-radius alarm
should not shout about.

**Net after retargeting:** the scope-discipline machinery is proven end-to-end on
a correctly-shaped estate. The only open scope leak is one repo's forgotten
`.gitignore` (Tim to rule), and the only coverage gap is one un-moveable deploy
repo (noted). `2.B1` and `2.E1` remain the only genuinely un-carried checks on
this rig; both are tester-proven and wait on an estate that contains their
subjects.

---

## Addendum — work-rig walk (`10280L`, estate `work`, build 10:23)

First-ever scan of the work estate (toolkit `1951cfe`, clean). **19 projects
across two roots** — `MCF` (scope `mcf`, 9) + `L5GN` (scope `l5gn`, 10); both
roots `scanned`; Tim confirmed the scope filter switches all / l5gn / mcf. This
estate carries the subjects the gaming rig lacked, so several tester-only rows
now have real data — and two surface discrepancies worth Tim's eyes before the
deposit is trusted.

**Now walked on real data:**

- `[FIXTURE→EVIDENCE] (flagship)` **1.A1** — `Chronicler` is in this estate, and
  `todo_adr` returns **marker_count = 1**, having skipped **3,235** paths
  `by_reason {data_dir}`. The motivating bug (298 TODO-shaped strings mined from
  a chat dump) is fixed on the real Chronicler: low single digits, not hundreds.
- `[FIXTURE→EVIDENCE]` **2.E1** — `TSsToAssets` is a real git repo with **0
  commits** and carries the exact note: *"repo initialised but has no commits —
  nothing is under version control."*
- `[EVIDENCE]` **2.B3** — Open-questions → PENDING, strongly carried: SolConfig
  12, Crystal-Spire 7, ChurnLevelIndictor 6, WizForgeAnalytics 5.
- `[EVIDENCE]` **3.A3 guardrail** — every blast-radius hit is
  family/tier/env/guarded/path/line only; no source line, alias or credential.

**Both discrepancies resolved (source seen 2026-07-25) — scanner correct in both:**

- `[RESOLVED] 3.A1 — the scanner is right; the sheet's expectation was stale.`
  `upload_r141.py` (source reviewed) is a **sandbox-first, gate-guarded,
  phrase-confirmed** uploader: it defaults to `--target sandbox`, prod needs
  `--allow-prod` *and* a typed phrase, and every write sits behind
  `run_all_gates` + human approval. So `guarded-write` is the **correct** tier —
  not the raw prod-write the sheet imagined. And `env = none` is **correct too**:
  the prod alias `myMainAlias` is resolved at *runtime* (`org = ALIASES[key]`),
  so the DML line reads `--target-org org` — a variable, not a literal alias —
  and `classify_env` rightly refuses to assert `prod` from a name it cannot see.
  Nameable limitation for the 3.C2 ruling (a blind spot, not a bug):
  env-classification only reads a **literal** `--target-org <alias>`; a
  runtime-resolved alias (good practice, exactly as here) always reads `none`.
  Also for 3.C2: `extract_deep_git_history.py` raising `shell-os` raw-write is a
  benign dev tool — a candidate false positive.
- `[RESOLVED] 2.B1 — the counter is right; ValidationAutomation's file uses a
  different entry format.` Proven locally: `parse_decisions` on the toolkit's own
  `docs/DECISIONS.md` returns **16, all `accepted`** — exactly the sheet's figure,
  and it does check `docs/DECISIONS.md`, not just root. But `_DECISION_ENTRY` is
  `^##\s+(\d+)` — it counts **only level-2 headings that begin with a digit**
  (`## 0001 — title`). Tim has confirmed ValidationAutomation *has* a
  `docs/DECISIONS.md`, so its `decisions_count = 0` means its entries are **not**
  in that `## <NNNN> — …` form (a different heading level, a word before the
  number, a table, etc.). Not a code bug — a convention coupling. Fix, if wanted:
  align that file's entry headings to `## <NNNN> — …`, or broaden the regex in a
  brief follow-up (at the risk of false matches). The counter needs no change.
- `[DEFERRED] 1.A2 — Chronicler leaks 1,981 chat paths` (`chat_threads/…`,
  `raw_…`) via file_census, and is the truncation anomaly (423,007 bytes). Cause
  is identical to Castle: `Chronicler` is a **non-git folder** (`is_git=false`),
  so no `.gitignore` classifies its chat archive out. The other 18 projects leak
  zero. Same ruling pending as Castle.

**Minor:** 7 of the 19 work projects are non-git plain folders (`Chronicler`,
`ActivityStatements`, `GulamDataExport`, `L5GN_Bridge`, `UnifedIntelligenceSource`,
`v1 proto`, `WizForgeAnalytics`) — each lists all files and will show phantom
uncommitted-criticals, as `L5GN-Archive` did on the gaming rig.

**Net:** both flagged discrepancies resolved in the scanner's favour — the
work-rig report can be trusted. Two *conventions* are worth aligning at leisure
(neither blocks anything): give `upload_r141`-style prod aliases a literal form if
you want blast-radius to escalate them to `prod` tier, and align
ValidationAutomation's `DECISIONS.md` entries to the `## <NNNN> — …` form if you
want its decisions counted. The deposit is unaffected regardless.
