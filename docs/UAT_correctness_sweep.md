# UAT walk-sheet — correctness sweep

**Brief:** `docs/COWORK_BRIEF_correctness_sweep.md`
**Report:** `docs/COWORK_REPORT_correctness_sweep.md`

**Built:** 2026-08-17, on `LucasGoonPC`, commit `142c11f`. **Gate:**
`python verify.py` GREEN before every commit in the series
`2f17af6..142c11f` (six commits: the brief, and one per fix except items 4
and 5, which share their commit with the tester registration and the
dependency change respectively — see the report for the full list).

**Nothing below has been walked.** This is a skeleton, not a completed walk
— the code changes and their testers are gate-green, which is `verify.py`'s
claim about the code, not a human's claim about the running surface (0031).

Mark each `[G]`/`[W]`/`[H]` per 0031 once walked. Items below use the
sidebar's own item syntax (bold id, plain-bracket layer marker) on purpose —
this sheet is walkable through the tool it's testing.

## A · the layer marker badge

- [ ] [H] **A1** Open a sheet with mixed `[G]`/`[W]`/`[H]`/unmarked items in
  the UAT sidebar (e.g. a copy of a `UAT_layered.md`-shaped fixture, or any
  real sheet carrying markers). Confirm each item shows a badge naming its
  layer (`[G] gate`, `[W] witness`, `[H] human`) or `unmarked` when the
  sheet carries no marker for that item, and that the badge matches the
  sheet. No automated witness covers the rendered badge itself in this
  round — `tester_uat_sidebar` proves the data reaches the item (`layer`
  field), not that it paints correctly.

## B · the docs board's checkbox parser

- [ ] [G] **B1** Reload the docs board and confirm `UAT_knowledge_curator.md`
  and `UAT_project_wizard.md` read `22 open / 0 done` and `16 open / 0 done`
  respectively, not `0/0`. Confirmed directly against the live files during
  the build — see the report — but the human ruling is walking the actual
  rendered board, not trusting a script's print statement.

## C · the sidebar's path citation

- [ ] [G] **C1** On the real Windows machine, open a sheet by a
  mismatched-case stem (e.g. request `UI_Witness` when the file on disk is
  `UAT_ui_witness.md`) and confirm the "results log already exists" banner
  cites `docs/UAT_ui_witness_results.md`, not `docs/UAT_UI_Witness_results.md`.
  `tester_uat_sidebar` carries a Windows-gated regression test for exactly
  this; this item is walking it on the actual surface once more, for real.

## D · the startup banner

- [ ] [G] **D1** Start `run.py app` bound to loopback (the default on a
  non-personal-estate machine) and confirm no `phone on the tailnet` / `on
  the LAN` line prints — only the "bound to loopback only" line.
- [ ] [G] **D2** Start it bound non-loopback (personal estate, or
  `--host 0.0.0.0` where 0025 permits it) and confirm the tailnet/LAN line
  prints with the real port and no `<knight-...>` placeholder.

## E · the StarletteDeprecationWarning

- [ ] [H] **E1** Run `pip install -e .[review]` (or `pip install httpx2`
  directly) and re-run `python verify.py`. Confirm the
  `StarletteDeprecationWarning` about `httpx`/`starlette.testclient` no
  longer prints. This was not exercised in the build session — no network
  reachable from where the files were written — so this is the first real
  test of whether the fix works, not a confirmation of one already run.

---

## Also worth noting while walking

- The incidental fix to `docs/COWORK_REPORT_curator_correction.md` and
  `docs/UAT_curator_correction.md` (72 → 73 testers) is not a UAT item —
  it's a mechanical consequence of registering `tester_run_banner`, made
  per `docs/README.md`'s own rule that a live doc's stale count is fixed,
  not exempted in place. Nothing to walk there beyond noticing it's correct.
