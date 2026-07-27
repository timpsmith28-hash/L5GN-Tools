> **ARCHIVED** 2026-07-27 · completed pair · pairs with `COWORK_REPORT_relink_scoring.md`; walk-sheet `UAT_relink_scoring.md` + results `UAT_relink_scoring_results.md` archive alongside
> Superseded by: nothing supersedes the request itself — its scorer fix (A/B/C/E/F) landed at `52193bd`, was walked (`UAT_relink_scoring_results.md`, 2026-07-25), and was consumed as `apply_alignment`'s precondition 1, which is what closed the need for this brief to stay live.
> Read as the request as asked (co-origin collapse, corroboration floor, count caps, no synthetic `repo_folder_path`, one registry path). Task D (measured-ownership stoplist) was explicitly deferred by the brief itself, not silently dropped — still open if wanted.

# Cowork brief — relink scoring: evidence must be independent before it can compound

**Origin:** design thread, 2026-07-25, out of `COWORK_REPORT_intent_evidence.md`.
With `build_inventory` reading the census, S4/S5 fire for the first time — and the
dry-run immediately showed the scorer over-counts. **A single sentence naming
`L5GN-Crystal-Spire\world_graph.json` scores 0.997**, outvoting three genuinely
independent sources at 0.936. This is the load-bearing blocker: **no `relink
--apply` may run until it's fixed**, or the first real alignment bakes the
over-count into the vault as `evidence`-locked links a human then can't undo.

**Read first:** `chronicler/pipeline/relink.py` — `combine()` (L303), `score_thread()`
(L326), `decide()` (L433); the S4/S5 producers `chronicler/pipeline/xref_filenames.py`
and `extract_path_mentions.py`; `COWORK_REPORT_intent_evidence.md`; `docs/DECISIONS.md`
0011–0012.

## Working rules

- **BUILD, then STOP.** Nothing commits. Everything staged for Tim's review.
- `python verify.py` **GREEN** before you report; every scoring change gets a
  **hermetic tester** (synthetic signals, no live vault).
- **Dry-run stays the default.** This brief writes *no* decisions to any vault.
  Prove every fix on synthetic fixtures and, where useful, a dry-run against the
  snapshot — never `--apply`.
- Read-only, stdlib-only, UTC ISO-8601, loud failure (unchanged house rules).

---

## The defect, precisely

`combine()` (L318–322) is `score = 1 − Π(1 − wᵢ)` — the independent-evidence
combination. It is correct **only if the signals are independent.** They aren't.
`SIGNAL_COUNT_CAP` (L110) dedupes *within* a signal type (`vocabulary:3`), but S4
`filename_xref`, S5 path-mention and the inline `name_alias` are **different
types**, so one textual mention of one file produces up to three "independent"
signals that then compound:

```
filename_xref(0.97) ⊕ path_mention(0.90)  →  1 − (0.03)(0.10) = 0.997
```

Three failure modes fall out, all confirmed in the intent report:

1. **Double/triple count** — the same basename cited once fires across types and
   compounds as if corroborated.
2. **Lone-signal auto-link** — one unique-filename hit caps at 0.97, clears
   `AUTO_LINK_THRESHOLD` (0.90) with `lead = 0.97` (no rival), and **auto-links
   with zero corroboration**.
3. **Uncapped filename count** — `filename_xref` has no `SIGNAL_COUNT_CAP` entry,
   so N hits in one thread drive the product toward 1.0.

---

## Task A — co-origin de-duplication (the core fix)

Signals that share a **textual origin** are one piece of evidence, not several.
Before `combine()` runs the product, collapse signals that cite the same origin
into a single signal at the **strongest** weight among them.

1. Define origin as the **basename** the signal is about (`world_graph.json`),
   normalised lower-case. `filename_xref`, path-mention and a `name_alias` that
   fired on the same file/token all share it. The producers already carry the
   file in `link_evidence.detail`; if the string isn't reliably parseable,
   **stamp a structured `origin` field** at produce time in S4/S5 and read it
   here rather than regexing prose.
2. In `score_thread()` / `combine()`, group a project's signals by origin; each
   origin contributes **once**, at `max(weight)` across the co-origin group.
   Cross-*type* corroboration only counts when the types cite **different**
   origins.
3. Keep the existing per-type `SIGNAL_COUNT_CAP` and per-weight `CAP` — this adds
   a grouping *upstream* of them, it doesn't replace them.

**Verify:** the `world_graph.json` case drops from 0.997 to ≈0.97 (one origin,
capped), and a thread citing three *different* owned files still combines to a
high, legitimately-corroborated score.

**Tester:** synthetic signals — (a) `filename_xref` + `path_mention` + `name_alias`
all on `world_graph.json` collapse to a single 0.97 origin; (b) three distinct
basenames stay three origins and compound.

---

## Task B — auto-link requires corroboration

A single origin, however strong, must not **auto-link**. Auto-link is the only
category that writes an `evidence`-locked row a human can no longer change, so it
must clear a higher bar than "one confident sentence."

1. In `decide()`, gate `auto_link` on **≥ 2 independent origins** (post-Task-A)
   for the winning project, in addition to the existing `adjusted ≥ 0.90` and
   `lead ≥ 0.25`. One origin, whatever its score → **`suggest`** at most.
2. Leave `suggest`/`ambiguous`/`downgrade` thresholds unchanged — a
   single-strong-signal thread should still surface as a suggestion for the human,
   just never as a silent lock.
3. Put the corroboration count in the decision `summary` so the report shows
   *why* a 0.97 thread was a suggestion, not an auto-link.

