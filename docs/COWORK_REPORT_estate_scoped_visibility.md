<!-- gate-frozen: commit=e565c98 -->

# Cowork report — estate-scoped visibility

Pair: `docs/COWORK_BRIEF_estate_scoped_visibility.md`. Session 2026-07-27, on top
of `e565c98` (DECISIONS 0025 already accepted there). **BUILD, then STOP —
nothing committed; everything staged for Tim's review and the work-laptop walk.**

`python verify.py` — **GREEN**, 6 auditors + **46** testers at this build (no new
tester module registered; `tests/tester_review.py` extended in place, per the
brief's "extend the wall assertions rather than replacing them").

| Task | State | What landed |
|---|---|---|
| 1 — filter becomes estate-scoped | **green** | `core.account_clause_for_estate`, config-derived, resolved once |
| 2 — loopback enforcement | **green** | `run.py review` preflight refuses a non-loopback bind on a work estate |
| 3 — testers | **green** | mirror case, refusal case, loopback predicate case added to `tester_review` |
| 4 — MCF-scoped registry | **green, documented not built** | `build_registry.py --estate work` already does it; `SOLO_PLAYBOOK.md` §11 updated |

**Not walked here** — no work laptop, no MCF dataset in this session. Every UAT
item in `docs/UAT_estate_scoped_visibility.md` is ready to walk, not walked.

---

## Task 1 — the filter becomes estate-scoped

`chronicler/review/core.py`'s `_PERSONAL_ACCOUNT_CLAUSE` constant is unchanged
in *shape* — it still exists as the literal `personal` clause — but it is no
longer the only clause and no longer read directly by the query builders. New:

- `_WORK_ACCOUNT_CLAUSE = "t.account LIKE '%-work'"`, the mirror.
- `account_clause_for_estate(estate) -> str`, the one function that turns a
  declared estate into a clause: `"personal"` → the personal clause, `"work"` →
  the work clause, anything else (`"both"`, `None`, `""`, `"junk"`) → `ValueError`
  naming DECISIONS 0025 and the config key to fix. This is the allowlist-not-
  blocklist shape the original comment insisted on, extended rather than
  replaced — an estate value that isn't recognised stays walled out by refusing
  to serve, never by falling through to some default.
- `pending_rulings()` and `queue_by_project()` both gained an `account_clause`
  parameter, defaulting to `_PERSONAL_ACCOUNT_CLAUSE` so every existing caller
  (including the pre-existing tester assertions) keeps today's personal-only
  behaviour with zero changes at the call site. Neither function reads
  `config` — the brief's requirement that `review/` stay independent of config
  resolution, the same way it stays independent of `pipeline.db`.

Resolution happens exactly once, in `run.py review`'s preflight
(`config.machine()["estate"]` → `core.account_clause_for_estate(estate)`), and
the resulting string is threaded down: `run.py` → `app.run()` → `app.create_app()`
→ closed over by every route handler → passed as `account_clause` into
`core.pending_rulings` / `core.queue_by_project` on each request. Nothing
re-derives it per-request or inside `core.py`.

The comment block above the constants was extended, not deleted, per the
brief — it still states why this is a deny-by-default allowlist and now also
states why the estate is config-derived while the loopback rule (Task 2)
deliberately is not.

## Task 2 — loopback enforcement on a work-estate surface

Added `core.is_loopback_host(host)` — a tiny literal set
(`{"127.0.0.1", "::1", "localhost"}`), no DNS resolution, auditable at a glance.
`run.py`'s `_cmd_review` preflight now does, before anything binds:

```python
estate = m.get("estate")
account_clause = core.account_clause_for_estate(estate)   # refuses loudly
if estate != "personal" and not core.is_loopback_host(args.host):
    print("review: refusing to bind ... DECISIONS 0025 ... --host 127.0.0.1")
    return 2
```

This is unconditional on `args.host`'s *value*, not on whether `--host` was
passed explicitly — the shared `--host` default (`0.0.0.0`, still correct for
`serve` and for a `personal`-estate `review`) is not special-cased, so a work
laptop that forgets to pass `--host 127.0.0.1` is refused by the same rule as
one that passes `--host 0.0.0.0` on purpose. Nothing about this rule reads
config — the estate is config-derived, the loopback requirement is not, exactly
as the brief specifies ("derive the estate from config; derive the *rule* from
the code").

The knight's `personal`/`both` defaults are untouched: `estate != "personal"`
only fires for `"work"` (an `unrecognised`/`"both"` estate is already refused
one step earlier, by `account_clause_for_estate`, before the loopback check is
ever reached).

`SOLO_PLAYBOOK.md` §11 (the `[WORK]` profile — the brief named §10, which is
now Troubleshooting after a prior renumbering; the content lives in §11) states
the new documented default: `--host 127.0.0.1`.

## Task 3 — testers

`tests/tester_review.py` extended in place (no new module, no change to
`verify.py`'s registration list):

- **Mirror case.** `account_clause_for_estate("work")` used directly against
  the existing fixture: `TWORK` (`gemini-work`) appears under the work clause,
  `T1`/`T2` (`*-personal`) do not, on both `pending_rulings` and
  `queue_by_project`. Same rows, same DB state as the existing personal-wall
  assertions just above it — only the clause changes, proving the filter is
  scoped rather than disabled.
- **Refusal case.** `account_clause_for_estate` called with `"both"`, `None`,
  `""`, `"junk"` — each must raise `ValueError` and each message must name
  `"0025"`.
- **Loopback case.** Rather than driving `run.py`'s CLI/subprocess from a
  hermetic tester (out of keeping with this module's style — no FastAPI, no
  uvicorn, no process spawned), the test reproduces `_cmd_review`'s exact
  preflight condition, `estate != "personal" and not is_loopback_host(host)`,
  against `core.is_loopback_host` directly for the four required combinations:
  work+`0.0.0.0` refuses, work+`127.0.0.1` proceeds, work+`::1` proceeds,
  personal+`0.0.0.0` proceeds (the knight default, unchanged). This exercises
  the real primitive `run.py` calls, not a re-implementation of it — if
  `is_loopback_host`'s literal set is ever wrong, this catches it the same as
  a CLI-level test would, without the process-spawning cost.
- The pre-existing personal-only wall assertion (`TWORK` never appears in an
  unfiltered/default-clause read) is untouched — the brief's "must keep passing
  exactly as it does now."

`python verify.py`: **GREEN, 6 auditors + 46 testers** (unchanged tester count;
this session extended an existing module rather than adding one).

## Task 4 — the MCF-scoped registry, documented not built

Checked `chronicler/pipeline/build_registry.py` first, per the brief's
instruction to check before building anything. It already accepts `--estate`
(wired to `build(estates_dir, only_estate)` → `find_estate_snapshots`, which
filters to the one named estate's deposit directory before
`discover_from_estates` ever runs) — so `--estate work` on a work rig already
produces a registry built from only that machine's own work-estate deposit
snapshot, nothing personal-side folded in. No filter code was missing; this is
exactly the "playbook paragraph and nothing more" case the brief anticipated.

`SOLO_PLAYBOOK.md` §11 gained two paragraphs: one restating the estate-scoped
visibility rule end-to-end for the `[WORK]` profile (what `review` now shows,
the loopback requirement, the new documented `--host 127.0.0.1` default, and
that an undeclared/ambiguous estate refuses rather than guesses), and one
naming `build_registry.py --estate work` as the way to produce the MCF-only
registry this brief asked to be documented.

---

## What did NOT change

- `DECISIONS.md` 0010 (the deposit wall) — untouched; this brief is display-only,
  as it says explicitly.
- The TOTP gate (0023) — still unbuilt, still out of scope; still required for
  any surface that co-renders more than one estate or is reachable beyond
  loopback. A solo work box on loopback is neither.
- `run_ledger`, transcript intake, anything else on the deck roadmap — untouched.
- `config/machines.json` / `config/local.json` — already carried `estate` per
  machine (`personal` / `work` / `both` / `unknown`) before this session; no
  config schema change was needed, Task 1 consumes what was already there.

## Open items for the walk

- The work laptop (`10280L`) has never been walked this session — every check
  in `docs/UAT_estate_scoped_visibility.md` is Tim's to run against the real
  MCF dataset.
- `config/local.json`'s work-laptop entry needs `--host 127.0.0.1` added to
  however `review` is actually launched there (a shortcut, a script, or by
  hand) — the code now refuses the old bare invocation, on purpose.
