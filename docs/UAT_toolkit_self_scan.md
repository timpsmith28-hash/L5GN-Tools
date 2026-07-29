# UAT walk-sheet — the toolkit sees itself

**Brief:** `docs/COWORK_BRIEF_toolkit_self_scan.md`
**Report:** `docs/COWORK_REPORT_toolkit_self_scan.md`
**Built:** 2026-07-28, base commit `ac7710d`, working tree dirty.
**Nothing committed** — walk against the staged tree.
**Gate at build time:** `python verify.py` → **GREEN**, 6 auditors + 53 testers
(+1 `tester_project_root`; +2 from the local-deck slice registered alongside). Two `gate-frozen` markers were added to finished
docs so `auditor_doc_claims` stops red — see the report's closing section before
treating that as unrelated tidying.

**Where the numbers came from.** The Cowork session ran in a Linux sandbox
against the rig's real working tree and real `.git` via a mount, **not on
`LucasGoonPC`**. Two artefacts of that, both material to items below:

- the working copy carried a **5-file stand-in `.venv`** (the real one is
  **35,644 files**), so `file_census.total_files` will read ~**37,382** on the
  rig, not 1,743;
- `chronicler.db` was unreachable, so **nothing DB-side was run** — no
  `build_registry`, no `build_inventory`, no `xref_filenames`.

Every item below is **ready to walk**, none marked passed — that is Tim's call,
and the result belongs in `docs/UAT_toolkit_self_scan_results.md` with a commit
stamp, or `auditor_uat_stamp` refuses the commit.

**Walk order is load-bearing.** Section B must complete before section C. The
registry's auto-id collision is the *default* outcome, not a risk — deposit
first and you get two `l5gn-tools` entries.

---

### A — rig-runnable, before anything is deposited

- [x] **A1.** `python verify.py` → GREEN, and `tester_project_root` is in the
      list and OK.
- [x] **A2.** `python run.py config` on the gaming rig shows both roots:
      `…/GitHub/L5GN` (scope l5gn) and `…/GitHub/L5GN-Tools`
      (scope l5gn, `is_project`).
- [x] **A3.** `python run.py census` (or any `--all` sweep) lists **`L5GN-Tools`
      plus the same 8 projects as before** — 9 in total. Specifically **not**
      present: a project called `L5GN`, a project called
      `l5gn-mesh-vertex-3_prod`, and nothing called `docs`, `config` or
      `l5gntools`. If any of those appear, the root is mis-scoped — **stop**.
- [x] **A4.** `python run.py file_census --target L5GN-Tools` resolves by bare
      name (does not error, does not fall through to the cwd).
- [x] **A5.** The work rig and the knight are untouched — `config/local.json`
      entries for `10280L` and `l5gn-castle-worker` have no new root.

### B — the registry, BEFORE the deposit

- [x] **B1.** `python3 chronicler/pipeline/build_registry.py --report-aliases`
      runs and is **read**. Note whether any entry anywhere carries a
      `file_inventory` — the report claims **zero** across both registry copies
      on this rig, and that is either confirmed here or corrected here.
- [x] **B2.** The repo-tier diff in the report is applied to
      `config/project_registry.json`: `l5gn-tools` gains one repo
      `l5gn-tools-repo`, `canonical_name: "L5GN-Tools"`, with
      `seed_suppress: ["Tools"]` **on the repo, not the project**.
      *(Applied 2026-07-29 after the collision fired. `config/…` is
      `GROUPS_PATH`, the curated layer — **not**
      `L5GN/.intel_sync/project_registry.json`, which is the generator's
      output and does not yet exist on this rig. 62 ids, no duplicates.)*
- [x] **B3.** `l5gn-tools` still carries `low_signal_body: true` (it already
      did — confirm it survived the edit).

### C — the scan and deposit

- [x] **C1.** `python run.py build` completes; `report.html` renders;
      `data/estate.json` parses.
