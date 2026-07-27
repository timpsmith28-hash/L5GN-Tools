# Cowork report — repo-tier producers: the evidence pass now descends into repos

**Pair:** `docs/COWORK_BRIEF_repo_tier_producers.md`. Session 2026-07-27, gaming rig.
**Gate:** `python verify.py` → **6 auditors, 42 testers** (was 40; +2:
`tester_xref_filenames`, `tester_extract_path_mentions` — neither producer had a
hermetic tester before this round). **Every tester passes, including the two
existing ones extended with repo-tier assertions.** One auditor is red —
`auditor_doc_claims`, on 11 lines across 8 **pre-existing, untouched** docs from
earlier rounds (file_census, intent_evidence, relink_scoring, the 2026-07-24
cowork run) whose frozen "Gate at build time" counts (6 auditors and 40
testers, correctly quoted at the time each was written)
no longer match the live count now that this round legitimately added two
testers. See "The one red auditor" below — not fixed here, on purpose.
**Nothing committed.** Everything staged for Tim's review.

Read-only, stdlib-only throughout. No `--apply`, no live vault touched — every
claim below is against synthetic fixtures (a three-tier registry + a synthetic
deposit + a throwaway sqlite DB built from the real `schema.sql`), per the
brief's working rules.

---

## Done vs pending

| Task | State | Note |
|---|---|---|
| A — `build_inventory` repo-tier descent | **done** | inventory attaches to whichever tier owns the files; no synthetic inventory on a repo-less concept project |
| B — `build_activity` repo-tier descent + kill fabricated window | **done** | the `Path("") == cwd` bug is gone; a path-less entry now yields `activity: None`, never a scan-date window |
| C — `xref_filenames` id-keyed, repo-aware | **done** | basename index built from projects **and** repos; `link_evidence.project` writes the registry id |
| D — `extract_path_mentions` id-keyed, repo-aware | **done** | project-key map built from projects **and** repos; id-keyed; origin now derived from the path's trailing segment so it collapses with an S4 hit on the same file |
| Migration note | **confirmed, no action needed** | fresh vault, empty `link_evidence` — first pass writes id-keyed clean (see below) |

A+B+C+D are all landed — "one shape applied four times" is now one shared
generator (`db.iter_folder_backed_entries`) used by all four producers, rather
than four independent walks that could drift apart again.

---

## The defect, and the one-shape fix

All four producers did `for entry in registry["projects"]` and resolved a
project's own deposit by its own `canonical_name`. Under DECISIONS 0012 a
concept project (`crystal-spire`) can carry no deposit of its own at all — its
files live in a repo named differently (`L5GN-Crystal-Spire`). The fix, applied
identically in all four places via one new helper:

```python
# chronicler/pipeline/db.py
def iter_folder_backed_entries(registry: dict):
    """Yield every folder-backed registry entry: each project, then each of
    its repos, in that order."""
    for project in registry.get("projects", []):
        yield project
        for repo in project.get("repos") or []:
            yield repo
```

`build_inventory`, `build_activity`, `xref_filenames.load_basename_index`, and
`extract_path_mentions.load_project_keys` all iterate through this one
generator now, instead of four separately-hand-rolled loops. A flat (no
`repos` key) registry entry yields itself only — the existing flat-registry
testers pass unchanged, no special case needed.

---

## Task A — `build_inventory`: inventory attaches to whichever tier owns the files

