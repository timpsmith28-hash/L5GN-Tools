<!-- uat: commit=174e57e dirty=false host=LucasGoonPC walked=2026-08-15 -->

> **ARCHIVED** 2026-08-17 · completed pair (results) · Sheet:
> `archive/UAT_ui_witness.md`
> Superseded by nothing. Original purpose: the record of the 2026-08-15..17
> walk — 19 of 19 items, with ten carried findings.
> Findings 5, 7 and 10 were closed by the 2026-08-17 correctness sweep: the
> `[G]`/`[W]`/`[H]` marker now renders as a badge, and the checkbox parser
> counts the backticked form (`UAT_knowledge_curator.md` and
> `UAT_project_wizard.md` read 22 and 16 open where they read 0). Finding 8
> closed as **no defect** — see this pair's report stamp for why. The remaining
> findings, including finding 9's unexplained `200 OK`, were live when this was
> written and **their disposition is not recorded here.**

# UAT results — the third check layer (`COWORK_BRIEF_ui_witness.md`)

Sheet: `docs/UAT_ui_witness.md`. Pair:
`docs/COWORK_BRIEF_ui_witness.md` + `docs/COWORK_REPORT_ui_witness.md`.

**Walked:** 2026-08-15 on `LucasGoonPC`, against `174e57e`.
**Gate:** `python verify.py` GREEN on the clean tree, and again via the
pre-commit hook on every commit in the `13fef34..174e57e` series.

**All 19 items are walked.** The sheet is complete.

**Walked is not passed.** `A1` was walked and **did not pass** — its counts do
not reproduce. It is ticked because it was looked at, and its verdict is a
finding. `D1` passed against the file and could not be walked on the surface
the item names. Both are recorded as what they are rather than rounded to the
nearest tick.

The sheet carries no `[G]`/`[W]`/`[H]` markers, so this log keeps the flat
by-section shape rather than the Machine-verified / Human-ruling split — which
is itself the condition `F1` checks, and `F1` passed.

---

## A — the assignment rule and the counts

- [x] **A1.** **Walked — FINDING, does not reproduce.** The assignment rule
  places every item without argument, and the item total is right: 61 across
  the two sheets. **The split is not.** Counted directly off the marked sheets:

  | | `local_deck_docs_and_time` | `uat_sidebar` | total | report Task 1 |
  |---|---|---|---|---|
  | `[G]` gate | 11 | 6 | **17** | 18 |
  | `[W]` witness | 30 | 11 | **41** | 40 |
  | `[H]` human | 1 | 1 | 2 | 2 |
  | unmarked | 1 | 0 | 1 | 1 |
  | items | 43 | 18 | 61 | 61 |

  One item carries `[W]` where Task 1 counted `[G]`. The totals agreeing while
  the split does not is the signature of a re-marked item rather than a
  miscount of the whole — and `docs/UAT_local_deck_docs_and_time.md` was
  rewritten during this round (committed at `a2aa1ec`), so the likeliest
  explanation is that the sheet moved after the report's count was taken.

  **Not resolved here.** Either the report's count is stale, or an item is
  mis-marked. Which one it is decides whether anything needs fixing, and that
  needs the round's author. Recorded, not guessed.

- [x] **A2.** **Passed, with a caveat on its own wording.** The check body is
  *"confirm the markers do not break item parsing (ids, text, sheet notes all
  still show)"* — and they do: ids, item text and sheet notes all render
  correctly on both marked sheets.

  The item's *title* says the sheets "render their `[G]`/`[W]`/`[H]` markers
  correctly", which is not literally true — the sidebar does not display the
  markers at all (finding 7). Passed against what the check asks, flagged
  against what its title implies.

## B — a mis-marked item shows up as a finding

- [x] **B1.** **Passed — and the extended case found something.** Walked on a
  throwaway copy, `docs/UAT_probe.md`, so no real sheet was mutated.

  **The literal check.** `C2` was mis-marked `[G]` → `[W]`. Screenshots before
  and after the swap are indistinguishable: id, text and sheet note all render,
  no error, nothing complains. The marker is read and not validated, exactly as
  the item predicts. On emit, `C2` landed under `## Machine-verified` — which is
  where `[G]` would have put it too.

  **That flip is inert by construction.** `build_results_body` sorts
  `layer in ("G","W")` into Machine-verified and `layer in ("H", None)` into
  Human ruling. A `[G]`↔`[W]` mis-mark therefore cannot change the output at
  all. B1 passes, but it passes trivially.

  **The extended flip, `[H]` → `[W]`, is the one that bites** — see finding 10.


