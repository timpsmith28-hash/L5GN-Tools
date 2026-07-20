# Cowork report — build round 3: concurrency safety, three-tier registry, estate-driven build

**Date:** 2026-07-20 · **Pairs with:** `COWORK_BRIEF_build_round_3.md`
**Gate:** green — every auditor and every tester passes.
**Nothing committed.** All changes staged for Tim's review.

---

## Done vs pending

| Task | State | Note |
|---|---|---|
| A — WAL + busy_timeout | **done, green** | three DB paths were bypassing the shared helper; all routed through it now |
| B — serve reads a snapshot | **done, green** | `serve` cannot open the live vault; refuses rather than falling back |
| C — build_registry reads estate.json | **done, green** | **it ran successfully for the first time** |
| D — three-tier registry | **done, green** | id scheme resolved; roll-up implemented; dry-run below |
| G — debris cleanup + STATUS.md | **done** | stub deleted (no permission-blocked leftovers); STATUS.md rewritten |
| F — work-rig playbook | **done** | new `docs/PRODUCER_SETUP.md`, per-step verification |
| E — vocabulary guarded rebuild | **not built — blocked** | see "Task E: why it stopped" below; the blocker is worth reading |

Priority order was followed as written: A and B first, then C, then D, then the
cheap items, then E last.

---

## Task A — the finding: which paths opened the DB outside the helper

This was the requested finding, and the answer is three, all real:

| Path | What it did | Now |
|---|---|---|
| `chronicler/review/app.py::_connect` | own `sqlite3.connect`, set only `foreign_keys` | routed via `core.connect` → `dbsafe` |
| `l5gntools/backup.py::vacuum_into` | own `mode=ro` connect, no busy_timeout | `dbsafe.connect_readonly` |
| `l5gntools/scanners/vault_reader.py::_connect_ro` | own `mode=ro` connect, no busy_timeout | `dbsafe.connect_readonly` |

`project_trail.py` reuses `vault_reader._connect_ro`, so it was fixed by the same
change. Every pipeline stage already went through `db.get_connection` and needed
no edit — the gap was entirely outside the pipeline, which is the concrete extent
of the single-writer convention gap.

**One structural decision you should sanity-check.** The pragmas live in a new
`l5gntools/dbsafe.py`, not in `chronicler/pipeline/db.py` as the brief suggested.
Reason: `backup.py` and the vault scanners also open the vault, and the scanners
are held to the stdlib-only contract that permits importing `l5gntools` and
forbids importing `chronicler`. Putting the helper in `chronicler` would have
forced those three paths to duplicate the pragmas — the exact thing the task was
avoiding. `chronicler/pipeline/db.py` now re-exports from `dbsafe`, so
`from db import get_connection` is unchanged for every pipeline stage.

`.gitignore` did **not** cover the WAL sidecars — the `*.db-journal` rule does not
match `-wal`/`-shm`. Both added, plus the transient `serve-snapshot/` directory.

---

## Task B — serve now targets a snapshot

- **Snapshot path:** `<CHRONICLER_HOME>/serve-snapshot/chronicler-serve.db`,
  a sibling of the backup directory, resolved from config exactly like every
  other path. Deliberately *not* in the backup directory — a serving copy must
  never enter keep-last-N and age out a real off-box generation.
- **Refresh model:** overwritten in place on every `run.py serve` launch. It is
  scratch; it never accumulates.
- **Staleness surfaced twice:** printed to the console at launch, and written
  into a generated Datasette metadata file so the banner carries it in the UI.
  That second one matters because the usual reader is a phone on the tailnet,
  nowhere near the launching terminal.
- **Failure behaviour:** if the snapshot cannot be taken, `serve` **refuses to
  start**. It does not fall back to the live DB — falling back is precisely the
  behaviour 0013 forbids.
- **Review confirmed live:** `run.py review` still opens the live vault
  (`core.connect`), documented in the docstring. It has to see live state or it
  would re-serve threads already ruled.

---

## Task C — build_registry, first successful run ever