Each entry (project **and** repo) is matched to a deposit by its **own**
`canonical_name`. A concept project with no deposit of its own and a non-empty
`repos` list is now reported in a new `container` bucket ("concept project —
files carried by its repos") rather than either inventing a synthetic inventory
or cluttering the missing-list — a project genuinely missing (no repos, no
deposit) still reports MISSING as before.

**Hermetic proof** (`tests/tester_build_inventory.py::_check_repo_tier`): a
synthetic deposit named `L5GN-Crystal-Spire` carrying `world_graph.json`, under
a concept project `crystal-spire` with that repo as its only child —

- the **repo** entry gains `file_inventory` with `world_graph.json` in
  `basename_set()`, sourced `"deposit"` (no local-disk reconstruction attempted);
- the **concept** entry gets `file_inventory: None` — not a fabricated block;
- no exception, on either tier.

All four pre-existing `tester_build_inventory` assertions (deposit-driven
harvest, skip-if-unchanged, truncation, `--dry-run`, no-deposits-is-loud) still
pass unmodified.

---

## Task B — `build_activity`: the fabricated-window bug, found and killed

**The actual defect**, once traced: `resolve_fs(entry)` returned
`Path(entry.get("path") or "")`. `Path("")` is `Path(".")` — the **current
working directory**, wherever this producer's process happens to run — and
`Path(".").is_dir()` is `True`. So a concept project with no `path` key (the
normal shape for one under DECISIONS 0012) fell through to the local-disk
fallback, which then walked **whatever files were sitting in cwd** and reported
their mtimes as the project's "activity window." That is exactly the
`2026-07-17..27` fabricated window the brief's origin section describes — it is
today's scan/build dates, not any project's real history, and `time_plausibility`
would have used it to hard-zero real threads for every concept project this
round exists to fix.

**The fix:** `resolve_fs` now returns `None` for a path-less entry, and `run()`
checks `fs_path is None or not fs_path.is_dir()` before ever touching the
local-disk fallback. Combined with the repo-tier descent (same shape as Task A),
a project with no deposit and no path gets **no activity block at all** —
`None`, which `relink`'s `time_plausibility` already treats as neutral (1.0),
never zero.

**Hermetic proof** (`tests/tester_build_activity.py::_check_repo_tier`):

- a concept project (repo owns the deposit) → **no** activity block, not a
  fabricated window;
- a genuinely orphaned project (no repos, no path, no deposit) → **no** activity
  block either — the fix isn't just "container projects are special-cased," the
  underlying `Path("")` bug is gone regardless of why an entry has no path;
- the repo → its real window (`first_commit: 2026-02-01`, from its own deposit);
- a curated `first_seen` keyed by the **repo id** still reaches it through
  `apply_first_seen` at repo tier (`load_curated_first_seen`'s project→repo
  cascade was already correct, per the brief; this confirms `run()` actually
  applies what it returns).

All four pre-existing `tester_build_activity` assertions (burst clustering,
thin-deposit fallback, mtime precision, truncation flag, skip-if-unchanged,
`--dry-run`, no-deposits-is-loud) still pass unmodified, and
`tester_first_seen` (the unit-level cascade/widen logic) is unaffected.

---

## Task C — `xref_filenames`: id-keyed, repo-aware basename index

`load_basename_index` now walks `iter_folder_backed_entries` and keys the index
by `entry["id"]`, not `canonical_name` — the Finding-3 fix. `origin` was already
being stamped (`52193bd`); no change needed there.

**Sample evidence rows** (`tests/tester_xref_filenames.py`, fresh hermetic run):

| thread | project (written) | signal | detail | weight | origin |
|---|---|---|---|---|---|
| t1 | `l5gn-crystal-spire` | filename_xref | world_graph.json | 1.0 | `worldgraph` |
| t2 | `smelt-gateway` | filename_xref | shared_util.py | 0.5 | `sharedutil` |
| t2 | `l5gn-armory-v4` | filename_xref | shared_util.py | 0.5 | `sharedutil` |

`project` resolves in the registry by id in every row (`l5gn-crystal-spire` ≠
its canonical_name `L5GN-Crystal-Spire`, which is deliberately what the tester
checks — a regression to canonical_name-keying would be caught immediately).
A generic basename (`README.md`) produces no row. Re-running `--apply` is
idempotent (row count unchanged); `--dry-run` (the default) writes nothing.

---

## Task D — `extract_path_mentions`: id-keyed, repo-aware, origin collapses with S4

`load_project_keys` now walks `iter_folder_backed_entries` too, same id-keying.
The more subtle half of Task D: **what `origin` gets stamped.** Before, it was
derived from `detail` — the matched alias/canonical_name (e.g.
`"L5GN-Crystal-Spire"`), which normalises to `l5gncrystalspire`. But a path like
`...\L5GN-Crystal-Spire\world_graph.json` is evidence *about a specific file*,
and an S4 `filename_xref` hit on that same attached file stamps origin
`worldgraph`. Those two origins would never collapse.

The fix: origin is now derived from the **path's own trailing segment**
(`origin_token()`), not from the matched alias. `detail` is unchanged (still the
human-readable alias, for the report). Verified end-to-end
(`tests/tester_extract_path_mentions.py`) by running **both** producers against
one fixture DB and comparing the written rows directly:

| producer | project (id) | signal | detail | origin |
|---|---|---|---|---|
| S4 `xref_filenames` | `l5gn-crystal-spire` | filename_xref | world_graph.json | `worldgraph` |
| S5 `extract_path_mentions` | `l5gn-crystal-spire` | path_mention | L5GN-Crystal-Spire | `worldgraph` |

Same id, same origin — `relink.combine()`'s co-origin collapse now treats these
as one piece of evidence, not two independently-corroborating ones, exactly the
brief's acceptance case. A noise-only system path
(`C:\Python314\Lib\site-packages\...`) still produces nothing; `--dry-run`
writes nothing.

---

## Migration note — confirmed, no action needed

The golden apply resumes from an **empty `link_evidence`** (fresh build), so
there are no legacy canonical_name-keyed rows to migrate — the first id-keyed
pass writes clean. Nothing in this round adds or requires a re-key migration.

---

## The one red auditor — surfaced, not silenced

`auditor_doc_claims` scans every `docs/*.md` for the compound pattern
`"N auditors + M testers"` and fails when a doc's claim doesn't match the live
`verify.py` registration. Adding the two required testers moved the live count
from 40 testers to 42, which now disagrees with 11 "Gate at build time" lines
frozen in **8 pre-existing docs this brief never touched**:
`COWORK_REPORT_file_census.md`, `COWORK_REPORT_intent_evidence.md`,
`COWORK_REPORT_relink_scoring.md` (×2), `UAT_cowork_run_2026-07-24.md`,
`UAT_cowork_run_2026-07-24_results.md`, `UAT_file_census.md` (×2),
`UAT_intent_evidence.md` (×2), `UAT_relink_scoring.md`.

Those counts were **true when each doc was written** (confirmed: before this
round, the live count actually was 40). Editing them to say "42" would be
exactly the kind of laundered-history the `docs-archivist` skill and
`auditor_uat_stamp`'s own design guard against. The correct fix is archiving
those finished brief/report pairs into `docs/archive/` (non-recursive glob
exempts it by design) — but `docs-archivist` requires Tim to ratify each pair
individually (confirm the UAT was actually walked), which is not this session's
call to make, and "archive a live doc to make the gate green" is explicitly the
skill's own anti-pattern. **Surfaced for Tim's separate ratification, not
archived here.** Every other auditor and all 42 testers are green.

---

## Suggested order followed

A → B (inventory + activity feed the join) → C → D (the evidence producers that
consume it), as the brief recommended.

---

## Files touched

`chronicler/pipeline/{db,build_inventory,build_activity,xref_filenames,extract_path_mentions}.py`,
`tests/tester_build_inventory.py`, `tests/tester_build_activity.py` (extended),
`tests/tester_xref_filenames.py`, `tests/tester_extract_path_mentions.py` (new),
`verify.py` (+2 registrations). No schema change, no live-DB write, no commit.