- [x] **B2.** **Passed in substance.** The emitted log for
  `docs/UAT_uat_sidebar_results.md` prints, inline, against two `[W]` items:

  ```
  - **C1** With B1/B2 given real verdicts, emit. Open the emitted
    [no witness observation] not present in the cited witness artefact for this item id

  - **C2** Check the stamp comment on the first line: `commit=` matches
    [no witness observation] not present in the cited witness artefact for this item id
  ```

  The finding surfaces inline and does **not** sit quietly as if walked, which
  is what the item asks for.

  **How it arose matters.** B2 as written follows B1 — give *the mis-marked
  item* a verdict and emit. No mis-mark was made; these two items are
  legitimately `[W]` and genuinely have no witness observation. The behaviour
  is therefore proven by a naturally occurring case rather than the constructed
  one. That is arguably stronger evidence, but it is not the same test. B1 was
  subsequently walked on its own terms (see above) and the constructed case was
  covered there.

## C — the witness suite itself

- [x] **C1.** **Passed.** `python -m tests.witness.run_witness uat_sidebar`
  wrote `data/witness/uat_sidebar.json`. Outcome values across the entire
  file are `{matched}` only — no `passed`, `ok` or `result` anywhere. Five
  observations returned:

  ```
  [ matched] B1: textarea round-trip of 3 pasted lines survived verbatim=True
  [ matched] B3: item=W2 flagged=True message_visible=True message="W2: 'deferred' requires a reason recorded in the evidence box -- the useful line in every existing log is the one saying why, not just that."
  [ matched] B4: item=W3 flagged=True message_visible=True message="W3: 'blocked' requires a reason recorded in the evidence box -- the useful line in every existing log is the one saying why, not just that."
  [ matched] B6: 'already recorded' badge present on W4=True
  [ matched] B7: resume_banner_present=True resumed_verdict_populated=True
  ```

- [x] **C2.** **Passed.** Run twice consecutively with nothing changed. Both
  runs reported identical outcomes for every one of the five item ids.

- [x] **C3.** **Passed** — and this is the item that proves the layer can
  fail. Line 182 of `chronicler/review/static/panes/uat.js`
  (`v.textContent = msg; v.style.display = "block";`) was commented out and the
  suite re-run:

  ```
  [ matched] B1: ... verbatim=True
  [diverged] B3: item=W2 flagged=True message_visible=False message=''
  [diverged] B4: item=W3 flagged=True message_visible=False message=''
  [ matched] B6: 'already recorded' badge present on W4=True
  [ matched] B7: resume_banner_present=True resumed_verdict_populated=True
  ```

  `flagged=True` survived (the item still takes its `.err` class) while
  `message_visible` flipped to `False`. B1, B6 and B7 stayed `matched`. The
  divergence isolated to the two observations that assert the message, and to
  nothing else. Line 182 was then restored and the suite re-run, returning to
  five `matched`.

  **Finding — the sheet's instruction is stale, not wrong.** C3 names
  `chronicler/review/static/index.html`'s `uatItemHtml`. The `unified_app`
  round moved `uatItemHtml` to `chronicler/review/static/panes/uat.js`; only
  the `.verr` CSS rule remains in `index.html` (line 265). The sheet is
  `gate-frozen: commit=69d1112`, which predates the split, so this is expected
  drift in a frozen document rather than a defect. Recorded so a cold reader is
  not sent to the wrong file.

  **Observation on the output format, not a failure.** The divergence names the
  *field* (`message_visible=False message=''`) but not the *expectation* — it
  does not carry what the message should have been. A reader of the diverged
  output alone can tell that something is absent, but needs a prior `matched`
  run to know what. Worth considering whether an observation should carry its
  expected value; not required by anything in this round.

- [x] **C4.** **Passed.** `python verify.py` GREEN, runtime unchanged.
  `grep -n witness verify.py` returns nothing — neither `AUDITORS` nor
  `TESTERS` names anything under `tests.witness`. No module `verify.py` imports
  reaches `tests.witness` transitively either: the only occurrence of the
  string anywhere outside `tests/witness/` is a **string literal** in
  `tests/tester_uat_sidebar.py:282` (`"fixture": "tests/witness/fixtures/x"`),
  which is fixture data, not an import.

