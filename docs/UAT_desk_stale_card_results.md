<!-- uat: commit=d4d65c4 dirty=true host=LucasGoonPC walked=2026-08-28 -->

# Results log — Decision Desk, stale-output triage (re-walked 2026-08-28, LucasGoonPC) — D7/D8/D9 CLOSED

> **Re-walk, 2026-08-28.** The trial reached ten. D7, D8 and D9 were deferred on
> 2026-08-20 pending that, and are answered below; every other item's verdict is
> untouched and still reads as of 2026-08-19/20. The stamp is re-cut to the
> commit this walk ran against.
>
> **On the freeze.** `CONVENTION_docs.md` §2 holds that a `_results` log is
> frozen. This one was stamped **INTERIM** on Tim's explicit call of 2026-08-19,
> against the brief's own Reporting section, precisely so it could be revised
> when the trial closed — and its closing line said it would be. Revising it is
> therefore what the file asked for rather than a breach. **The convention has no
> carve-out for an interim results log and should probably grow one**; recorded
> here rather than fixed in passing.
>
> **What the re-walk changed, beyond the three verdicts:** D7's note that the
> trial was *"entirely on `uat-decisions-fixture`, not yet on
> `l5gn-tools-fixture`'s real `estate_freshness` stage"* was true when written and
> is **out of date** — the real card fired three times. That correction is made in
> place because leaving a superseded worry standing reads as a live one.

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
  [EVIDENCE — trial closed] **Ten reached: `cards_raised: 10, cards_ruled: 9, cards_resolved_without_ruling: 1`, median 21.6h.** Was the evidence enough, or did I go hunting? **Enough — no finding was ever logged against a card's evidence** across the whole trial; the log's two `finding` events are D13's disqualification and one about the instrument. The honest qualification, which D9 carries: **ten occurrences came from three fingerprints, two of them hand-edited UAT fixtures.** The real card contributed **three occurrences, one disqualified by D13, so n=2 clean.** A ten that is two is what Phase 2 inherits, and it is named rather than netted.

  **The 2026-08-20 note below is superseded and left standing as the record of what was true then.** It read that the trial was *"entirely on `uat-decisions-fixture`, not yet on `l5gn-tools-fixture`'s real `estate_freshness` stage"*. The real card fired on 2026-08-18, 2026-08-20 and 2026-08-24. The worry was legitimate when written and is discharged.

  **Original 2026-08-20 note.** Recomputed directly from `data/desk/events.jsonl` via `desk.latency_summary()` itself (not by hand): **`cards_raised: 5, cards_ruled: 4, cards_resolved_without_ruling: 1`** as of this walk (2026-08-20). The four ruled: the pre-fix button-test occurrence on `57860823ba56...` (disqualified, see D13), the 2026-08-19 recurrence on `652d40c4fd26...`, the Trigger B occurrence on `78a5d9f55fb2...`, and a fresh recurrence on `652d40c4fd26...` sighted and ruled today, 2026-08-20T11:37–11:38Z — the first occurrence in this log genuinely spaced by more than a day from its predecessor rather than clustered inside one testing session. Six to go. No "hunt" findings have been logged against a card itself yet (one finding has been logged about the *instrument*, not a card — see the new project_wizard.py-untested finding, out of scope for this sheet); evidence on the cards has been sufficient so far, but the sample is still small and entirely on `uat-decisions-fixture`, not yet on `l5gn-tools-fixture`'s real `estate_freshness` stage.

