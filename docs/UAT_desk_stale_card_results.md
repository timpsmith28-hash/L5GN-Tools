<!-- uat: commit=fb6fa5c dirty=true host=LucasGoonPC walked=2026-08-20 -->

# Results log — Decision Desk, stale-output triage (walked 2026-08-20, LucasGoonPC) — INTERIM, trial in progress

Partner to `docs/UAT_desk_stale_card.md`.

**This is not the trial's closing walk.** The brief's own Reporting section
says results get stamped "after the trial, not after the build," on an
open-ended trial that runs until ten real cards are ruled. As of this walk
the events log shows **four** ruled (see D7 below), and the fixture itself
was only stood up today. Tim's explicit call, 2026-08-19: enough real
adaptation has already happened mid-build (the silent-week cut, the
occurrence-model rewrite, the "Rebuild now" ordering fix) to justify writing
the report and this results log *now*, ahead of the brief's own schedule,
understanding both will be revised and re-stamped as the trial continues
toward ten. Treat every verdict below as current-as-of-2026-08-19, not
final.

This log records a verdict and its evidence per item — never a computed
pass. `[EVIDENCE]` walked (with evidence) · `[DEFERRED]` deferred, with a
reason · `[BLOCKED]` blocked, with a reason · `[N/A]` not applicable.

---

## Machine-verified

_No witness artefact found at `data/witness/desk_stale_card.json` for this
sheet — reported here, not silently omitted. No `[G]`/`[W]` item on
`docs/UAT_desk_stale_card.md` is registered as a `verify.py` auditor for
this round (the brief never asked for one), so there is nothing this
section could cite even in principle. Every item, including the ones marked
`[G]`, is walked as a human observation below, same gap the
`pin_mechanism` results log names for its own sheet._

## Human ruling

- **D1** A repo with a delegated-freshness stage reporting stale raises exactly one card, trigger quotes the answer verbatim.
  [EVIDENCE] Walked live on `uat-decisions-fixture::state_freshness`. The card's evidence panel showed the delegated command's own line verbatim (e.g. `37.66h old (generated_at=2026-08-19T14:02:57+01:00) -- STALE`, later `0.03h old ... -- fresh`), tagged `delegated`. Exactly one card for this fingerprint at every render across the session — confirmed by screenshot and by the fact `cards_raised` in `events.jsonl` never shows more than one open sighting for it at a time.

- **D2** `depends_on` pair raises a card with both timestamps; running B clears it because facts changed.
  [EVIDENCE] `uat-decisions-fixture::derived` (Trigger B, depends on `source`) raised a card reading "run marker finished_at=2026-08-19T14:14:09Z at 2026-08-19T14:14:09Z, this stage last built 2026-08-19T14:04:34Z" — both timestamps present. Cleared on next render twice in this session: once through the card's own "Rebuild now" (after the ordering fix), once by running `derived` directly from Project Wizard outside the card entirely — both confirm it's the underlying `derived.json` timestamp moving, not a client-side dismissal, that clears it.

- **D3** Same standing staleness across renders = one fingerprint, one sighting, never a duplicate per render.
  [EVIDENCE] Confirmed by reading `data/desk/events.jsonl` directly rather than inferring it from the UI. Fingerprint `78a5d9f55fb2...` has exactly one `sighting` event despite dozens of intervening `GET /api/desk/cards` polls in the server log between its rulings (visible in the pasted startup/request logs). No fingerprint in the log this session shows more than one open, un-aged sighting.

- **D4** `POST /api/desk/rule` refuses an unknown fingerprint and an empty dismiss-reason; no route accepts a path or argv.
  [EVIDENCE], partial. The unknown-fingerprint refusal was exercised live — not deliberately, but by the pre-fix "Rebuild now" ordering bug: `POST /api/desk/rule` returned exactly the documented refusal (`'652d40c4fd26e2a9' is not a currently-derived card. Refused -- rulings only land against a fingerprint the board can see right now.`) when the fingerprint it was asked to rule had already stopped being derived. The empty-dismiss-reason refusal was **not** exercised live this session — the client blocks an empty dismiss before the request is ever sent, so the server-side `DeskRefused("empty_dismiss_reason", ...)` path was only exercised by the existing automated test suite (`run_test*.py`), not walked through the UI. No route was ever seen to accept a path or argv this session, in either the wizard's own logs or the Desk's.

- **D5** Kill the deck mid-ruling: events file stays valid JSONL, board re-derives identically.
  [DEFERRED] Not attempted this session — genuinely destructive (force-closing the server process at the instant of a click) and judged not worth doing casually on a session that was otherwise making steady progress. `_read_events()`'s tolerance for a trailing corrupt line is covered by the existing unit tests, but the literal kill-mid-write scenario has not been walked. Defer to a deliberate, standalone pass.

