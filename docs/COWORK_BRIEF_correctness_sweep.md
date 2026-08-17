# Cowork brief — correctness sweep (five small fixes off the UAT walk)

**Origin:** the UAT walk of 2026-08-15..17, recorded in
`docs/UAT_ui_witness_results.md`. Its "Carried findings" section (items 5, 6,
7, and this section's own note on 4/10) holds the evidence for most of what
follows. Nothing here was invented for this brief; it was found doing other
work and parked until now.

**Read first:** `docs/README.md` (doc classes, the archiving convention, the
UAT stamp), DECISIONS **0025** (surface-scoped visibility; the loopback rule
is structural, not a warning) and **0031** (a witness reports findings and
never a verdict — the `[G]`/`[W]`/`[H]` split this sweep makes visible),
`docs/UAT_ui_witness_results.md` §"Carried findings".

**Shape of this round:** five independent, small fixes. None touch each
other's files except (1) and (2), which both live in `chronicler/review/` but
in different modules. Do them in any order; report on all five together.

---

## Working rules

- `python verify.py` **GREEN** before every commit.
- `git commit -F <file>` — never `-m` with an embedded newline.
- Every fix gets a tester where one can exist. (1), (2) and (3) all can; write
  them. (4) is print-statement wording plus a structural condition already
  covered by existing loopback testers — extend rather than duplicate. (5) may
  have no tester of its own if the fix is a dependency change; say why in the
  report if so.
- **Do not widen scope.** Five fixes, nothing else. A sixth thing noticed
  while in these files goes in the report as a carried finding, not into the
  diff.

---

## 1 ▸ the layer marker is parsed and never rendered

**The important one.** `chronicler/review/uat_sidebar.py`'s `_ITEM` regex
(line 67) captures the optional `[G]`/`[W]`/`[H]` marker, and
`build_results_body` (line 360ff) uses it to route each item: `layer in
("G","W")` → Machine-verified, `layer in ("H", None)` → Human ruling.
`chronicler/review/static/panes/uat.js` never renders that marker anywhere on
the item.

Consequence, proven on a probe sheet during the walk (finding 10): marking an
`[H]` item as `[W]` moves it into Machine-verified, where it gets a witness
citation and **no human verdict field**, and the emitted `## Human ruling`
section then prints *"No `[H]` items were recorded on this walk."* The log
does not just misplace the judgement — it asserts the absence of one that was
required, and the walker had no way to see the mis-mark coming because the
surface they're looking at doesn't show layers at all.

**Fix:** render the marker as a badge beside the existing `open` /
`already recorded` chips in `uatItemHtml` (`panes/uat.js`), so the layer is
visible at the point of walking, not just in the emitted artefact.

**Tester:** a sheet with mixed `[G]`/`[W]`/`[H]`/unmarked items renders each
item's badge matching its parsed `layer`.

---

## 2 ▸ the docs board's checkbox parser has a confident zero

`chronicler/review/docs_board.py`'s `_CHECK` regex (line 198) matches only
`- [ ]` / `- [x]` / `- [~]`. Sheets using the post-0031 backticked form
(`` - `[ ]` ``) count as **zero** — not "unreadable", zero. Today
`docs/UAT_knowledge_curator.md` (22 items) and `docs/UAT_project_wizard.md`
(16) read as "0 open / 0 done" on the board: 38 unwalked items reporting as
nothing to do, on the surface used to decide what still needs walking.

**Fix:** widen `_CHECK` to match both the plain and backticked forms. Check
`uat_sidebar.py`'s `_ITEM` regex too — same shape of match, and worth
confirming it isn't carrying the same gap silently (0031 finding 7's fix
touches the same file; do both checks in the same pass).

**Tester:** extend `tester_docs_board.py`'s checkbox coverage with a sheet
using the backticked form; assert non-zero, correct counts.

---

## 3 ▸ the UAT sidebar cites paths built from the caller's keystrokes

