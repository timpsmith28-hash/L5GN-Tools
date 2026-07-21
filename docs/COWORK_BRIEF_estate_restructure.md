# Cowork brief — estate restructure: one level, clean roots, fingerprinted

**Origin:** design thread, 2026-07-21, after the projects-reconciliation report
showed three generations of identity in one table and a rename nobody had
recorded. Structure decided by Tim in that thread. Authoritative rationale:
`docs/DECISIONS.md` 0012, `docs/COWORK_REPORT_projects_reconciliation.md`
Findings 1–3.

**This brief moves real files on Tim's machine.** It is not a code task. Read the
safety rules before anything else.

---

## Mount and safety

- **Mount `C:\Users\timps\Documents`**, not just the repo — the new `vendor\` and
  `scratch\` folders are siblings of `GitHub\`, and a session mounted on
  `GitHub\` alone cannot create them.
- **Nothing is deleted in this session. Ever.** Moves only. Deletion happens in a
  later pass, after Tim has confirmed the backups landed and the estate still
  scans.
- **Task 0 runs before any move.** It captures evidence that moving destroys.
- Every move is proposed as a table first and executed only after Tim says go.
  Batch the proposal; don't ask per folder.
- After each batch, `git -C <repo> status` on every moved repo. A repo whose
  `.git` did not travel is a stop-the-line event.

---

## The target structure

```
Documents\
  GitHub\                          <- Obsidian vault root; estate repos ONLY
    L5GN\                          <- config root, scope "l5gn"
      <every L5GN repo, one level deep>
    MCF\                           <- work rig only (already this shape)
  vendor\                          <- out of the vault, out of the scan
    all-MiniLM-L6-v2
    godot-demo-projects
    Godot_v4.6.3-stable_win64.exe  Godot_v4.6.3-stable_win64_console.exe
  scratch\
    test_folder
    L5GN-Crystal-Spire.zip
    PROJECTS_REVIEW.md             <- unless Task 4 promotes it
