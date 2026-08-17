<!-- uat: commit=001d037 dirty=false host=LucasGoonPC walked=2026-08-17 -->

# UAT results — architecture census (DECISIONS 0030)

Walked against `docs/UAT_architecture_census.md`. All ten items **pass**.

- [x] `[G]` `data/architecture_census.json` exists after a build and
  contains all six sections. Confirmed via `python run.py architecture_census`
  and direct inspection of the six section keys.
- [x] `[W]` Two consecutive runs of `census(TOOLKIT_ROOT)` produce identical
  output (`json.dumps` equality, both by hand and in the gate via
  `tests/tester_architecture_census.py`).
- [x] `[G]` No absolute path anywhere in the JSON or the rendered markdown
  (route paths under `/api/...` correctly excluded as URLs). Gate-checked.
- [x] `[G]` A planted unparseable module is named `{"status": "unparsed", ...}`
  and never appears in `write_targets` reading as "no writes." Gate-checked
  with a synthetic fixture.
- [x] `[W]` `docs/_architecture_shape.md` renders, carries the do-not-edit
  header and the producing commit, and reads as true against the live tree.
- [x] `[W]` Reproduces **A4**: `chronicler/review/core.py` writes
  `{projects, review_rulings, threads}`, never `review_queue`.
- [x] `[W]` Reproduces **A12**: `render_log` is in `schema_frozen.sql`,
  absent from `schema.sql`.
- [x] `[W]` The gate refuses a stale render (hand-edited one line, `verify.py`
  went RED with a printed diff; restored, went GREEN; separately, deleting
  the file entirely produced a distinct "does not exist" failure).
- [x] `[G]` `doc_census` counts `docs/_architecture_shape.md` as
  **generated**, not authored, after this round's fix to
  `classify_provenance`.
- [x] `[H]` `docs/ARCHITECTURE.md` is unchanged by this round (`git diff`
  against it, empty).

**Gate at the walked commit:** `python verify.py` → GREEN, 10 auditors + 75
testers (printed counts match `docs/COWORK_REPORT_architecture_census.md`).

**Found during the walk, not named in the brief, three fixed before this
stamp:**

0. The build had started from a stale base: this session's cloud clone was
   taken from GitHub at `afc246b`, eight commits behind the actual local
   checkout (`a0c3901`, the unpushed `correctness_sweep` round). Caught
   before syncing anything back, by checking `git log` on the local device
   directly rather than assuming the GitHub clone was current. The whole
   round was rebased onto `a0c3901` — clean, no conflicts, including on
   `pyproject.toml`, which both this round and `correctness_sweep` touch —
   and every count/fact in the report and this results log reflects the
   rebased state, not the stale one.

1. `doc_census.classify_provenance` checked only directory segments for a
   leading `.`/`_`, never the filename itself -- `docs/_architecture_shape.md`
   read `authored` on the unmodified tree, which would have failed the
   `doc_census` acceptance item above outright. Fixed; two new fixture cases
   added to `tests/tester_doc_census.py`.
2. `auditor_architecture_current` went RED on the commit immediately
   following the one that landed it, because the render's own do-not-edit
   header names "the producing commit" and a commit that adds/updates the
   file necessarily gets a new SHA the moment it's made -- the render a
   commit lands always names its parent, never itself. Fixed by excluding
   the header's commit/dirty line from the auditor's diff (masked, not
   ignored -- everything else in the file still compares in full);
   `tests/tester_architecture_current.py` proves the mask hides only that
   line, never a real content change. Walked twice across a real commit
   boundary to confirm the fix holds, not just asserted.
