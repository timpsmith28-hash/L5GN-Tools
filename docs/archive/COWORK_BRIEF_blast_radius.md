> **ARCHIVED** 2026-07-28 · completed pair · brief + report + walk-sheet; evidence in
> `archive/UAT_cowork_run_2026-07-24_results.md` (items 3.x), ratified by Tim 2026-07-28
> Superseded by: nothing — `l5gntools/scanners/blast_radius.py` is the living output.
> Accurate history: the tiering design and the guardrail that no script body, alias or
> credential is ever stored. That guardrail was re-confirmed independently on the work rig
> (`10280L`, 2026-07-28), not just on the rig it was built against. The `db-writes`
> false-positive tuning (bare `.commit()` / `.execute()`) held.
> Ratification, 2026-07-28: Tim confirmed 3.C1/C3 — the estate list matches his sense of the
> sharp edges. One genuine prod-write hit estate-wide (a Salesforce write from the work
> laptop), everything else correctly not escalated. A discriminating result, not a thin one.
> Stop trusting: any count in this body predates the root retarget to `…/GitHub/L5GN`. At the
> time of writing, Finding 1 of the run log had the whole `L5GN/` tree scanning as one non-git
> project, which inflated and distorted per-project figures; the run log's addenda supersede
> them. Auto-blocking a commit on a critical finding is still explicitly out of scope.

# Cowork brief — blast-radius scanner + the uncommitted-critical alarm

**Origin:** design thread, 2026-07-24, after the work rig's SolConfig r141 pipeline
— a scripted, six-gate, fail-closed clone of five live `Solution_Configuration__c`
rows into production (job `750bI00000kfklxQAA`) — was found to be **completely
invisible** to the estate report. The report ranked SolConfig's risk by a big parts
CSV while `upload_r141.py` was shelling `sf data import bulk --target-org
myMainAlias` at PROD, uncommitted. This brief teaches the tool to rank risk by
*consequence*, not byte size.

**Read first:** `docs/INTENT.md` §3 (defensibility is now a success criterion) and
§5 (rigor is graduated), `l5gntools/scanners/env_scanner.py` (the pattern-matching
precedent), `l5gntools/scanners/file_census.py` (tracked/untracked status), and — as
the training fixture — the r141 pipeline on the work rig (`gates.py`,
`upload_r141.py`, `SolConfig_Safe_Write_Pattern.md`).

## Why this is the flagship of the defensibility turn

Two prior findings were the same finding in disguise: TSsToAssets flagged as risky
for a big PII CSV rather than its 0-commit repo, and SolConfig ranked by a parts CSV
rather than its prod-write pipeline. **The tool measures size; the estate's real risk
is blast radius.** A governance harness that cannot see the code most able to cause
harm is doing the easy half. This brief closes that — and it lands on the exact
capability INTENT now names: *the record can be shown to whoever doubts you.*

## Working rules

- **BUILD, then STOP.** Nothing commits. Everything staged for Tim's review.
- `python verify.py` **GREEN** before you report; every behaviour gets a hermetic
  tester registered in `verify.py`.
- Read-only, stdlib-only. `--no-optional-locks` on any git call. **This scanner
  reads code as text and never executes it** — detecting a prod-write is not running
  one.
- **Runs after the scanner bug fixes.** It must inherit the `.gitignore` / data-dir
  scoping from `COWORK_BRIEF_scanner_bugfixes.md` Task A, or it will scan chat
  archives for `sf data import` strings and false-positive on transcripts.
- Depends on the governance scanners' **B2** (tracked-status join) for Task B. If
  that has not landed, Task B reuses its `git ls-files` join rather than duplicating.

---

## Task A — BUILD: `blast_radius` scanner

New scanner `l5gntools/scanners/blast_radius.py`, registered in
`l5gntools/registry.py`. `ESTATE_LEVEL = False`, `SAFETY = SAFE`.

Statically flag code that can **mutate a system outside its own repo**. Match on
text, cite every hit with file + line, never execute.

**Signal families (start here; make the list data-driven so it extends without a
code change):**

| Family | Example markers |
|---|---|
| Salesforce DML | `sf data import`, `sf data upsert/update/delete`, `--target-org`, Bulk API `job`/`ingest`, `Database.update/upsert/delete`, `DELETE FROM`, `@future(callout=true)` |
| Shell / OS | `subprocess`/`os.system` invoking `rm`, `mv`, `curl … -X POST/PUT/DELETE`, `scp`, `ssh` |
| Cloud / infra | `aws … rm/put/delete`, `terraform apply`, `kubectl apply/delete`, `gcloud … delete` |
| DB writes | `INSERT`/`UPDATE`/`DELETE`/`DROP`, `.commit()` against a non-test DSN |
| HTTP writes | `requests.post/put/patch/delete`, `httpx` same |

**Per hit, capture and classify:**

