<!-- gate-frozen: commit=d1a1b76 -->

> **ARCHIVED** 2026-07-28 · completed round record · walk-sheet + stamped results, with two addenda
> Superseded by: nothing — terminal record of the 2026-07-24 Cowork run, walked 2026-07-25.
> Accurate history: the walk of briefs 1–4 across three builds — the gaming rig, the re-walk after
> the root was retargeted to `…/GitHub/L5GN`, and the work-rig (`10280L`) addendum. Finding 1 (the
> `L5GN/` container scanned as one non-git project) colours the first build's numbers; the addenda
> supersede them and say so in-body.
> Note for a cold read: this log is the **evidence base for three pairs still live in core `docs/`**
> — `scanner_bugfixes` (1.x), `governance_scanners` (2.x) and `blast_radius` (3.x). It records
> `[EVIDENCE]` / `[FIXTURE]` / `[BLOCKED]` / `[DEFERRED]` per item and states plainly that it
> captures evidence, not acceptance. It closes none of those pairs by itself.

# Consolidated UAT list — Cowork run 2026-07-24

One walk-list across the four briefs run this session, appended after each brief.
Per-brief detail lives in each `UAT_<brief>.md`; this is the single sheet to walk
top to bottom. All work is **staged, not committed**. Built on `23b5ffa`.

Gate after each brief: `python verify.py` must be GREEN. Current (live, maintained):
6 auditors + 40 testers. Per-brief sections below record each brief's own
build-time count in the frozen `**N**` form.

Order run: scanner_bugfixes → governance_scanners → blast_radius → estate_restructure.

---

## Brief 1 — scanner_bugfixes  ·  status: BUILT, ready to walk

- [ ] **1.A1** Full-estate build incl. Chronicler → `todo_adr` markers in the low
  tens, not hundreds. *(needs work rig)*
- [ ] **1.A2** No `raw_*` / `chat_threads` / `Takeout` / `*_files` path appears in
  the report.
- [ ] **1.A3** No chat-transcript text anywhere in the report or `data/`.
- [ ] **1.A4** Every content scanner emits a `scope` block; `data_dir` skips are
  counted on a project with a chat archive.
- [ ] **1.B1** `estate.json` and the report's embedded `DATA` both parse; report
  renders.
- [ ] **1.B2** Oversize/pre-fix case caps honestly or fails the build loud with a
  named culprit — never a silent truncation.
- [ ] **1.B3** Payload-anomaly banner shows for an oversized/capped scanner.
- [ ] **1.B4** `verify.py` GREEN at 6 auditors + **30** testers (this brief's
  build); new testers `tester_scanner_scope` + `tester_report_selfcheck` listed OK.
- [ ] **1.C1** Task C (Open-questions → PENDING) confirmed as governance-brief
  scope, not expected here.

_Verified in-session (automated, not a substitute for the walk): 299 → 1 marker on
a Chronicler-shaped fixture; `verify.py` GREEN; build self-validates._

---

## Brief 2 — governance_scanners  ·  status: BUILT, ready to walk

- [ ] **2.A1** Scope control switches all / mcf / l5gn with no re-scan; every tab
  refilters.
- [ ] **2.A2** Empty root reads "empty this run", not "zero projects".
- [ ] **2.A3** Cross-scope caveat banner shows when a filter is active.
- [ ] **2.B1** `DECISIONS.md` counts by entry + tier (CONFIRMED/ASSUMED/PENDING and
  accepted/superseded). *(This repo: 16 entries, all accepted.)*
- [ ] **2.B2** `adr/NNNN` count unchanged; both conventions shown side by side.
- [ ] **2.B3** `## Open questions` section contributes to PENDING.
- [ ] **2.C1** Committed `.env` → TRACKED, sorts first; `.env.example` suppressed.
- [ ] **2.C2** gitignored `.env` → ignored; on-disk-only `.env` → untracked; no
  secret values in output.
