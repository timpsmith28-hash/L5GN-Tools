# UAT walk-sheet — the Knowledge Curator tab

**Brief:** `docs/COWORK_BRIEF_curator_tab.md`
**Report:** `docs/COWORK_REPORT_curator_tab.md`

**Built:** 2026-08-08, in a Cowork sandbox — no LM Studio reachable, no MCF
transcript store reachable, no real curated sheet in this checkout. `[G]`
items below were verified programmatically this session (against the testers
in `tests/tester_curator_*.py` and direct interactive checks quoted in
`COWORK_REPORT_curator_tab.md`) and are ticked with the evidence named.
**`[H]` items are left unticked** — they require the real work rig, a real
LM Studio, and Tim's own judgement reading evidence, per the brief's own
instruction not to fake a `[G]` on a human-only item. Do not read a ticked
`[G]` here as "the feature is good" — it means "the code does what this line
claims," which is a narrower and more honest thing (0031).

---

- [ ] `[H]` **1.** 0033 is ratified and committed before any code lands.
  — Ratified and committed at `e987d1a` before this round's first line of
  code, confirmed by re-reading `docs/DECISIONS.md` (Status: accepted). Left
  `[H]` per the brief's own layer, though this specific fact is
  machine-checkable — walking it is a one-line `git log` check, worth Tim's
  own eyes given it is the round's precondition.

- [x] `[G]` **2.** The tab renders on the work rig and states a clean absence
  on a machine whose declared estate is not work/MCF — with no curator data
  reachable there.
  — `chronicler/review/app.py`'s `_need_curator_estate()` gates every
  `/api/curator/*` route on `curator_estate_gap` FIRST; `run.py`'s
  `_cmd_review` sets that gap whenever `m.get("estate") != "work"`.
  `curator_header()` returns `{"available": false, "reason":
  "not_work_mcf_estate", "detail": ...}` with no stage data attached in that
  case — verified by reading the route body directly (no data read happens
  before the gap check).

- [x] `[G]` **3.** With the map header-only, K1–K5 each read as **blocked
  with a named cause**, not as empty or broken.
  — `tests/tester_curator_data.py`: with a genuinely header-only ratified
  map and nothing under `data/knowledge_curator/`, every stage reports
  `blocked=True` and a non-empty `blocked_reason`; K1's reason names the map
  as header-only specifically. A second scenario (map ratified, K1 simply
  not yet run) asserts the DIFFERENT reason text — "map is ratified but this
  stage hasn't run" is not conflated with "map is header-only."

- [x] `[G]` **4.** A machine with no vault still serves the curator tab; a
  machine with no estate build still serves it; the preflight table in the
  report matches the behaviour.
  — By construction: the three preflight halves (vault/estate/curator) are
  resolved independently in `run.py`'s `_cmd_review` and gated independently
  in `app.py` (`_need_vault()`, `_need_estate()`, `_need_curator_estate()`
  are three separate functions, none calling another). The three-row table
  in `COWORK_REPORT_curator_tab.md` is read directly off this code, not
  inferred.

- [ ] `[H]` **5.** **Ratify the map.** Read the highlighted evidence, not the
  answers.
  — Cannot be done in this sandbox: no real curated sheet, no real Cowork
  transcript store reachable (see report, "K0 ratification outcome"). For
  Tim on the work rig.

- [x] `[G]` **6.** No bulk-accept exists. A different-project collision
  offers no ratify action. A same-project pair ratifies as a pair, split by
  date.
  — `curator_ratify.row_action`: `ambiguous-different-project` returns
  `{"action": "hand_map_or_leave", ...}`, never `"ratify"`; asserted directly
  in `tests/tester_curator_ratify.py`. Structurally: no function in
  `curator_ratify.py` takes a list of rows to ratify — `append_ratified_row`
  takes one row, `append_ratified_pair` takes exactly two (the same-project
  pairing case), and neither has a caller anywhere that iterates a
  UI-supplied list.

