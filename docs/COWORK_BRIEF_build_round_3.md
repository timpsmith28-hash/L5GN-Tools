# Cowork brief — build round 3: concurrency safety, three-tier registry, estate-driven build

**Origin:** design thread, 2026-07-20. Read `docs/DECISIONS.md` **0012–0016** and
`docs/project_linking_skillset_spec.md` before starting — this brief assumes both.

**Working rule (unchanged): BUILD, then STOP before committing.** Each task to green
(`python verify.py`), staged, uncommitted, reported. Do not `git commit`. Tim reviews
the diff and commits.

**Priority order is deliberate and dependency-driven.** Tasks A and B are small,
pure-safety hardening that make every later task safe to run against the live DB — do
them first. Then the registry work (C, D), which is the session's real payload. E
(vocabulary) and F (work-rig) are stretch / Tim-run. **If time runs out, stop after
the task you're on and report done-vs-pending clearly.**

**DO NOT TOUCH:** `render_md.py` / `sync_back()` / `render_log` base (sync-back removal
is gated on the write endpoint being trusted — not this round). Do not run any task
from `docs/cowork_tasks_cleanup_and_qol.md` as-written — that doc predates the current
DECISIONS log and is largely superseded (its B2 runner exists; its parked "web UI" is
the review endpoint; its sync-back assumptions violate 0008). Its only live content is
folded into Task G below.

---

## Task A — WAL mode + busy_timeout (DECISIONS 0014) — do first

Make concurrent DB access safe by construction. This is the smallest change with the
widest safety benefit, so it goes first — every later task then runs against a DB that
can't throw torn-read / false-malformed errors.

1. Find the single shared connection helper (`chronicler/pipeline/db.py`,
   `get_connection`). Set on every connection, at open time:
   - `PRAGMA journal_mode=WAL;`
   - `PRAGMA busy_timeout=5000;`
2. Every code path that opens the DB must go through this helper so the pragmas can't
   be forgotten on one path — audit `review/`, `backup.py`, `viewer.py`/serve, and the
   pipeline stages. Report any path that opens SQLite *without* the helper; route it
   through the helper rather than duplicating the pragmas.
3. WAL creates `-wal`/`-shm` sidecar files. Confirm `.gitignore` already excludes them
   (the `chronicler/**/*.db-journal` rule may not cover `-wal`/`-shm` — check and add
   if missing).
4. Tester: assert a connection opened via the helper reports `journal_mode=wal`.

