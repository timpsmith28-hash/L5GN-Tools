<!-- gate-frozen: commit=a0c3901 -->
> **ARCHIVED** 2026-08-31 · completed pair · pair `COWORK_BRIEF_correctness_sweep.md` + `COWORK_REPORT_correctness_sweep.md`, walked 2026-08-18
> Superseded by the fixes themselves being live, and by `CONVENTION_docs.md` §4 for the archiving rules its walk-sheet exercised · Original purpose: a sweep of correctness defects found across the deck panes and the gate, fixed one at a time with a commit each.
> Accurate history: the fix-by-fix account and its commit for each, which is what makes this pair worth keeping. **Stop trusting:** "9 auditors + 73 testers" — the live gate is **12 auditors + 81 testers**. Its *"What wasn't exercised"* section is still true and still matters: the route-level `TestClient` checks skipped rather than ran, because `fastapi`/`httpx` were absent from the verification environment. That is a **gap in the evidence, not in the build**, and it has not been closed since.

# Cowork report — correctness sweep

Built against `docs/COWORK_BRIEF_correctness_sweep.md`, commit series
`2f17af6..142c11f` on `LucasGoonPC`. Gate: **9 auditors + 73 testers,
GREEN** before every commit (verified with `fastapi`/`httpx` unavailable in
the verification environment — see "What wasn't exercised" below; the
route-level `TestClient` checks in `tester_docs_board`/`tester_uat_sidebar`
skipped gracefully rather than running, same as they do on any machine
without the `review` extra installed).

This is testimony about what was built, not a status board — it will not be
updated as the tree moves on.

## What changed, fix by fix

**1 — the layer marker badge (`25ad2ee`).** `chronicler/review/static/panes/uat.js`'s
`uatItemHtml` now renders a badge for each item's `[G]`/`[W]`/`[H]` marker
(`layer-G`/`layer-W`/`layer-H` CSS classes, `chronicler/review/static/index.html`),
or `unmarked` when the sheet carries none — labelled rather than left blank,
because an unmarked item defaults to Human ruling on emit and that default
is itself worth showing. No backend change: `parse_sheet` already returned
`"layer"` per item; nothing consumed it on the pane side. Verified with
`node --check` (syntax only — no browser harness exercises the rendered
badge in this round; the walk-sheet item for this fix is `[H]`, a real
human look).

**2 — the docs board's checkbox parser (`94e5f8c`).** `docs_board.py`'s
`_CHECK` regex now accepts an optional backtick on each side of the
brackets, matching both `` - [ ] `` and `` - `[ ]` ``. Confirmed directly
against the live files:

```
UAT_knowledge_curator.md {'done': 0, 'open': 22, 'readable': True}
UAT_project_wizard.md    {'done': 0, 'open': 16, 'readable': True}
```

— both now read their real counts on the board (`board()` returns
`open_items=22`/`16`, `done_items=0`, in the `built_not_walked` column),
where they previously read `0/0`. `tests/tester_docs_board.py` gained a
`backticked` fixture card asserting the two forms count identically.

**3 — the sidebar's path citation (`cbff1e3`).** `uat_sidebar.sheet_view`
now derives `sheet_rel`/`results_rel` from the resolved `sp`/`rp` (via
`relative_to(root)`) instead of formatting them from the caller's typed
`stem`. Confirmed against the real `ui_witness` sheet:

```
sheet_rel:   docs/UAT_ui_witness.md
results_rel: docs/UAT_ui_witness_results.md
```

`tests/tester_uat_sidebar.py` gained a general assertion that `sheet_rel`
matches the resolved path, plus a `os.name == "nt"`-gated regression test
that reproduces the finding's exact scenario (request `Fixture`, real file
is `fixture`) — gated because the bug is genuinely Windows-specific: a
case-sensitive filesystem refuses the mismatched request at `no_sheet`
before either path is ever built, so there's nothing to compare there. The
verification environment for this build was Linux, so this specific
regression branch did not execute this session; it will on the real
Windows pre-commit run.