- **target environment**, when derivable — `--target-org myMainAlias` resolving to a
  prod alias is a different tier from a sandbox alias. Read alias/config files in the
  repo to resolve where you can; where you cannot, mark `env: unknown` and **treat
  unknown as prod-tier for ranking** (fail-safe, per INTENT's "fail loud, never
  silently wrong").
- **guarded or raw** — is the write behind an approval gate in the same repo? The
  r141 pattern (typed-phrase gate, sandbox-first, post-verify) is *lower* risk than a
  bare `sf data import` with no gate. Detect the presence of a gate module / typed
  approval near the write; do **not** judge whether the gate is *good* — presence
  only, the usual discipline.

**Emit a per-project `blast_radius` tier** — `none / read-only / guarded-write /
raw-write / raw-write-prod` — and make it a **top-level risk signal in the report,
ranked above file size.** The loudest thing the report says about a project should be
"contains an ungated production write," not "has a big CSV."

**Do not** try to prove exploitability or trace data flow. This is a smoke detector,
not a static-analysis engine. A flagged false positive the operator dismisses is
acceptable; a missed prod-write is not — bias toward flagging.

**Tester:** a fixture with (a) a raw `sf data import --target-org prod` script, (b)
the same behind a typed-gate module, (c) a read-only `sf data query`, (d) a
`requests.get`. Assert the four tiers, that `--target-org unknown` ranks prod, and
that a `sf data import` string inside a gitignored chat JSON is **not** flagged
(inherits Task A scoping from the bugfix brief).

---

## Task B — BUILD: the uncommitted-critical alarm

The single highest-value alert in the estate: **write-capability ∩ untracked.** r141
is this today — a five-file pipeline that wrote to PROD, created 16:04–16:18, with
the last commit at 10:24. The exact code that mutated production has **no provenance
in version history**, and the report registered it only as an anonymous bump in
`dirty_files` — unable to tell one dirty README from an entire untracked prod-write
toolkit.

Cross `blast_radius` (Task A) with git tracked-status (governance B2 / `file_census`):

- A `guarded-write`+ file that is **untracked or uncommitted-dirty** →
  **`UNCOMMITTED-CRITICAL`**, surfaced at the very top of the report, above at-risk
  and above size.
- The alarm names the files, their tier, and their git state — "prod-write code with
  no commit behind it" in one line a reviewer reads first.

This directly answers the estate's own worst case: the highest-stakes action leaving
no provenance. It is also the sharpest expression of the drift thesis — *built,
consequential, and not in the record.*

**Tester:** a fixture with a tracked guarded-write (not critical) and an untracked
raw-write (critical); assert only the second raises `UNCOMMITTED-CRITICAL` and it
sorts first.

---

## Task C — REPORT: run against the real estate, prove r141 surfaces

Run the two new signals against the work rig (or the deposited work estate) and
report:

- Does SolConfig now surface `raw-write-prod` (or `guarded-write` if r141's gate is
  detected) and an `UNCOMMITTED-CRITICAL` alarm if the pipeline is still uncommitted?
- What else in the estate lights up — expected (deploy scripts, `push-exports.ps1`,
  the knight's own `sf`/`scp` calls) vs surprising?
- The false-positive rate on a first pass, and which markers caused it. A scanner
  that cries wolf gets muted (INTENT §5: a routed-around gate protects nothing), so
  the tuning matters as much as the detection.

**Guardrail:** report tiers and file paths only. **Do not reproduce the contents of
any prod-write script or its credentials/aliases in `docs/`** — naming that
`upload_r141.py` is a raw-write-prod is the finding; pasting its body recreates the
exposure, the same lesson as the Crystal Spire Drive IDs.

---

## Not in scope

- Judging whether a gate is *sufficient* — presence only. Whether the r141 typed
  phrase should be four-eyes is the operator's ruling, not the scanner's.
- Data-flow / taint analysis. Smoke detector, not SAST.
- A run/execution ledger (capturing that a pipeline *ran*, with job id and result).
  That is the natural next brief and the answer to the Safe-Write doc's open question
  #2, but it is a new data store, not a scanner — keep it separate.
- Auto-blocking a commit on a critical finding. This *reports*; whether a
  raw-write-prod should fail the gate is a graduated-rigor decision for Tim, and a
  hard block on a solo operator's own repo may be exactly the tightness INTENT §6
  warns about. Recommend, don't enforce, this round.

---

## Suggested order

A → B → C. A is the detector, B is the one cross-product that makes it urgent, C
proves it on the case that motivated it. If the budget is tight, **A and B are a
successful session** — C can be a follow-up run once the work estate is deposited.

---

## UAT — acceptance checks (Tim walks these)

- **A:** `run.py blast_radius --target SolConfig` (or a full run) names
  `upload_r141.py` as a prod-write and ranks SolConfig by that, not by its CSV. A
  read-only query project shows `read-only`.
- **A (scoping):** no hit originates from a gitignored data or chat path.
- **B:** if r141 is still uncommitted, `UNCOMMITTED-CRITICAL` fires and sorts to the
  top; once committed, it drops to a normal `guarded-write`. Tim can watch the alarm
  clear by committing.
- **C:** the estate-wide list matches Tim's own sense of where the sharp edges are —
  no prod-write he knows about is missing, and the false positives are few and
  obvious.

Mark each **ready to walk**, never "passed".

---

## Reporting

Report tasks green vs pending; the blast-radius tiers across the estate; the
uncommitted-critical alarms; the false-positive notes and any marker tuning; and the
**UAT walk-list**. Note the toolkit version bump — WizForge floats on `main` and a
new top-level risk signal is a change its consumers should see.

Write the report as `docs/COWORK_REPORT_blast_radius.md` and the walk-sheet as
`docs/UAT_blast_radius.md`. The results log needs a uat stamp or the gate refuses the
commit (`docs/README.md` §3). Nothing commits — everything staged, for Tim's review.