### The gap report (asked for first)

The deposited `estate.json` carried project **name** and git-derived **dates**
(`git_summary.first_commit_date` / `latest_date` / `commit_count`) — enough to
replace the folder walk's date logic. It did **not** carry two things the walk
had been deriving from the filesystem:

1. **A per-project path.** Now deposited (`projects[].path`).
2. **A scope tag.** This was the real gap. The estate recorded one
   `estate_root` and nothing about which configured root a project sat under —
   and the gaming rig's root is flat, so scope was *not derivable at all*.

**Resolution (the config-tag route, per C.3):** `roots` in machine config now
accepts `{"path": ..., "scope": "l5gn"|"mcf"}` alongside the old bare string.
Scope is declared on the producer's root and deposited as a fact; it is never
inferred from folder nesting. **No rig has to reorganise its folders.** I tagged
the gaming rig's root as `l5gn` in `config/local.json`, and updated
`machines.json` / `local.json.example` to document the shape. An untagged root
still scans; its projects land as scope `other` and are listed under DEPOSIT GAPS
rather than silently guessed — a wrong scope mis-files a project invisibly.

### What it can and cannot see today

**Can see (personal estate, from the local build output):** L5GN-Archive,
L5GN-Armory, L5GN-Armory_v2, L5GN-Castle, L5GN-Continuous-Ingestion-Daemon,
L5GN-Crystal-Spire, l5gn-mesh-vertex-3_prod, L5GN-server-hub-iso,
L5GN_Armory_v4, L5GN_Managed_Workspace. (`outputs`, `uploads` and `test_folder`
are skipped as scan artefacts, not projects.)

**Cannot see:** everything on the work rig — every MCF repo — because it has
never deposited. They are all present in the registry as link targets with
`present=false`; Task F unblocks this. Also `v1 proto` and `smelt-gateway`, which
are curated repos of Citadel MicroIDE that no current deposit contains.

Note the scope gaps in the run below are an artefact of `data/estate.json` being
a **pre-tagging** build. Re-run `run.py build` on the rig and they clear.

### `--report-aliases`, abridged

```
ESTATE SOURCES — what this registry could see
  estate=(local build output)  generated=2026-07-19T11:49:58+01:00  projects=11

THREE-TIER REGISTRY — program > project > repo (DECISIONS 0012)
id scheme: id  (every tier is a link target; project_link always holds an id)

PROGRAM  l5gn-os  (L5GN OS)
  PROJECT  citadel-microide      Citadel MicroIDE  (l5gn, manual)
      alias 'Citadel'  'CID'  'MicroIDE'
      REPO   citadel-v1-proto    v1 proto        [NOT IN ANY DEPOSIT]
      REPO   l5gn-armory         L5GN-Armory     [present, first_seen=2026-06-13]
      REPO   l5gn-armory-v2      L5GN-Armory_v2  [present, first_seen=2026-06-15]
      REPO   l5gn-armory-v4      L5GN_Armory_v4  [present, first_seen=2026-06-17]
      REPO   smelt-gateway       smelt-gateway   [NOT IN ANY DEPOSIT]
  PROJECT  crystal-spire         Crystal Spire  (l5gn, manual)
      alias 'Crystal Spire'  'DesktopsAndDungeons'  'DAndD'
      REPO   l5gn-crystal-spire  L5GN-Crystal-Spire  [present]
  PROJECT  l5gn-mesh-network     L5GN Mesh Network  (l5gn, manual)
      REPO   vertex-3            l5gn-mesh-vertex-3_prod  [present, first_seen=2026-06-04]
  PROJECT  chancellor / chronicler-gas / auditor-arbiter / universal-content-pipeline
  PROJECT  l5gn-os-program       L5GN OS (program-level)  [low_signal_body]

PROGRAM  wizforge-analytics  (WizForgeAnalytics)
  PROJECT  mcf-activity-statements, mcf-churn-level-indicator,
           mcf-data-access-layer, mcf-pricing-modelisation, mcf-sol-config,
           mcf-tss-to-assets, mcf-validation-automation      (all repo-less today)

STANDALONE  (no program)
  PROJECT  l5gn-tools-chronicler [low_signal_body]   (the 2026 Python Chronicler)
  PROJECT  l5gn-tools            [low_signal_body]
  PROJECT  learning-ai-and-computers [low_signal_body]
  PROJECT  sovereign             [low_signal_body]
  PROJECT  l5gn-archive, l5gn-castle, l5gn-continuous-ingestion-daemon,
           l5gn-server-hub-iso, l5gn-managed-workspace       (auto — unclassified)

UNMAPPED Claude project names: (none)
```

