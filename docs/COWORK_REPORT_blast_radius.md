# Cowork report — blast-radius scanner + the uncommitted-critical alarm

Pair: `docs/COWORK_BRIEF_blast_radius.md`. Session 2026-07-24, on top of `23b5ffa`,
after the scanner bug-fix pair (whose `Scope` filter this inherits) and the
governance pair (whose tracked-status join it crosses in Task B). **BUILD, then
STOP — nothing committed; everything staged for Tim's review.**

`python verify.py` — **GREEN**, 6 auditors + **37** testers at this build (two
testers added this session; frozen build-time count).

| Task | State | What landed |
|---|---|---|
| A — `blast_radius` scanner | **green** | data-driven signal families, env + guard classification, per-project tier ranked above size |
| B — the uncommitted-critical alarm | **green** | write-capability ∩ untracked/dirty, surfaced at the very top of the report |
| C — run against the real estate | **partial** | run here on L5GN-Tools + an r141-shaped fixture; the work-rig run is Tim's (rig not mounted) |

---

## Task A — the report now ranks by consequence, not byte size

`l5gntools/scanners/blast_radius.py` (registered, `ESTATE_LEVEL = False`,
`SAFETY = SAFE`) statically flags code that can mutate a system **outside its own
repo**, matching on text and citing file + line. It never executes anything and
never stores a raw source line.

**Signal families are data-driven** (`SIGNALS`), so the list extends without a code
change: `salesforce-dml`, `shell-os`, `cloud-infra`, `db-writes`, `http-writes`
(writes) and `salesforce-read`, `cloud-read` (reads). Each hit is classified:

- **target environment** from a `--target-org` alias — `prod` / `sandbox` /
  `unknown`. Per the brief's fail-safe rule, **unknown is ranked as prod** (a false
  prod costs a glance; a missed prod costs an incident), while still *reported* as
  unknown so the operator sees the ambiguity.
- **guarded or raw** — presence of a gate marker (typed-phrase, four-eyes,
  `def gate`, `import gates`, …) in the same file. Presence only; the scanner never
  judges whether the gate is *sufficient* — that is Tim's ruling. Biased toward
  **raw** (a write is raw unless a gate is clearly present).

Per-project **tier** — `none / read-only / guarded-write / raw-write /
raw-write-prod` — is the loudest hit, and the report ranks projects by it in a new
**Blast Radius** tab, above the file-size view. A guarded write ranks *below* a
bare write, exactly as the r141 typed-gate is lower risk than a bare
`sf data import`.

**Guardrail, structural.** A hit stores the signal family, a cleaned signal name
(e.g. `sf data import upsert update delete`), the path, the line, the env
*classification* and guarded/raw — **never** the raw line, the alias, or a
credential. Naming `upload_r141.py` a raw-write-prod is the finding; the body is
never in the output, so the exposure cannot be recreated from `docs/`.

### Proof on an r141-shaped fixture

A synthetic clone of the r141 situation — `upload_r141.py` running
`sf data import bulk --target-org myMainAlias`, a `gates.py` typed-phrase module,
a read-only `query.py` — with the upload script **left untracked**:

- Project tier: **`raw-write-prod`**.
- `upload_r141.py` → **UNCOMMITTED-CRITICAL**, `git_state: untracked`.
- The stored hit is `sf data import …` (the family verdict); `myMainAlias` never
  appears in the output.

`tester_blast_radius` asserts the four canonical tiers, that an unknown alias ranks
prod, and that a `sf data import` string inside a **gitignored chat JSON is not
flagged** (scope inherited from the bug-fix brief).

## Task B — the uncommitted-critical alarm

The single highest-value alert: **write-capability ∩ untracked**. Inside
`blast_radius.scan`, every file carrying a `guarded-write`-or-worse hit is crossed
with git working-tree state (`git status --porcelain`, `--no-optional-locks`). A
file that is **untracked or uncommitted-dirty** (or in a non-git repo, where
*everything* is uncommitted) becomes **UNCOMMITTED-CRITICAL**, naming the file, its
tier and its git state.

