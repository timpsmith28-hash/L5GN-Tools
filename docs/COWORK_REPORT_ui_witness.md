<!-- gate-frozen: commit=69d1112 -->
# Report — the third check layer: rendered state, deterministically

**Brief:** `docs/COWORK_BRIEF_ui_witness.md`
**Walk-sheet:** `docs/UAT_ui_witness.md`
**Ratification:** DECISIONS 0031 (2026-08-03), read in full before any code —
a witness asserts rendered/observed state, emits findings never a verdict,
and never gates a commit. The name **witness** is settled per `docs/README.md`
§3's *testimony*.

---

## Task 1 — the assignment rule, applied to both live sheets

The rule from the brief, applied mechanically to every item on
`docs/UAT_local_deck_docs_and_time.md` (43 items) and `docs/UAT_uat_sidebar.md`
(18 items):

| question | layer |
|---|---|
| Assertable without a running surface? | **gate** |
| Needs a rendered surface, deterministic expected state? | **witness** |
| Needs a human to say "yes, that's what I wanted"? | **walk-sheet** |

| sheet | gate | witness | human | unplaceable |
|---|---|---|---|---|
| `UAT_local_deck_docs_and_time.md` | 12 | 29 | 1 | 1 |
| `UAT_uat_sidebar.md` | 6 | 11 | 1 | 0 |
| **combined** | **18** | **40** | **2** | **1** |

**66% of what was being walked by hand (40/61 real checks) was never human
work.** Human judgement survives on exactly two items across both sheets:

- `UAT_local_deck_docs_and_time.md` B2 — search ranking. *"Does it surface
  the right document?"* has no computable expected answer; the brief already
  names this pattern explicitly.
- `UAT_uat_sidebar.md` B2 — the sidebar's own judgement item, matching the
  brief's explicit "not B2" for Task 4.

**Gate items** (18 total) are checks that never needed a browser at all:
path-traversal / forged-id / route-signature responses (C1–C4 on the local
deck sheet), the no-vault / no-estate startup banner and process exit codes
(D1, D4, D6), filesystem/git persistence checks (F1, F3–F5), and — on the
sidebar sheet — the stamp/refuse-vs-append/staging/git checks (C2–C5, E1, E2)
that `tests.tester_uat_sidebar`'s `TestClient` coverage already exercises,
confirming the brief's own claim rather than re-deriving it.

**One unplaceable item, reported rather than forced:** `UAT_local_deck_docs_and_time.md`
F2 ("browse several documents, run several searches, open the Time tab") is a
setup action for F3, not an independent check — it has no computable expected
state of its own. It stays unmarked on the sheet with an inline note, and
`build_results_body` (Task 6) treats any unmarked item as defaulting to the
Human ruling section on emit, rather than silently dropping it, in case it is
ever given a verdict through the sidebar.

**Two items classed witness against the sheet's own "matches your memory"
framing:** G2 and G7 on the local-deck sheet invite a human "does this match
what you remember" read, but the actual assertion — project timeline order,
delta-panel claims — is checkable against `git log` directly. Classed witness
on the mechanical rule, not the framing, and confirmed with Tim before Task 2
proceeded.

No item on either sheet hit the "rule cannot place an existing check" stop
condition, once F2 was treated as a non-check rather than forced into a
category.

---

## Task 2 — the template carries the layer

Both live sheets now carry `[G]`/`[W]`/`[H]` markers in place, per the
classification above:

```
- [ ] [G] **C1.** In the browser, hand-edit the URL to ...
- [ ] [W] **B4.** A hit from a `knowledge` document has a green left edge ...
- [ ] [H] **B2.** **Does it surface the right document?** Judge this honestly.
```

`chronicler/review/uat_sidebar.py`'s `_ITEM` regex now captures an optional
`(?:\[(?P<layer>[GWH])\]\s*)?` group between the checkbox and the bold id, so
the sidebar's own sheet parser (and therefore the board and any future
counting) can read the marker without a second implementation.

**Board/sidebar marker-count surfacing:** recommend yes, in a follow-up round
— a card reading *"12 items, 9 of them [G]"* is exactly the queue-shrinkage
signal the brief names, and `docs_board.py`'s `_count_checkboxes` is the
natural place to add a marker tally alongside the existing done/open count.
Not built this round: Task 2 asked only that the template carry the marker
and that a mis-marked `[G]` surface as a finding, which the emitted-log split
in Task 6 already produces (an item marked `[G]`/`[W]` with no matching
witness observation prints `[no witness observation]` inline rather than
disappearing).

---

## Task 3 — the harness, fixtures only

`tests/witness/` — new package, never on `verify.py`'s `AUDITORS`/`TESTERS`
lists and never imported by anything that is:

- **`schema.py`** — `Observation` (`id`, `outcome`, `detail`) and `WitnessRun`
  dataclasses. `outcome` is validated against `("matched", "diverged",
  "error")` in `__post_init__`; there is no field anywhere in the shape that
  can spell "passed". `WitnessRun.write()` targets `data/witness/<sheet>.json`
  only.