**Five auto projects want your attention.** `L5GN-Archive`, `L5GN-Castle`,
`L5GN-Continuous-Ingestion-Daemon`, `L5GN-server-hub-iso` and
`L5GN_Managed_Workspace` were deposited but are not in the curated registry, so
each became its own single-repo project with `provenance: auto`. Nothing is lost,
but they are unfiled. File them in `config/project_registry.json` when you know
where they belong.

---

## Task D — three tiers, one identifier

### The id-scheme decision (D.3)

**Chosen: the registry `id`, at every tier.** `threads.project_link` always holds
an id — never a canonical_name, never a folder name.

Why the id rather than canonical_name:

1. **It is stable under rename.** `L5GN-Armory` → `smelt-gateway` is a rename
   this estate has actually performed. Every canonical_name-keyed link would
   have been orphaned by it, silently.
2. **It requires no migration of human rulings.** The review endpoint — the top
   of relink's authority ladder — already wrote ids. Choosing canonical_name
   would have meant rewriting the most authoritative rows in the DB.
3. **Repo ids are link targets too**, so nesting `vertex-3` under
   `l5gn-mesh-network` cost nothing: any ruling already made against `vertex-3`
   still resolves.

relink was changed from keying on `canonical_name` to keying on id, and
`upsert_project` now writes `project_id = <id>, name = <canonical_name>` — the
same row shape the endpoint writes. **This is gated**: `tester_registry_tiers`
drives both writers at the same target and fails if they disagree.

**One migration you must do.** `l5gn-os` used to be a *project* id; it is now the
*program* id, and one id must mean exactly one thing. The old meaning survives as
`l5gn-os-program`. Any thread already linked to `l5gn-os` should be re-pointed:

```sql
UPDATE threads SET project_link='l5gn-os-program' WHERE project_link='l5gn-os';
```

Check the count before running it — under DECISIONS 0011 these early values are
being reset rather than trusted, so it may be zero and moot.

### Schema

Programs and projects live in `config/project_registry.json` (curated, manual
provenance, gitignored). The generator reads it as the grouping seed, attaches
estate facts to each repo, and writes the tiered registry. Curated data is never
rewritten — the standing manual-alias rule, extended to the hierarchy, so a
re-run cannot flatten it back out. Seeded from the ground-truth audit exactly as
the brief specified.

### `low_signal_body` (D.4) — set, and it demonstrably works

Set on: **Chronicler (2026)**, **Chronicler-GAS**, **L5GN Tools**,
**Auditor/Arbiter**, **L5GN OS (program-level)**, **Sovereign**,
**learning-ai-and-computers**, and on **both programs**.

The programs needed it and this was found by running the dry-run, not by
reasoning: a program name is by nature mentioned in passing inside conversations
about its children, so without the flag the umbrella **outscored the specific
project it contains**. A test thread whose body read *"I'll log this in
Chronicler and note it against L5GN OS later"* scored a 0.60 suggestion before
the flag and correctly became a **no-op** after it.

### The relink dry-run (D, requested)

Run against a synthetic five-thread vault, since the live vault is not on this
machine. What matters is the *shape* of the change.

