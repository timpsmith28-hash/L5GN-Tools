# Cowork brief — projects reconciliation: one identity per project

**Origin:** design thread, 2026-07-21, after the round-3 UAT walk surfaced three
generations of identity living in one `projects` table. Authoritative rationale is
`docs/DECISIONS.md` (0010, 0011, 0012) and `docs/ARCHITECTURE.md`. Where this
brief and those docs disagree, the docs win.

**Read before starting:** DECISIONS 0010, 0011, 0012; `docs/COWORK_ROUND_3_REPORT.md`
Task D; `docs/UAT_round_3_results.md`. This brief assumes that context and does not
restate it.

## Working rules

- **BUILD, then STOP.** Nothing commits. Every change staged for Tim's review.
- `python verify.py` must be **GREEN** before you report.
- Live-vault work happens on the knight. If you cannot reach it, produce exact
  copy-paste runbooks and say so plainly — do not simulate a result and report it
  as executed.
- Pipeline scripts run as `.venv/bin/python`; they import `l5gntools` and fail
  outside the venv (`docs/PRODUCER_PLAYBOOK.md` §10).
- **Take a backup before any write to the live vault** (`run.py backup`,
  DECISIONS 0005/0006). Report the snapshot filename.

---

## The state of the world, measured

Three queries run against the live vault on 2026-07-21 (`chronicler-serve`
snapshot). This is evidence, not estimate.

**Row census — 25 rows in `projects`:**

| Generation | Rows | Written by |
|---|---|---|
| Claude project uuids (`source_system_id` set) | 9 | `normalize_claude.py:84` |
| Legacy canonical-name ids | 8 | `relink.upsert_project` **before** the D.3 id ruling |
| Current registry ids | 8 | `relink.upsert_project` / `review.core._upsert_project` **after** D.3 |