- **D8** The latency footer at trial's end: is the number believable?
  [EVIDENCE] **No — believable as arithmetic, misleading as a decision-latency figure, and the reason is worth more than the number.** The footer reads `median 21.6h` at trial's end. Reconstructed from `data/desk/events.jsonl` independently of `latency_summary()` and landing on the same 21.59h, the split is: **fixture occurrences median 10.05h (n=6, one at 169.63h)**; **real-card occurrences 24.36h and 85.34h (n=2 clean, after D13's 93.50h disqualification)**. So **the headline median is carried by the two hand-edited UAT fixtures**, and the one card doing a real job — `estate_freshness` on the dev rig — was ruled between one and three and a half days after its condition became observable, against a 24h staleness threshold. The number is not wrong; it is an average over two populations that should never have been averaged, and a footer that cannot say which is which will keep producing it. Recorded as a defect in the instrument's reporting, not in the trial.

- **D9** The falsifier, answered in one paragraph, yes or no.
  [EVIDENCE] **Yes — and the sample is n=2, taken knowingly.** The falsifier has two limbs and they do not resolve alike. *Did cards reach me with the evidence I actually needed?* — **yes**: across ten occurrences no finding was ever logged against a card's evidence, the two `finding` events in the log being D13's disqualification and one about the instrument. That is a real answer on a thin sample. *Is decision latency visibly better than patrol-and-remember?* — **this limb cannot be answered, and could not have been since 2026-08-19**, when the silent week that was to build the patrol baseline was cut. The Addendum was right to cut it and recorded why the instrument could not do the job; what nobody recorded is that cutting it left this half of a program-gating falsifier with no instrument, permanently. Reaching ten did not fix that and nothing will. So the yes rests on limb 1 plus judgement, not on the comparison the test asked for. **Ruled yes anyway**, deliberately: the Desk is worth keeping given more to decide on, and waiting for a comparison that cannot be built is a worse error than proceeding on a stated n=2. Phase 2 inherits this qualification rather than a clean pass, and this paragraph is what it inherits.

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
- **D7, D8, D9** — **closed 2026-08-28.** Superseded; the 2026-08-20 text is
  kept below as the record of what was deferred and why.

  *"cannot be closed before the trial reaches ten ruled cards, by design
  (open-ended trial, per the 2026-08-19 addendum). Current state recorded above
  so this log is honest about where the trial stands, not silent about it."*

  **That reason was right for D7 and D8 and wrong for D9**, and the difference
  only became visible at ten: D7 and D8 were waiting on sample size, which
  arrived. D9's second limb was waiting on a baseline that had already been
  cancelled six days earlier. Reaching ten was never going to answer it. **A
  deferral that names the wrong blocker looks identical to one that names the
  right blocker, and keeps looking identical right up until the blocker is
  supposed to clear** — which is this trial's most transferable finding and
  belongs to the practice, not to the Desk.

This log was re-walked and re-stamped on 2026-08-28 when D7 reached ten, as its
2026-08-20 revision said it would be. **The trial is closed.** Further Desk work
opens its own round.

---

## Correction, 2026-09-02 — `gate=` removed from the stamp

**No verdict above is changed**, and the trial stays closed. The stamp's
`gate=12a/81t` field was removed; `commit=` and `walked=` stand, and they are
what `auditor_uat_stamp` requires.

**Why.** Registering a thirteenth auditor on 2026-09-02 turned this log red.
`auditor_uat_stamp` compares `gate=` — a fact about the moment of the walk —
against `verify.py`'s count at HEAD. That comparison has two stable outcomes
over time: the gate goes red whenever gate composition changes, or historical
stamps get re-cut to match. **The second is laundering a number into a document
to satisfy a check, which is the incident that auditor's own docstring says it
was built to catch.**

`gate=` is optional in that auditor, and it duplicates something `commit=`
already fixes — check out that commit and count the lists. Removing a
denormalised copy is not losing provenance; keeping one beside its source is how
the two drift.

**This log's note above already saw the neighbouring gap** — *"the convention
has no carve-out for an interim results log and should probably grow one"*. This
is the same seam from the other side: a frozen log's claims keep being measured
against a moving tree. **The auditor is not fixed by this edit and should be**,
by resolving `gate=` against the census at the stamped commit. That is a code
change, outside the round that found it, and wants its own card.
