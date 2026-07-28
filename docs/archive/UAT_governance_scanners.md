<!-- gate-frozen: commit=25ede96 -->

> **ARCHIVED** 2026-07-28 · completed pair · brief + report + walk-sheet; evidence in
> `archive/UAT_cowork_run_2026-07-24_results.md` (items 2.x), closed 2026-07-28 against real
> data from both estates
> Superseded by: nothing — the governance scanners and `auditor_decision_records` are live.
> Accurate history: scope honesty (2.A), open-questions → PENDING (2.B3, carried on both
> estates — Crystal-Spire personally, SolConfig at work), tracked-secret labelling on a real
> secret (2.C), and 15 shared-filename verdicts (2.D).
> Three items closed after the fact, with the measurements that closed them:
> · **2.B1 — RESOLVED, confirmed on real data.** The counter is correct. `doc_census` sees
>   `ValidationAutomation/docs/DECISIONS.md` ("Decisions Log", 4 headings, 1,145 words) while
>   `todo_adr_scanner` scores `decisions_count: 0`, because `_DECISION_ENTRY` matches only
>   `^##\s+(\d+)`. A convention mismatch, not a defect.
> · **2.B2 — upgraded from FIXTURE to real evidence.** CID reports `adr_files: 9` on the
>   2026-07-28T21:09 personal build (`a1f9169`). It read 0 at walk time only because CID was
>   collapsed inside the `L5GN/` container before the root retarget.
> · **2.E1 — no carrier in either estate, measured not assumed.** No project reports "repo
>   initialised but has no commits" on the personal build above or the work build
>   (`10280L`, 2026-07-28T20:55). Only "not a git repository" appears. Closed as tester-proven
>   with the gap recorded, rather than held open for an estate that may never contain one.
> Stop trusting: `decisions_count` as a measure of whether an estate keeps decision records.
> It scores 0 on **both** estates while real decision logs exist in each — the work estate
> encodes decisions as extracted knowledge documents (`SolConfig_Knowledge.md`,
> `LEGACY_BUNDLE_KNOWLEDGE.md`) rather than numbered entries. The scanner measures one
> convention; the estates use two. Unresolved when this pair closed.
> Also never ruled on: the data-sensitivity / PII flag this brief flagged as out of scope.

# UAT walk-sheet — governance scanners + scope-in-UI

Pair: `docs/COWORK_BRIEF_governance_scanners.md` → `docs/COWORK_REPORT_governance_scanners.md`.
Built on `23b5ffa`. Gate at build time: `python verify.py` **GREEN**, 6 auditors
+ **35** testers (frozen build-time count). Mark each **ready to walk**, never
"passed". Nothing is committed.

## A — scope filter + honesty

- [ ] **A1.** One `python run.py build` produces a report whose **Scope** control
  switches between all / mcf / l5gn (and any other scope) **without re-scanning** —
  every tab refilters instantly.
- [ ] **A2.** An empty root reads as **"empty this run"**, not "zero projects".
- [ ] **A3.** With a filter active, the **cross-scope caveat banner** appears and
  summary counts are described as reflecting the filtered view.

## B — decision records

- [ ] **B1.** `ValidationAutomation`'s `docs/DECISIONS.md` now counts, with a
  CONFIRMED / ASSUMED / PENDING breakdown Tim recognises. *(On this repo:
  `docs/DECISIONS.md` shows 16 entries, all `accepted`.)*
- [ ] **B2.** CID-Daemon's `adr/NNNN` count is unchanged (both conventions show
  side by side in the TODO/ADR/Decisions tab).
- [ ] **B3.** An r141-style `## Open questions` section contributes to a visible
  PENDING count.

## C — tracked secrets

- [ ] **C1.** A deliberately committed test `.env` shows **TRACKED** and sorts to
  the top; the neighbouring `.env.example` is **absent** from the suspect list.
- [ ] **C2.** A gitignored `.env` shows **ignored**; an on-disk-only `.env` shows
  **untracked**. No secret value appears anywhere in the output.

## D — shared-filename verdicts

- [ ] **D1.** A `reconcile.py` shared across two projects is labelled **identical**
  or **divergent**, and Tim can act on the answer.

## E — 0-commit note

- [ ] **E1.** `TSsToAssets` (git repo, 0 commits) carries the note *"repo
  initialised but has no commits — nothing is under version control."*

## Gate

- [ ] **G1.** `python verify.py` GREEN; the five new testers
  (`tester_governance_scope`, `tester_decision_records`, `tester_env_tracked`,
  `tester_dupe_labels`, `tester_zero_commit_note`) all listed OK.

---
*Ready-to-walk sheet. The results log needs a uat stamp (`docs/README.md` §3).*