- [x] **C5.** **Passed.** `docs/UAT_uat_sidebar.md` opened in a fresh session
  with `data/witness/uat_sidebar.json` present, carrying `matched` observations
  for **B1, B3, B4, B6, B7**. Every one of those five renders
  `— pick a verdict —` with an empty evidence box. Nothing is auto-ticked,
  nothing is pre-filled, nothing suggests a verdict.

  The clean separation is visible in one screen. **B1, B6 and B7** have witness
  observations and no prior results-log entry: they render entirely blank, with
  no badge. **B3 and B4** have witness observations *and* prior entries: they
  render an `already recorded: deferred` / `already recorded: blocked` badge —
  and still show `— pick a verdict —` with an empty evidence box.

  So prior state is *announced* without being *applied*, and the witness
  artefact does not reach the form at all. Pre-filling happens only on an
  explicit **Resume**, which reads the results log, never `data/witness/`.

- [x] **C6.** **Passed.** Run for real against a genuine Chromium (already
  present in `.venv`; no download needed). All five observations — `B1`, `B3`,
  `B4`, `B6`, `B7` — returned `matched` on an unmodified checkout.

  Worth noting: `COWORK_REPORT_ui_witness.md`'s Verification section flagged
  this as never run end-to-end, because the build sandbox's network policy
  blocked the browser download. It has now been run end-to-end.

- [x] **C7.** **Passed**, in the same run as C3 above — that break was
  performed against a real Chromium, not a simulation, so C3 and C7 close
  together rather than separately.

## D — the sidebar's own sheet is shorter

- [x] **D1.** **Passed against the sheet; not walkable on the surface the item
  names.** `docs/UAT_uat_sidebar.md` carries exactly **6 `[G]` / 11 `[W]` /
  1 `[H]` across 18 items**, and the single `[H]` is `B2` (line 58) — precisely
  as the item predicts. The human queue for that sheet is one item.

  **But the item says "re-open it in the sidebar" and "confirm 6 *read* `[G]`".
  The sidebar does not display the markers** (finding 7), so this was confirmed
  by counting the file, not by reading the rendered surface. The numbers are
  right; the check as written cannot be performed.

## E — the emitted log, and the citation

- [x] **E1.** **Passed.** `B2` was walked for real and emitted to
  `docs/UAT_uat_sidebar_results.md` as an appended walk section. In it,
  `## Machine-verified` sits **above** `## Human ruling`, and Human ruling
  contains **only `B2`** — the sheet's sole `[H]` item. Seven items sit under
  Machine-verified (`B1`, `B7`, `C1`, `C2`, `B3`, `B4`, `B6`).

- [x] **E2.** **Passed.** The citation is visible body text directly beneath the
  `## Machine-verified` heading, not inside the `<!-- uat: -->` stamp comment:

  > Machine-verified items below are cited from a witness run:
  > `data/witness/uat_sidebar.json`, fixture `tests/witness/fixtures/uat_sidebar`,
  > commit `174e57e`, ran 2026-08-15T11:08:51+01:00 on `LucasGoonPC`. Re-run the
  > witness at that commit against that fixture to re-derive these observations.

  Artefact path, fixture, commit and `ran_at` all present, plus host. It also
  states the re-derivation procedure, which the item does not require.

- [x] **E3.** **Passed.** The citation names commit `174e57e` and fixture
  `tests/witness/fixtures/uat_sidebar`. The suite was re-run twice at that
  commit against that fixture and returned the same five observations, all
  `matched`, with byte-identical detail strings.

  One caveat recorded for honesty: `174e57e` is `HEAD`, so "re-run at that
  commit" required no checkout. The citation has not been exercised against a
  commit that is no longer current — the harder case, and the one that would
  prove the citation survives time rather than merely being correct today.

- [x] **E4.** **Passed.** `[ OK ] auditor_uat_stamp` on every `verify.py` run
  this session. `git diff --stat 69d1112 HEAD -- auditors/auditor_uat_stamp.py`
  is **empty** — the file is untouched since `4d885f9`, which predates this
  round entirely.

- [x] **E5.** **Passed in substance, via the never-existed case.** The probe
  sheet has no `data/witness/probe.json`, and both appended sections render, as
  visible italic body text above the item list:

  > _No witness artefact found at `data/witness/probe.json` for this sheet. The
  > machine-verified section below has no witness observations to cite --
  > reported here, not silently omitted._

  A blank section that could be misread as "nothing to check" is exactly what
  does not happen, which is the item's requirement.

  **What was not exercised:** E5 as written says *delete*
  `data/witness/uat_sidebar.json` and re-emit. The deletion path was not run —
  the artefact for `uat_sidebar` is intact at `ran_at 2026-08-15T11:08:51`. The
  branch is almost certainly the same existence check, but "never existed" and
  "existed and was removed" are two states, and only one of them was walked.
- [x] **E6.** **Passed.**
  `grep -rn '"passed"\|"ok"\|"result"' data/witness/` returns nothing. The
  artefact's top-level keys are `sheet`, `commit`, `dirty`, `host`, `fixture`,
  `ran_at`, `items` — no verdict vocabulary at any level.

