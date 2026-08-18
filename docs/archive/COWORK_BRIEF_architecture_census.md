> **ARCHIVED** 2026-08-17 · completed pair (brief) · Report:
> `archive/COWORK_REPORT_architecture_census.md` · Walked:
> `archive/UAT_architecture_census_results.md`
> Superseded by nothing — the round completed. Original purpose: commission a
> scanner that emits the toolkit's shape as data, and a rendered view of it the
> gate refuses to let go stale (DECISIONS 0030).
> Accurate as the request that was made. Its live output is
> `docs/_architecture_shape.md`, which is generated and stays in core `docs/` —
> do not look for it here. The brief's **AST-never-regex** rule and its
> **report-parse-failure-as-`unparsed`** rule are load-bearing and were met;
> read them before changing the census, not after.

# Cowork brief — the toolkit describes its own shape, deterministically

**Origin:** design thread, 2026-08-02, out of
`investigation/2026-08-02_architecture-drift_claude_2-response.md`.
**Deliverable:** a scanner that emits the toolkit's **shape** as data, and a
rendered markdown view of it that the gate refuses to let go stale.
**Builds on:** 0012 (contracts), 0016 (what ARCHITECTURE.md is for), 0026
(provenance by path segment), and the scanner contract itself.

`ARCHITECTURE.md` was last written 2026-07-18 and cites decisions 0002–0008 and
nothing after. Three of its statements are not stale but **inverted** — §5 names
`review_queue` as the review endpoint's write target, which is the one table 0024
says it may never write. The audit found twelve such findings (A1–A12).

**The root cause is not neglect.** ARCHITECTURE is written from DECISIONS, never
from code — it records what was *decided*, in the present tense, as though it
were what was *built*. A4 is 0007's design faithfully recorded and then
superseded by the implementation; nothing closed the loop. So the fix is not a
rewrite. A rewrite drifts again by September.

**Read first:** the investigation above (all twelve findings), `docs/README.md`
§1 (*"a document earns its place by holding something that can't be derived"*),
`l5gntools/registry.py`, `l5gntools/contract.py`, `auditors/auditor_stdlib.py`
(the AST pattern you are extending), and `COWORK_REPORT_toolkit_self_scan.md`
finding #2 — the estate-level cache defect you must not inherit.

---

## Precondition ▸ a DECISIONS entry must be ratified before any code

0016 declares `docs/ARCHITECTURE.md` **the authoritative as-built reference**.
This brief splits that role in two. That is an amendment to 0016's premise and
must not be made silently.

**Draft the entry below to Tim, get it ratified and committed, then build.** If
he rules against the split, the scanner is still worth having as `data/` output
and Task 4 falls away.

> ## 00NN — Shape is generated; rationale is authored. ARCHITECTURE.md keeps the half that can't be derived
>
> **Date:** 2026-08-02 · **Status:** proposed · **Amends:** 0016 (does not
> supersede it) · **Builds on:** `docs/README.md` §1's governing rule ·
> **Source:** the 2026-08-02 architecture drift audit
>
> **Context.** `ARCHITECTURE.md` holds two kinds of content. **Rationale** — why
> the `l5gntools/` ↔ `chronicler/` boundary is capability and not custody, why
> the `--no-syncback` belt was traded for the `render_log` base — cannot be
> derived from anything and is the reason the document exists. **Shape** — which
> modules exist, which routes require what, which tables a module writes, what
> the gate is composed of — is derivable from the tree, and is the half that
> drifted. All twelve findings of the 2026-08-02 audit are shape claims in a
> rationale document.
>
> `docs/README.md` §1 already rules on this: *a document earns its place by
> holding something that can't be derived.* Status is derived, so it does not
> live in `docs/`. Shape is derived by the same argument and nobody had noticed.
>
> **Decision.** The two halves are separated:
> 1. **Shape is generated** by a scanner, from the tree, and rendered to a
>    committed, machine-owned document. It is never hand-edited.
> 2. **`ARCHITECTURE.md` keeps the rationale** and cites the generated document
>    for shape. It stops asserting module lists, route tables, write targets and
>    gate composition — the claims it cannot keep current.
> 3. **0016's resolution stands.** ARCHITECTURE remains the replacement for the
>    never-located `chronicler_design_and_intent_v2.md`; what it is *authoritative
>    for* narrows to rationale, with shape delegated to a document that cannot
>    disagree with the code because it is produced from it.
>
> **Consequences.** The A1/A4/A8 failure class becomes structurally impossible
> rather than a thing to remember. The cost is a generated file in the repo and a
> gate check that refuses a stale one — the lockfile pattern, with the lockfile's
> familiar friction: adding a route means regenerating. That friction is the
> feature. A document that *can* silently disagree with the code eventually does.