The report surfaces these in a red banner **at the very top, above at-risk and
above size** — "write-capable code with no commit behind it: the exact code that
can mutate the outside world, with no provenance in version history." This is the
r141 case in one line a reviewer reads first, and the sharpest expression of the
drift thesis: *built, consequential, and not in the record.*

`tester_blast_uncommitted` asserts a tracked, committed guarded-write is **not**
critical while an untracked raw-write **is**, and that it sorts first.

## Task C — what lights up on the real estate

The work rig (host `10280L`, where SolConfig / r141 live) is not mounted this
session, so the SolConfig run is Tim's to walk. Two runs were done here:

**The r141 fixture** surfaced exactly as designed (above).

**L5GN-Tools itself** scans as tier **`raw-write`**, 218 hits:

| Family | Hits | Note |
|---|---:|---|
| `db-writes` | 153 | **dominant false positive** — almost all bare `.commit()` and SQL against the *local* Chronicler SQLite vault, not an external system |
| `shell-os` | 47 | `subprocess`/`scp`/`ssh` in `deploy/` and backup paths — expected, mostly legitimate |
| `salesforce-dml` | 13 | in the vendored chronicler pipeline; several sit near gate markers → `guarded-write` |
| `cloud-infra` | 1 | one `terraform/kubectl`-shaped marker |
| reads | 4 | `requests.get` / `sf data query` — correctly `read-only` |

**False-positive assessment (the tuning the brief asked for).** The cry-wolf risk
is real and concentrated: **`.commit()` and generic SQL against a local DB drive
~70% of hits.** A scanner that flags every local-SQLite commit as blast radius gets
muted, defeating the point. Recommended tuning, for Tim's graduated-rigor call
(not made unilaterally, since it changes what the flagship flags):

- Gate `db-writes` on a **non-local DSN** — require a host/URL near the write, so a
  local `sqlite3.connect("vault.db")` + `.commit()` does not trip it.
- Consider dropping bare `.commit()` from the default family and keeping the
  explicit DML verbs (`INSERT`/`UPDATE`/`DELETE`/`DROP`).

These are left as recommendations because the marker list is deliberately
data-driven and muting a signal is a defensibility decision, not a code cleanup.

**A self-demonstrating note on the alarm:** L5GN-Tools reported 8
UNCOMMITTED-CRITICAL files this run — which are this very session's own new,
write-capable, *not-yet-committed* code. The alarm firing on uncommitted new blast
radius is the alarm working correctly; it clears when Tim commits.

---

## Not built (as scoped)

Gate sufficiency judgement, data-flow/taint analysis, a run/execution ledger, and
auto-blocking a commit on a critical finding are all explicitly out of scope — this
*reports*, it does not enforce. Whether a raw-write-prod should fail the gate is a
graduated-rigor decision for Tim.

## Files touched

- `l5gntools/scanners/blast_radius.py` — **new** scanner (Tasks A + B).
- `l5gntools/registry.py` — registered `blast_radius`.
- `l5gntools/report.py` — top-of-page UNCOMMITTED-CRITICAL banner; **Blast Radius**
  tab (tier-ranked, scope-aware); `tierPill`.
- `tests/tester_blast_radius.py`, `tests/tester_blast_uncommitted.py` — **new**,
  registered in `verify.py`.

## Assimilation list (carried forward)

- **`db-writes` DSN refinement** (above) — the first tuning the flagship needs to
  stay credible.
- **A run/execution ledger** — capturing that a pipeline *ran* (job id, result) is
  the natural next brief and the answer to the Safe-Write doc's open question #2. A
  new data store, not a scanner — kept separate, as the brief directs.
- **Toolkit version bump** — a new top-level risk signal is a change WizForge (on
  `main`) should see; recommend cutting a version. Tim's call.

---

## UAT

Walk-sheet: `docs/UAT_blast_radius.md`. Consolidated run list:
`docs/UAT_cowork_run_2026-07-24.md` (Brief 3 section appended). The results log
needs a uat stamp (`docs/README.md` §3). Nothing commits until then.
