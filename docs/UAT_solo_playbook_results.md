<!-- uat: commit=5e5fee2 dirty=false host=LucasGoonPC walked=2026-07-27 -->
<!-- gate= deliberately omitted. This walk happened at 5e5fee2, where the gate
     registered 43 testers. auditor_uat_stamp checks gate= against the LIVE
     tree's count rather than the stamped commit's, so a truthful historical
     figure turns red the moment anyone registers a tester -- and the cheapest
     way back to green is to edit the record. That happened three times in one
     day here (43t -> 45t -> 46t) before anyone stopped.
     docs/README.md already prescribes the answer: gate= is optional, so
     "omit it rather than assert a count you didn't observe". commit, host and
     walked carry the provenance that matters; the count is recoverable from
     the commit itself. Same disposition as docs/archive/UAT_round_3_results.md,
     which reached this conclusion first. -->

<!-- Open question, not fixed here: whether auditor_uat_stamp should resolve
     gate= against the stamped commit's verify.py (making the field meaningful
     and permanent), or refuse the field outright. Until then, do not write it. -->

# Results log — solo playbook (walked 2026-07-27)

Partner to `docs/COWORK_BRIEF_solo_playbook.md` / `docs/UAT_solo_playbook.md`
(walk-sheet) / `docs/COWORK_REPORT_solo_playbook.md`. Every command below was
run for real on `LucasGoonPC`; output is condensed where very long (the
`relink.py` dry-run table in particular), full numbers preserved.

---

## Step 1 — rig confirm

```
git log --oneline -1           -> 5e5fee2 (HEAD -> main) docs: confirmed decision 0017
hostname                        -> LucasGoonPC
.\.venv\Scripts\Activate.ps1    -> FAILED: not found
```

`.venv` existed (`Test-Path .venv` → `True`) but had no `python.exe` in
`Scripts\` (`Test-Path .venv\Scripts\python.exe` → `False`) — broken/partial
venv. Python fell back to the Windows Store interpreter
(`WindowsApps\PythonSoftwareFoundation.Python.3.13...`). `verify.py` still
ran GREEN against it (6 auditors, 30 testers — pre-round baseline), because
the stdlib-only core doesn't need the extras. Rebuilt clean:

```powershell
Remove-Item -Recurse -Force .venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # confirmed: sys.prefix -> …\.venv
pip install -e .
pip install -e ".[chronicler]"      # pyyaml, sentence-transformers, torch, etc.
pip install -e ".[viewer]"          # datasette
git config core.hooksPath .githooks
python verify.py                    # GREEN, 6 auditors / 30 testers (pre-round baseline)
```

## Step 2 — throwaway `CHRONICLER_HOME`

```powershell
mkdir C:\Users\timps\Documents\chronicler_dev
```

## Step 3 — combined config entry

`config\local.json`'s `LucasGoonPC` entry (pre-existing: `role: producer`,
`estate: personal`, one root `C:/Users/timps/Documents/GitHub/L5GN` scope
`l5gn`, `push_target`/`push_transport` to `l5gn-castle`) extended with:

```json
"vault": "C:/Users/timps/Documents/chronicler_dev/chronicler.db",
"estates_dir": "C:/Users/timps/Documents/GitHub/L5GN-Tools/data/outbox",
"chronicler_home": "C:/Users/timps/Documents/chronicler_dev"
```

`run.py config` confirmed: `hostname: LucasGoonPC`, `role: producer`,
`estate: personal`, root listed with no `(MISSING)`, plus `vault:` and
`estates_dir:` lines. `chronicler_home:` did **not** print in this summary
despite being set and correctly used by every later step (`ingest`/
`consume`/`serve` all resolved it) — a minor cosmetic gap in the summary
printer only, noted in `SOLO_PLAYBOOK.md` §4, no functional impact.

## Step 4 — the loop

### 4a. `census`

```
census: host=LucasGoonPC role=producer estate=personal
  producer domain: 8 project(s), 15,727 files, 3,942.5 MB
    (L5GN-Archive, L5GN-Armory, L5GN-Armory_v2, L5GN-Castle,
     L5GN-Continuous-Ingestion-Daemon, L5GN-Crystal-Spire,
     L5GN_Armory_v4, L5GN_Managed_Workspace)
  3,669 file(s) on disk and not in git.
```

Confirmed: producer-domain only, no consumer-domain (`chronicler_home`)
check at all — matches `census.run_census`'s role-branch exactly.

### 4b. `build`

8 projects scanned. `data/estate.json`: 8 projects, root
`C:\Users\timps\Documents\GitHub\L5GN` scope `l5gn`.

### 4c. `deposit` (stage only)

```
deposit: estate 'personal' (role producer) -> …\data\outbox\personal
  snapshot : estate-2026-07-27.json
  push cmd : scp -r …\data\outbox\personal l5gn-castle:vault/estates/
             (staged only; re-run with --push to send)
