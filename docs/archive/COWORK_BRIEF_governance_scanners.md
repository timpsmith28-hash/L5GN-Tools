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

# Cowork brief — governance scanners + scope-in-UI

**Origin:** design thread, 2026-07-24, from the work rig's critique of L5GN-Tools
(host `10280L`, MCF estate, toolkit `v0.1.0` / `23b5ffa`). Rulings are Tim's, made
in that thread. Authoritative rationale: `docs/DECISIONS.md`, `docs/ARCHITECTURE.md`.

**Read first:** `l5gntools/scanners/todo_adr_scanner.py`, `env_scanner.py`,
`duplicate_finder.py`, `l5gntools/report.py`, and `docs/COWORK_REPORT_file_census.md`.

## Context that shapes these tasks

- **L5GN-Tools is now consumed by WizForgeAnalytics** as a vendored toolkit,
  floating on `main`. No pinning yet; WizForge uses `main` and files complaints
  back to this workstream. So `main` staying green is now load-bearing for a
  second program, not just this one.
- **The work laptop runs a dual role:** a solo *consumer* of its own MCF threads,
  while still a *producer* in the wider mesh sync. These scanners run producer-side
  and must not assume the knight.
- **The direction is defensibility** — a report you could hand to a security
  council. B1 (decision records) and B2 (tracked secrets) are the first concrete
  steps; whether it goes further than good git hygiene is an open investigation,
  not this brief.

## Working rules

- **BUILD, then STOP.** Nothing commits. Everything staged for Tim's review.
- `python verify.py` **GREEN** before you report. Every new behaviour gets a
  hermetic tester registered in `verify.py`.
- These are read-only scanners under the stdlib-only contract. No scanner may
  write into a scanned folder — the `--no-optional-locks` discipline applies to
  any new git call (`l5gntools/common.py`).
- If any doc states an auditor/tester count, it moves; `auditor_doc_claims` will
  fail the gate if a doc contradicts `verify.py`. Update the counts.

---

## Task A — scan once, filter scope in the report (A3 + scope honesty)

Today, getting a work-only or personal-only view means physically moving a folder.
Replace that with a filter over a single scan.

1. **Scan all configured roots**, each carrying its `scope` tag (already deposited
   per project). The report holds the full estate; the *view* is filtered.
2. **A scope control in `report.html`** — `all / l5gn / mcf / <others>` — that
   filters every tab (Git, Files, Docs, Duplicates, etc.) client-side. No re-scan
   to switch view. Persist the choice in memory only (no `localStorage`).
3. **Scope honesty in the header (D1).** The work run labelled itself
   `estate: work` with **both** roots listed but only MCF populated — a reader
   concludes L5GN has zero projects. Distinguish, per root:
   - *scanned, N projects*
   - *empty or absent this run* — the root resolved to no projects, which is not
     the same as "zero projects exist".
4. **Cross-scope caveat (D2).** Counts are not comparable across different scope
   views or `--target` scopes — the Duplicates count dropping 39 → 2 was the
   scope narrowing, not a cleanup. When a filter is active, the affected
   summary counts should say they reflect the filtered view, not the whole estate.

**Design note.** The scorer of "which scope is active" is the UI; the data carries
every scope. Do not bake a scope filter into the *scan* — that reintroduces the
re-scan-to-switch problem this task exists to remove. A `--scope` scan flag may be
added later as an optimisation, but the deposit and report always carry all scopes.

Tester: assert the report data carries per-scope project grouping and that a root
yielding zero projects is marked distinctly from a scanned non-empty one.

---

## Task B — teach the estate its own decision records (B1)

`todo_adr_scanner` counts `Status:` in `docs/adr/*.md` and `adr/*.md`. It is
**blind to `DECISIONS.md`** — the format this estate actually standardised on.
Proof on real data: the work rig's `ValidationAutomation`, whose `docs/DECISIONS.md`
is the defensibility log, reports `adr_count: 0`; only `L5GN-Continuous-Ingestion-Daemon`,
which uses the `adr/NNNN-*.md` convention, scores (9). The one tool meant to police
the estate cannot see the artefact the estate is standardising on.

1. **Recognise `DECISIONS.md`** (root and `docs/`) as a decision record. An
   append-only DECISIONS log is one file holding many entries (`## NNNN — title`),
   not one file per decision — count **entries**, not files.
2. **Tier-count the entries.** This estate's entries and WizForge's both carry a
   status vocabulary. Count `CONFIRMED / ASSUMED / PENDING` (and the trinity's
   `accepted / superseded`) so the report can say, per project, *how much of its
   reasoning is settled vs still open*. That tier count is the defensibility
   signal — "this project's decisions are 80% CONFIRMED" is the sentence a council
   wants.
3. **Report both conventions side by side** — `adr/NNNN` files and `DECISIONS.md`
   entries — rather than forcing one. Whether the estate converges on one is a
   later ruling; the scanner should see both now.