```
Summary
  auto-link              1
  suggestion             3
  ambiguous              0
  no-op                  1

AUTO-LINKS
     0.960  smelt-gateway    t1  smelt-gateway refactor: plugin lifecycle
                             = name_alias:smelt-gateway@title(0.80), Smelt@title(0.80)

SUGGESTIONS
     0.960  t2  Armory v4 forge worker crash
            -> citadel-microide  [L5GN OS > Citadel MicroIDE]
               rolled up from rival repos of the same project: l5gn-armory-v4, l5gn-armory
     0.800  t3  Crystal Spire world_graph traversal
            -> l5gn-crystal-spire  [L5GN OS > Crystal Spire > L5GN-Crystal-Spire]
               absorbed same-lineage candidates: crystal-spire
     0.800  t4  ActivityStatements monthly reconciliation
            -> mcf-activity-statements  [WizForgeAnalytics > ActivityStatements]
```

**Two roll-up rules had to be added, and both came out of running it.** The tiers
initially made things *worse*, in ways worth recording:

1. **Self-ambiguity.** A title matching "Crystal Spire" matched both the project
   and its own repo (which inherits the alias). The flat scorer saw two
   near-identical candidates and declared AMBIGUOUS. Every project with a repo
   would have self-ambiguated and flooded the queue. Fixed by
   `collapse_lineage`: a candidate that is an ancestor or descendant of a
   stronger one folds into it; ties go to the more specific tier, because the
   specific incarnation can always be rolled up for display whereas the reverse
   loses information.
2. **Sibling ambiguity.** Two rival *repos of the same project* tied — "which
   Armory incarnation was this?" is unanswerable from a title, and queuing it
   asks you a question you cannot answer either. Now it rolls up to a suggestion
   at the shared parent (`citadel-microide`), which is the most specific thing
   the evidence actually supports. That is the practical payoff of the tier
   change: **ambiguities went to zero and became answerable suggestions.**

Both rules are gated in `tester_registry_tiers`, including a check that genuinely
unrelated rivals are still *not* collapsed.

The review endpoint offers all three tiers and returns a
`program > project > repo` breadcrumb per entry; a legacy flat registry still
loads read-only rather than taking the review surface down.

---

## Task E — why it stopped (read this one)

Not built. The brief's own precondition — "confirm S3 activity windows are
populated first" — is what stopped it, and the reason is more useful than the
task would have been.

**`build_activity.py` has the identical defect Task C just fixed in
`build_registry.py`.** It resolves each project as
`GITHUB_ROOT_FS / <L5GN|MCF> / canonical_name` and skips any project whose folder
is not on the local disk. That layout exists on neither machine, so on the knight
*every* project resolves as missing and no activity windows are produced.
`build_vocabulary.py` does the same thing, and additionally needs to read each
project's **source files** — which the consumer, by doctrine, must never reach
back to a producer's disk to get. Both also still read the flat registry shape.

So vocabulary is blocked behind: (a) build_activity refactored onto deposited
estate facts, and (b) a decision from you about where vocabulary harvesting is
allowed to run at all.

**Audit of the three guards, since it was asked for:**

- **Stopword list** — already present.
- **Cross-project commonality cutoff** — already present, TF-IDF-shaped, drops a
  term appearing in more than about a third of projects. The brief's premise
  that these were absent is not accurate for the current file.
- **S3 activity-window time filter** — **genuinely absent.** The evidence pass
  never looks at a thread's date; there is no time filter and no conservative
  threshold for undated threads. This is the one guard that must actually be
  built, and it cannot be built meaningfully until S3 windows exist.

**Recommendation.** The activity data is nearly free now: the deposits already
carry `first_commit_date` and `latest_date` per repo, and `build_registry` is
already attaching them as `first_seen` / `last_activity`. Refactoring
`build_activity.py` to read those instead of walking disk is a small, contained
change — and it would make S3 windows real on the knight for the first time.
Worth its own task before vocabulary is attempted.

---

## UAT walk-list — each item ready to walk

Marked **ready to walk**, not passed. Only you walking it passes it.

### A — WAL