`uat_sidebar.py:250` builds `results_rel` from the `stem` argument rather
than from `rp`, the path the code actually resolved and read (line 234).
Opening a sheet as `UI_Witness` produces a banner citing
`docs/UAT_UI_Witness_results.md` when the file on disk is
`docs/UAT_ui_witness_results.md`. Windows' case-insensitivity hides this —
the read still succeeds — but a case-sensitive filesystem answers differently
for the same input, and either way `results_rel` is the string a citation
carries. A citation built from what the caller typed is not provenance.

**Fix:** one line — derive `sheet_rel` / `results_rel` from the resolved
`sp` / `rp`, not from `stem`.

**Tester:** open a sheet with mismatched casing on a case-sensitive-style
resolve path; assert the displayed path matches the resolved path, not the
input.

---

## 4 ▸ the startup banner advertises non-loopback URLs on a work-estate box

On `10280L`, `run.py`'s app startup prints, unconditionally:

```
app: estate='work' -- rendering only that estate's threads (DECISIONS 0025)
app: binding 127.0.0.1:54553
app: phone on the tailnet: http://<knight-100.x>:54553/ | on the LAN: ...
```

The bind is correct — 0025's loopback rule is already enforced structurally a
few lines above (`run.py` ~line 626). The message directly under it
contradicts the bind, with unfilled `<knight-...>` placeholders, on the
estate 0025 is most careful about. This looks like mesh-era text (the
tailnet/LAN banner makes sense on the knight) that survived the
`unified_app` Task 6 mesh-command split.

**Fix:** the tailnet/LAN line is only true, and only useful, when the bind is
actually reachable beyond loopback. Gate it on `core.is_loopback_host(args.host)`
(already imported/used just above) — print it only when the bind is
non-loopback, and print the honest alternative when it isn't: bound to
loopback, reachable from this machine only.

**Tester:** extend the existing loopback/bind tester coverage to assert the
tailnet/LAN line is absent on a loopback bind and present (with real values,
no placeholders) on a non-loopback one — or confirm existing coverage already
proves the bind condition and add only the print-content assertion.

---

## 5 ▸ `StarletteDeprecationWarning` on every gate run

*"Using `httpx` with `starlette.testclient` is deprecated; install `httpx2`
instead."* Non-fatal, printed on every `TestClient` use in the test suite
(`tester_docs_board.py`, `tester_uat_sidebar.py`). Confirmed cause: installed
`starlette` (1.3.1) prefers `httpx2` for its test client and falls back to
`httpx` (0.28.1, which is what's installed) with this warning
(`starlette/testclient.py:33-51`).

**Fix:** install `httpx2` (add it to the `review` extra in `pyproject.toml`
alongside `fastapi`/`uvicorn`, since it's only needed where `TestClient` is
used) and confirm the warning is gone on a clean `.venv` install. If `httpx2`
turns out to be unavailable, broken, or the wrong call for some reason found
during the fix, record why not in the report instead — this item is allowed
to close as "investigated, not fixed" per the working rules, but say so
explicitly.

**Tester:** none required — this is a dependency change, not a behaviour
change. Confirm by running the gate and checking the warning is gone.

---

## UAT — acceptance checks (Tim walks these)

- **1.** A sheet with `[G]`/`[W]`/`[H]`/unmarked items shows each item's
  layer as a visible badge in the sidebar, matching the sheet.
- **2.** `docs/UAT_knowledge_curator.md` and `docs/UAT_project_wizard.md` read
  their real open/done counts on the docs board, not `0/0`.
- **3.** Opening a sheet by a mismatched-case stem cites the resolved path in
  the results-log banner, not the typed one.
- **4.** Starting the app bound to loopback prints no tailnet/LAN URLs;
  starting it bound non-loopback (personal estate) prints real values, no
  placeholders.
- **5.** `python verify.py` runs clean of the `StarletteDeprecationWarning`,
  or the report says why it still appears.

Mark each **ready to walk**, never "passed".

---

## Reporting

`docs/COWORK_REPORT_correctness_sweep.md`, walk-sheet
`docs/UAT_correctness_sweep.md`, items marked `[G]`/`[W]`/`[H]` per 0031 —
this round is a fitting place to start actually using the split it's fixing.
Note in the report which of the five got testers and which didn't, and why.