**Report:** which paths were opening the DB outside the helper (this is itself the
finding — it's the concrete extent of the single-writer convention gap).

---

## Task B — serve reads a snapshot, not the live DB (DECISIONS 0013)

The false-`malformed` incident's structural fix. `run.py serve` must never point
Datasette at the live `chronicler.db` under `--immutable`.

1. On `run.py serve` launch: take a fresh `VACUUM INTO` snapshot (reuse `backup.py`'s
   snapshot logic — do not duplicate it) to a well-known transient path, and point
   Datasette `--immutable` at *that snapshot*, not the live file.
2. The snapshot is read-only-consumer scratch; it can live in a `serve-snapshot/`
   temp location, overwritten each launch. Don't pollute the real backup rotation with
   these.
3. Surface the staleness honestly: `serve` should print (and ideally the UI banner
   should note) "showing vault as of <snapshot time> — re-launch to refresh." This is
   the one-line note 0013 asks for, so review-endpoint writes not yet in the snapshot
   aren't mistaken for lost rulings.
4. Confirm the review endpoint (`run.py review`) still reads/writes the **live** DB —
   only the read-only *serve* surface moves to a snapshot. (Review must see live state
   to not re-serve already-ruled items.)

**Report:** confirm serve now targets a snapshot; note the snapshot path and refresh
model.

---

## Task C — Refactor build_registry to consume estate.json, not scan folders (DECISIONS 0012 groundwork)

**This is the unblock.** `build_registry.py` currently scans `GITHUB_ROOT/L5GN/` and
`GITHUB_ROOT/MCF/` folders — a layout that exists on **neither** machine (knight has
`~/L5GN` but no `~/MCF`; gaming rig is flat). It has never run successfully anywhere.
Per the mesh doctrine (producers scan their own estate and deposit facts; the consumer
reads deposited facts, never reaches back to a producer's disk), it must read the
**deposited `estate.json`** instead of walking folders.

1. **Report first:** read how `estate.json` is structured (what the estate scanner
   deposits per project — name, path, git status, scope if any). Confirm it carries,
   or can carry, enough to replace `discover_folders()`: project name, a scope/origin
   tag, and git-derived dates (for the S3 activity signal). Report the gap if any.
2. Replace `discover_folders()`'s filesystem walk with a reader over the deposited
   estate snapshots (personal + work) on the knight. Keep everything else
   build_registry already does well — alias seeding, Claude-project folding, the
   manual-alias-preserving merge, loud failure, atomic write.
3. **Scope tag comes from the estate deposit, not folder nesting** (this is the
   config-tag resolution — no folder reorg needed on the gaming rig, per the ground-
   truth audit). Each project's `scope` (l5gn/mcf) is whichever configured root it was
   scanned under on its producer.
4. Keep it runnable where the estates actually are. If estates are only complete once
   the work rig deposits (Task F), build_registry can run now against personal-only and
   re-run when work lands — report which projects it can and can't see today.

**Report:** the `--report-aliases` output once it runs against estate data — this is
the seed list the three-tier registry (Task D) gets built from.

---

## Task D — Three-tier schema: program → project → repo (DECISIONS 0012)

**Depends on C producing a runnable seed.** Evolve the registry from flat scope→project
to program → project → repo.

1. **Schema:** add a `program` tier above projects, and a `repos`/`incarnations` list
   under a project (the physical folders that are versions of one project). Preserve
   all existing fields rel45 reads (`canonical_name`, `aliases`, `alias_sources`,
   `scope`, `activity`, `low_signal_body`). Seed structure from Task C; layer the
   program/project grouping as **manual-provenance** data (so the generator's re-runs
   preserve it, per build_registry's existing manual-alias rule).
2. **Seed content from the ground-truth audit + census** (both in the design thread;
   Tim can paste the registry JSON drafts `project_registry.json` /
   `project_registry_v1.json` which carry his curated aliases, notes, and the MCF
   project splits). Known mappings to encode:
   - Program **L5GN OS** ⊃ projects: Citadel MicroIDE (⊃ repos `v1 proto`,
     `L5GN_Armory_v4`, `L5GN-Armory`, `L5GN-Armory_v2`, `smelt-gateway`), Crystal Spire
     (repo `L5GN-Crystal-Spire`, alias DesktopsAndDungeons/DAndD), UCP, Mesh
     (`l5gn-mesh-vertex-3_prod`), Chancellor, Chronicler-GAS, Auditor/Arbiter.
   - Program **WizForgeAnalytics** ⊃ MCF projects: ActivityStatements,
     ChurnLevelIndicator, PricingModelisation, DataAccessLayer, TSsToAssets,
     ValidationAutomation, plus Solution Configurator (SolConfig).
   - Standalone/other: `l5gn-tools-chronicler` (the 2026 Python Chronicler — NOT the
     GAS one), `learning-ai-and-computers` (broad bucket).
3. **Resolve the id-vs-canonical_name divergence** (round-2 flag): relink writes repo
   canonical_names (`smelt-gateway`), the review endpoint writes registry ids
   (`crystal-spire`). Pick ONE identifier scheme across all tiers and make relink + the
   endpoint agree. Report the choice; recommend the more stable of the two (likely the
   id).
4. Set `low_signal_body: true` on the meta-tool entries that get name-dropped inside
   conversations about *other* projects — at minimum **Chronicler**, **L5GN OS**,
   **Sovereign**-family aliases. This is the built-but-unset false-positive guard
   (relink already honours the flag; it demotes body-only alias hits 0.60→0.15).
5. Update `relink.py` and the review endpoint to understand the tiers: a repo-level
   evidence match rolls up to its project/program for display; rulings can be made at
   the project tier; the hierarchy shows for context (estate/account still shown,
   still agnostic per 0010).

**Report:** the new registry structure, the id-scheme decision, and a relink `--dry-run`
against it so Tim can see how the three-tier rollup changes the decision table before
any `--apply`.

---

## Task E — Vocabulary (S2) guarded rebuild (DECISIONS 0015) — stretch

Only if C/D are solid and time remains. Revive `build_vocabulary.py` per spec §S2 **with
the three guards it originally lacked**: stopword list, cross-project commonality cutoff
(TF-IDF-shaped — drop terms appearing across many projects), and the S3 activity-window
time filter (conservative higher threshold for the 14.4% undated threads).

1. Confirm S3 activity windows are populated first (vocabulary's era-discriminator
   depends on them) — report if `build_activity.py` output is present/stale.
2. Dry-run only this round. Spot-check: vocabulary-*safe* projects (Crystal Spire's
   `world_graph`, tui-specific terms) gain signal; vocabulary-*dangerous* ones (shared
   design vocabulary) are suppressed by the commonality cutoff. **Do not `--apply`
   vocabulary to the live DB this round** — dry-run report for Tim's GO/NO-GO first.

---

## Task F — Work-rig deploy prep (Tim runs the deploy; Cowork readies the playbook)

Exercises the wall for the first time and unblocks the MCF projects in Task C/D.
**Cowork does NOT deploy** (no work-rig access) — it makes the deploy runnable and
correct, Tim executes it as deliberate practice.

1. Update `docs/KNIGHT_PLAYBOOK.md` (or a new `PRODUCER_SETUP.md`) with the exact
   work-rig producer steps: clone, `.venv`, `pip install -e .`, add the work-rig
   hostname to `local.json` (role producer, estate work, roots pointing at the `MCF/`
   and `L5GN/` folders that exist there, push_target), first `deposit --push`.
2. Note the git-hook auto-apply option (post-merge → verify) as a *documented future*
   step with the supply-chain caveat from the design thread (a hook turns `pull` into
   `execute` — fine on a repo only Tim controls). Do not implement the hook this round.
3. Report the exact command sequence for Tim to run, in order, with the one-line
   verification after each step.

---

## Task G — Debris cleanup (folded from the superseded cleanup doc)

The only still-live content from `cowork_tasks_cleanup_and_qol.md`. Attempt deletion;
list any permission-blocked ones for Tim to remove from Windows.
- `pipeline/_reconcile_gemini_verify.py` (12-byte stub, already flagged for deletion)
- any `_test.db` / `_test.db-journal` / `_lock_test.txt` / `_orphaned_*.bak` leftovers
- **Do NOT touch** `pipeline/_presync_suggested_close.py` (kept deliberately).
Also: refresh `pipeline/STATUS.md` if it still claims build items are "not started"
that are now done — but keep it a short handoff note, and point its "authoritative
reference" line at `docs/ARCHITECTURE.md` (per DECISIONS 0016), not the missing v2 doc.

---

## UAT — acceptance tests (the human walks these; the report answers them)

`verify.py` green proves the code *works*; it cannot prove the code *does what was
asked*. These are the end-user acceptance checks — "when I do X, the thing I wanted
actually happens" — that Tim walks before a task counts as done. The report should
state, per item, the exact command/URL to run and what a passing result looks like, so
walking them is mechanical.

- **A (WAL):** after the change, open the live DB from two shells at once (one holding
  a write, one reading) and confirm the reader doesn't error or see a torn state — the
  false-malformed class is gone. `PRAGMA journal_mode;` returns `wal`.
- **B (snapshot serve):** run `run.py review`, make a ruling, then `run.py serve` —
  confirm serve shows the vault *as of its snapshot* and the banner states the snapshot
  time (so a not-yet-in-snapshot ruling reads as "refresh to see," not lost). Confirm
  serve cannot be made to write (still `--immutable`, now on a copy).
- **C (estate-driven build_registry):** `build_registry.py --report-aliases` runs
  without the "configured root missing" error and lists real projects from the
  deposited estate(s). Tim recognises the project list as his actual repos.
- **D (three-tier):** in the review UI, a thread can be ruled to a project, and the
  program→project→repo hierarchy is visible for context. `project_link` values written
  by a ruling and by relink use the *same* identifier scheme (no `smelt-gateway`
  vs `crystal-spire` split in one column). Tim rules ~3 threads and they persist.
- **E (vocabulary dry-run):** the dry-run report lets Tim make a GO/NO-GO by showing
  which projects gain/lose signal — he can answer "would I trust this?" from it.
- **F (work-rig):** Tim can follow the playbook steps start-to-finish without hitting
  an undocumented gap or an unanswered question (the deploy is his UAT of the doc).

The report marks each UAT item as **ready to walk** (built, here's how) — not "passed"
(only Tim walking it passes it). A completed pair is archivable only once Tim has
walked the UAT.

## Reporting

Before the session ends, report: tasks green vs pending, the build_registry
`--report-aliases` output (Task C), the three-tier relink dry-run table (Task D), the
id-scheme decision (D.3), any DB path found opening outside the shared helper (A), and
the **UAT walk-list** (each item: how to run it, what passing looks like). Nothing
commits — all staged, for Tim's review.