- [x] **C1a.** *(added on the walk — blocks C2.)* The estate-level scanners are
      cached under an unkeyed name and did **not** re-run when the project set
      went 8 → 9, so the git-summary page has no `L5GN-Tools` row and
      `estate_status.project_count` reads 8 beside 9 projects. Clear the two
      estate caches and rebuild:
      ```
      del data\estate_status.json data\duplicate_finder.json
      python run.py build
      ```
      Then confirm `estate_status.project_count` is **9** and `L5GN-Tools` has a
      row. (`--fresh` also works but rescans 2.8 GB of `L5GN_Armory_v4`.)
      Report §"The build defect found on the walk".
- [x] **C2.** `L5GN-Tools` appears as a project in the estate report with sane
      counts: `working_set` **246 files**, `commit_count` 76+, `scope: l5gn`.
      *(Per-project data confirmed present and correct in `data/estate.json`
      already — this item is now about the **git-summary page**, which needs
      C1a.)*
- [x] **C3.** `file_census.total_files` is in the **~37,000** range, not 1,743 —
      that is the real `.venv` being counted, and it is expected. `working_set`
      must still be ~244.
- [x] **C4.** `python run.py deposit` stages the bundle.
- [x] **C5.** `python3 chronicler/pipeline/build_registry.py --report-aliases`
      again → **exactly one** `l5gn-tools` entry, `provenance: manual`, its repo
      `l5gn-tools-repo` **present** with the real path and
      `first_seen=2026-07-10`. **No second entry, no `provenance: auto` twin.**
      *(2026-07-29: this aborted with `duplicate registry id 'l5gn-tools'`
      because B2 had not been applied — the predicted collision, caught loudly
      by `collect_link_targets`, nothing written. B2 is applied now; this
      item is the re-run that must come back clean.)*
- [x] **C6.** `Tools` is **not** a live alias anywhere in `--report-aliases`
      output; `L5GN-Tools` and `L5GN Tools` are.

### D — hygiene, the disclosure check

- [ ] **D1.** Search `data/estate.json` for `project_registry.json` and
      `local.json`. **Expected: both appear, in `env_scanner.config_files` and
      nowhere else.** This is the known scope defect, not a surprise — the item
      is to confirm it is *only* there and *only* the filename.
- [ ] **D2.** In the same file, confirm **no registry or config file
      *contents*** appear — no employer codename, no `push_target`, no
      hostname beyond the producer host. `env_scanner.secret_suspects` is `[]`
      and `credential_files` is `[]`.
- [ ] **D3.** `file_census.files[]` for L5GN-Tools contains **no gitignored
      path** (`config/local.json.example` is tracked and is allowed).
      Gitignored bulk appears only in `mass[]` with `reason: "ignored"`.
- [ ] **D4.** Rule on `outliers[]`, which **does** name `data/estate.json`,
      `report.html` and `chronicler/chronicler.db` by path. The report argues
      this is disclosure by design (naming the large ignored file is the point).
      Accept or raise it as a second defect.
- [ ] **D5.** Nothing under `.venv/`, `__pycache__/` or `l5gntools.egg-info/`
      appears in any per-file list.
- [ ] **D6.** Decide the `env_scanner` defect: 185 `data/` paths in
      `config_files`. Accept as a recorded finding for a later brief, or treat
      it as a blocker on depositing the toolkit at all.

### E — what it says about itself

- [ ] **E1.** `blast_radius` on L5GN-Tools: `tier: raw-write`, `hit_count`
      **~270**, `by_family` dominated by `db-writes`. Read the top-hit files —
      `relink.py`, `group_fallback.py`, `finalize_db.py`, `review/core.py`,
      `pull-report.ps1` — and confirm the dangerous operations are the ones
      flagged and **nothing important is missing**.
- [ ] **E2.** Every project in the estate reads `tier: raw-write` / rank 3 — the
      toolkit ties at the ceiling rather than topping the ladder, and separates
      only on `hit_count` (270 vs 29 next). Confirm and rule: is a saturated
      tier ladder acceptable, or its own brief?
- [ ] **E3.** The `git_state` dead branch: any file in `uncommitted_critical`
      that is tracked-and-modified still reads `"untracked"`. Reproduce on any
      dirty repo, then leave it — the fix is out of scope here.
