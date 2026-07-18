# Chronicler investigation — 2026-07-18

Read-only forensic pass over the Chronicler pipeline and its frozen data store.
Nothing was fixed or applied. All DB work ran against a `/tmp` **copy** of the
live `chronicler.db`; the Task 1 proof ran against a **synthetic** DB + vault
built from the real `render_md.py`. The live DB and vault were never written.

Method note: the sibling `Chronicler\` folder had to be connected mid-task (only
`L5GN-Tools` was mounted at start). There is no `.db` inside the repo — the live
data lives only in `Chronicler\`.

---

## Task 0 — Recover the record

**0.2 Pipeline divergence (`Chronicler\pipeline\` vs repo `chronicler\pipeline\`).**
The original has **no file the repo lacks**. Every difference has the repo newer
and a strict content superset:

- Files only in the repo: `intake.py`, `normalize_md_transcript.py`,
  `set_substantive.py` (as the brief expected).
- `db.py` — differs: the repo adds `CHRONICLER_HOME` env-var support (deploy
  target / "the knight"); the original only had `PIPELINE_DIR.parent` +
  `CHRONICLER_DB_PATH`. Repo is ahead.
- `run_pipeline.py` — differs: the repo wires the two new stages
  (`md-transcript`, `substantive`) into the chain and adds their `--skip-*`
  flags. The original chain doesn't know about them. Repo is ahead.
- All other shared files (including `render_md.py`) are **byte-identical**.

Conclusion: **the original is behind on both files where they differ and even
with the two new stages absent, nothing needs salvaging from `Chronicler\pipeline\`
at the code level.** `scrape_gemini_share.py` at the `Chronicler\` root is identical
to the repo's copy.

**0.3 What in `Chronicler\` is NOT reproducible from the repo.** These are data
and inputs, not code, and exist nowhere in the repo:

- `chronicler.db` — 92 MB, the entire payload (1,171 threads, 22,004 messages).
- `chat_threads/` raw inputs: `raw_claude_files/` (43 MB, Claude export),
  `raw_gem_files/` (158 MB, 110 saved Gemini work conversations),
  `raw_gemini_files/` (125 MB Takeout, 1,657 activity files),
  `scraped_gemini/` (4 share JSONs + manifest), `zip_downloads/` (raw Takeout zip).
- `chat_threads/shatter.py` — present only here, not in the repo.
- `relink_applied.txt` / `relink_dryrun.txt` — S6 relink decision logs (they cite
  the real machine path `C:\Users\tim.smith\Github\L5GN\Chronicler`, 1,037 threads
  scanned at the time).
- `urls.txt` — **confirmed the share-link batch input, not debris.** Its four URLs
  (`f499add109e2`, `382bedba6a5f`, `439dd11e6940`, `4577d22c19f5`) are exactly the
  four `scraped_gemini/*.json` files. It is the input to `scrape_gemini_share.py`.
- `_test.db-journal` — inert debris (STATUS already flags it for manual deletion).

**0.4 Disposition — recommendation (Tim to rule).**
Retire `Chronicler\` as a code location but keep it as the **data home**, and end
the untracked-fork state. Concretely: the repo (`L5GN-Tools/chronicler/`) is the
authoritative code and is strictly ahead, so `Chronicler\pipeline\` should stop
being edited. But `Chronicler\` also holds the only copy of the DB and all raw
inputs, which by design (STATUS, `db.py` `CHRONICLER_HOME`) are meant to live on
the data volume separate from vendored code. So:

- Preferred: designate `Chronicler\` the **runtime data root** only — delete its
  `pipeline/` copy and point `CHRONICLER_HOME` there, running the repo's code
  against it. That removes the fork without touching the irreplaceable data.
- The one clearly-wrong option is the current one: a second, silently-diverging
  copy of `pipeline/` that nobody watches. That should not persist.

Do **not** delete `Chronicler\` wholesale — it is the sole home of the DB and raw
exports. This is your call; the above is a recommendation.

---

## Task 1 — Is there a live edit-loss path? **Yes, and it is proven.**

**The brief's core hypothesis is half right and half wrong.** §13.5's atomic
ordering was *not* abandoned — it **is implemented** in `render_md.run()`:
`sync_back()` drains file→DB for *every* thread and commits, *then* the render
loop re-reads each row fresh (`SELECT * ... WHERE thread_id=?`, line 332) and
renders from that fresh row. That is exactly "read frontmatter → apply → re-read
fresh → render." The code refutes "it appears never to have been implemented."

What is real is the **edit-loss path**, but its root cause is different from the
brief's framing. It is not a missing §13.5 ordering; it is the `--no-syncback`
belt on the full chain colliding with the documented workflow.

**Does `--no-syncback` rewrite frontmatter from the DB?** Yes. Even with
`no_syncback=True`, `run()` skips only `sync_back()`; it still loops every thread
and calls `render_thread()`, which does `out_path.write_text(...)` from the DB
row. `--no-syncback` = **DB→file, unconditionally overwriting every `.md`.**

**Default sync-back state:** ON. `python3 pipeline/render_md.py` (no args) syncs
back. `run_pipeline.py --render-only` renders with sync-back ON. The **full
chain** (`run_pipeline.py` with no `--render-only`) forces `--no-syncback` on the
render stage (line 156-157). So the only mode that absorbs Obsidian edits is
`--render-only`.

**Callers outside `run_pipeline.py`:** `bulk_review.py` invokes `render_md.py`
**with sync-back ON** (no `--no-syncback` — `run_render()`, line 135). It stays
safe only because it pre-patches `review_status: confirmed` into the frontmatter
first, so sync-back is a no-op. And `render_md.py` is directly hand-runnable with
sync-back ON by default. So sync-back-ON renders do happen outside the full chain.

### The hazard, proven on a synthetic DB + vault (real `render_md.py`)

- **Scenario A — the loss.** Seed a thread, render (base recorded). Human edits
  `review_note` in the `.md` (a genuine Obsidian edit, not yet absorbed). Run the
  full-chain render (`--no-syncback`). Result: `review_note` **wiped back to
  `null`** in both file and DB. *The edit is silently lost.*
- **Scenario B — what would have saved it.** Same edit, render with sync-back ON
  (the `--render-only` path). Result: the edit is **written into the DB and
  survives**.
- **Scenario C — why sync-back ON is now safe.** Simulate a pipeline DB write
  (relink updates `project_link` in the DB) with the `.md` left stale — the exact
  133-link setup. Render with sync-back ON: **0 overrides applied**, the DB's
  fresh value wins, no clobber. Guard (b) (the `render_log` 3-way base) correctly
  reads the stale file field as a stale default (file == base), not an edit.

**This is the crux.** The 133-link clobber was fixed with two guards: (a)
`--no-syncback` (belt) and (b) the `render_log` base (suspenders). Scenario C
proves **(b) alone prevents the clobber in both directions.** With (b) in place,
(a) is redundant — and (a) is the sole thing that overwrites unabsorbed Obsidian
edits during a full-chain run. **The fix inverted the hazard: it traded "stale
file clobbers fresh DB" for "fresh DB clobbers unabsorbed edit," when the
suspenders already made the belt unnecessary.**

**The workflow makes it live, not theoretical.** STATUS's periodic workflow is
"review in Obsidian; edits flow back on the next render," and the command it
documents for the next run (step 2) is `run_pipeline.py` — the full chain, which
renders `--no-syncback` and does **not** flow edits back. Edits survive only if
Tim happens to run `run_pipeline.py --render-only` *before* the next full run.
Nothing enforces that ordering.

**The 133-link incident (from `RECOVERY_render_syncback.md`).** The original
sync-back trusted the file unconditionally ("file wins"). After a pipeline DB
write the on-disk frontmatter was older than the DB (e.g. `project_link: null`);
the next render read those stale nulls back as if a human had typed them and
overwrote 133 fresh evidence links to NULL, logging 359 bogus `manual_override`
rows. Recovery: delete the bogus overrides, clear the bogus `project_confidence='manual'`
(~133), re-run `relink.py --apply` (re-derives the 133 from `link_evidence`, which
was never touched), render `--no-syncback`, verify 133-before == 133-after and 0
new overrides. **The live DB confirms recovery succeeded: 0 `manual_override`
rows remain and 0 threads carry the clobber signature (`project_link IS NULL AND
project_confidence='manual'`).**

**Is §13.5 implementable as designed?** It already is. What was *correctly
abandoned* is the literal §13.3 "file wins, unconditionally" — replaced by "file
wins only when it differs from the last render (a proven edit)." That is stronger
than the design and is what makes both directions safe. The disagreement between
design and code is therefore in §13.3's "unconditionally," not §13.5's ordering —
a decision for the design thread, not a code fix in this pass.

---

## Task 2 — What the dead fingerprint path costs (live DB, read-only)

Census of the frozen DB (`schema_version 1.0-frozen`, `frozen_at
2026-07-17T07:31:16Z`). 1,171 threads, 22,004 messages, 2,836 attachments, 15
projects.

**Threads by source / account:** gemini 1,136 (gemini-personal 1,026,
gemini-work 110), claude 35 (claude-personal 35).

**By provenance (`parser_version`) — the reconciliation vs Layer A/B/C split:**

| provenance | threads |
|---|---|
| `group_fallback_v1` (Layer A/B/C, §12) | 1,022 |
| `gemini_work_v1` (direct normalize) | 110 |
| `claude_v1` (direct normalize) | 35 |
| `reconcile_v1` (§11 reconciliation) | **4** |

Reconciliation produced exactly **4 threads** — the four scraped shares — against
1,022 fallback-grouped Takeout threads. This confirms §12's expectation of a
handful of skeletons vs thousands of Takeout records. Within the fallback:
**Layer A (exact fingerprint) 761, Layer B (idle-gap session) 261, Layer C
(semantic) 0.** Layer C never formed a single group.

**By project_confidence / coverage:**

| confidence | threads |
|---|---|
| NULL (unlinked) | 1,013 |
| evidence | **150** |
| fuzzy | 7 |
| exact | 1 |
| manual | **0** |

- **150 evidence links confirmed**, exactly as STATUS expects. 158 threads linked
  at any confidence.
- **Real coverage: 150/1,171 = 12.8%** of all threads (13.5% at any confidence).
- Worse when you ask about *real* threads: of the 332 substantive threads (≥4
  messages), only **27** carry an evidence link — **8.1%**. The other 123 evidence
  links land on sub-4-message Takeout fragments. The system's whole payload is
  thin and skewed toward fragments.

**`link_evidence`: 746 rows, by signal —** `filename_xref` 568, `name_alias` 98,
`path_mention` 80. **Zero `vocabulary` (confirmed) and zero `time_window`.** The
absence of `time_window` is the dead fingerprint path made visible: §11.3.2 calls
hash-anchor windowing "the main defense against false positives from repeated
stock phrasing," and with no attachment hash exposed by the share scrape there is
no anchor, no window, and not one `time_window` evidence row. All 746 rows come
from the three content/name signals with no temporal disambiguation.

**`review_queue`: 2,069 rows (pending 1,079 / confirmed 990).**

| type | total | status |
|---|---|---|
| thread_grouping | 1,022 | 839 confirmed / 183 pending |
| close_suggestion | 738 | all pending |
| link_upgrade | 150 | all confirmed (auto-resolved audit) |
| project_link | 136 | all pending |
| link_ambiguous | 15 | all pending |
| link_downgrade | 4 | all pending |
| reconciliation_gap | 2 | pending |
| reconciliation_fuzzy_match | 1 | pending |
| bulk_accept | 1 | confirmed (audit) |

Already-applied audit rows (not awaiting anyone): the 150 `link_upgrade` (one per
evidence link — verified 150 == 150), the 1 `bulk_accept`, and the 839
`thread_grouping` confirmed by the ≥0.95 bulk sweep (verified: groupings with
confidence ≥ 0.95 == 839 exactly). These 990 = the entire "confirmed" pile.
Genuinely awaiting a human ruling: **15 ambiguous + 4 downgrade** (matches
STATUS's "still open" line exactly), plus 136 `project_link`, 3 reconciliation
rows, 183 low-confidence groupings, and 738 low-stakes close suggestions.

**Is anything `review_status: confirmed`?** 749 threads are — but that is a
grouping artifact, not a linking decision. Only 22 of those 749 are substantive;
the rest are fragments confirmed en masse by the bulk-accept sweep. Decisively:
**no thread has `project_confidence='manual'` — zero human-confirmed project
links exist.** Every link in the system is automation-derived (evidence/fuzzy/
exact). At the level §11.3.6 cares about (reconciliation and project-link
confirmation), everything is still pending/automatic, as designed.

---

## Task 3 — The tunables, with data

The headline: **three of the four defaults govern paths that produced almost no
data, so there is nothing to retune them against. The fourth is the only one with
a real distribution, and it sits deep in the tail.**

**`ratio >= 0.90` — fuzzy content match (§11.3.4).** Fuzzy matching only fires in
reconciliation, and reconciliation ran on **4 skeletons total**. Exactly **one**
fuzzy match was ever recorded: `reconciliation_fuzzy_match` note = *"Skeleton
index 1 matched at ratio 0.935."* n = 1, and it cleared 0.90 with room to spare.
There is no histogram to draw. The threshold has essentially never been exercised;
retuning it empirically is impossible with the current input volume.

**`idle_gap_minutes = 30` — Layer B session segmentation (§12.2).** The only
tunable with real data (261 Layer B groups). Distribution of 6,849 consecutive
inter-turn gaps across the gemini-personal stream:

```
   <1m : 51.4%
  1-5m : 21.2%
 5-15m : 20.9%
15-30m :  3.4%
30-60m :  1.2%
  1-3h :  0.8%
 3-12h :  0.7%
   >12h:  0.6%
```

Percentiles: p90 = 11.4 min, p95 = 18.7 min, p99 = 214 min. **96.8% of all gaps
are under 30 minutes; only 3.2% are ≥ 30.** The empirical elbow — where
within-session density collapses — is around **15 minutes** (the 15-30m bucket is
already down to 3.4%). So the 30-minute default sits far out in the tail, at
roughly the p97 mark. It is a *conservative* (merge-biased) boundary: it captures
essentially all genuine within-session activity plus slack. That bias is
defensible for a review-oriented grouping (over-grouping into one reviewable
thread beats fragmenting), but the data does not support 30 as an elbow — a
tighter 15-20 min would track the real distribution. Note the groups that *did*
form are far tighter than the threshold (implied intra-session avg gap: p90 = 5.6
min), so 30 rarely bound anything; it only mattered at session edges.

**`similarity_threshold = 0.6` and `semantic_window_days = 14` — Layer C (§12.3).**
**Layer C produced zero groups.** No `Layer C` rows exist in `review_queue`;
sentence-transformers was evidently not installed (Layer C "skips cleanly if that
isn't installed," per STATUS/`group_fallback` docstring), or every message was
consumed by Layers A/B first. Either way there is **no data at all** — not even
the sub-threshold best-similarity scores §12.3 says it records. Both defaults
governed nothing. The doc's own flag that 0.6 is "explicitly an empirical guess"
remains untested.

**Recommendation (not applied):** only `idle_gap_minutes` has enough data to
reason about, and the reasoning says 30 is loose-but-defensible; a move toward
15-20 min would match the elbow if tighter sessions are wanted. The other three
cannot be retuned without more reconciled shares (ratio) and an actual Layer C run
with sentence-transformers installed (similarity, window). The design's "retune
empirically once real output exists" hasn't happened because, for three of four,
the real output is empty.

**Why was `signal='vocabulary'` rolled back?** The rationale is **not** in the
design doc but **is** in `pipeline/SCHEMA.md` (lines 75-76): *"The `vocabulary`
signal was evaluated and **dropped** — it degraded linking — so no `vocabulary`
rows exist; `build_vocabulary.py` remains on disk unused."* The mechanism is
implied by `relink.py` (line 27): time-window is "what separates same-vocabulary
projects worked on in different eras." Vocabulary terms overlap across projects
(shared boilerplate/terminology), and with the `time_window` signal dead there was
no way to separate projects that share vocabulary but were active in different
periods — so vocabulary evidence generated false links and was rolled back to the
`filename_xref` / `path_mention` baseline. This ties directly to Task 2: the same
missing temporal anchor that kills the fingerprint window is what made vocabulary
unusable. The *decision* to drop it is recorded (SCHEMA.md); the deeper evaluation
data behind "it degraded linking" is not in the code or DB and may exist only in a
chat thread that isn't reachable here.

---

## Decisions this pass surfaces for Tim (none applied)

1. **`Chronicler\` disposition** — retire its `pipeline/` copy, keep the folder as
   the data root under `CHRONICLER_HOME`; end the untracked fork.
2. **Edit-loss path** — design (§13.3 "file wins unconditionally") vs code (guard
   b, "file wins only if changed since last render"). Scenario C shows guard (b)
   alone is safe, so dropping `--no-syncback` from the full chain would remove the
   edit-loss path. Alternatively, at minimum, correct STATUS's workflow so
   `--render-only` runs before the full chain. Which is right is a design-thread
   call.
3. **Tunables** — `idle_gap_minutes` optionally 15-20; the other three are
   un-retunable until more reconciled shares and a real Layer C run exist.