**4 — the startup banner (`85d2d9a`).** Pulled the reachability line out of
`_cmd_app` into `_reachability_line(label, host, port, is_loopback_host)`, a
pure function: prints the tailnet/LAN URLs only when
`is_loopback_host(host)` is false, and a plain "bound to loopback only"
line otherwise — no more unconditional print with unfilled
`<knight-...>` placeholders under a bind that DECISIONS 0025 had already
restricted to loopback. `tests/tester_run_banner.py` exercises both
branches directly, registered in `verify.py` (9 auditors + 73 testers, up
from 72).

That registration is itself why the next paragraph exists: it moved the
live tester count, which `auditor_doc_claims` checks against two docs from
the unrelated, still-unwalked `curator_correction` round
(`docs/COWORK_REPORT_curator_correction.md`,
`docs/UAT_curator_correction.md`, both claiming "72 testers"). Neither doc
carries a `gate-frozen` marker and neither is archivable yet (the pair
hasn't been walked), so per `docs/README.md` §3's rule — *"a live doc whose
numeric claims have gone stale should be fixed or archived, never exempted
in place"* — both were bumped to "73 testers" in the same commit. Not scope
creep: a direct, documented consequence of adding a tester, folded into the
commit that caused it rather than left red for someone else to trip over.

**5 — the StarletteDeprecationWarning (`142c11f`).** Confirmed cause by
reading `starlette/testclient.py:33-51` directly: installed `starlette`
(1.3.1) prefers `httpx2` for its test client and falls back to the
installed `httpx` (0.28.1) with exactly this warning. Added `httpx2` to the
`review` extra in `pyproject.toml`, alongside `fastapi`/`uvicorn` — the
extra that enables the `TestClient` routes producing the warning in the
first place. **Not yet installed or verified fixed** — no network was
reachable from where these files were written this session. Needs
`pip install -e .[review]` (or `pip install httpx2` directly) run locally,
then `python verify.py` re-run to confirm the warning is gone. This is
walk-sheet item 5, marked `[H]` for exactly that reason.

## What wasn't exercised

The gate ran GREEN throughout the build, but the verification environment
had no `fastapi`/`httpx`/`starlette` installed — it is not the Windows
`.venv` the real pre-commit hook runs against. Two consequences:

- The `TestClient`-driven route checks inside `tester_docs_board` and
  `tester_uat_sidebar` (`route_coverage`) skipped rather than ran, same as
  they already do on any machine without the `review` extra — not a gap
  introduced by this round, but worth naming so "GREEN" isn't read as
  "every line ran."
- Fix 5 could not be confirmed fixed, only diagnosed and applied — see
  above.

Re-running `python verify.py` on `LucasGoonPC`'s real `.venv` (which does
have the full dependency set, per the pre-commit hook) is the first thing
worth doing before walking the sheet, both to exercise the skipped route
checks for real and to confirm fix 5.

## Commit series

```
2f17af6 docs: add the correctness-sweep brief
94e5f8c fix(docs_board): count the post-0031 backticked checkbox form
25ad2ee fix(uat): render the [G]/[W]/[H] layer marker on the item
cbff1e3 fix(uat_sidebar): cite the resolved path, not the caller's typed stem
85d2d9a fix(run): only advertise tailnet/LAN reachability when the bind is not loopback
142c11f fix(deps): add httpx2 to the review extra, quieting StarletteDeprecationWarning
```

Each commit's own message carries the full reasoning for that fix; not
repeated here beyond the summary above.

## UAT

Walk-sheet: `docs/UAT_correctness_sweep.md`. Five items, one per fix, marked
per 0031 as described in "What changed" above: `[H]` for 1 and 5 (no
automated coverage of the rendered badge or the installed-package effect),
`[G]` for 2, 3 and 4 (covered by their testers; walking is confirming the
real surface agrees, not discovering something new).
