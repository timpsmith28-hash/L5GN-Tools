# UAT — architecture census (DECISIONS 0030)

Walk against `docs/COWORK_BRIEF_architecture_census.md`'s acceptance checks.
Mark each `[G]`/`[W]`/`[H]` per 0031 as you go — `[G]` machine-verified by the
gate, `[W]` walked by hand and observed, `[H]` a human judgement call.

- [x] `[G]` `data/architecture.json` exists after a build and contains all six
  sections. *(Written as `data/architecture_census.json` — `architecture.json`
  bare would collide with nothing else in `data/`, but the scanner's own
  `NAME` is `architecture_census` and every other estate-level scanner writes
  `data/<NAME>.json`; keeping that convention was worth more than matching
  the brief's shorthand filename literally. Confirmed: `python run.py
  architecture_census` writes it, and it parses with all six section keys —
  `scanners`, `gate`, `routes`, `write_targets`, `schema`,
  `dependency_wall` — present.)*
- [x] `[W]` **Two consecutive runs produce identical output.** Ran twice by
  hand: `python3 -c "from l5gntools.scanners import architecture_census as
  ac; from l5gntools.common import TOOLKIT_ROOT; import json;
  print(json.dumps(ac.census(TOOLKIT_ROOT))==json.dumps(ac.census(TOOLKIT_ROOT)))"`
  → `True`. Also asserted in the gate (`tester_architecture_census`).
- [x] `[G]` **No absolute path appears anywhere** in the JSON or the rendered
  markdown. Checked by the gate over the full JSON payload (route paths
  under `/api/...` are the one legitimate `/`-leading string and are
  excluded as URLs, not filesystem paths); spot-checked the rendered
  markdown by hand for `TOOLKIT_ROOT`'s own string and any `/tmp` or `C:\`
  fragment — none found.
- [x] `[G]` An unparseable module is **named as unparsed**, not silently
  absent. Gate-tested with a planted syntax-error fixture file; also
  confirmed the same fixture file never appears in `write_targets` reading
  as "no writes."
- [x] `[W]` `docs/_architecture_shape.md` renders, carries the do-not-edit
  header and the producing commit, and reads as true. Read section by
  section against the live tree by hand.
- [x] `[W]` **It reproduces A4** — the endpoint's write set excludes
  `review_queue`. Section 4 of the rendered doc: `chronicler/review/core.py`
  writes `{projects, review_rulings, threads}`, zero unresolved lines,
  `review_queue` absent.
- [x] `[W]` **It reproduces A12** — `render_log` present in frozen, absent
  from `schema.sql`. Section 5's delta: `only in schema_frozen.sql:
  meta, path_scan_log, render_log`.
- [x] `[W]` **The gate refuses a stale render.** Edited one line of
  `docs/_architecture_shape.md` by hand, ran `verify.py` — RED,
  `auditor_architecture_current` printed a unified diff and the path to a
  freshly regenerated copy. Restored the file, ran `verify.py` again — GREEN.
  Separately: deleted the committed file entirely and confirmed a distinct
  named failure ("does not exist"), then restored it.
- [x] `[G]` `doc_census` counts `_architecture_shape.md` as **generated**,
  not **authored**. Was `authored` on the unmodified tree (a real gap in
  `classify_provenance`, fixed as part of this round — see the report);
  confirmed `generated` after the fix, both directly
  (`doc_census.classify_provenance("docs/_architecture_shape.md")`) and via
  the gate (`tester_doc_census`, two new fixture cases).
- [x] `[H]` `ARCHITECTURE.md` is unchanged by this round. `git diff` against
  `docs/ARCHITECTURE.md` for this round's changes is empty — confirmed by
  inspection; the brief's Task 3 acceptance list also required this and it
  was never touched.

All ten items ready to walk; walked once during the build itself as each
piece landed, then re-walked start to finish against the final tree before
this report was written. Stamped results in
`docs/UAT_architecture_census_results.md`.
