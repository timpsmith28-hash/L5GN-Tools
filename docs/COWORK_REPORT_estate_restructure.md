<!-- gate-frozen: commit=699b480 -->

# Cowork report — estate restructure

Pair: `docs/COWORK_BRIEF_estate_restructure.md`. Sessions 2026-07-24. **Nothing was
deleted. Nothing committed.** Moves were executed only after Tim's go, in one
batch, with per-repo verification against the Task 0 fingerprint.

`python verify.py` — **GREEN**, 6 auditors + **37** testers (frozen build-time
count; this brief changed no scanners or testers).

## Status: PARTIALLY EXECUTED — 5 of 9 estate repos moved; 4 locked; assets deferred to Tim

The `Documents` sub-folders (`GitHub`, `vendors`, `scratch`, `Backups`) were mounted
this session, so Tasks 0 and 1 ran in full and the approved safe batch of Task 2 was
executed. Four repos could not be moved and the large cross-mount assets are Tim's to
move (his instruction); details below.

---

## Task 0 — fingerprint (DONE, captured before any move)

`deploy/estate_fingerprint.py` captured every repo under `Documents\GitHub\` **before**
anything moved. Headline findings:

- **No two repos share a `root_commit_sha`** — there is no hidden rename-duplicate
  inside the personal estate.
- **L5GN-Castle** `root=832863248d5c`, 12 commits, remote **`l5gn-mesh-vertex-3_v0.git`**
  — cleanly the head of the Castle → mesh-vertex line, *not* the Citadel/Armory line.
- **L5GN-Armory** `root=cfca268d`, an entirely different root — confirming
  reconciliation Finding 2 that Armory shares none of Castle's identity.
- The `smelt-gateway` / `L5GN-Castle` question is **not answerable here**: smelt-gateway
  lives on the work rig (`10280L`), which is not mounted. Castle's root SHA
  (`832863248d5c`) is now recorded so a work-rig session can compare against it.

Raw output is reproducible any time with
`python deploy/estate_fingerprint.py "C:/Users/timps/Documents/GitHub" --json …`.

## Task 1 — disposition (DONE, verified against real folder contents)

| Item | Class | Destination | Note |
|---|---|---|---|
| L5GN-Armory, L5GN-Armory_v2, L5GN_Armory_v4, L5GN_Managed_Workspace | estate repo | `GitHub\L5GN\` | **moved ✓** (HEAD verified) |
| L5GN-Archive | estate repo (⚠ not git — file snapshot) | `GitHub\L5GN\` | **moved ✓** (no version control behind it) |
| L5GN-Castle, L5GN-Continuous-Ingestion-Daemon, L5GN-Crystal-Spire, l5gn-mesh-vertex-3_prod | estate repo | `GitHub\L5GN\` | **BLOCKED — folder locked (in use)**; the 4 active/running projects |
| L5GN-Tools | estate repo (the toolkit) | `GitHub\L5GN\` | **deliberately not moved** — the session runs from it; move last/manually |
| all-MiniLM-L6-v2 | vendor | `Documents\vendors\` | ⚠ **has a dependency** — CID loads it via `CITADEL_MINILM_PATH`; update that path before/after moving or CID breaks |
| godot-demo-projects, both `Godot_v4.6.3…` (.exe 172 MB) | vendor | `Documents\vendors\` | large cross-mount — **Tim to move** |
| L5GN-server-hub-iso | **vendor / infra** (per Tim's ruling; PROJECTS_REVIEW agrees) | `Documents\vendors\` | ⚠ **holds `l5gn.com.key.txt` + `l5gn.com.pem.txt` — a TLS private key + cert in plaintext, untracked.** Secure these before moving. Not moved this session. |
| test_folder, L5GN-Crystal-Spire.zip (25 MB) | scratch | `Documents\scratch\` | Tim to move |
| PROJECTS_REVIEW.md | promote | `L5GN-Tools\docs\investigation\` | **done ✓** → `2026-07-10_projects-review.md` |
| `.obsidian` | stays put | `GitHub\` | vault root by design |

**Disposition conflict resolved:** the brief listed `L5GN-server-hub-iso` as an estate
repo; its actual contents (ISO, Rufus, TLS material) and `PROJECTS_REVIEW.md` both say
infra asset. Tim ruled **vendor**. Flagged, not filed silently — and the exposed
credentials are the more urgent finding.

**`PROJECTS_REVIEW.md` read and promoted.** It is a 2026-07-10 LLM-generated first-pass
review of the estate and holds reconciliation-grade lineage absent from
`config/project_registry.json` — the Citadel line (Archive → Armory → Armory_v2 →
Armory_v4 → CID) and the Castle line (Castle, remote `l5gn-mesh-vertex-3_v0`, →
mesh-vertex-3_prod). Promoted into `docs/investigation/` as durable evidence for the
reconciliation follow-up rather than filed to scratch.

## Task 2 — the move (executed for the safe batch; verified)

Created `GitHub\L5GN\` and moved 5 repos into it as within-mount renames, so each
`.git` travelled intact. **Verified:** every moved git repo's `rev-parse HEAD` matches
its pre-move value —

| repo | HEAD (pre = post) |
|---|---|
| L5GN-Armory | `488df20…` ✓ |
| L5GN-Armory_v2 | `2b44083…` ✓ |
| L5GN_Armory_v4 | `0e21976…` ✓ |
| L5GN_Managed_Workspace | `4247770…` ✓ |
| L5GN-Archive | (no-git snapshot; folder present, intact) |

**Stop-the-line:** L5GN-Castle, L5GN-Continuous-Ingestion-Daemon, L5GN-Crystal-Spire and
l5gn-mesh-vertex-3_prod returned **Permission denied** on the folder rename while
remaining writable *inside* — the signature of an **open directory handle** (a running
process, IDE, Obsidian, container, or Explorer window holding the folder). These are
precisely the estate's active/running projects. Per the brief's discipline, a move that
does not go cleanly is a stop event: they were left exactly in place, intact, not forced.

## Config + Task 5 — HELD until the estate is whole

`config/local.json` roots for `LucasGoonPC` were **not** changed. Flipping the root from
`…/GitHub` to `…/GitHub/L5GN` now would drop the 4 still-in-`GitHub\` active repos from
every scan. The config update and the Task 5 "prove the estate still scans" build must
run **after all 9 estate repos are in `L5GN\`** — otherwise the proof would be run
against a half-moved estate. Held deliberately, not forgotten.

## Task 3 — backup topology (OPEN QUESTION, unchanged)

Still not answerable from inside the repo: DECISIONS 0005/0006 imply two boxes (knight +
Castle), round-3 UAT ran on one host (`l5gn-castle-worker`). Needs the real hostnames.
`Backups\` on this rig holds `L5GN-Crystal-Spire_*` snapshots and `chronicler_backups\`
— noted; no backup plan proposed until Tim states the topology.

## Task 4 — drop code out of L5GN-Castle (NOT DONE — Castle is locked)

Castle could not be moved and is one of the locked repos; its module-by-module
assimilate/infra/dead classification is deferred to a session where it is free.

---

## What Tim needs to run (exact commands)

**1. Free and move the 4 locked repos.** Close whatever holds them — the CID daemon, any
running mesh-vertex containers, and any editor / Obsidian / Explorer window open on
Castle or Crystal-Spire — then, in `Documents\GitHub\`:

```powershell
foreach ($r in 'L5GN-Castle','L5GN-Continuous-Ingestion-Daemon','L5GN-Crystal-Spire','l5gn-mesh-vertex-3_prod') {
  Move-Item ".\$r" ".\L5GN\$r"
  git -C ".\L5GN\$r" rev-parse HEAD   # compare to the fingerprint before trusting the move
}
```
(Ask me to retry these in a session once they're closed, and I'll verify each against the fingerprint.)

**2. Move the vendor assets to `Documents\vendors\`** (large, cross-drive):
```powershell
Move-Item ".\godot-demo-projects" "..\vendors\"
Move-Item ".\Godot_v4.6.3-stable_win64.exe","..\Godot_v4.6.3-stable_win64_console.exe" "..\vendors\"
```
**Do NOT move `all-MiniLM-L6-v2` until `CITADEL_MINILM_PATH` is updated** — CID loads
the model by that path and will break otherwise. Move it and fix the path together.

**3. `L5GN-server-hub-iso` → `vendors\`, but first secure the credentials.** It holds
`l5gn.com.key.txt` and `l5gn.com.pem.txt` (a private key + cert in plaintext). Move/rotate
those out of a plaintext `.txt` before relocating the folder.

**4. Scratch → `Documents\scratch\`:** `test_folder`, `L5GN-Crystal-Spire.zip`.

**5. Once all 9 estate repos are in `L5GN\`:** point the root at it and prove the scan —
```powershell
# config/local.json  LucasGoonPC.roots -> [{ "path": "C:/Users/timps/Documents/GitHub/L5GN", "scope": "l5gn" }]
python run.py config      # the L5GN root resolves without (MISSING)
python run.py build       # same project list as before, all scope l5gn, no vendor/scratch
python run.py deposit     # stage only, do NOT --push (registry is mid-reconciliation)
```

**6. Optional:** move `L5GN-Tools` itself into `L5GN\` last, from outside a running session.

---

## Assimilation list (carried forward)

- **`root_commit_sha` in `git_summary`** — noted, not built (brief's instruction);
  `deploy/estate_fingerprint.py` computes it standalone meanwhile.
- **`SKIP_PROJECT_NAMES`** — a clean root SHA removes its reason to exist.
- Data-sensitivity flag, `db-writes` DSN refinement, run/execution ledger (from the
  earlier briefs) remain open.
- **New:** the locked-folder move is a recurring estate hazard — a short "close these
  before restructuring" checklist (daemon, containers, Obsidian, editors) belongs with
  the restructure runbook.

## UAT

Walk-sheet: `docs/UAT_estate_restructure.md`. Consolidated list:
`docs/UAT_cowork_run_2026-07-24.md`. Nothing commits.