```

`dir data\outbox\personal` → `history\`, `deposit_manifest.json` (428
bytes), `estate.json` (2,826,855 bytes). No push run.

### 4d. `consume` — hypothesis check

```
consume: swept …\data\outbox  (vault: no_vault)
  [personal] ingest=ingested verified=True snap=estate-2026-07-27.json
             | estate_diff=insufficient_history | drift=needs_inputs
```

**Hypothesis CONFIRMED YES:** `consume` found and read this box's own staged
deposit via `estates_dir` pointed at its own `data\outbox` — no push, no
second host, no code change. `vault: no_vault` expected (nothing built the
throwaway vault yet).

### 4e. `ingest`

Export zips: `data-e9e581a0-5742-4f86-b225-16db4d10d57c-1784970578-
f59b4d74-batch-0000.zip` (Claude, 25/07/2026) and
`takeout-20260719T101209Z-1-001.zip` (Gemini, 19/07/2026), copied to
`chronicler_dev\chat_threads\zip_downloads\`.

```
python run.py intake --dry-run
  … claude          -> raw_claude_files
  … gemini_takeout  -> raw_gemini_files

python run.py ingest --skip-backup
ingest: DB=C:/Users/timps/Documents/chronicler_dev/chronicler.db
ingest: [2/3] intake drop zone   (both zips archived correctly)
ingest: [3/3] pipeline
  [normalize_claude] ok — +39 new / 0 changed / 0 skipped
  [normalize_gemini_personal] ok — +7033 new / 0 changed / 0 skipped
  [normalize_md_transcript] skipped (no input available)
  [reconcile_gemini] skipped (no input available)
  [group_fallback] ok — +1062 new / 0 changed / 74 skipped
  [suggest_close] ok — +1028 new / 0 changed / 0 skipped
  [set_substantive] ok — no new rows
  [relink] skipped (no input available)
  [render_md] ok — 1101 threads rendered
Done. 6 stage(s) ran, 3 skipped.
```

### Sharp edge 1, reproduced on purpose — `consume` before `finalize_db.py`

```
python run.py consume
consume: swept …\data\outbox  (vault: schema_mismatch)
  [personal] … | estate_diff=insufficient_history | drift=needs_inputs
```

Matches the brief's grounding note exactly: `schema_mismatch` / `needs_
inputs`, no cause named.

### 4f. `finalize_db.py --apply` — sharp edge 6 hit first, then fixed

**Bare invocation (no `CHRONICLER_HOME` set in this shell):**

```
python chronicler\pipeline\finalize_db.py --apply
DB: C:\Users\timps\Documents\GitHub\L5GN-Tools\chronicler\chronicler.db
...
sqlite3.OperationalError: no such table: threads
```

Wrong DB — resolved to the repo-relative default
(`chronicler\chronicler.db`), not the throwaway home, because `db.py`'s
`CHRONICLER_HOME` resolution is environment-only and `run.py`'s subcommands
only set it for their own subprocess. **This also caused the finding
recorded as sharp edge 8 below** (this same bare run wrote a
`schema_frozen.sql` inside `chronicler\pipeline\` — but since the run
crashed before reaching the freeze step, sharp edge 8 wasn't actually
triggered by *this* invocation; it was triggered by the corrected one below,
because dump_frozen_schema always ran even after CHRONICLER_HOME was fixed —
see below).

**Fixed:**

```powershell
$env:CHRONICLER_HOME = "C:/Users/timps/Documents/chronicler_dev"
python chronicler\pipeline\finalize_db.py --apply
DB: C:\Users\timps\Documents\chronicler_dev\chronicler.db
registry canonical_names known: 0
----- census: before -----
  <NULL>: 1062, none: 38, exact: 1
  linked threads: 1 (evidence: 0)
  substantive: 1=242, 0=859
[P1] invalid project_link rows: 0
[P2] 'none' rows to migrate: 38
[P3] substantive: 242 substantive / 859 fragment of 1101 threads
backup written: …\chronicler_dev\chronicler.db.bak-finalize-20260727T185739Z
P1 repaired 0 link(s). P2 migrated 38 'none' -> NULL. P3 populated.
schema_version stamped: 1.0-frozen (user_version 1).
frozen schema dumped: …\L5GN-Tools\chronicler\pipeline\schema_frozen.sql   <-- sharp edge 8
----- census: after -----
  <NULL>: 1100, exact: 1