- **`harness.py`** — `fixture_server(fixture_root)`, a context manager that
  boots the real `chronicler.review.app` FastAPI app on a free loopback port
  via `uvicorn.Server` in a background thread, against `fixture_root`. It
  works by patching `chronicler.review.estate_data.REPO_ROOT` for the
  duration: the UAT routes (`/api/uat/sheet`, `/api/uat/emit` in `app.py`)
  import `REPO_ROOT` fresh from the module on every request rather than
  closing over it at app-creation time, so this redirects the whole UAT
  surface at a fixture tree with **no production code changes** for a detail
  only the witness needs. Restored on exit, including on a crash.
- **`fixtures/uat_sidebar/`** — a fixture `docs/UAT_wsample.md` (four `[W]`
  items) and a pre-existing `UAT_wsample_results.md` (one prior entry, for
  the already-recorded-badge / resume checks). Verified live in this round:
  `fixture_server` boots against it and `/api/uat/sheet?stem=wsample` returns
  the expected sections, layer markers and `prior_entries` — confirmed with a
  smoke request in this session (see Verification, below).

**No new extra.** Reused `[scrape]` — its only dependency is `playwright`
itself, which is exactly what the harness needs. Nothing else the harness
imports (`uvicorn`, `fastapi`) is new; both already ship under `[review]`,
which the review server itself requires to run at all, fixture or not.

---

## Task 4 — first suite: the sidebar's own DOM half

`tests/witness/witness_uat_sidebar.py` ports exactly the items the build
thread named as browser-only:

| item | check | outcome id |
|---|---|---|
| B1 (UI half) | multi-line paste survives the textarea round-trip | `B1` |
| B3 | deferred + empty evidence → refused, item flagged, message shown | `B3` |
| B4 | same, for blocked | `B4` |
| B6 | "already recorded" badge renders on the right item | `B6` |
| B7 | Resume banner exists and populates a prior verdict | `B7` |

**B1's backend half** (does the emitted file carry the pasted text verbatim)
is left to `tests.tester_uat_sidebar`, which already asserts it via
`TestClient` — the witness suite only proves the DOM round-trip into the
in-memory form state, which is the half nothing else can see.

**Explicitly not B2.** No selector in this suite reads or grades prose.

**Not run end-to-end in this session** — see Verification.