- [ ] **2.D1** Shared `reconcile.py` labelled identical/divergent.
- [ ] **2.E1** 0-commit repo (`TSsToAssets`) carries the no-commits note.
- [ ] **2.G1** `verify.py` GREEN at 6 auditors + **35** testers; five new testers
  listed OK.

_Verified in-session (automated): DECISIONS.md → 16 entries all accepted; scope
filter cut 156 gitignored paths on this repo; embedded report JS passes
`node --check`; build self-validates; all five new testers green._

---

## Brief 3 — blast_radius  ·  status: BUILT, ready to walk

- [ ] **3.A1** Full run / `blast_radius --target SolConfig` names `upload_r141.py`
  a prod-write and ranks SolConfig by it, not its CSV. *(needs work rig)*
- [ ] **3.A2** No hit originates from a gitignored data/chat path.
- [ ] **3.A3** No script body / alias / credential in the report or `data/`; verdicts
  and paths only.
- [ ] **3.A4** Blast Radius tab ranks projects by tier, above file size.
- [ ] **3.B1** UNCOMMITTED-CRITICAL fires for an untracked prod-write, sorts to the
  very top, and clears when committed.
- [ ] **3.B2** A committed guarded-write does not raise the alarm.
- [ ] **3.C1** Estate list matches Tim's sense of the sharp edges; nothing missing.
- [ ] **3.C2** Rule on the recommended `db-writes` DSN tuning (bare `.commit()` /
  local-SQLite is the dominant false positive).
- [ ] **3.G1** `verify.py` GREEN at 6 auditors + **37** testers; `tester_blast_radius`
  + `tester_blast_uncommitted` listed OK.

_Verified in-session (automated): r141 fixture → raw-write-prod + `upload_r141.py`
UNCOMMITTED-CRITICAL (untracked); alias never stored; L5GN-Tools self-scan tier
raw-write with the `.commit()` false-positive quantified; report JS passes
`node --check`; build self-validates; both new testers green._

---

## Brief 4 — estate_restructure  ·  status: PARTIALLY EXECUTED

Folders mounted; Tasks 0 + 1 done, safe batch of Task 2 executed with Tim's go.
**Nothing deleted, nothing committed.** 5 of 9 estate repos moved; 4 locked.

- [x] **4.0** Fingerprint captured before any move; no shared root SHAs; Castle root
  `832863248d5c` (remote `l5gn-mesh-vertex-3_v0`). *(automated; walk to confirm)*
- [x] **4.1** Disposition verified vs real folders; server-hub-iso → vendor (Tim);
  PROJECTS_REVIEW.md promoted to `docs/investigation/`.
- [x] **4.2a** 5 repos moved to `GitHub\L5GN\`; every moved git HEAD matches pre-move.
- [ ] **4.2b** Move the 4 LOCKED repos (Castle, CID, Crystal-Spire, mesh-vertex-3_prod)
  after closing the daemon/containers/editors holding them; verify vs fingerprint.
- [ ] **4.V** Move vendor assets to `vendors\` — NOT `all-MiniLM-L6-v2` until
  `CITADEL_MINILM_PATH` is updated (CID dependency).
- [ ] **4.S** ⚠ Secure `l5gn.com.key.txt` / `.pem.txt` in server-hub-iso, then → vendors.
- [ ] **4.cfg/5** Only once all 9 repos are in `L5GN\`: flip `local.json` root to
  `…/GitHub/L5GN`, `run.py build` (same list, all l5gn, no vendor/scratch), deposit staged.
- [ ] **4.3** Tim states knight/Castle topology before any backup.

_In-session: 5 repos renamed within the GitHub mount (.git verified intact); config root
held at `…/GitHub` deliberately so the 4 unmoved active repos aren't dropped. The 4 locks
are open directory handles (running processes) on Tim's machine — a stop-the-line event,
left intact, not forced._

---

<!-- next brief appended below -->