---

## Working rules

- **Read-only, stdlib-only, registered in `registry.py`.** The four scanner
  auditors must pass without exemption. If the contract cannot express this
  scanner, that is a finding worth reporting — do not weaken the contract.
- **A scanner writes only via `common.write_json` under `data/`.** Rendering the
  markdown is therefore a **separate step**, not part of the scan. A scanner that
  writes into `docs/` breaks `auditor_readonly`, and rightly.
- Gate GREEN before commit. All logic in testable functions.
- **AST, never regex.** See Task 2's warning; it is the whole quality bar.

## Grounding — what exists

- `l5gntools/contract.py` `build_manifest` already declares-and-verifies a
  scanner's shape. This is the same move applied to the repo.
- `auditors/auditor_stdlib.py` already walks source with `ast`. Extend that
  pattern; do not invent a second one.
- The board round added a **repo root derived from `Path(__file__)`** rather than
  config. Reuse it. This scanner's target is always this checkout, so it needs no
  root, no config and no estate — which is unusual and worth stating in the
  report.

---

## Task 1 ▸ the census — facts only

`l5gntools/scanners/architecture_census.py`, estate-level. It emits
`data/architecture.json`. Six sections, each a list of facts:

1. **Scanners** — every entry in `registry.SCANNERS` with `NAME`, `DESCRIPTION`,
   `ESTATE_LEVEL`, `SAFETY`, and its module path.
2. **Gate composition** — `verify.py`'s `AUDITORS` and `TESTERS`, by name and
   count. This is where the `gate-frozen` count-drift problem dies at source.
3. **Route table** — every route in `chronicler/review/app.py`: method, path, and
   **the dependency it requires** (vault, estate, or nothing). The slice-1 report
   states this table in prose; derive it instead.
4. **Write targets, per module** — for every module that opens a DB, the set of
   tables it writes. **This is the section that would have caught A4.**
5. **Schema shape** — tables and columns from `schema.sql`, plus the **delta
   against `schema_frozen.sql`**. The current delta is `path_scan_log`,
   `render_log`, `meta`; A12 should fall out of this section without being looked
   for.
6. **Dependency wall** — declared extras in `pyproject.toml` against imports
   actually found per subsystem.

Plus a provenance block: `toolkit_git_info()` as every other scan already stamps.

## Task 2 ▸ the quality bar — three constraints, each with a tester

**Determinism.** Two runs against an unchanged tree must produce **byte-identical
output**. Sort every collection. No wall-clock inside the payload — the
provenance block is the only place a timestamp may appear, and it sits outside
the compared region. A tester runs the scan twice and asserts equality.

**No absolute paths, ever.** Every path repo-relative. The output is a candidate
deposit artefact and 1.A2 treats a leaked path as a defect; an absolute path is
also machine-specific and would break determinism across rigs. A tester asserts
no value in the payload starts with `/` or matches a drive letter.

**Parse failure is reported, never counted as zero.** This is the one that
matters. A module the AST cannot parse must appear as
`{"module": ..., "status": "unparsed", "reason": ...}` — never as a module with
no writes and no routes. A regex implementation cannot make this distinction at
all, which is why regex is out: *a scanner that cannot tell "no writes" from "I
could not look" is the confident-zero class this estate has now rediscovered
three times.* A tester plants an unparseable file and asserts it surfaces.

## Task 3 ▸ render, and prove it against known answers

A renderer (suggested `l5gntools/report.py`, beside `build_all`) turns
`data/architecture.json` into **`docs/_architecture_shape.md`**.

