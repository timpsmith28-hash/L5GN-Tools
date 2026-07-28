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

# Cowork report — governance scanners + scope-in-UI

Pair: `docs/COWORK_BRIEF_governance_scanners.md`. Session 2026-07-24, on top of
`23b5ffa`, immediately after the scanner bug-fix pair (which this brief depends on
for the `.gitignore` scoping and which supplies the tracked-status join reused
here). **BUILD, then STOP — nothing committed; everything staged for Tim's review.**

`python verify.py` — **GREEN**, 6 auditors + **35** testers at this build (five
testers added this session; frozen build-time count).

| Task | State | What landed |
|---|---|---|
| A — scan once, filter scope in the report | **green** | client-side scope control, per-root scope honesty, cross-scope caveat |
| B — teach the estate its own DECISIONS.md | **green** | entries counted + tier-counted, both conventions side by side, Open-questions → PENDING |
| C — `env_scanner` tracked-status (the hard half) | **green** | TRACKED/untracked/ignored, examples suppressed, TRACKED sorts first |
| D — content-hash on shared filenames | **green** | identical vs divergent labels, hashed once |
| E — the 0-commit blind spot | **green** | `at_risk_note` now fires for an initialised-but-empty repo |

---

## Task A — one scan, a filtered view, and honest scope labels

Getting a work-only or personal-only view used to mean physically moving a folder.
Now the scan carries every scope (each project already deposits its `scope` tag)
and the **report** filters client-side:

- **Scope control** in `report.html` — `all / l5gn / mcf / …`, built from the
  scopes actually present — filters every tab (Git, Code, Files, Docs, Hygiene,
  Duplicates, TODO/Decisions) with no re-scan. The choice lives in memory only,
  no `localStorage`.
- **Scope honesty (D1).** A per-root line distinguishes *scanned, N projects* from
  *empty this run*. The work run's bug was labelling a root with zero populated
  projects the same as a real zero, so a reader concluded L5GN had no projects;
  `scope_summary` now marks the empty case distinctly. (`tester_governance_scope`
  asserts a populated root reads `scanned` and a zero-yield root reads `empty`.)
- **Cross-scope caveat (D2).** When a filter is active the report shows a banner —
  "filtered to mcf (N of M projects); summary counts reflect this view" — so a
  count dropping reads as the filter narrowing, not a cleanup. This is the lesson
  from the Duplicates count that fell 39 → 2 when the scope narrowed.

The scan still carries all scopes; the *scorer of which scope is active is the
UI*, never the scan, so the re-scan-to-switch problem this task removed does not
creep back.

## Task B — the estate can finally see its own decision records

`todo_adr_scanner` counted `Status:` only in `docs/adr/*.md` and `adr/*.md`, so
`DECISIONS.md` — the format this estate actually standardised on — scored zero.
It now recognises `DECISIONS.md` (root and `docs/`) as a decision record and,
critically, **counts entries, not files**: an append-only log is one file holding
many `## NNNN — title` entries.

Each entry's status is tier-counted in *both* vocabularies — WizForge's
`CONFIRMED / ASSUMED / PENDING` and the trinity's `accepted / superseded` — so the
report can say, per project, how settled its reasoning is. Run against this
estate's own `docs/DECISIONS.md`: **16 entries, all `accepted`** — the trinity
log, now visible where before it read as `adr_count: 0`.

Both conventions report side by side in the TODO/ADR/Decisions tab (ADR files *and*
DECISIONS entries + tiers); the scanner does not force convergence — that is a
later ruling.

**Folded in from the bug-fix brief (its Task C):** an `## Open questions` /
`## Open decisions` heading in any doc contributes its list items to the PENDING
tier, mechanically (section presence + item count, no prose parsing). This is why
r141's "Open questions" sections now register as pending design decisions.

## Task C — `env_scanner` finishes the hard half

The scanner flagged secret-suspect files by name/content but never answered the
one question that matters: **is the secret committed?** Now every suspect is
joined against git (reusing `file_census.status_of`) and labelled:

- **`TRACKED`** — in git. The alarm: a live secret in history.
- **untracked** — on disk only. Noted, not alarming.
- **ignored** — matched by `.gitignore`. The correct state, reported as such.