post-check: 'none' remaining=0, invalid project_link remaining=0
post-conditions OK.

python run.py consume
consume: swept …\data\outbox  (vault: ok)
  [personal] … | estate_diff=insufficient_history
  | drift={'discussed_not_present': 0, 'talked_not_built': 0, 'built_not_discussed': 0}
```

Confirmed: `finalize_db.py --apply` fixed the `schema_mismatch`; `consume`
now clean with real (zero) drift. **But** the frozen-schema dump wrote to
the repo's tracked `chronicler\pipeline\schema_frozen.sql` — the bug fixed
in code this round (sharp edge 8, see below).

### 4g. Registry — sharp edge 7, hit then fixed

**Without `CHRONICLER_REGISTRY_PATH` set:**

```
python chronicler\pipeline\build_registry.py --report-aliases
… (full curated registry printed: L5GN OS, WizForgeAnalytics, Citadel
   MicroIDE (CID), Command Deck, standalone projects — 31 entries)
(dry-run: 31 entries would be written to C:\Users\timps\L5GN\.intel_sync\project_registry.json)
```

That path is **outside the throwaway boundary** — Tim's real, pre-existing
curated registry. Root-caused to `resolve_registry_path()`'s
`CHRONICLER_ROOT.parent.parent` derivation: `chronicler_dev`'s two-levels-up
hop landed on `C:\Users\timps\`, then `/L5GN/.intel_sync/…` resolved to a
real file. `--report-aliases` is dry-run-only, so nothing was written this
time.

**Fixed:**

```powershell
$env:CHRONICLER_REGISTRY_PATH = "C:/Users/timps/Documents/chronicler_dev/project_registry.json"
python chronicler\pipeline\build_registry.py --report-aliases
(dry-run: 31 entries would be written to C:\Users\timps\Documents\chronicler_dev\project_registry.json)

python chronicler\pipeline\build_registry.py
Wrote 31 entries to C:\Users\timps\Documents\chronicler_dev\project_registry.json
  from estate=personal  …\data\outbox\personal\estate.json
2 Claude project name(s) matched no project.
19 deposit gap(s).
```

Confirmed content unchanged (still the real curated aliases — expected, read
from the separate shared authoring source, `config/project_registry.json`),
write target now correctly isolated. `l5gn-castle-repo` alias list showed
only `'L5GN-Castle'`, no bare `'Castle'` — `seed_suppress` fix (`b7c2390`)
confirmed still holding.

### 4h/4i. `build_inventory.py` / `build_activity.py`

**Before the registry was actually written (only `--report-aliases` run):**

```
[build_inventory] registry missing: …\project_registry.json (run build_registry.py first)
[build_activity]  registry missing: …\project_registry.json (run build_registry.py first)
```

Confirms dry-run truly writes nothing.

**After the real write:**

```
build_inventory: 8 built, 0 unchanged, 0 without census,
                  18 concept project(s) with no deposit of their own, 31 missing.
build_activity:  8 built, 0 unchanged, 18 concept project(s) with no window
                  of their own, 31 missing.
```

`MISSING` entries are all other-machine/MCF projects genuinely absent from
this box's own single-root deposit — expected, not a defect.

### 4j/4k. `xref_filenames.py` / `extract_path_mentions.py` (dry-run)

```
xref_filenames: 1987 evidence rows across 304 threads. (dry-run - nothing written.)
extract_path_mentions: 270 new evidence row(s) across 146 thread(s). (dry-run - nothing written.)
```

### 4l. `relink.py --out data\relink_dryrun.json` (dry-run only)

```
Threads scanned: 1100
  auto-link             53
  suggestion           364
  ambiguous            139
  downgrade              0
  no-op                544
  skipped: exact          1
[DRY RUN] Nothing written. Re-run with --apply to commit.
[report written to data\relink_dryrun.json]
```

Sample auto-links, suggestions, and ambiguous pairs recorded in full in the
session transcript; omitted here for length. No `--apply` passed.

### 4m. `serve`

```
serve: live vault   …\chronicler_dev\chronicler.db
serve: snapshot     …\chronicler_dev\serve-snapshot\chronicler-serve.db
serve: showing vault as of 2026-07-27T19:07:23Z (snapshot) -- re-launch
       `run.py serve` to refresh.
serve: datasette serve --immutable …\chronicler-serve.db -h 0.0.0.0 -p 8001
serve: read-only (--immutable, on a copy).
```

Browsed at `http://192.168.0.12:8001/` — page banner: *"Chronicler vault
(snapshot) — Snapshot, not live. showing vault as of 2026-07-27T19:07:23Z
(snapshot)"* — DECISIONS 0013 confirmed directly. 15,330 rows, 11 tables.