(The classifier used — `project_id GLOB '*[A-Z ]*'` — is a heuristic and
undercounts: `smelt-gateway`, `crystal-spire` and `v1 proto` are lowercase or
spaced and land in the wrong bucket. **The only sound test is membership in the
current registry's id set.** Task A fixes this.)

**Link census — 226 threads carry a `project_link`:**

| Bucket | Threads |
|---|---|
| unambiguously-legacy ids | 93 |
| `smelt-gateway` — an id valid under *both* schemes | 117 |
| current registry ids | 16 |
| Claude uuid rows | 0 — uuid rows are never link targets |

**Orphans: zero.** Every `project_link` resolves to a `projects` row, so the FK
has held throughout. Nothing is dangling; the problem is duplication, not breakage.

**The duplicate identity clusters, with their thread counts:**

| Real project | Rows competing for it |
|---|---|
| Chronicler | `Chronicler` (10) · `l5gn-tools-chronicler` (1) |
| Crystal Spire | `L5GN-Crystal-Spire` (6) · `DesktopsAndDungeons` (4) · `crystal-spire` (0) · uuid `L5GN Crystal Spire` (0) |
| L5GN OS | `l5gn-os` (10) · `L5GN OS` (2) — and `l5gn-os` is now the **program** id |
| Solution Configurator | `SolConfig` (6) · `MCF Solution Configurator` (4) · `mcf-solution-configurator` (0) · uuid `Solution Configurator` (0) |
| Citadel MicroIDE family | `smelt-gateway` (117) · `L5GN_Armory_v4` (51) · `v1 proto` (10) · four uuids (0) |

### The root cause

**DECISIONS 0011's reset was never executed.** It ruled in round 2 that existing
`project_link` values are noise from early auto-accept testing and should be reset
rather than trusted. The runbook was written; no knight access existed to run it.
Every relink and ruling since has layered onto a table the repo had already
decided not to trust. The three generations are that ruling's unpaid debt.

### The ruling for this brief

**Reset and rebuild. Do not migrate.**

Tim's call, and it matches 0011: the manual tagging done so far is small, the
linking logic is still improving, and a careful merge of 226 links across five
identity clusters would cost more than re-earning them — while producing a result
nobody can audit. A clean table under one scheme is worth more than preserved
noise.

**What survives the reset:** the Claude uuid rows (they are Claude's own project
entities, not registry entities, and hold no links), the vault's threads and
messages, the curated registry seed, and every alias Tim has authored.

**What does not:** every `project_link` / `project_confidence` value, and every
`projects` row that is not either a Claude uuid or a current registry id.

Draft a DECISIONS entry (**0017**) recording this — context, decision,
consequences, including the bad part (210 links discarded, re-earned by relink and
by Tim's rulings). Draft it in the report for Tim to ratify; do **not** append to
`DECISIONS.md` yourself. It is his log.

---

## Scope boundary — do NOT touch

- **Do not delete or rewrite any Claude uuid row.** They are the reconciliation
  axis for "Unmapped Claude project names", not duplicates.
- **Do not touch `threads`, `messages`, `link_evidence` or the vocabulary
  tables** beyond the two `project_link` / `project_confidence` columns.
- **Do not edit `docs/COWORK_ROUND_3_REPORT.md` or `docs/UAT_round_3_results.md`.**
  They are testimony (`docs/README.md` §2). Corrections go in your report.
- **Do not attempt Task E of round 3** (vocabulary). Still blocked on
  `build_activity.py`.

---

## Task A — REPORT: the definitive project list (do this first, it gates everything)

**This is the substantive ask.** Everything else is mechanical once this list is
right. Produce one reconciliation table that is the answer to "what projects
actually exist", built from every source that holds a piece of it:

1. **The curated seed** — `config/project_registry.json` (programs, projects,
   repo groupings, aliases, `low_signal_body`).
2. **The generated registry** — `<github_root>/L5GN/.intel_sync/project_registry.json`
   on the knight (29 entries at last run).
3. **Deposited estates** — `~/vault/estates/personal/estate.json` (12 projects,
   2026-07-17) and `~/vault/estates/work/estate.json` (17 projects, 2026-07-21).
   These are ground truth for *what exists on disk*, with git dates and paths.
4. **The `projects` table** — all 25 rows, including what each is linked from.
5. **Claude project uuids** — the 9 uuid rows, plus the "Unmapped Claude project
   names" output from `build_registry.py --report-aliases`.
6. **The threads themselves** — what names people actually *used*. Mine thread
   titles for names that match no registry entry; a project discussed under a
   name the registry has never heard of is a missing alias, and that is the
   single most valuable output of this task.

**Deliver, per project:**

| Column | Meaning |
|---|---|
| `id` | proposed registry id (the link target) |
| `tier` | program / project / repo |
| `parent` | program or project it sits under |
| `canonical_name` | the human name |
| `aliases` | every name seen in any source, including thread titles |
| `scope` | `l5gn` / `mcf` / `other` |
| `repos` | deposited repo folders that are incarnations of it |
| `present` | in a deposit today, yes/no — and which estate |
| `evidence` | which of the six sources above attest to it |
| `low_signal_body` | proposed flag, with the reason |

**Call out explicitly:**

- **Renames.** `L5GN-Armory` → `smelt-gateway` is one this estate has performed.
  Find the others; a rename that isn't recorded as an alias is a silently
  orphaned history.
- **The Armory generations.** `L5GN-Armory`, `_v2`, `_v4`, `smelt-gateway`,
  `v1 proto` — are these separate repos of one project, or separate projects?
  168 threads hang on the answer. Propose, with evidence; flag it for Tim's ruling.
- **`SolConfig` vs `MCF Solution Configurator` vs `mcf-solution-configurator`** —
  one project or two? The `mcf-*` prefix split the round-3 run already flagged.
- **The five unfiled auto projects** — `L5GN-Archive`, `L5GN-Castle`,
  `L5GN-Continuous-Ingestion-Daemon`, `L5GN-server-hub-iso`,
  `L5GN_Managed_Workspace`. Propose a home for each or argue they are standalone.
- **Anything in a deposit that no registry entry claims**, and anything the
  registry claims that no deposit contains (`NOT IN ANY DEPOSIT` today includes
  `v1 proto` and `smelt-gateway` — curated repos of Citadel MicroIDE).

Output the table **and** an updated `config/project_registry.json` implementing
it. That file is gitignored and shipped by scp — write it, list its diff in the
report, and state the sha256 so Tim can confirm what landed on the knight.

---

## Task B — REPORT: the exact reset, counted before it runs

Before writing anything, produce the numbers the reset will change:

```sql
-- what is about to be cleared, by target
SELECT project_link, project_confidence, COUNT(*) FROM threads
WHERE project_link IS NOT NULL GROUP BY 1, 2 ORDER BY 3 DESC;

-- rows that are neither a Claude uuid nor a current registry id
SELECT project_id, name, repo_folder_path FROM projects
WHERE source_system_id IS NULL AND project_id NOT IN (<registry ids from Task A>);
```

State the exact `UPDATE` / `DELETE` statements, the row count each affects, and —
importantly — **whether any row carries `project_confidence='manual'`**. Those are
Tim's own rulings. He has said losing them is acceptable; report the count anyway
so he is agreeing to a number rather than to a hand-wave.

Order matters: clear `threads.project_link` **before** deleting `projects` rows,
or the FK will refuse.

---

## Task C — BUILD: execute the reset

Only after Task A's list is agreed and Task B's counts are reported.

1. `run.py backup` — report the snapshot filename. No backup, no reset.
2. Clear `project_link` and `project_confidence` on every thread.
3. Delete `projects` rows that are neither Claude uuids nor current registry ids.
4. Rebuild the registry from the Task A seed:
   `.venv/bin/python chronicler/pipeline/build_registry.py --report-aliases`,
   then without the flag to write.
5. Re-run `relink.py` **dry-run** and report the decision table.

**Stop before `--apply`.** The dry-run table is Tim's GO/NO-GO — that is the whole
reason dry-run is the default, and it was skipped on the last pass.

---

## Task D — BUILD: make the drift structurally impossible

The table accumulated three generations because **nothing ever checked that a
`projects` row belongs to the current id scheme.** Both writers upsert by
`project_id` and neither can see a row written under an older convention.

Build a pre-flight invariant check in the relink/apply path: **refuse to apply
when `projects` contains a row that is neither a Claude uuid nor a current
registry id**, naming the offenders. Loud failure, not a warning — the whole class
of bug here is a silent accumulation.

Cover it with a hermetic tester (`tests/tester_*.py`, registered in `verify.py`)
driving a synthetic DB: a clean table passes, a table with one foreign row fails
and names it.

**Design note.** This cannot be a `verify.py` auditor — auditors are hermetic and
the vault is machine state, not repo state. It belongs at the point of write.

---

## Task E — BUILD: id reuse must be impossible

`l5gn-os` was a project id and became the program id, with the old meaning moved
to `l5gn-os-program`. One id must mean exactly one thing, forever — and this
collision is precisely why 10 threads are now linked to a program tier.

Add a check in `build_registry.py`: **fail the build if any id in the generated
registry has changed tier or canonical meaning since the previous generated
registry**, unless an explicit `--allow-id-remap` flag is passed. Compare against
the previous `.intel_sync/project_registry.json`. Report the check firing on the
`l5gn-os` case as proof it works.

---

## Task F — REPORT: does `collapse_lineage` actually fire on the knight?

Round 3 reported ambiguities driven to zero by lineage collapse and parent
roll-up. The round-3 UAT then observed `L5GN-Crystal-Spire` vs
`l5gn-crystal-spire-repo` presented as **rival candidates** in the review UI.

Those cannot both be true. Determine which:

- Does the knight's generated registry set the parent links `collapse_lineage`
  needs, or does regeneration drop them?
- Was the UI showing registry candidates, or `projects` rows?
- Did the dry-run's synthetic five-thread vault exercise a lineage shape the real
  registry doesn't have?

Report the answer with the query or code path that proves it. If lineage collapse
is not firing on real data, say so plainly — a rule proven only against a
synthetic fixture is a rule that has not been proven.

---

## Task G — REPORT: the registry path derivation

`build_registry.REGISTRY_PATH` is derived as
`CHRONICLER_ROOT.parent.parent / "L5GN" / ".intel_sync" / "project_registry.json"`.
On the knight `CHRONICLER_HOME=/home/l5gn/vault`, so the generated registry lands
in `/home/l5gn/L5GN/.intel_sync/` — a Github-root-shaped path on a machine with no
Github root. It works by accident of arithmetic.

Report: where should it live on a consumer, is `CHRONICLER_REGISTRY_PATH` the
right knob (`review/core.resolve_registry_path` already prefers it), and do relink
and the review endpoint provably read the **same file** today? Propose a fix;
build it only if it is small and obviously right.

---

## Suggested order

A (gates everything) → B → F and G (reports, cheap, inform C) → C → D → E.

If the budget runs short, **A and B alone are a successful session.** The list is
the deliverable; the reset is mechanical once the list is right.

---

## UAT — acceptance checks (Tim walks these)

`verify.py` green proves the code works; it cannot prove the identities are right.
State per item the exact command and what passing looks like.

- **A (the list):** Tim reads the reconciliation table and recognises his actual
  projects, their groupings and their aliases. Every rename he can remember is
  present as an alias. Nothing he owns is missing; nothing appears twice.
- **C (the reset):** after the reset, `SELECT COUNT(*) FROM threads WHERE
  project_link IS NOT NULL` returns 0, and `projects` contains only Claude uuids
  plus current registry ids. The generation census query returns two buckets, not
  three.
- **C (relink dry-run):** the decision table is readable and Tim can answer
  "would I trust this?" — auto-links look right, suggestions are answerable,
  ambiguities are few and genuinely ambiguous.
- **D:** deliberately insert a foreign row into a scratch DB; the apply path
  refuses and names it.
- **E:** the id-remap check fires on the `l5gn-os` case and is silenced only by
  the explicit flag.

Mark each **ready to walk**, never "passed" — only Tim walking it passes it.

---

## Reporting

Before the session ends, report: tasks green vs pending; the Task A
reconciliation table in full; the Task B counts including the `manual` ruling
count; the backup filename; the relink dry-run decision table; the drafted
DECISIONS 0017 for ratification; the answers to F and G; and the **UAT walk-list**
(how to run each item, what passing looks like).

Write the walk-sheet as `docs/UAT_projects_reconciliation.md` and the report as
`docs/COWORK_REPORT_projects_reconciliation.md`. The results log Tim produces from
the walk must carry a uat stamp (`docs/README.md` §3) or the gate will refuse the
commit — the auditor is `auditor_uat_stamp` and it is not optional.

Nothing commits. Everything staged, for Tim's review.