`*.env.example` / `.sample` / `.template` are **suppressed** from the suspect list
— an example file is supposed to hold placeholders, and flagging it trains the
reader to ignore the scanner. Suspects sort **TRACKED first**, and the Hygiene tab
shows a red `N TRACKED` pill so "is any secret committed?" is answerable without
reading a list. Scope stayed *names + tracked-status only* — no secret value is
ever read or emitted.

One subtlety worth recording: the bug-fix scope filter skips gitignored paths, but
this task must *see* a gitignored `.env` to label it `ignored`. `Scope.skip` grew
an `honor` parameter so `env_scanner` honours data/vendored skips but not the
gitignore skip — the ignored label is a finding, not something to hide.

## Task D — shared filenames, now with a verdict

`duplicate_finder` reported shared *filenames* but couldn't say whether same-named
files were the same file. Each shared-filename group is now labelled:

- **identical** — same basename, same sha1 everywhere: a genuine copy, a
  shared-toolkit or drift candidate (the `reconcile.py`-across-two-projects case).
- **divergent** — same basename, different content: coincidental or forked.

The file is hashed **once** and the digest feeds both the identical-content and
shared-filename views — no second pass, as the brief required. Divergent-but-shared
names sort first (a forked copy is the more interesting signal), and the
Duplicates tab shows the label as a pill.

## Task E — an empty repo no longer reads as safe

`TSsToAssets` on the work rig is `is_git: true`, `.gitignore` present, **0
commits**, 117 at-risk files — yet `at_risk_note` was `null`, because the note only
populated for non-git projects. `file_census` now sets, for the 0-commit git case:
*"repo initialised but has no commits — nothing is under version control."* A repo
with an unborn HEAD protects nothing, and the report no longer implies it might.

The out-of-scope half — a data-sensitivity flag distinguishing customer PII from a
big log — is **noted, not built**: it is a classifier with its own design and may
belong to WizForge rather than a generic estate scanner (assimilation list).

---

## Files touched

Build:

- `l5gntools/report.py` — `scope_summary`; `estate.scope_summary`; scope
  `<select>` + honesty line + cross-scope caveat in the viewer; decision-tier
  columns; content-label pills; TRACKED-suspect pill.
- `l5gntools/scanners/todo_adr_scanner.py` — `parse_decisions`,
  `parse_open_questions`; DECISIONS.md + Open-questions census.
- `l5gntools/scanners/env_scanner.py` — tracked-status join, example suppression,
  TRACKED-first sort, `tracked_suspect_count`.
- `l5gntools/scanners/duplicate_finder.py` — `label_shared`; identical/divergent
  labels; `shared_filename_divergent`.
- `l5gntools/scanners/file_census.py` — `_has_commits`; 0-commit `at_risk_note`.
- `l5gntools/scanners/_scope.py` — `Scope.skip(honor=...)` so env_scanner can see
  ignored files.

Tests (all new, registered in `verify.py`): `tester_governance_scope`,
`tester_decision_records`, `tester_env_tracked`, `tester_dupe_labels`,
`tester_zero_commit_note`.

Docs: the four maintained live gate claims (`file_census`, `intent_evidence`
report + UAT pairs) moved to 35 testers; this pair's own build count is frozen
`**35**`.

---

## Assimilation list (carried forward)

- **Data-sensitivity flag** (PII vs bulk log) for `at_risk` — real capability the
  defensibility direction wants, but a classifier of its own; likely WizForge's,
  not a generic scanner's. Noted for a ruling.
- **Toolkit version bump recommended.** This pair changes the report contract
  (new scope filter, decision tiers, tracked-status labels) that WizForge floats
  on `main` will pick up. Cutting `v0.1.0 → v0.2.0` would give its consumers a
  version to point at. **Not bumped here** — cross-program version policy is Tim's
  call; recorded so it is not lost.
- **DECISIONS convergence** — the estate now sees both `adr/NNNN` and
  `DECISIONS.md`; whether to converge on one is a later ruling, not the scanner's.

---

## UAT

Walk-sheet: `docs/UAT_governance_scanners.md`. Consolidated run list:
`docs/UAT_cowork_run_2026-07-24.md` (Brief 2 section appended). The results log
Tim produces needs a uat stamp (`docs/README.md` §3). Nothing commits until then.