## F — a legacy sheet is unaffected

- [x] **F1.** **Passed.** Emitted against `docs/UAT_probe.md` with all 18
  markers stripped — unmarked *at emit time*, which is what the item requires.
  The first section of `docs/UAT_probe_results.md` keeps the original
  flat-by-section shape:

  ```
  ## C · emitting the stamped results log (Task 3)
    - **C5** ... [EVIDENCE] tested
  ## D · closing the loop with the board (Task 4)
    - **D1** ... [EVIDENCE] tested
  ```

  No `## Machine-verified`, no `## Human ruling`. The two later sections of the
  same file — emitted after markers were restored — *do* carry the split, so one
  file demonstrates both shapes and the boundary between them.

---

## Provenance note on the first run

The first witness run of this session was made against a dirty tree
(`commit=e9ba614 dirty=True`), before the harness itself was committed. That
artefact could not have satisfied `E3` — the citation named a commit at which
`tests/witness/` did not exist, because the whole harness was untracked. The
round's own `dirty` field is what surfaced it.

The commits at `13fef34..174e57e` landed the harness, and the suite was re-run
so the artefact cites a commit that actually contains it. **E1–E5 were
deliberately deferred until after that point**, rather than walked against a
citation that could not resolve.

## Carried findings

1. **The sheet's C3 path is stale post-`unified_app`** (see C3 above). Frozen
   document, expected drift, no action beyond this note.
2. **A diverged observation names the field, not the expectation** (see C3).
   Candidate improvement, not a defect.
3. **`auditor_uat_stamp`'s sibling is now cheap.** `docs/README.md` §4 leaves a
   stamp-resolving auditor as "a small auditor and a separate decision."
   `docs/investigation/2026-08-02_knight-roles_claude_2-response.md` now carries
   two well-formed `actioned:` lines with the same field layout and two
   resolvable anchors (`f5a14d2`, `a2aa1ec`) — a real fixture rather than a
   hypothetical one. Recorded as a candidate round.
4. **`StarletteDeprecationWarning` in `tester_review`** — *"Using `httpx` with
   `starlette.testclient` is deprecated; install `httpx2` instead."* Non-fatal,
   printed on every gate run. Not this round's business; logged so it is not
   rediscovered.

5. **The docs board has no representation for a partial walk.** On this log
   landing, `ui_witness` moved to **Walked** with `19 open / 0 done` and the
   `checkbox_evidence_in_results_log` flag — because open/done are counted from
   the walk-sheet, which is untouched, while the flag is raised from the results
   log. Both are correct by the board's own rules. But a walk done in blocks
   across a session (7 of 19 here) reads on the card as indistinguishable from
   one done in a single pass, and the column flips to Walked on the first block.

   Related and worse: `_count_checkboxes` matches only `- [ ]`, so a results log
   written in the post-0031 backticked `` - `[x]` `` form would have counted
   **zero done**, the flag would not have fired, and the card would have read
   *"Walked, 19/0, no flags"* — identical to an empty results log. This log uses
   the plain form deliberately to avoid that. `UAT_knowledge_curator.md` (22
   items) and `UAT_project_wizard.md` (16) currently read as `0 open / 0 done`
   on the board for exactly this reason, which is a confident zero on the
   surface used to decide what still needs walking.

   Both belong to a `docs_board` round, ratified as *"log it, fix next round"*
   on 2026-08-15. Recorded here because this log is the artefact that surfaced
   the second one.

   **Proposed shape, Tim 2026-08-15: a `walking` lane.** A fifth column between
   *Built, not walked* and *Walked*, entered when a results log exists **and**
   the sheet still has open items, left when nothing is open. It is derivable
   from exactly the two facts the board already reads — results-log existence
   and the open count — so it stores nothing and breaks none of the module's
   four rules. It also gives the `checkbox_evidence_in_results_log` flag a
   column to live in rather than a warning bolted onto a card that claims to be
   finished. Worth arguing in the round rather than assuming: whether *Walked*
   should then mean "zero open", which is a stronger claim than the board makes
   about anything today.

6. **The UAT sidebar echoes the caller's casing instead of the resolved
   filename.** Opening the sheet as `UI_Witness` produced a banner citing
   `docs/UAT_UI_Witness_results.md`; the file on disk is
   `docs/UAT_ui_witness_results.md`. `uat_sidebar.py:250` builds `results_rel`
   from the `stem` argument rather than from `rp`, the path it actually
   resolved and read (line 234).

   On Windows the read succeeds — NTFS is case-insensitive — so the surface
   displays a path that does not exist as written. On a case-sensitive
   filesystem the same input refuses at line 230 with *"No walk-sheet
   docs/UAT_UI_Witness.md in this repository"*, which is an honest refusal but
   a different answer to the same question on the same repository.

   This matters beyond cosmetics: `results_rel` is the path a citation would
   carry, and `E2` requires the citation to name the artefact. A citation built
   from what the caller typed is not provenance. **Fix is one line** — derive
   the displayed paths from the resolved `sp`/`rp`, not from `stem`.