- [ ] **E4.** `decisions_count` for L5GN-Tools is **28**, tiers
      `{accepted: 27, other: 1}`, `adr_count: 0`. Cross-check against
      `DECISIONS.md` (`## 0001` … `## 0028`).
- [ ] **E5.** `todo_adr_scanner.marker_count` is **28** and roughly **26 of them
      are reflexive** — the scanner's own regex, its testers' fixtures, and docs
      *about* markers. Confirm the shape, then rule whether that is a finding
      for a later brief.
- [ ] **E6.** `doc_census`: `doc_count` **102**, `authored` 101, `classified_pct`
      **87.1**. `docs/archive` (45) and `docs/investigation` (5) are **counted**.
      Ratify that decision or overturn it — overturning takes the toolkit to 52
      and out of `out_of_band`.
- [ ] **E7.** `out_of_band` with the toolkit in the population: median **27**,
      threshold **81**, flagged = CID 358, Armory_v4 288, Crystal-Spire 97,
      **L5GN-Tools 102** — 4 of 9. Rule on whether a flag firing on 44% of the
      estate still discriminates, and on the report's suggestion to score
      `authored_count` rather than raw `doc_count`.
- [ ] **E8.** `import_scanner.third_party` lists ~27 names of which only 6 are
      actually third-party; the rest are `chronicler/pipeline` siblings imported
      by bare name. Confirm `auditor_stdlib` is green in the same run — the wall
      is intact and the scanner is wrong.
- [ ] **E9.** `bloat_audit` clean, `env_scanner` reports no committed secret,
      `git_deep_history` folds `timpsmith28-hash` → `L5GN` (76 commits).

### F — the linking payoff (dry-run only)

- [ ] **F0.** *(added on the walk — precondition for F1/F2.)* The **generated**
      registry `…/GitHub/L5GN/.intel_sync/project_registry.json` **does not
      exist on this rig** — `--report-aliases` is a dry run, and the first real
      write aborted on C5's collision. Until `build_registry.py` completes a
      non-dry run, `build_inventory` and `xref_filenames` have nothing to read,
      **for any project**. Confirm the file now exists before F1.
- [ ] **F1.** `python3 chronicler/pipeline/build_inventory.py` gives
      `l5gn-tools` (or `l5gn-tools-repo`) a real `file_inventory`. **Record
      `file_count` and the distinct-basename count — expected 246 and ~237.**
      A mismatch means the scan scope moved; explain it before continuing.
- [ ] **F2.** `python3 chronicler/pipeline/xref_filenames.py` **dry-run**
      (the default — do not pass `--apply`). Record how many `filename_xref`
      rows land on `l5gn-tools`, and how many of those were impossible before
      (all of them: the count was structurally zero).
- [ ] **F3.** Spot-check that `verify.py`, `relink.py`, `DECISIONS.md` and
      `SOLO_PLAYBOOK.md` are among the matched basenames, and that `run.py`
      is **not** (it is in `GENERIC_BASENAMES`).
- [ ] **F4.** Confirm **no `--apply` ran and `relink.py` was not invoked.**
      `link_evidence` row count is unchanged from before the walk.
- [ ] **F5.** `duplicate_finder` estate-wide, now with 9 projects: record
      `identical_content_groups` / `shared_filename_groups` against the 25 / 39
      baseline. Expected to rise; a large jump between `chronicler/` and
      `L5GN-Castle` is information, not a fault.

---

### Stop conditions — check these are still true at the end

- [ ] **S1.** One `l5gn-tools` in the registry, not two.
- [ ] **S2.** No gitignored path in scan output **other than** the known
      `env_scanner` case (D1/D6) and the labelled `file_census` mass/outliers
      (D3/D4).
- [ ] **S3.** No unrelated sibling folder pulled into the estate (A3).
- [ ] **S4.** Nothing committed, nothing applied, no link changed.

Results log needs a `uat` stamp naming the commit. **Do not write a `gate=`
field.**