- **D6** Empty allowlist renders an honest empty state, not an error.
  [DEFERRED] Not re-walked live this session. Covered by the FastAPI `TestClient` route tests written during the original Tasks 0–3 build, before this UAT round started; not re-confirmed against the real running app, since doing so would mean temporarily pulling both real allowlist entries and disrupting the live trial setup.

- **D7** Rule ten real cards over the trial; was the evidence enough, or did you go hunting?
  [DEFERRED — in progress] Recomputed directly from `data/desk/events.jsonl` via `desk.latency_summary()` itself (not by hand): **`cards_raised: 5, cards_ruled: 4, cards_resolved_without_ruling: 1`** as of this walk (2026-08-20). The four ruled: the pre-fix button-test occurrence on `57860823ba56...` (disqualified, see D13), the 2026-08-19 recurrence on `652d40c4fd26...`, the Trigger B occurrence on `78a5d9f55fb2...`, and a fresh recurrence on `652d40c4fd26...` sighted and ruled today, 2026-08-20T11:37–11:38Z — the first occurrence in this log genuinely spaced by more than a day from its predecessor rather than clustered inside one testing session. Six to go. No "hunt" findings have been logged against a card itself yet (one finding has been logged about the *instrument*, not a card — see the new project_wizard.py-untested finding, out of scope for this sheet); evidence on the cards has been sufficient so far, but the sample is still small and entirely on `uat-decisions-fixture`, not yet on `l5gn-tools-fixture`'s real `estate_freshness` stage.

- **D8** The latency footer at trial's end: is the number believable?
  [DEFERRED] Trial not at ten yet. Interim number for the record: `median_latency_hours ≈ 11.34` as of 2026-08-20 (up from ≈1.09 on 2026-08-19) — moving in the right direction as same-session fixture-testing rulings get diluted by a real overnight gap, but still not believable as a stable decision-latency figure off four points. This is exactly the "button test, not trial data" caveat Addendum (b) named for the pre-fix events; the report says so explicitly rather than letting the number stand unqualified.

- **D9** The falsifier, answered in one paragraph, yes or no.
  [DEFERRED] Cannot be answered honestly before the trial has real signal. Explicitly not answered in the accompanying report.

- **D10** Fixture card resolve-and-re-raise → second sighting, second occurrence's own latency.
  [EVIDENCE] Found directly in `events.jsonl`, not manufactured as a separate test: fingerprint `652d40c4fd26...` resolved at `2026-08-19T14:01:50Z`, then a fresh `sighting` fired at `2026-08-19T14:02:25Z` when it went stale again, and the ruling on that recurrence carries `occurrence_started_at: 2026-08-19T14:02:25Z` — the new occurrence's own opening timestamp, not the first occurrence's `13:37:47Z`. Reinforced by a second, independent recurrence a day later: the same fingerprint resolved and re-sighted again on 2026-08-20T11:37:39Z, ruled at 11:38:11Z with `occurrence_started_at` matching that new sighting, not either earlier occurrence's. Three occurrences on one fingerprint now, each correctly distinct.

- **D11** Rule the same open card more than once → one latency figure, `cards_ruled` +1.
  [EVIDENCE] Fingerprint `78a5d9f55fb2...` was ruled three times without the card clearing in between (`snooze` at `14:14:41Z`, `snooze` again at `14:22:55Z`, `rebuild` at `14:23:10Z`), and all three carry the identical `occurrence_started_at: 2026-08-19T14:14:18Z`. `latency_summary()`'s recomputation confirms this occurrence contributes exactly one entry to `cards_ruled` (part of the `cards_ruled: 3` total in D7), not three.

- **D12** Every ruling event after the fix carries `occurrence_started_at`.
  [EVIDENCE] Read `events.jsonl` directly: every `ruling` event with a timestamp after the addendum (b) fix landed (`652d40c4fd26...`'s and `78a5d9f55fb2...`'s, five rulings total) carries `occurrence_started_at`. The three pre-fix rulings on `57860823ba56...` correctly do **not** carry it, which is expected — they predate the fix and are read via the legacy-replay fallback, not rewritten.

- **D13** Pre-fix events still parse; footer still renders; disqualifying finding present and legible.
  [EVIDENCE] The app rendered the footer around the pre-fix five events all session without error. A `finding` event timestamped `2026-08-19T13:02:32Z` is present in the log, legible (aside from a cosmetic typo Tim explicitly said not to worry about), and correctly excludes that occurrence's ~93.5h figure from being read as real trial data.

---

## Not walked, and why

- **D5, D6** — deferred; both are resilience/edge-case checks better done as
  a deliberate, standalone pass rather than folded into a session that was
  actively driving the trial forward. Neither blocks the trial from
  continuing.
- **D7, D8, D9** — cannot be closed before the trial reaches ten ruled
  cards, by design (open-ended trial, per the 2026-08-19 addendum). Current
  state recorded above so this log is honest about where the trial stands,
  not silent about it.

This results log will be re-walked and re-stamped as the trial progresses,
most importantly once D7 reaches ten.
