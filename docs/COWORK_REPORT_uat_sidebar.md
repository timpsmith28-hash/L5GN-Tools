<!-- gate-frozen: commit=69d1112 -->
# Cowork report — the UAT sidebar

**Brief:** `docs/COWORK_BRIEF_uat_sidebar.md`. **Depends on:**
`docs/COWORK_BRIEF_docs_board.md`, built and walked first
(`docs/UAT_docs_board_results.md`, walked 2026-08-01) — confirmed before this
slice started. **Status:** built and gate-GREEN; walk-sheet is
`docs/UAT_uat_sidebar.md`.

**Base commit:** `b9fae8d`. **Gate:** `python verify.py` → **GREEN, 6
auditors + 55 testers** (+1: `tester_uat_sidebar`). **Nothing committed.**

---

## What this slice is

The *built, not walked* column's one real action: open a `UAT_<x>.md`
walk-sheet, record a verdict and its evidence per item, and emit a stamped
`docs/UAT_<x>_results.md`. It never computes a pass — the split the brief
insists on, and the same split `auditor_uat_stamp` already makes for the gate
as a whole (police provenance, never the verdict).

### Layout

| file | role |
|---|---|
| `chronicler/review/uat_sidebar.py` | stdlib-only: parse a sheet (Task 1), validate verdicts (Task 2), build and emit a stamped results log (Task 3). No server. |
| `chronicler/review/app.py` | two routes added: `GET /api/uat/sheet`, `POST /api/uat/emit`. Thin shells, no logic. |
| `chronicler/review/static/index.html` | one new tab, "UAT sidebar"; a "Walk it" button added to `built_not_walked` cards on the Docs board tab. |
| `tests/tester_uat_sidebar.py` | parsing, validation and emission against a fixture tree; containment against the real repo anchor; the loop-closing claim (Task 4) checked directly against `docs_board.board()`; routes end-to-end when the optional web extra is installed. |