```bash
# shell 1: hold a write open
sqlite3 ~/vault/chronicler.db
sqlite> PRAGMA journal_mode;      -- must print: wal
sqlite> BEGIN IMMEDIATE; INSERT INTO review_queue (type,thread_id,status,created_at)
        VALUES ('uat_probe','t','pending',datetime('now'));
# shell 2, while shell 1 holds it open:
sqlite3 ~/vault/chronicler.db "SELECT COUNT(*) FROM link_evidence;"
# then in shell 1: ROLLBACK;
```

**Passing:** shell 2 returns a count immediately, with no `database is locked`
and no `disk image is malformed`. `PRAGMA journal_mode` returns `wal`.
**Failing:** any error from the reader.

### B — snapshot serve

```bash
python3 run.py review          # rule one thread, note the time
python3 run.py serve
```

**Passing:** `serve` prints a `live vault` line and a *different* `snapshot`
line, plus "showing vault as of &lt;time&gt; — re-launch to refresh". The
Datasette index page carries the same note in its banner. A ruling made after the
snapshot time is absent from `serve` but present in the live DB — confirm with
`sqlite3 ~/vault/chronicler.db "SELECT project_link FROM threads WHERE thread_id='&lt;the one you ruled&gt;';"`.
That absence is correct behaviour, not a lost ruling.
**Also confirm it cannot write:** the argv line still shows `--immutable`, and the
path after it is the snapshot, not `chronicler.db`.

### C — estate-driven build_registry

```bash
python3 chronicler/pipeline/build_registry.py --report-aliases
```

**Passing:** no "configured root missing" error, an ESTATE SOURCES block naming
the deposits it read, and a project list you recognise as your actual repos.
**Look for:** the five auto/unclassified projects listed above, and the DEPOSIT
GAPS section. If scope gaps appear, run `run.py build` on the rig first — the
current `data/estate.json` predates root tagging.

### D — three tiers

```bash
python3 chronicler/pipeline/relink.py            # dry-run, the default
python3 run.py review                            # rule ~3 threads
sqlite3 ~/vault/chronicler.db \
  "SELECT project_link, COUNT(*) FROM threads WHERE project_link IS NOT NULL GROUP BY 1;"
```

**Passing:** the dry-run's SUGGESTIONS block shows a
`[L5GN OS > Citadel MicroIDE > smelt-gateway]` style breadcrumb on every line.
In the review UI each option carries its hierarchy. After ruling, the SQL returns
**only registry ids** — no `smelt-gateway`-style folder names mixed with
`crystal-spire`-style ids in the same column. Rulings persist across a restart.
**Do the `l5gn-os` → `l5gn-os-program` migration first** if that value is present.

### E — vocabulary

**Not ready to walk.** Blocked as described above.

### F — work rig

Follow `docs/PRODUCER_SETUP.md` start to finish on the work laptop. **Passing:**
you reach the end without hitting an undocumented gap or an unanswered question —
the doc's own UAT is whether it got you there. Then step 9 rebuilds the registry
and the MCF projects appear with real repo facts instead of `NOT IN ANY DEPOSIT`.

---

## Files changed

New: `l5gntools/dbsafe.py`, `docs/PRODUCER_SETUP.md`, and three testers
(`tester_dbsafe`, `tester_build_registry`, `tester_registry_tiers`).
Deleted: `chronicler/pipeline/_reconcile_gemini_verify.py`.
Modified: `run.py`, `verify.py`, `.gitignore`, `l5gntools/{config,report,viewer,backup}.py`,
`l5gntools/scanners/vault_reader.py`, `chronicler/pipeline/{db,build_registry,relink,STATUS.md}`,
`chronicler/review/{core,app}.py`, `config/{machines.json,local.json.example}`,
`docs/KNIGHT_PLAYBOOK.md`, `tests/{tester_config,tester_serve}.py`.

Gitignored and changed on disk (not staged, ship by scp as usual):
`config/local.json` (root now scope-tagged) and `config/project_registry.json`
(rewritten to the three-tier curated shape).

The gate is green across every auditor and every tester. Nothing is committed —
the diff is staged and waiting on your review.
