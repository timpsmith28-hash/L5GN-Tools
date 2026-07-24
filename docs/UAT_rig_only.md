# UAT — what can be proved on the gaming rig alone

Everything here runs on `LucasGoonPC` with **no knight, no work rig, no push**.
Pulled from the existing walk-sheets plus five checks that came out of reading
the 13:48 report payload. Items are cited to their sheet rather than restated —
walk them there, tick them here.

Knight-dependent items are listed at the bottom so nothing gets lost; do not
attempt them yet.

---

## 1. Straight from `UAT_file_census.md` — rig-runnable as written

| Item        | What it proves                                                       | Time   |
| ----------- | -------------------------------------------------------------------- | ------ |
| **A**       | the scanner tells the truth about a folder you can check in Explorer | 5 min  |
| **B**       | the scan does not touch `.git` — the read-only contract holds        | 5 min  |
| **D1 / D2** | the tree browses by clicking; at-risk is the first thing you see     | 5 min  |
| **F**       | the deposit size claim, measured rather than asserted                | 2 min  |
| **G / G2**  | the non-git projects, and the Castle finding                         | 15 min |
| **H1–H6**   | the refined at-risk panel, including that grouping never truncates   | 10 min |
| **C1–C4**   | `run.py census` on the **producer** side only                        | 5 min  |
| **J**       | the round-2 gate                                                     | 1 min  |

**G2b is the one with a decision attached** — `L5GN-Castle/data/` holds 3,599 of
the estate's 3,673 at-risk files and 45% of `estate.json`. Gitignore, commit, or
leave pending the reorg. G2c has the measured effect of gitignoring it, so the
choice is priced.

## 2. From `UAT_projects_reconciliation.md` — the reading half

Item **A** is a review, not an execution: read the reconciliation table against
`config/project_registry.json`. No vault needed. Worth doing now because §3 below
gives it new evidence.

Items B, C, F, G all touch the live vault. Not now.

---

## 3. Five checks from the report payload — new, quick, rig-only

### 3.1 Is `L5GN-Crystal-Spire` a git repo or not?

Two scanners disagree in the 13:48 payload: `file_census` reported
`is_git: true` with a root-level `.git` mass row (135 files, 20.6MB), while
`git_summary` and `estate_status` reported `is_git: false` — 7 repos vs 9.
`UAT_file_census.md` §G now asserts the *no-git* reading for four projects.

```powershell
cd C:\Users\timps\Documents\GitHub\L5GN-Crystal-Spire
Test-Path .git
Get-Item .git | Select-Object Name, Mode, Length     # dir or file?
git rev-parse --is-inside-work-tree
git log --oneline -1
```

- [ ] **3.1a** The four commands agree with each other.
- [ ] **3.1b** They agree with what the report says.

**Why it matters:** if it *is* a repo, the registry is missing its git dates —
`first_seen` / `last_activity` for a project with 6 linked threads — and the
census and `git_summary` disagree about the same folder, which is a defect in
one of them. Run the same two lines in `test_folder`, the other disputed one.

### 3.2 Does the at-risk count match its own list?

The payload had `L5GN-Armory` reporting `at_risk: 17` with 14 rows and
`truncated: false`.

- [ ] **3.2** In the current report, Armory's at-risk count equals the number of
      rows you can expand. If it doesn't, the counter and the list disagree and
      the panel under-reports.

### 3.3 Read the Duplicates tab as identity evidence

Not a defect check — a **reconciliation** check, and the highest-value thing on
this page. Cross-referencing identical-content and shared-filename groups gives
content-based clusters:

| Pair | Identical | Shared names |
|---|---|---|
| L5GN-Castle ↔ L5GN_Managed_Workspace | 8 | 5 |
| L5GN-Castle ↔ l5gn-mesh-vertex-3_prod | 2 | 15 |
| L5GN-Armory_v2 ↔ L5GN_Armory_v4 | 4 | 12 |
| **L5GN-Archive ↔ L5GN_Armory_v4** | **4** | **11** |
| L5GN-Archive ↔ L5GN-Armory | 3 | 6 |
| CID-Daemon ↔ L5GN_Armory_v4 | 2 | 9 |

- [ ] **3.3a** `L5GN-Archive` shares `citadel_archetypes.json`, `forge_engine.py`
      and `forge_campaign_generator.py` with the Armory line. **Does that make it
      Citadel material rather than infrastructure?** The reconciliation report
      proposed `l5gn-archive-repo` under `l5gn-estate-infrastructure` on the
      strength of its *name*; the content says otherwise.
- [ ] **3.3b** `handover_schema.py` appears in Castle, Managed_Workspace and
      vertex-3. Is that a shared spine — and does vertex-3 belong with the
      infrastructure group rather than under `l5gn-mesh-network`?
- [ ] **3.3c** `test_folder` shares `citadel_archetypes.json` and
      `extract_deep_git_history.py` with Armory and Castle. It is **not** junk;
      confirm before the restructure sweeps it into `scratch\`.

### 3.4 Read the untracked design docs — they are alias evidence

Untracked, unversioned, and never seen by any reconciliation pass:

- `L5GN-Crystal-Spire\NAME_GAZETTEER_SCAN.md` (20KB)
- `L5GN-Crystal-Spire\DRIVE_ID_SCAN.md` (22KB)
- `L5GN-Crystal-Spire\AUDIT_DOCTRINE.md`, `THREAD_HANDOFF_v3.md`
- `Documents\GitHub\PROJECTS_REVIEW.md` (18KB)

- [ ] **3.4** Skim each. A *name gazetteer* is, on the face of it, exactly the
      alias source the registry has been missing. If any of them holds project
      names or groupings, they belong in `docs/investigation/` before the next
      reconciliation pass rather than after it.

### 3.5 Is `l5gn.com.key.txt` a live secret?

`L5GN-server-hub-iso\l5gn.com.key.txt`, 1,732 bytes, untracked, sitting beside an
Ubuntu ISO in a folder with no git.

- [ ] **3.5** Open it. If it is a live private key or an API token, it wants
      rotating and moving regardless of anything else on this page.

---

## Knight / work-rig items — parked, not forgotten

- `UAT_file_census.md` **C5–C12** (consumer census) and **E** (`pull-report.ps1`,
  never executed — walk it expecting to find something).
- `UAT_round_3.md` **A, B, C, D** — all four need the live vault.
- `UAT_projects_reconciliation.md` **B, C, F, G** — the reset and the registry
  path, both live-vault.
- `UAT_round_3.md` **F** — the producer playbook on the work laptop.

---

## Recording the result

If you write these up, the results log needs a uat stamp or the gate refuses the
commit (`docs/README.md` §3):

```
<!-- uat: commit=<sha> dirty=<bool> host=LucasGoonPC walked=2026-07-21 gate=<Na/Mt> -->
```