**Do not** make the scanner parse prose or judge whether a decision is *good* —
it counts presence and declared status only, the same discipline as the rest.

Tester: a synthetic `DECISIONS.md` with mixed statuses is counted by entry and by
tier; an `adr/NNNN-*.md` set still counts as before; a project with neither
reports zero without error.

---

## Task C — `env_scanner`: finish the hard half (B2)

The scanner flags secret-suspect config files by name and content — but it
false-positives on examples and never says the one thing that matters: **is the
secret committed?** Scope stays *names and tracked-status only* — no secret value
is ever read or emitted (Tim's ruling; consistent with the existing "names only"
contract).

1. **Suppress `*.env.example`** (and `*.env.sample` / `*.env.template`). An
   example file is *supposed* to hold placeholders; flagging it trains the reader
   to ignore the scanner.
2. **Join against `git ls-files`** and label every suspect:
   - **`TRACKED`** — the file is in git. This is the alarm: a live `.env` in
     history.
   - **untracked** — on disk only. Noted, not alarming.
   - **ignored** — matched by `.gitignore`. The correct state; report as such.
   Use `git --no-optional-locks ls-files` / `check-ignore`; non-git projects
   report every suspect as `untracked (no git)`.
3. **Sort the output so `TRACKED` suspects surface first.** The report should let
   a reader answer "is any secret committed?" without reading a list.

Tester: a fixture with a tracked `.env`, an untracked `.env`, a gitignored `.env`
and an `.env.example` — assert the example is suppressed and the other three carry
the right label.

---

## Task D — content-hash on shared filenames (C3)

`duplicate_finder` already sha1s identical *content*. It reports shared
*filenames* separately but cannot say whether same-named files are the same file.
On the work rig, `reconcile.py` appears in both `TSsToAssets` and
`ValidationAutomation` — shared-toolkit candidate, or coincidence? The tool can't
tell.

Extend the shared-filename groups with a per-location content hash so each group
is labelled:

- **identical** — same basename, same sha1 everywhere → a genuine copy, a
  shared-toolkit or drift candidate.
- **divergent** — same basename, different content → coincidental or forked.

Reuse the `_sha1` already in the module; do not add a second hashing pass — hash
once, use for both the identical-content and shared-filename views.

Tester: two projects with a same-named identical file and two with a same-named
divergent file; assert the labels.

---

## Task E — the 0-commit blind spot (recommended; Tim to confirm scope)

Not formally ruled, but the work rig makes it concrete: `TSsToAssets` is
`is_git: true`, `.gitignore` present, **0 commits**, and **117 at-risk files
(~953 MB, including a Salesforce PII CSV)** — yet `at_risk_note` is `null`,
because the note only populates for *non-git* projects. An initialised repo with
nothing committed protects nothing, and the report reads as if it might.

**In scope, cheap, clearly right:** set `at_risk_note` for the 0-commit git case —
*"repo initialised but has no commits — nothing is under version control."*

**Out of scope, flagged for a later ruling:** a **data-sensitivity flag** (this is
customer PII, not a big log file). That is a real capability the defensibility
direction wants, but it is a classifier with its own design, and it may belong to
WizForge rather than to a generic estate scanner. Note it; do not build it.

Tester: a git project with zero commits carries the note; one with commits does not.

---

## Suggested order

A → B → C → D → E. A is the most visible and the others are independent. If the
budget runs short, **B and C alone are a successful session** — they are the two
defensibility steps and both are evidenced on the work rig.

---

## UAT — acceptance checks (Tim walks these)

- **A:** one `run.py build` produces a report whose scope control switches between
  all / mcf / l5gn without re-scanning, and an empty root reads as "empty this
  run", not "zero projects".
- **B:** `ValidationAutomation`'s `docs/DECISIONS.md` now counts, with a
  CONFIRMED / ASSUMED / PENDING breakdown Tim recognises. CID-Daemon's `adr/`
  count is unchanged.
- **C:** a deliberately committed test `.env` shows `TRACKED` and sorts to the
  top; the neighbouring `.env.example` is absent from the suspect list.
- **D:** `reconcile.py` across two projects is labelled identical or divergent,
  and Tim can act on the answer.
- **E:** `TSsToAssets` carries the no-commits note.

Mark each **ready to walk**, never "passed".

---

## Reporting

Report: tasks green vs pending; the scope-filter behaviour; the DECISIONS tier
counts for the real estate; the tracked-secret labels; the shared-filename
verdicts; and the **UAT walk-list**. Note the toolkit version bump if one is cut
(`v0.1.0` → next), since WizForge floats on `main` and will pick it up.

Write the report as `docs/COWORK_REPORT_governance_scanners.md` and the walk-sheet
as `docs/UAT_governance_scanners.md`. The results log needs a uat stamp or the gate
refuses the commit (`docs/README.md` §3).

Nothing commits. Everything staged, for Tim's review.
