# Cowork brief — repo-tier producers: the evidence pass must descend into repos

**Origin:** the golden apply, halted at a clean checkpoint (2026-07-26). The
fresh-build dry-check found only **10 of 58 targets** got a `file_inventory` —
exactly the entries whose project `canonical_name` equals a deposit folder name.
Every L5GN effort whose files live in a repo named differently from its concept
project got nothing: `crystal-spire` has no inventory and neither does its repo, so
`world_graph.json` is indexed **nowhere** and Crystal Spire, Citadel/Armory and
estate-infrastructure would produce **zero** filename evidence. This is the proper
**DECISIONS 0012 repo-tier implementation**, not a patch — and the golden apply
cannot proceed correctly until it lands.

**Safe checkpoint — do not disturb it.** The vault is a clean 725-thread slate,
`link_evidence` is empty, nothing applied, off-box backup verified
(`chronicler-20260726T111220Z.db`). This brief is a **rig code change**; the golden
apply resumes from it via commit → push → knight pull → re-run.

**Read first:** `chronicler/pipeline/build_inventory.py`, `build_activity.py`,
`xref_filenames.py`, `extract_path_mentions.py`; **the reference pattern** —
`chronicler/pipeline/relink.py::load_registry` (L177–212, already descends
program→project→repo) and `build_activity.py::load_curated_first_seen` (L309–329,
already walks `proj["repos"]`); `docs/DECISIONS.md` 0011–0012; the relink-scoring
report (`52193bd` added the `origin` column and the id-keyed scorer this must feed).

## Working rules

- **BUILD, then STOP.** Nothing commits; everything staged for Tim.
- `python verify.py` **GREEN** before you report; every change gets a **hermetic
  tester** (synthetic three-tier registry + synthetic deposit, no live vault).
- Read-only, stdlib-only. **Dry-run only** — this brief writes no evidence to any
  live vault; it makes the producers *capable* of the repo tier and proves it on
  fixtures.

---

## The defect, precisely

All four producers do `for entry in registry["projects"]` and resolve the deposit
by `entry["canonical_name"]`. Under 0012 a concept project (`crystal-spire`) carries
its files in **repos** (`L5GN-Crystal-Spire`) whose names are the deposit names. The
producers never read `entry["repos"]`, so:

- repo-tier `file_inventory`, git dates and evidence are all skipped;
- `xref`/`extract` key `link_evidence.project` by `canonical_name`, but the scorer
  (post-`52193bd`) keys candidates by **id** — so even the evidence that is written
  points at a key the scorer can't resolve (the standing **Finding-3** defect);
- `build_activity`'s fallback hands concept projects a **fabricated** `2026-07-17..27`
  window (the scan dates), which `time_plausibility` would use to **time-zero real
  threads**.

The fix is one shape applied four times: **iterate project *and* repo tiers, match
each folder-backed entry to its own deposit, and key evidence by id.**

---

## Task A — `build_inventory`: attach inventories to repos, not just projects

1. Iterate every **folder-backed** entry — each `project` **and** each of its
   `repos` — not just the project tier. Match each to its deposit by that entry's
   own `canonical_name` (repos are named for the deposits).
2. Attach `file_inventory` to the entry that owns the files: a repo-tier entry gets
   its repo's census. A concept project with no deposit of its own gets **no**
   synthetic inventory — its repos carry them, and the scorer rolls a repo hit up to
   its project via `collapse_lineage` (already built; no relink change here).
3. Keep the census-reading path (`52193bd`'s no-synthetic-`repo_folder_path` and
   single config-driven registry path) intact — this widens *what* is iterated, not
   *how* a deposit is read.

**Verify:** on a synthetic estate where repo `L5GN-Crystal-Spire` nests under concept
`crystal-spire`, the **repo** entry gains a `file_inventory` containing
`world_graph.json`; the concept entry has none and does not error.

**Tester:** three-tier registry + a deposit named for the repo → assert repo
inventory populated, concept inventory absent, no `<root>/<scope>/<canon>`
reconstruction attempted.

---

## Task B — `build_activity`: descend into repos, and kill the fabricated window

1. Same repo-tier descent: activity windows come from **real** deposits (repo tier)
   and the curated `first_seen` (already repo-aware at L309–329), never from the
   concept tier inventing one.
2. **Remove the mtime fallback that fabricates a window.** A tier with no real git
   history or deposit gets `activity = None` (relink already treats undated as a
   neutral 0.7, never a zero) — it must **not** receive the scan-date range, which
   is what produced the `2026-07-17..27` window that would annihilate real threads.