`docs_board.py` itself is **untouched**. Task 4 ("the card advances by
itself") is true by construction: the column was already a function of
`docs/UAT_<x>_results.md` existing, and this slice's only effect on the
filesystem is to make that file exist. `tester_uat_sidebar` asserts this
directly rather than trusting the claim: it writes a fixture brief + report +
sheet, confirms the card starts `built_not_walked`, calls `emit_results_log`,
and confirms `docs_board.board()` — called fresh, on the same fixture root,
with no other code path touched — now reports the card as `walked`.

## Design decisions, and why

**In-progress state lives in a plain JS object in the browser tab, never
`localStorage`.** The brief requires that a lost session lose the notes —
`localStorage` would survive a reload and quietly violate that. Switching the
stem in the sidebar's input also clears the in-memory notes, on purpose:
"session-scoped" is scoped to the sheet you are looking at, not a carry-over
that could let one sheet's evidence bleed into another's emitted log.

**Verdict vocabulary is `walked` / `deferred` / `blocked` / `not_applicable`,
tagged `[EVIDENCE]` / `[DEFERRED]` / `[BLOCKED]` / `[N/A]` in the emitted
markdown** — the same tags `archive/UAT_cowork_run_2026-07-24_results.md`
already uses (that file's legend additionally has `[FIXTURE]`, for "proven by
its tester only, no real data to exercise it" — not a verdict a human chooses
here, so it is not in this module's vocabulary; nothing stops a human writing
it into the evidence prose if it applies).

**An item never given a verdict is simply absent from the emitted log**, not
recorded as anything. The brief's own working rule — "never compute a pass" —
extends to never inventing a verdict either; a partial walk emits a partial
log, and the "not walked, and why" section is populated only from items that
were actually given a non-`walked` verdict this session. Nothing here declares
an untouched item `not_applicable` on the walker's behalf.

**Pasted multi-line evidence is fenced verbatim** (a ` ``` ` block under the
item), never reflowed. Single-line evidence stays inline after the tag. This
was the concrete failure mode the brief called out: "every results log we
have is mostly pasted output," and a re-wrap or a paraphrase would be exactly
the kind of drift the uat stamp exists to stop happening to the *claim*,
applied here to the *evidence* instead.

**Appending never rewrites the original stamp.** `emit_results_log(...,
mode="append")` keeps the file's first line byte-for-byte and adds a new
`## Additional walk — <date>, <host> (<its own stamp>)` section below. This
mirrors the golden close-out's rule (`archive/UAT_cowork_run_2026-07-24_results.md`'s
stamp: "records addenda, and supersedes them and says so in-body" rather than
editing the original observation).

**The unticked-but-walked finding is shown generically, not by name.**
`sheet_view` computes `evidence_in_results_log` from the sheet's and results
log's checkbox counts — the same derivation `docs_board.py` already owns
(reused via `docs_board._count_checkboxes`, not reimplemented) — so it
applies to any stem with that shape, not a hardcoded pair. This matters
because of a finding below.

## What the board's walk had already invalidated, or settled before this slice started

The brief posed two open questions and said the board's walk would answer
them. In fact:

**Ratification scope (session vs. persisted) was never the board's walk to
rule on — DECISIONS 0028 already settled it**, before the board was even
built: "performed only on a per-pair ratification given in that session,
never in bulk and never inferred from a green gate." `UAT_docs_board_results.md`
confirms the board's own walk found Task 3/Task 4 (ratification, staging)
"deferred by instruction before any code was written" — the board's walk
neither exercised nor re-litigated 0028; it just recorded that the question
was untouched by that slice. This module follows 0028 directly rather than
inventing a second answer: emit is per-call, per-stem, and nothing here
persists a ratification across sessions or infers one from a gate.

**The checkbox-inconsistency finding is bigger than this brief assumed.** The
brief names two affected pairs (`doc_provenance_coverage`,
`repo_tier_producers`). The board's walk (finding B1) found **five**:
those two plus `work_rig_solo`, and two archived pairs
(`apply_alignment`, `relink_scoring`) that predate anyone noticing the split.
Because this slice's detection is derived from checkbox counts rather than a
list of stems, it already covers all five (and any future one) without
needing the brief's assumption corrected in code — only in this report.

**No board ruling changed the "sheet is the request, results log is the
answer" default.** The brief's own out-of-scope list makes ticking the source
sheet conditional on the board ruling otherwise; the board's walk did not
rule on this at all (it deferred the ratification/staging tasks that would
have exercised it), so the default from `docs/README.md` stands: this slice
never writes to a walk-sheet, only to its results log.

## A cross-slice side effect, and how it was resolved

Registering `tester_uat_sidebar` in `verify.py` added one to the live tester
count (auditors unchanged), which put two of
`docs_board`'s own finished documents (`COWORK_REPORT_docs_board.md`,
`UAT_docs_board.md`) out of sync with `auditor_doc_claims` — exactly the
staleness `gate-frozen` markers exist to absorb (`docs/README.md`, "the gate
and the reversible part"). Both docs already claimed a specific base commit
(`a202ba0`); a `<!-- gate-frozen: commit=a202ba0 -->` marker was added to each,
at the very top, above the title — a stamp, not a body edit, the same
distinction `docs/README.md` draws for the archive stamp. No other line in
either document changed.

## Addendum — resume, added after the first live walk

The first live walk (against the real `docs/`, gate GREEN, card observed
moving `built_not_walked` → `walked`) surfaced a real gap: opening the sidebar
on a sheet that already has a results log gave no obvious way back into what
was already recorded, and the existing-log fact itself was a clause in a
counts line rather than something you'd notice.

Added: `uat_sidebar.parse_results_log` reads a previously emitted results log
back into `{id: {verdict, evidence}}` (the exact inverse of
`build_results_body`'s per-item shape; fenced multi-line evidence is
unwrapped, not re-parsed as markdown). `sheet_view` now returns this as
`prior_entries`. The UI shows an unmissable banner whenever a results log
exists, a badge on every item already recorded (visible without pressing
anything), and a **Resume** button that loads prior verdicts into the
session.

**Resuming does not resubmit untouched items.** A resumed entry is tagged
`_resumed` client-side; touching its verdict or evidence clears the tag.
Emitting only submits entries with a verdict that are not still tagged
`_resumed` — so pressing Resume and then emitting with nothing further
touched appends nothing, and only genuinely new or edited items land in the
new section. This was a deliberate choice over the alternative (resubmit
everything on resume): re-printing already-recorded items into every new
section would make an appended log noisier with each pass, and the append
model already exists precisely so old testimony is never touched — only
added to.

`tests/tester_uat_sidebar.py` gained direct coverage: recovering both
single-line and fenced multi-line evidence, an item never emitted staying
absent from the parse, `sheet_view.prior_entries` matching
`parse_results_log` exactly, and — walking the same id across two appended
sections with different verdicts — confirming the **latest** occurrence is
what's offered back, not the first.

## Known follow-ups (not silently fixed, recorded)

- **Item-continuation notes are folded heuristically.** `parse_sheet` treats
  any indented, non-blank line following an item as that item's `sheet_note`,
  stripped of leading `-`/`*`/em-dash. This works on every sheet inspected
  during this build (`UAT_docs_board.md`, `UAT_work_rig_solo.md`,
  `UAT_estate_restructure.md`) but is a heuristic, not a grammar — a sheet
  with unusual continuation formatting could fold two different things
  together. Worth a second look if a future sheet's notes render oddly.
- **A card's stem, not an arbitrary path, is the only thing the sidebar
  accepts from a caller** (`_STEM` = `[A-Za-z0-9_-]+`), matching the board's
  own "no second path resolver" rule (0027 condition 3). The board's own
  "Walk it" button passes the card's `key` directly, so this is exercised on
  every real card, not just the fixture.