```

**Why one level.** `roots` in machine config are parents whose *direct children*
are projects; nesting is fixed at one. A program/project/repo folder tree would
need every project folder registered as a root and a config edit per new project.
More importantly, DECISIONS 0012 deliberately put the program→project→repo
hierarchy in the **registry** so the filesystem doesn't carry it. Encoding it in
folders too creates a second source of truth that can drift out of sync with the
first — the failure mode 0009 already rejected once.

**Why `vendor\` and `scratch\` leave `GitHub\` entirely.** The Obsidian vault is
rooted at `GitHub\` and that is deliberate — one vault, cross-repo search, no
`.obsidian` in every repo. Keeping it means non-code material must live outside
it: a 90MB sentence-transformer model and a demo-project tree are not notes and
are not projects.

---

## Task 0 — REPORT: fingerprint every repo BEFORE anything moves

**The highest-value task here, and it is destroyed by doing it later.**

For every directory in `Documents\GitHub\` (and on the work rig, every directory
under `MCF\` and `L5GN\`), capture:

| Field | How |
|---|---|
| `root_commit_sha` | `git -C <d> log --format=%H --reverse \| Select-Object -First 1` |
| `head_sha`, `branch` | `git -C <d> rev-parse HEAD` / `--abbrev-ref HEAD` |
| `commit_count` | `git -C <d> rev-list --count HEAD` |
| `first_commit_date`, `latest_date` | `git -C <d> log --format=%aI` first/last |
| `remotes` | `git -C <d> remote -v` |
| `is_git` | false for `vendor\`-bound folders — record them anyway |
| `size_mb`, `file_count` | for the disposition table |

**Deliver two things:** a readable table, and
`docs/investigation/2026-07-21_estate-fingerprint_<rig>_2-response.md` holding the
raw output (`docs/README.md` §4 naming).

### The question this settles

`smelt-gateway` (work rig) and `L5GN-Castle` (personal rig) share a first commit
timestamp to the second, a last commit timestamp to the second, and a commit
count — while `L5GN-Armory`, which the docs claim `smelt-gateway` was renamed
from, shares none of it and starts two weeks later
(`COWORK_REPORT_projects_reconciliation.md` Finding 2).

**Identical `root_commit_sha` means one repo under two names.** 117 threads — the
largest single cluster in the vault — are currently attributed to Citadel MicroIDE
on the strength of the rename claim. If the root SHAs match `L5GN-Castle`, they
belong to infrastructure instead, and the registry is wrong.

Report the answer plainly. Do not act on it — it is Tim's ruling and it belongs to
the reconciliation follow-up, not to this move.

### What to recommend afterwards

`git_summary` records branch, HEAD, depth and working-tree state, but not the root
commit SHA. A root SHA is **rename-proof identity**: it survives every rename,
fork and folder move that has confused this estate. Recommend adding it as a
`git_summary` field so the estate deposit carries it and no future rename orphans
a project. Do not build it here — note it for the assimilation list.

---

## Task 1 — REPORT: the disposition table

Classify every item in `Documents\GitHub\`. Nothing moves yet.

| Item | Class | Destination | Size | Evidence |
|---|---|---|---|---|

Classes: **estate repo** (git repo, belongs to a project) · **vendor**
(third-party code, models, binaries) · **scratch** (archives, test folders,
one-offs) · **unknown** (say so; do not guess).

Known going in, from the folder listing:

- **Estate repos → `GitHub\L5GN\`:** L5GN-Tools, L5GN-Castle, L5GN-Archive,
  L5GN-Crystal-Spire, L5GN-Armory, L5GN-Armory_v2, L5GN_Armory_v4,
  L5GN-Continuous-Ingestion-Daemon, l5gn-mesh-vertex-3_prod, L5GN-server-hub-iso,
  L5GN_Managed_Workspace.
- **Vendor → `Documents\vendor\`:** all-MiniLM-L6-v2, godot-demo-projects, both
  `Godot_v4.6.3-stable_win64` executables.
- **Scratch → `Documents\scratch\`:** test_folder, `L5GN-Crystal-Spire.zip`
  (24.6MB), `PROJECTS_REVIEW.md` (18KB).
- **Stays put:** `.obsidian` — the vault root is `GitHub\` by design.

Flag anything not in that list rather than filing it silently.

**`PROJECTS_REVIEW.md` needs a read, not a move.** 18KB of project review at the
estate root is very likely a source the reconciliation pass never saw. Read it,
say whether it contains project identities, aliases or groupings absent from
`config/project_registry.json`, and recommend promoting it into
`docs/investigation/` if so.

---

## Task 2 — BUILD: create the structure and move

Only after Tim approves the Task 1 table.

1. Create `GitHub\L5GN\`, `Documents\vendor\`, `Documents\scratch\`.
2. Move whole directories — `.git` and all. Never copy-then-delete a repo; never
   `git mv` across repo boundaries.
3. **Verify every moved repo:** `git -C <new path> status` returns cleanly and
   `rev-parse HEAD` matches the Task 0 fingerprint. A mismatch means the move was
   not clean — stop and report.
4. Update `config\local.json` on this rig:
   ```json
   "roots": [{"path": "C:/Users/timps/Documents/GitHub/L5GN", "scope": "l5gn"}]
   ```
5. `python run.py config` — the root must resolve without `(MISSING)`.

**Do not touch the work rig in this session.** It already has the right shape
(`MCF\` + `L5GN\`); restructuring both rigs at once means two sets of moves and
one set of eyes.

---

## Task 3 — REPORT then BUILD: backup to the infrastructure node

**Establish the topology before pushing anything.** The docs are ambiguous and
this must not be guessed at:

- DECISIONS 0005 relocated data to L5GN-Castle; 0006 corrected it, making the
  knight the live primary and "the L5GN-Castle copy a stale backup" — implying
  two boxes.
- The round-3 UAT ran on host `l5gn-castle-worker`, implying one.

Report which hosts exist, their hostnames, roles and reachable paths, and state
plainly whether the knight and the Castle are the same machine. Then, and only
then, propose what gets backed up where.

**Scope of the backup:** full repo copies including `.git`, for every repo Tim
marks dormant, plus `scratch\L5GN-Crystal-Spire.zip`. Verify by sha256 on both
ends — a backup that has not been verified has not been taken (the
`manifest_verified` doctrine, `PRODUCER_PLAYBOOK.md` §8).

**Nothing is deleted locally in this session,** however clean the backup looks.

---

## Task 4 — REPORT: drop the code out of L5GN-Castle, note what to assimilate

L5GN-Castle becomes the infrastructure node; the code in the `L5GN-Castle` repo
comes out. This task **reports**; it does not delete.

For every file or module in the repo, classify:

- **Assimilate into L5GN-Tools** — it does something the toolkit should own. Name
  the destination module and why. Anything touching the vault, deposits, backup
  or the registry is a candidate by default.
- **Infrastructure config** — belongs to the node as a machine, not as a repo
  (systemd units, paths, host config). Note where it should live instead.
- **Dead** — superseded, never finished, or duplicated in L5GN-Tools. Say which,
  and cite the thing that supersedes it.

**Keep a running ASSIMILATION list across every task in this brief**, not just
this one — anything noticed anywhere that the toolkit should absorb. Report it as
one table at the end. `root_commit_sha` in `git_summary` (Task 0) is already on
it; `SKIP_PROJECT_NAMES` is a second, since a clean root removes the reason it
exists.

---

## Task 5 — BUILD: prove the estate still scans

```powershell
python run.py build
python run.py deposit          # stage only, no --push
```

**Verify:** `data\estate.json` lists the same repos as before the move, each with
`scope: "l5gn"`, and the vendor and scratch material is **absent** — not skipped
by name, genuinely out of the scan path. Report the before/after project count and
explain any difference.

Do not push the deposit. The knight's registry is mid-reconciliation and a new
deposit lands in the middle of it.

---

## Suggested order

0 → 1 → 2 → 5 (prove the move) → 3 → 4.

Task 0 before everything. Task 5 immediately after the move, so a broken scan is
caught while the change is small and fresh. If the budget runs short, **0, 1 and 2
alone are a successful session** — the fingerprint census is worth the sitting on
its own.

---

## UAT — acceptance checks (Tim walks these)

- **Structure:** `Documents\GitHub\` contains `L5GN\`, `.obsidian` and nothing
  else. Obsidian opens and cross-repo search still works; the model folder and
  Godot binaries no longer appear in it.
- **Repos intact:** open two or three moved repos in the IDE — history is there,
  remotes resolve, nothing shows as a fresh clone.
- **Scan:** `run.py build` produces the same project list as before, all scope
  `l5gn`, with no vendor or scratch entries.
- **Fingerprint:** the Task 0 table names, for each repo, a root commit SHA — and
  Tim can answer the `smelt-gateway`/`L5GN-Castle` question from it.
- **Backups:** the sha256 of a backed-up repo bundle matches on both ends.

Mark each **ready to walk**, never "passed".

---

## Reporting

Report: tasks green vs pending; the Task 0 fingerprint table and the root-SHA
answer; the Task 1 disposition table with anything unexpected flagged; what moved
and what verified clean; the topology finding from Task 3; the L5GN-Castle
classification from Task 4; the **ASSIMILATION list**; and the UAT walk-list.

Write the report as `docs/COWORK_REPORT_estate_restructure.md` and the walk-sheet
as `docs/UAT_estate_restructure.md`. The results log from the walk must carry a
uat stamp or the gate refuses the commit (`docs/README.md` §3,
`auditor_uat_stamp`).

`python verify.py` must be GREEN before you report. Nothing commits — everything
staged for Tim's review.
