> **ARCHIVED** 2026-07-20 · completed pair · report: `docs/chronicler_investigation_2026-07-18.md` (archived alongside)
> Superseded by DECISIONS 0001–0005 + `docs/ARCHITECTURE.md` · Original purpose: the
> first alignment pass — recover the inherited record, then report (not fix) on the
> edit-loss path, the dead fingerprint path and the tunables.
> Read as the request. Its Tasks 5–7 (fold relink, `auditor_doc_claims`, off-box backup)
> were deliberately *not* executed in that pass and were re-issued as round 1's Tasks
> B/D/C, where they landed — do not re-run them from here. Its Task 0 found
> `chronicler_system_design.md` outside the repo (now in `archive/`); the
> `chronicler_design_and_intent_v2.md` it hunted was never located and is resolved to
> ARCHITECTURE.md by DECISIONS 0016.

# Cowork brief — Chronicler alignment pass

**Origin:** design thread, 2026-07-17. Written after a cold read of the estate and
of `chronicler_system_design.md`, which was found **outside this repo** at
`C:\Users\timps\Documents\GitHub\Chronicler\`.

**Posture:** most of this is *investigate and report*, not *change*. The lesson that
produced this brief is that code was absorbed without its rationale, so the failure
mode to avoid is fixing things we don't yet understand. **Tasks 1–3 are reporting
tasks. Do not act on their findings in the same pass — report, then wait.**

**Rules:** `python verify.py` green before every commit. Every status claim written
into `docs/` must be checked against the code, not recalled from this session.

---

## Task 0 — Recover the record (do first, blocks nothing else)

The authoritative design doc is not in this repo. `chronicler/pipeline/STATUS.md`
says: *"the authoritative reference is `chronicler_system_design.md` in the repo
root."* That file lives in `GitHub\Chronicler\`, which is **not a git repo** (no
`.git`), alongside a second doc we have not read (`chronicler_db_finalize_brief.md`),
a live `chronicler.db`, and a full second copy of `pipeline/`.

1. Copy `chronicler_system_design.md` and `chronicler_db_finalize_brief.md` into
   `chronicler/docs/`. Commit them. The *why* now lives with the *what*.
2. Report the divergence between `Chronicler\pipeline\` and
   `chronicler\pipeline\`. Known: this repo has `intake.py`,
   `normalize_md_transcript.py`, `set_substantive.py`; the original does not.
   Report anything else — especially any file where the *original* is ahead.
3. Report what else in `Chronicler\` is not reproducible from this repo
   (`chat_threads/`, `chronicler.db`, `relink_applied.txt`, `relink_dryrun.txt`,
   `urls.txt`). `urls.txt` may be the share-link batch list — if so it is an input,
   not debris.
4. **Do not delete `Chronicler\` yet.** Recommend a disposition (retire vs keep as a
   real upstream with a remote) and let Tim rule. The current third state — an
   untracked fork nobody watches — is the only option that's clearly wrong.

---

## Task 1 — REPORT: is there a live edit-loss path? (highest priority)

**Hypothesis, unverified.** Design §13.5 specifies an atomic per-thread ordering:
read frontmatter → apply to DB → re-read the row fresh → render from that fresh row.
That ordering is what makes §13.3's "file wins, unconditionally" safe in both
directions. It appears never to have been implemented. Instead `run_pipeline.py`
uses a mode switch: the full chain renders with `--no-syncback`; only `--render-only`
syncs back. Its docstring records that stale frontmatter "once wiped 133 evidence
links" — i.e. sync-back ran in the full chain, the DB was fresh, the files were
stale, and "file wins" clobbered the links to NULL. See also
`chronicler/pipeline/RECOVERY_render_syncback.md`.

If that's right, the fix inverted the hazard rather than removing it: a frontmatter
edit made in Obsidian and not yet absorbed via `--render-only` is **overwritten by
the next full pipeline run.** Note `STATUS.md`'s periodic workflow tells the user to
review in Obsidian and says *"edits flow back on the next render"* — while the
command it documents for the next run is the full chain, which does not sync back.

**Report:**
- Read `render_md.py`. Does `--no-syncback` rewrite frontmatter from the DB? Confirm
  or kill the hypothesis with the code.
- Prove it on a **copy** of the DB and vault — never the live ones. Edit a
  frontmatter field, run the full chain, report what survives.
- Is `render_md.py`'s default sync-back ON or OFF? Anything invoking it outside
  `run_pipeline.py`?
- Read `RECOVERY_render_syncback.md` and report what the 133-link incident actually
  was and how it was recovered.
- Assess: is §13.5's atomic ordering implementable as designed, or was it abandoned
  for a reason the code will show us?

**Do not fix in this pass.** The design and the implementation disagree; which one is
right is a decision, and decisions come from the design thread.

---

## Task 2 — REPORT: what the dead fingerprint path costs

Design §11.3a confirms the share-scrape side exposes no attachment hash — the
fingerprint anchor path is permanently dead, not pending. Consequences worth
quantifying, because §11.3.2 calls hash-anchor windowing *"the main defense against
false positives from repeated stock phrasing"* and names your own recurring
boilerplate as the risk. With no anchors, there is no window.

**Report, from the live DB (read-only):**
- Thread counts by `source` / `account` / `review_status` / `project_confidence`.
- How many threads came from reconciliation (§11) vs Layer A / B / C (§12)?
  Design §12 expected 4 skeletons vs 3,507 Takeout records — confirm the real split.
- `review_queue` census by `type` and `status`. How much is genuinely awaiting a
  human ruling vs already-applied audit rows?
- `link_evidence`: total, and the breakdown by `signal`. STATUS expects 150 and zero
  `signal='vocabulary'`. Confirm. 150 links across ~1,171 threads is the payload of
  the whole system — state the real coverage as a percentage.
- Is any thread `review_status: confirmed`, or is everything pending per §11.3.6?

---

## Task 3 — REPORT: the tunables, with data

The design's closing note: *"start with the stated defaults and retune empirically
once real reconciliation/grouping output exists."* Real output exists; the retune
never happened. Given Task 2, these defaults are likely doing nearly all the work.

The four, with their design locations:
- `ratio >= 0.90` — fuzzy content match (§11.3.4)
- `idle_gap_minutes = 30` — Layer B session segmentation (§12.2)
- `similarity_threshold = 0.6` — Layer C, flagged in the doc as an *empirical guess* (§12.3)
- `semantic_window_days = 14` — Layer C comparison window (§12.3)

**Report distributions, not opinions:** the histogram of match ratios actually
achieved, the distribution of inter-turn gaps (is 30 min anywhere near the real
elbow?), and the spread of Layer C best-similarity scores including sub-threshold
ones (§12.3 deliberately records these). Where does each default sit against its
distribution? Recommend, don't apply.

Also report: why was `signal='vocabulary'` rolled back? `build_vocabulary.py` is
still in the tree; the rationale is not in the design doc. If the code and the DB
can't tell us, say so — the reasoning may only exist in a chat thread we can't reach.

---

## Task 4 — Make the inherited invariant structural

**Only after Task 1 reports.** The house style is "can't, not shouldn't": the wall is
path separation, the deposit contract makes cross-estate writes physically
impossible, the auditors scope to `registry.SCANNERS`, the gate is a pre-commit hook.
The sync-back rule is the one guarantee in the estate that's a convention living in
one orchestrator's docstring — and it's the one protecting the only irreplaceable
data. Bring it in line with the rest of the house, in whatever shape Task 1 shows is
correct.

---

## Task 5 — Fold `relink` into the pipeline

`chronicler/pipeline/relink.py` already exists, and `relink_applied.txt` /
`relink_dryrun.txt` in `Chronicler\` show it has been run. This has been described
across three threads as the sharpest open edge and the most valuable follow-up; it
appears to be one tuple in `run_pipeline.py`'s `STAGES` list, behind the embeddings
dep, skipping cleanly when unavailable (same pattern as Layer C).

Report first: what does `relink.py` do, what does it need, and is it safe to run on
every pass or is it a rescan-and-apply tool with different semantics? Then wire it,
with a tester.

---

## Task 6 — `auditor_doc_claims.py`

The estate's purpose is catching the gap between what was said and what was done, and
nothing checks the docs against the code. `HANDOFF.md` claimed 18 hermetic testers;
`verify.py` registers 14. Nobody counted. A cold read caught it.

Add an auditor that fails the gate when a documented claim contradicts the code.
Start with the count of registered auditors/testers as asserted anywhere in `docs/`
or `README.md`. Keep it narrow and mechanical — a small auditor that always runs
beats a large one that rots. Extend only to claims with a single machine-checkable
source of truth.

While here: `HANDOFF.md` still says 18. Fix to 14.

---

## Task 7 — Off-box backup for the vault

The vault is the one irreplaceable thing in the estate — a deleted Gemini share link
does not come back. It is now single-homed on the knight, and the only backup is
playbook §9's manual `cp chronicler.db chronicler.db.bak`: same disk, one generation,
only if the operator remembers.

`VACUUM INTO` produces an atomic consistent copy safe to move anywhere. Wire it as an
automatic pre-ingest step, and get one copy off the knight. Do **not** put a live
SQLite file in any file-sync service — that's the known corruption trap.

---

## Task 8 — Reconcile the inherited docs

Cheap, do last, but do it:
- `chronicler/pipeline/STATUS.md` lists six pipeline stages; `run_pipeline.py` has
  eight (`md-transcript` and `substantive` were added since). Its freeze runbook says
  `cd <repo root>` then `python pipeline/finalize_db.py` — wrong now that the path is
  `chronicler/pipeline/`. Either fix it or mark it clearly as a historical record of
  the freeze, superseded.
- `chronicler/README.md` describes `pipeline/` as "ingest stages (normalize →
  reconcile → group → render) plus db.py, the schema, and finalize_db.py." There are
  ~25 modules, including a whole linking subsystem (`relink`, `xref_filenames`,
  `extract_path_mentions`, `build_registry`, `build_vocabulary`) that appears nowhere
  in the design doc or the README. Describe what's actually there.
- STATUS's own cleanup list was never actioned: `_reconcile_gemini_verify.py` (a
  12-byte stub it says to delete) was copied *into this repo*. Delete it here. Keep
  `_presync_suggested_close.py` — STATUS says deliberately.
- Report whether `chronicler/README.md`'s follow-up #2 ("live test pending") is still
  true. `HANDOFF.md` claims knight auto-ingest is live. One of them is wrong.

---

## Not in scope

- The stranded HITL surface. `vault_staging/` now lives under `CHRONICLER_HOME` on a
  headless knight with no Obsidian, while ~19 `review_queue` items await a ruling
  "in Obsidian." Design §7.1 offered a local web UI as option (b) and deferred it,
  accepting the Obsidian dependency; moving the writer to the knight broke that
  dependency, so the deferral is now due. **That's a design decision, not a task** —
  it belongs to the design thread. Task 2's review_queue census is the input to it.
- Retuning anything. Task 3 reports; the design thread rules.