- **The leading underscore is deliberate.** 0026's provenance rule classifies a
  path segment starting with `.` or `_` as derived/tool-managed. Without it,
  `doc_census` counts this as an authored document and the estate's own authored
  ratios go wrong — the scanner corrupting the measurement it belongs to.
- The file opens with a **do-not-edit header** naming the producing commit.

**The acceptance test has a known correct answer, which is rare — use it.** The
first render must independently reproduce two findings nobody told it about:

- §4 must show the review endpoint writing `{threads, projects, review_rulings}`
  and **never** `review_queue` — contradicting `ARCHITECTURE.md` §5 (finding A4).
- §5 must show `render_log` in `schema_frozen.sql` and absent from `schema.sql`
  (finding A12).

If it does not reproduce both, the census is wrong, not the findings.

## Task 4 ▸ the gate refuses a stale document

`auditors/auditor_architecture_current.py`: regenerate to a temp location, diff
against the committed `docs/_architecture_shape.md`, fail on any difference with
the diff printed.

This is the lockfile pattern and it carries the lockfile's friction: adding a
route means regenerating before you can commit. **That friction is the point** —
it converts "remember to update the doc" into "cannot commit without it", which
is `INTENT` §5's *prefer "can't" to "shouldn't"* applied to documentation.

Do not make the auditor regenerate-and-write. It reports; the human runs the
generator. A gate that silently fixes what it audits cannot be trusted to audit.

---

## Explicitly out of scope

- **Rewriting `ARCHITECTURE.md`.** The rationale half is Tim's judgement and a
  separate act. This brief only stops the document being *obliged* to carry
  shape.
- **Fixing A1, A2 or any other finding.** A2 (the sync-back removal 0008
  authorised) is its own brief and should not ride along.
- Any prose generation. The census emits facts; the renderer arranges facts. A
  sentence explaining *why* is authored by a human, always.
- Scanning any repo but this one.
- The Historian / Shadow work. Adjacent, separately briefed.

## Stop conditions

- **The scanner cannot satisfy the four scanner auditors** → stop and report. Do
  not exempt it; an exemption for the scanner that describes the contract is the
  worst possible precedent.
- **Output is not byte-stable across two runs** → stop. A non-deterministic
  generator is worse than the hand-written document it replaces, because the gate
  check in Task 4 would then fail at random and be disabled within a week.
- **The census contradicts a finding it should reproduce** and the census is
  right → stop and report. That is a new finding and it outranks this brief.
- **Estate-level caching repeats self-scan finding #2** (an unkeyed cache that
  never invalidates on a changed input set) → stop; that defect is known and must
  not be inherited.

---

## UAT — acceptance checks (Tim walks these)

- `data/architecture.json` exists after a build and contains all six sections.
- **Two consecutive runs produce identical output.** Worth doing by hand once.
- **No absolute path appears anywhere** in the JSON or the rendered markdown.
- An unparseable module is **named as unparsed**, not silently absent.
- `docs/_architecture_shape.md` renders, carries the do-not-edit header and the
  producing commit, and reads as true.
- **It reproduces A4** — the endpoint's write set excludes `review_queue`.
- **It reproduces A12** — `render_log` present in frozen, absent from `schema.sql`.
- **The gate refuses a stale render.** Edit one line of the generated file by
  hand, run `verify.py`, confirm it goes red and prints the diff. Regenerate,
  confirm green.
- `doc_census` counts `_architecture_shape.md` as **generated**, not authored.
- `ARCHITECTURE.md` is unchanged by this round.

Mark each **ready to walk**. Results log needs a uat stamp naming the commit; do
not write a `gate=` field.

---

## Reporting

`docs/COWORK_REPORT_architecture_census.md`, walk-sheet
`docs/UAT_architecture_census.md`, stamped results after the walk.

Record the ratification, the six sections' contents verbatim on first run, the
determinism proof, **which of A1–A12 the census reproduced independently**, and
anything the toolkit's own shape turns out to be that we would rather it weren't.

An acknowledgement line should be added to
`investigation/2026-08-02_architecture-drift_claude_2-response.md` per
`docs/README.md` §4 once this lands — naming the findings it closed and the
commit that closed them. This will be the convention's first use.