7. **The layer marker is load-bearing and invisible.** `_ITEM` (line 67) parses
   the optional `[G]`/`[W]`/`[H]` marker, and `build_results_body` (line 360ff)
   uses it to decide whether an item lands under `## Machine-verified` or
   `## Human ruling` on emit. **`panes/uat.js` never renders it** — no
   occurrence of the marker anywhere in the pane.

   So the walker cannot see which layer an item belongs to on the surface where
   they do the walking. They cannot tell, without opening the raw markdown,
   whether an item is theirs to judge or the machine's to observe — which is
   the distinction 0031 exists to draw. `D1` is the item that exposes this: it
   asks Tim to *read* the marker split off the sidebar, and the sidebar does
   not show it.

   Small fix (a badge beside the existing `open` / `already recorded` chips),
   disproportionate value: it makes 0031's split visible at the point of work
   rather than only in the emitted artefact.

8. **`COWORK_REPORT_ui_witness.md` Task 1's assignment counts do not
   reproduce** — 17 gate / 41 witness against a claimed 18 / 40. See `A1`
   above for the full count and the two candidate explanations. Needs the
   round's author to say which; not resolvable from the artefacts alone.

9. **Unexplained: `GET /api/uat/sheet?stem=UAT_Sidebar` returned `200 OK`.**
   Observed in the server log this session. It should have been a `404`:
   `sheet_path` builds `docs/UAT_UAT_Sidebar.md`, no such file exists at any
   casing, and `app.py:484` maps `no_sheet` to 404 — which is exactly what the
   2026-08-03 walk recorded for `stem=UAT_repo_tier_producers`.

   Not reproducible from outside the rig, and not explained by Windows
   case-insensitivity (the constructed name has a doubled `UAT_` prefix that
   matches nothing on disk). **Recorded as an open question, not a verdict.**
   Re-test directly against the running server:

   ```
   curl -i "http://127.0.0.1:<port>/api/uat/sheet?stem=UAT_Sidebar"
   curl -i "http://127.0.0.1:<port>/api/uat/sheet?stem=Nonsense_Sheet"
   ```

   If the first returns 200 and the second 404, something is resolving the
   doubled prefix and that is worth understanding before it is relied on. If
   both 404, the log line was a stale artefact of an earlier build and this
   finding closes.

10. **An `[H]` → `[W]` mis-mark silently converts a human ruling into a machine
    verification, and the log then asserts no human judgement was required.**
    Found by extending `B1` past its stated flip.

    `build_results_body` sorts `layer in ("G","W")` into Machine-verified and
    `layer in ("H", None)` into Human ruling. `B1` tests `[G]`↔`[W]`, which
    cannot change anything. The consequential flip is across that boundary.

    Walked on `docs/UAT_probe.md` by marking `B2` — the sheet's only
    judgement-shaped item — as `[W]`. The emitted section reads:

    ```
    ## Machine-verified
    _No witness artefact found at `data/witness/probe.json` for this sheet..._

    - **B2** Pick one judgement-shaped item (a "does this feel right" call).
      [no witness observation] not present in the cited witness artefact for this item id

    ## Human ruling

    _No `[H]` items were recorded on this walk._
    ```

    Two things go wrong together, and the second is the serious one. The item
    is filed under machine verification, where it carries a witness citation
    and **no human verdict field**. And `## Human ruling` then states
    affirmatively that *no `[H]` items were recorded* — so the log does not
    merely misplace the judgement, it **asserts the absence of a judgement that
    was required**. A reader of that log has no way to tell a sheet needing no
    human ruling from one whose human ruling was mis-filed.

    The `[no witness observation]` line is the only thread back to the truth,
    and it reads as a gap in coverage rather than as a mis-classification.

    **Not a defect in this round's stated scope** — 0031's assignment rule is
    documented as read-and-not-validated, and `B1` says so. But the estate's
    own doctrine is *prefer "can't" to "shouldn't"* (INTENT §5), and this is a
    single-character edit that quietly removes a human from the loop. Candidate
    for the same round as finding 7: if the marker were rendered on the item,
    the mis-mark would be visible at the point of walking. One fix, both
    findings.