3. Curated `first_seen` (Crystal Spire, `d1a1b76`) still wins where set.

**Verify:** the concept projects carry **no** `2026-07-17..27` window; a repo with
real git dates carries its true window; Crystal Spire keeps its curated `first_seen`.

**Tester:** a project with no deposit → `activity None` (not a fabricated range); a
repo with dates → its window; curated `first_seen` overrides.

---

## Task C — `xref_filenames` (S4): iterate repos, key evidence by **id**, stamp `origin`

1. Build the basename index from **every** folder-backed entry's `file_inventory`
   (projects and repos), mapping `basename(lower) → set(entry_id)` — **ids, not
   canonical_names**.
2. Write `link_evidence.project` as the **id** (update the schema comment at L98 and
   the INSERT at L198). This is the **Finding-3 fix**, folded in: evidence the scorer
   keys on by id now matches the registry it resolves by id.
3. Populate the structured **`origin`** column (the basename) that `52193bd` reads
   for co-origin collapse — the producer is the natural place to stamp it.

**Verify:** on the fixture, `world_graph.json` produces a `filename_xref` row keyed
to the **`L5GN-Crystal-Spire` repo id**, `origin=world_graph.json`; the 1/n
multi-hit split and the generic-name stoplist behave as before.

**Tester:** unique basename → weight-1.0 row keyed by repo id with `origin` set;
shared basename → 1/n across the owning ids.

---

## Task D — `extract_path_mentions` (S5): iterate repos, key by **id**, stamp `origin`

1. Build the project-key map from projects **and** repos (canonical_name + aliases),
   so a path segment matching a repo name votes for that repo.
2. Key the written `link_evidence.project` by **id** (same Finding-3 fold-in), and
   stamp `origin` consistently with S4 so co-origin collapse dedupes an S4+S5 hit on
   the same basename.
3. Preserve the `path_scan_log` watermark and the left-of-match ignore rule
   unchanged.

**Tester:** a message naming `L5GN-Crystal-Spire\world_graph.json` yields a
path-mention row keyed by the repo id with `origin=world_graph.json`, and (with the
S4 row) collapses to a single origin in the scorer.

---

## Migration note — the fresh vault makes the re-key free

Because the golden run starts from an **empty `link_evidence`** (fresh build), there
are no legacy `canonical_name`-keyed rows to migrate — the first id-keyed pass writes
clean. State this in the report so nobody adds a re-key migration that isn't needed.
If this code ever runs against a non-fresh vault, the re-key is a separate step, not
this brief's.

---

## Suggested order

A → B (the inventory + activity that feed the join), then C → D (the evidence
producers that consume it). **A+C is the successful-session floor** — inventories on
repos and id-keyed filename evidence are what unblock the golden apply; B prevents a
correctness regression and D is the second evidence source. All rig-runnable, no
knight.

---

## UAT — acceptance checks (Tim walks these, resuming the golden apply)

The walk is the **re-run of apply_alignment Task 1** on the knight after
commit → push → knight `git pull`:

- **A:** `build_inventory` on the live deposit gives `L5GN-Crystal-Spire`,
  `L5GN_Armory_v4`, `smelt-gateway` (and the estate-infra repos) a `file_inventory`;
  the 10-of-58 becomes near-complete for folder-backed targets.
- **C:** `world_graph.json` resolves to the Crystal Spire repo id; `link_evidence` is
  **id-keyed** (spot-check `SELECT DISTINCT project FROM link_evidence` — all resolve
  in the registry, none are folder-name strings).
- **B:** no concept project carries a `2026-07-17..27` activity window; real threads
  are not time-zeroed.
- **Then continue Step 4:** S4/S5 `--apply` → relink **DRY-RUN** as the GO/NO-GO gate
  (read the table together — Crystal Spire / Citadel / estate-infra now align, no
  auto-link rests on a single origin) → `relink --apply` on GO only → the three verify
  queries → deposit/consume with the wall check → **uat stamp** on the results log.

Mark each **ready to walk**, never "passed".

---

## Reporting

Write the report as `docs/COWORK_REPORT_repo_tier_producers.md` and the walk-sheet as
`docs/UAT_repo_tier_producers.md`. Record: the before/after inventory coverage
(10/58 → ?), a sample of id-keyed evidence rows with `origin`, the removed
activity-fallback, and the **UAT walk-list** that resumes the golden apply. Nothing
commits — everything staged for Tim; then rig commit → push → knight pull → re-run
Task 1.
