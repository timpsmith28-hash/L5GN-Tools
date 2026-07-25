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