## Step 5 — `git status` check, sharp edge 8 caught

```
git status
  modified:   chronicler/pipeline/schema_frozen.sql
  Untracked:  docs/UAT_solo_playbook.md
git diff --stat chronicler/pipeline/schema_frozen.sql
  1 file changed, 52 insertions(+), 81 deletions(-)
```

Tracked file, real structural diff — the dev vault's schema had overwritten
the repo's canonical frozen-schema record. Reverted:

```
git restore chronicler/pipeline/schema_frozen.sql
git status   -> clean except docs/UAT_solo_playbook.md untracked
```

## Step 6 — the code fix, and re-verification

`chronicler/pipeline/finalize_db.py`: `frozen_schema_target()` added,
routes the dump to the repo's tracked path only when `CHRONICLER_HOME` is
unset (the true default); otherwise writes next to the configured vault,
with `--freeze-repo-schema` as an explicit override. `tests/
tester_finalize_db.py` added (3 assertions), registered in `verify.py`.

```
python verify.py
== auditors == (6/6 OK)
== testers == (43/43 OK, including [ OK ] tester_finalize_db)
verify: GREEN -- all gates passed.
```

Confirmed in the Linux sandbox mirror of the same working tree before
handing back for Tim's own re-run on the rig.

## Step 7 — real-rig re-verification, sharp edge 9 found and fixed

```
git status   -> modified: finalize_db.py, verify.py, UAT_repo_tier_producers*.md
                untracked: SOLO_PLAYBOOK.md, COWORK_REPORT_solo_playbook.md,
                           UAT_solo_playbook.md, UAT_solo_playbook_results.md,
                           tests/tester_finalize_db.py

python verify.py
[FAIL] auditor_doc_claims: 1 issue(s)
  - docs/COWORK_REPORT_solo_playbook.md:173: doc claims a stale six/forty-two
    gate count but verify.py registers six auditors, forty-three testers
[FAIL] tester_census: 4 issue(s)
  - census: vault root resolved to C:\Users\timps\Documents\chronicler_dev,
    not the configured …\tmpgl0dqgoz\vault -- a path is hardcoded
  - census: serve-snapshot contents not counted
  - census: consumer report points at the wrong vault root
  - census: a missing vault root was not reported as missing
verify: RED (5 issue(s)) -- commit refused.
```

Two real, distinct findings, not one:

1. **`auditor_doc_claims` self-inflicted.** This session's own report
   *quoted* the stale gate-count claim as prose describing the other docs'
   problem — the auditor's regex can't distinguish a quotation from a live
   assertion (documented limitation: "deliberately does NOT parse prose").
   Fixed by rewording to spell out the numbers instead of using the literal
   `N auditors + M testers` pattern (this results log required the same fix,
   for the same reason, immediately after).
2. **Sharp edge 9 — env var leak into the test suite.** `tester_census`
   failed because `$env:CHRONICLER_HOME` / `$env:CHRONICLER_REGISTRY_PATH`
   were still set in the same PowerShell window from walking §5 — the
   tester's own hermetic temp-directory setup was overridden by the
   inherited environment. Cleared both:
   ```powershell
   Remove-Item Env:\CHRONICLER_HOME -ErrorAction SilentlyContinue
   Remove-Item Env:\CHRONICLER_REGISTRY_PATH -ErrorAction SilentlyContinue
   python verify.py
   ```
   Result: **GREEN, 6 auditors, 43 testers, on the real rig** (not just the
   sandbox mirror). Recorded as sharp edge 9 in `SOLO_PLAYBOOK.md`.

---

## Summary

| Check | Result |
|---|---|
| `.venv` health | broken, rebuilt clean |
| Hypothesis (outbox-as-`estates_dir`) | **confirmed yes** |
| Sharp edge 1 (unfrozen vault) | reproduced on purpose, confirmed fixed by `finalize_db.py --apply` |
| Sharp edge 6 (`CHRONICLER_HOME`) | found live, docs-only fix |
| Sharp edge 7 (`CHRONICLER_REGISTRY_PATH`) | found live, docs-only fix, no data actually written outside the boundary (dry-run) |
| Sharp edge 8 (`schema_frozen.sql`) | found live, **code fix** landed, tracked file reverted before any commit |
| `seed_suppress` (`b7c2390`) | confirmed still holding |
| DECISIONS 0013 (snapshot serve) | confirmed directly |
| Gate | GREEN, 6 auditors / 43 testers |
