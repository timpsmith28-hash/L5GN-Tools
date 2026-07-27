<!-- gate-frozen: commit=25ede96 -->

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
