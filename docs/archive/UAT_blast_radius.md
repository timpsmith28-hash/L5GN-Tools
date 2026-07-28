<!-- gate-frozen: commit=bb257fd -->

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

# UAT walk-sheet — blast-radius scanner + uncommitted-critical alarm

Pair: `docs/COWORK_BRIEF_blast_radius.md` → `docs/COWORK_REPORT_blast_radius.md`.
Built on `23b5ffa`. Gate at build time: `python verify.py` **GREEN**, 6 auditors
+ **37** testers (frozen build-time count). Mark each **ready to walk**, never
"passed". Nothing is committed.

## A — the detector

- [ ] **A1.** `python run.py blast_radius --target SolConfig` (or a full build)
  names `upload_r141.py` as a prod-write and ranks SolConfig by that, not by its
  CSV. A read-only query project shows `read-only`. *(Needs the work rig.)*
- [ ] **A2 (scoping).** No hit originates from a gitignored data/chat path — search
  the blast-radius output for `raw_` / `chat_threads` and expect nothing.
- [ ] **A3 (guardrail).** No prod-write script body, alias, or credential appears
  anywhere in the report or `data/**`; only tiers, paths, families and env
  *classifications*.
- [ ] **A4.** The report has a **Blast Radius** tab ranking projects by tier
  (raw-write-prod loudest), above the file-size view.

## B — the alarm

- [ ] **B1.** If r141 is still uncommitted, **UNCOMMITTED-CRITICAL** fires and sorts
  to the very top of the report; once committed, it drops to a normal
  `guarded-write`/`raw-write`. Tim can watch the alarm clear by committing.
- [ ] **B2.** A tracked, committed guarded-write does **not** raise the alarm.

## C — on the real estate

- [ ] **C1.** The estate-wide list matches Tim's sense of where the sharp edges are
  — no prod-write he knows about is missing.
- [ ] **C2.** False positives are few and obvious; review the recommended
  `db-writes` DSN tuning (bare `.commit()` / local-SQLite noise) and rule on it.
- [ ] **C3.** Expected lights (deploy scripts, `push-exports.ps1`, the knight's own
  `sf`/`scp`) appear; surprises are investigated.

## Gate

- [ ] **G1.** `python verify.py` GREEN; `tester_blast_radius` and
  `tester_blast_uncommitted` listed OK.

---
*Ready-to-walk sheet. The results log needs a uat stamp (`docs/README.md` §3).*