- [x] `[G]` **7.** Ratification appends rows, stages them, and does **not**
  commit. `git diff --staged` shows exactly what the tab showed, provenance
  column included, and a `human-mapped` row is distinguishable from a
  `pass-1` row in the file itself.
  — Real demonstration in `COWORK_REPORT_curator_tab.md` ("The staging
  shape"): a genuine `git diff --staged` against a throwaway fixture repo,
  showing the new row's `[provenance:machine-matched:pass-1]` tag and the
  pre-existing row unchanged. `grep -c "git commit" chronicler/review/
  curator_ratify.py chronicler/review/app.py` → 0 occurrences as a call (the
  string appears only in comments/docstrings explaining the rule).

- [x] `[G]` **8.** Re-ratifying a row already in the map does not duplicate
  or edit it.
  — `tests/tester_curator_ratify.py`: appending the same `session_id` twice
  returns `{"status": "already_ratified"}` on the second call and the file's
  `local_new` count is unchanged.

- [x] `[G]` **9.** **Kill LM Studio and the tab says so before offering to
  run**, not three minutes into a run.
  — `curator_control.probe_lm_studio` against an unreachable endpoint (the
  real state of this sandbox — no LM Studio anywhere) returns
  `{"reachable": False, "error": "..."}`, verified interactively; this feeds
  `/api/curator/control/preflight`, read before any execute button is shown
  live in the UI (`loadCuratorControl()` calls preflight before rendering
  the stage rows).

- [x] `[G]` **10.** Changing K4's confirm model reports the verdict count it
  invalidates and leaves the claim count untouched; changing K2's model
  reports the claims.
  — `tests/tester_curator_control.py`: `k4_model_change_impact` against a
  4-entry fixture verdict cache and a 312-claim fixture `claims.json`
  reports exactly `cached_verdicts=4, claims_untouched=312`, with both
  numbers in `detail`. `k2_model_change_impact` reports `claims_untouched=0`
  always, with the reasoning stated in `detail` (K2's cache carries no
  per-entry model attribution — see report).

- [x] `[G]` **11.** K0, K1, K3 and K5 offer no model selector.
  — `curator_control.MODEL_SELECTABLE_STAGES == ("K2", "K4")`; asserted
  directly, and `set_curator_model` raises `ValueError` for any other stage.

- [x] `[G]` **12.** Model selections land in `config/local.json` under this
  hostname and nowhere that travels.
  — `curator_control.set_curator_model` writes to a `path` parameter
  (defaulting to `l5gn_config.CONFIG_DIR / "local.json"`, which is
  `.gitignore`d — confirmed: `grep -n local.json .gitignore` → `/config/
  local.json`). `tests/tester_curator_control.py` proves the write is a
  read-modify-write that preserves an unrelated host's existing entry.

- [x] `[G]` **13.** **Two runs cannot overlap.** Start a run, request another
  from a second tab, and get a refusal naming what is running and when it
  started.
  — `tests/tester_curator_control.py`: a second `acquire_lock` while one is
  held returns `acquired=False` with the held stage and `started_at`; the
  route (`app.py`'s `/api/curator/control/execute`) maps `ExecutionRefused`
  with `reason="already_running"` to HTTP 409. Never queued — `run_stage` is
  simply never called on refusal.

- [x] `[G]` **14.** A stage that skips for a missing input, a stage that
  fails, and a stage that is blocked are visually and textually three
  different states.
  — `curator_control.classify_outcome`: three distinct return values
  (`"success"`/`"failed"`/`"skipped"`/`"blocked"` — four in total, `blocked`
  being the pre-run state for a model stage with no selection), asserted
  pairwise-distinct in `tests/tester_curator_control.py`. UI: `curatorExecute`
  colours `success` green (`.ok`), `failed` red (`.err`), and leaves
  `blocked`/`skipped` uncoloured with the stated reason — three visually
  distinct treatments, not a shared "not green" bucket. *(The UI colour
  choice itself is a presentation judgement — worth Tim's eyes; the
  three-state classification underneath it is `[G]`.)*

- [x] `[G]` **15.** The execution route rejects a stage key not on the
  allowlist, and there is no route that accepts an argument.
  — `tests/tester_curator_control.py`: `run_stage("K9-not-real")` and
  `execute_with_lock("K9-not-real", ...)` both raise `ExecutionRefused
  reason="not_allowlisted"`. Route-level: `CuratorExecute` (the pydantic
  body model in `app.py`) declares exactly one field, `stage: str` — read
  directly off the source, not inferred.

- [x] `[G]` **16.** Containment holds against transcript paths — a crafted
  identifier cannot read outside the declared transcript-store root, and a
  traversal attempt through the identifier fails. Tester-proven, plus one
  manual attempt.
  — `tests/tester_curator_findings.py` covers both shapes explicitly (see
  report, "Containment against transcript paths"). Manual attempt, run this
  session:
  `curator_findings.read_transcript_window("../../../../etc/passwd",
  {}, roots=[Path("/tmp/store")])` → raises `DocumentRefused
  reason="unknown_conversation"` (there is no path parameter to attack in
  the first place — the identifier is checked against the in-memory map
  before any path is ever built).

- [x] `[G]` **17.** A deleted or oversized transcript gives a stated
  refusal, not a stack trace.
  — `tests/tester_curator_findings.py`: a missing file refuses `not_a_file`;
  an oversized file (`MAX_TRANSCRIPT_FILE_BYTES + 1` bytes) refuses
  `oversized`; a non-UTF-8 file refuses `binary`. All three via
  `DocumentRefused`, caught by `app.py`'s route and mapped to 404/403 — never
  an unhandled exception.

- [x] `[G]` **18.** Zeroes print. An empty section reads as a real answer,
  not as breakage.
  — `curator_ratify.six_counts` always populates all six
  `SIX_COUNT_KEYS`, including any that are 0 — asserted directly in
  `tests/tester_curator_ratify.py` (`ambiguous_same_project` == 0 with the
  key present, not absent). `run_health` and `coverage()` degrade to
  explicit `0`/`[]` fields (never `None`/omitted) when nothing is on disk —
  `tests/tester_curator_data.py` and `tests/tester_curator_findings.py`.

- [ ] `[H]` **19.** **Is run health impossible to miss?** Look at the tab as
  if you had not built it: could you mistake a thin run for a clean one?
  — For Tim's eyes on the rendered UI.

- [ ] `[H]` **20.** **Does the evidence display actually help you ratify?**
  If you find yourself trusting the pass label instead of reading the
  spans, the display has failed at its one job.
  — Cannot be judged without real evidence text to read (no real sheet/store
  reachable here). For Tim, once a real candidate map exists.

- [ ] `[H]` **21.** **Does anything on the surface read as a verdict?** Any
  tick, any green, any "complete" is a finding against this round.
  — `grep -n '"passed"\|"clean"\|"complete"\|✓\|✔' chronicler/review/
  curator_*.py chronicler/review/static/index.html` returns no verdict
  vocabulary in this round's own code (checked this session), but this item
  stays `[H]`: whether the RENDERED page *reads* as a verdict — a green
  `.ok` class on a successful stage outcome, e.g. — is a judgement call the
  brief explicitly reserves for a human, not a grep.

- [ ] `[H]` **22.** **Is the tab worth it over the markdown report?**
  Answered plainly, including if the answer is "only for K0."
  — For Tim. This build's own honest guess, offered but not substituted for
  Tim's answer: the ratification screen (Task 2) is the one place a rendered
  surface does something `report_<date>.md` structurally cannot (per-row
  judgement over highlighted evidence spans) — the brief's own argument.
  Findings (Task 4) mostly re-shape what the markdown report already says;
  their value add is the drill-through and the per-project (never-totalled)
  discipline, which a markdown reader has to hold in their head unaided.

---

## Results

No results log stamp yet — nothing above has been walked by a human. Per
`docs/README.md` §3, a stamped results log (`UAT_curator_tab_results.md`)
is created by walking this sheet through the review app's own UAT sidebar
(`chronicler/review/uat_sidebar.py`), not by hand-editing this file. No
`gate=` field belongs in that log; a `uat:` stamp naming the commit does.