**Sidebar sheet shrinkage after this round:** of the sidebar's own 18 items,
6 are now gate-covered (never walked at all — already-tester-proven), 11 are
witness-covered (4 executed by this suite: B1/B3/B4/B6/B7 overlapping across
those ids — the remaining witness items, A1/A2/B5/C1/D1/D2, are candidates
for a second suite, not built this round since Task 4 scoped strictly to the
build thread's named browser-only list), and 1 (B2) is genuinely Tim's. The
walk-sheet itself now shows this split via its `[G]`/`[W]`/`[H]` markers —
the acceptance argument the brief asks for.

---

## Task 5 — where it runs, and who starts it

Per `docs/investigation/2026-08-02_knight-roles_claude_2-response.md` §4,
**the Shadow never says green** — it runs outside the pre-commit budget,
emits a findings ledger, and is explicitly the class this witness belongs to:
deterministic, non-gating, findings-only. The recommendation holds: **the
Shadow schedules the witness; the witness runs where a surface can run.**

That surface is not currently the knight. Per
`docs/investigation/2026-08-02_knight-session_claude_2-response.md` §N10, the
knight's `local.json` never got the toolkit added as a scanned root — its
docs board reports `0 authored documents`, a one-line config gap, not a code
gap. Until that lands, a witness scheduled on the knight would either run
against fixtures only (which does not need the knight's own estate data at
all — the fixture tree in this round is self-contained) or find no live
surface to check anything beyond fixtures against. **Recommendation: the
Shadow can schedule the witness today** because this round's suite is
fixture-only by construction (Task 3's constraint) and needs no estate data
from any machine; extending the witness to assert against *rendered* live
content (as opposed to fixture content) should wait for N10's one-line fix,
the same way any live-estate Shadow check would.

**Where findings land:** `data/witness/<sheet>.json`, cited (never
duplicated) into the sheet's results log — see Task 6. 0022's run ledger
remains the intended long-term home once built; this round's schema is
already shaped as one row per run with `ran_at`/`host`/`commit`/`fixture`, so
that migration is a move, not a rewrite, per the brief's own instruction.

---

## Task 6 — the results log gains a citation, not a stamp

`chronicler/review/uat_sidebar.py` changes:

- **`_ITEM` regex** now parses an optional `[G]`/`[W]`/`[H]` layer marker per
  item (Task 2's syntax).
- **`witness_citation_line(root, stem, current_commit)`** reads
  `data/witness/<stem>.json` if present and returns a visible prose line (not
  an HTML comment) naming the artefact path, fixture, commit and `ran_at`,
  plus a per-item outcome map. If the artefact is **missing**, the line says
  so explicitly — *"No witness artefact found at `data/witness/<stem>.json`
  for this sheet"* — rather than the section being silently blank. If the
  artefact is **stale** (its `commit` differs from the current walk's), the
  line adds a visible `**Stale**` note rather than presenting it as current.
- **`build_results_body`** now branches on whether any item on the sheet
  carries a layer marker at all:
  - **No markers (legacy sheets)** — unchanged flat-by-section shape. Every
    existing results log and every sheet not yet touched by Task 2 keeps
    working exactly as before; `tests.tester_uat_sidebar`'s original fixture
    (no markers) still exercises this path and still passes.
  - **Markers present** — splits into `## Machine-verified` (`[G]`/`[W]`
    items, plus any unmarked item as a safety net so an entered verdict is
    never silently dropped for lack of a marker) and `## Human ruling`
    (`[H]` items only). Machine-verified items print the witness's own
    `[matched]`/`[diverged]`/`[error]` outcome inline, sourced from the
    citation — **no `[EVIDENCE]`/`[DEFERRED]`/... human verdict tag appears
    for them at all**, even if a verdict was entered in the UI for that item.
    Human ruling items keep the original `[EVIDENCE]`/`[DEFERRED]`/`[BLOCKED]`/
    `[N/A]` tags exactly as before.
- **No auditor change.** `auditors/auditor_uat_stamp.py` is untouched —
  the citation lives in the body, below the stamp comment, exactly the
  distinction the brief draws between a stamp (provenance of *this*
  document) and a citation (points at a run elsewhere).
- **The sidebar stays the only writer.** The witness never writes into a
  results log; it writes its own JSON, which the sidebar reads at emit time.

`tests/tester_uat_sidebar.py` gained coverage for: the split appearing when
markers are present, honest-absence text when no witness artefact exists,
the cited `[matched]` outcome appearing inline once an artefact is written,
the citation living outside the stamp's HTML comment, and the legacy flat
shape surviving unchanged for an unmarked sheet. `python verify.py` is
**GREEN** with this coverage included (see Verification).

---

## Verification

- `python verify.py` → **GREEN**, 6 auditors + 55 testers, unchanged in
  count — the new coverage lives inside `tests.tester_uat_sidebar`'s existing
  `run()`, not a new module, and `tests/witness/` stays off both
  `AUDITORS`/`TESTERS`, confirmed by inspection of `verify.py`'s lists, which
  are explicit, not a glob.
- **Fixture harness, live-checked in this session:** installed `[review]`
  and `playwright` in the sandbox, then ran `fixture_server` against
  `tests/witness/fixtures/uat_sidebar/` and requested
  `/api/uat/sheet?stem=wsample` directly. Confirmed: both sections parse, `W1`
  carries `layer="W"`, `results_exists=True`, and `prior_entries` recovers
  `W4`'s prior `walked` verdict from the fixture's results log — the resume
  path Task 4's suite depends on works end-to-end at the HTTP layer.
- **Not verified end-to-end: the Playwright browser itself.** This sandbox's
  network allowlist blocks the Chromium download
  (`playwright install chromium` → `403 Connection blocked by network
  allowlist`), and there is no `sudo` to install the OS-level deps `--with-deps`
  needs either. `witness_uat_sidebar.py` compiles cleanly and its selectors
  were written directly against `chronicler/review/static/index.html`'s
  actual markup (`.tab[data-pane="uat"]`, `#uat-stem`, `#uat-pick button.primary`,
  `.uat-item[data-id="..."]`, `.verr`, the `.badge:has-text(...)` text, the
  Resume button text) rather than guessed — but its first real run needs to
  happen on a machine that already has Playwright's browser installed
  (`python -m playwright install chromium`, one-time). **This is the first
  thing to run before trusting the suite's output.**
- All new/modified files compile (`py_compile`) clean.

---

## Files touched

- `chronicler/review/uat_sidebar.py` — layer-marker parsing, citation,
  machine/human split in `build_results_body`.
- `tests/tester_uat_sidebar.py` — coverage for the above.
- `tests/witness/` — new package: `__init__.py`, `schema.py`, `harness.py`,
  `witness_uat_sidebar.py`, `run_witness.py`,
  `fixtures/uat_sidebar/docs/UAT_wsample.md`,
  `fixtures/uat_sidebar/docs/UAT_wsample_results.md`.
- `docs/UAT_local_deck_docs_and_time.md`, `docs/UAT_uat_sidebar.md` —
  `[G]`/`[W]`/`[H]` markers added in place; no items re-filed or moved.
- `docs/investigation/2026-08-02_knight-roles_claude_2-response.md` —
  acknowledgement line appended (§4's prediction, first instance).

## Not done this round, named rather than silently skipped

- Board/sidebar surfacing of per-card marker counts (Task 2's open question)
  — recommended, not built.
- A second witness suite for the sidebar's remaining `[W]` items
  (A1/A2/B5/C1/D1/D2) — Task 4 scoped strictly to the build thread's named
  browser-only list.
- Re-filing any walk-sheet item into a different file — explicitly out of
  scope per the brief.
- Running `witness_uat_sidebar.py` against a real Chromium — blocked by this
  sandbox's network policy; first run belongs on a dev machine.