**Verify:** a lone unique-filename thread that auto-linked at 0.970 before now
lands as `suggest`; a thread with two independent origins ≥ the bar still
auto-links.

**Tester:** one-origin thread → `suggest`; two-origin thread over threshold →
`auto_link`; assert the corroboration count in the summary.

---

## Task C — cap the filename/path signal counts

Even post-Task-A, extend the count caps so no single thread's raw hit-count can
compound without limit.

1. Add `filename_xref` and the path-mention type to `SIGNAL_COUNT_CAP`. Propose
   starting values (spec caps `vocabulary` at 3 — mirror it), but **dry-run the
   effect** against the snapshot and report the distribution before settling.
2. State the interaction with Task A explicitly in the code comment: A collapses
   *co-origin* duplicates; C caps *distinct-origin* hits of the same type. Both
   are needed and they are not the same lever.

**Tester:** N > cap distinct-origin `filename_xref` signals → only the strongest
`cap_n` are used.

---

## Task D — measured-ownership stoplist (deferrable)

The intent report's `docker compose` finding: Crystal Spire's "earliest thread"
was a Docker chat, because `engine.py` / `tui.py` / `repl.py` are unique **within
these 11 projects** but not **distinctive**. "Uniqueness within the estate is not
distinctiveness." Replace the hardcoded generic-name stoplist in the S4 producer
with a **measured** signal: down-weight a basename by how generic it is
(estate-wide frequency, or a length/commonness heuristic), computed from the
census inventory rather than a static list.

This touches `xref_filenames.py` / `build_inventory`, not just relink. **It is the
one task a tight session may defer** — A/B/C are the `--apply` blocker; D is a
precision improvement that can follow.

**Tester:** a generic basename owned by one project yields a materially lower
weight than a distinctive one.

---

## Task E — stop writing dead `repo_folder_path` into the vault

`load_registry()` L189 synthesises `repo_folder_path = f"{SCOPE_TO_ROOT[scope]}/
{canon}"` — a `L5GN/<name>` path that exists on **no rig** — and `upsert_project()`
(L518) writes it into `projects.repo_folder_path`. That column is what
`vault_reader`/`project_trail` use to classify a project as *repo* vs *concept*
(`repo_folder_path IS NULL`), so a fabricated path **mis-classifies** and splits a
project's thread count. Write the **real** path from the census/registry, or write
**NULL** when there isn't one — never a constructed guess.

**Tester:** a target with no known on-disk path upserts `repo_folder_path` NULL,
not a synthetic string.

---

## Task F — one config-driven `REGISTRY_PATH`, not four hardcoded ones

`build_registry.py:68` hardcodes `REGISTRY_PATH = GITHUB_ROOT_FS / "L5GN" /
".intel_sync" / "project_registry.json"` and `build_activity`, `build_inventory`,
`build_vocabulary` and `relink` all import it. That path matches no rig — the
knight actually writes `/home/l5gn/L5GN/.intel_sync/…` and the curated source is
`config/project_registry.json`. Resolve it **through config**, one source, so the
four consumers and the writer agree on one location per host.

**Verify:** all five modules resolve the same path from config on each host; no
literal `GitHub/L5GN/.intel_sync` remains.

**Tester:** config resolution returns the configured path; a missing config fails
loud (not a silent fallback to the dead literal).

---

## A note carried from the reconciliation (Finding 3), not a task here

`link_evidence.project` still holds ~332 rows keyed to **folder names**, not
registry ids. Because `upsert_project()` creates a `projects` row for whatever
`best["project"]` is, an `--apply` over folder-name-keyed evidence would
**resurrect the legacy `projects` rows** 0011 told us to discard. This is handled
by the **apply brief**, not this one: a knight **fresh build** starts from an empty
`link_evidence`, so the re-derived rows are id-keyed from the start and the re-key
is moot. Named here only so the two briefs' boundary is explicit — do not re-key
in this session.

---

## Suggested order

A → B → C, then E → F, with **D deferrable**. A/B/C are the scoring core and the
`--apply` blocker; land them and the double-count is dead. E and F are the two
highest-value code fixes the intent report named and both are small. **A+B+C alone
is a successful session** — they unblock the golden apply.

---

## UAT — acceptance checks (Tim walks these)

- **A:** on the snapshot dry-run, the `world_graph.json` thread scores ≈0.97, not
  0.997; a genuinely multi-file thread still scores high.
- **B:** no auto-link in the dry-run rests on a single origin; spot-check three
  former lone-signal auto-links now read as suggestions.
- **C:** the filename/path caps are set to a defended value with the distribution
  that justified it shown in the report.
- **E:** a project with no on-disk path reads `repo_folder_path` NULL in a rebuilt
  vault, and no `L5GN/<name>` synthetic path appears.
- **F:** `run.py`/pipeline resolve one registry path from config on the rig and
  (by inspection) on the knight; the dead literal is gone.

Mark each **ready to walk**, never "passed". The decisive walk is on the **knight
against the live vault** — that belongs to the apply brief; here the acceptance is
the snapshot dry-run plus the hermetic testers.

---

## Reporting

Report tasks green vs pending, the before/after scores on the `world_graph.json`
case and at least two other real threads, the chosen `SIGNAL_COUNT_CAP` values with
their distribution, and the **UAT walk-list**. Write the report as
`docs/COWORK_REPORT_relink_scoring.md` and the walk-sheet as
`docs/UAT_relink_scoring.md`. Nothing commits — everything staged for Tim.
