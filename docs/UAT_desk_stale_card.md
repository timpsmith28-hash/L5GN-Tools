<!-- uat: commit=fb6fa5c dirty=true host=LucasGoonPC walked=YYYY-MM-DD -->

# UAT — the Decision Desk's first card, stale-output triage (DECISIONS 0048/0049)

Walk against `docs/COWORK_BRIEF_desk_stale_card.md`'s acceptance checks,
including the four added by Addendum (b), 2026-08-19. Mark each `[G]`/`[H]`
per 0031 as you go. **None of the `[G]` items on this sheet are registered
as `verify.py` auditors** — the brief never asked for one, so `[G]` here
means "deterministic to check, not a matter of judgement," not
"gate-checked by the machine." Fill in `walked=` above with the date you
actually do this pass; the running results log lives in
`docs/UAT_desk_stale_card_results.md` and gets a fresh `walked=` stamp of
its own each time it's updated, because — unlike most rounds — this one is
explicitly a long-running trial: the brief's own line is "open-ended...
until ten real cards have been ruled," so this sheet gets walked more than
once before it's done.

---

- [ ] **D1. `[G]`** A repo with a delegated-freshness stage reporting stale
  raises exactly one card, whose trigger quotes the delegated command's
  answer verbatim (0042 clause 7) — not a re-derived or paraphrased
  verdict.

- [ ] **D2. `[G]`** A `depends_on` pair, where A's run marker or output is
  newer than B's, raises a card showing both timestamps; running B (via the
  card's "Rebuild now", or directly through Project Wizard) clears the card
  on the *next* render — because the underlying facts changed, not because
  the card was marked done client-side.

- [ ] **D3. `[G]`** The same standing staleness across many renders stays
  one fingerprint with one sighting event, ageing in place — never a
  duplicate card, and never a duplicate sighting, per render.

- [ ] **D4. `[G]`** `POST /api/desk/rule` refuses an unknown fingerprint and
  an empty dismiss-reason; no Desk route ever accepts a repo path or an
  argv.

- [ ] **D5. `[G]`** Kill the deck process mid-ruling: `data/desk/events.jsonl`
  is still valid JSONL afterward (append-only survives a hard kill), and
  the board re-derives identically once the app restarts.

- [ ] **D6. `[G]`** With an empty allowlist, the Desk renders an honest
  empty state — not an error, not a blank crash.

- [ ] **D7. `[H]`** **Rule ten real cards over the trial.** Was the evidence
  already on the card enough, or did you have to leave the Desk to go
  hunting? Every hunt is a finding naming what was missing, logged via
  `append_finding()`.

- [ ] **D8. `[H]`** At the point the tenth card is ruled: is the latency
  footer's number believable, and does it move against your own memory of
  patrol-and-remember?

- [ ] **D9. `[H]`** The falsifier, answered in one paragraph, yes or no:
  *did cards reach you with the evidence you actually needed, and did you
  rule on them rather than scroll past?* A no is a successful experiment
  and a cancelled programme for Phases 2–5 — say plainly which this was.

### Added by Addendum (b), 2026-08-19 — the occurrence-model fix

- [ ] **D10. `[G]`** Let a fixture card resolve and re-raise (rebuild, wait
  for staleness to return, re-render): the log shows a **second** sighting
  for the same fingerprint, and the second occurrence's latency is measured
  from *its own* `condition_first_observable`, not the first occurrence's.

- [ ] **D11. `[G]`** Rule the same still-open card more than once (e.g.
  snooze, snooze, rebuild without the card clearing in between): **one**
  latency figure results, timed from the *first* ruling; `cards_ruled`
  increments by exactly one for that occurrence, not once per ruling.

- [ ] **D12. `[G]`** Every ruling event written after the fix landed carries
  an explicit `occurrence_started_at` field — never left for a reader to
  re-infer from timestamp ordering.

- [ ] **D13. `[G]`** The five pre-fix events (the button-test sequence on
  fingerprint `57860823ba56c2c7`) still parse without error, the footer
  still renders around them, and the disqualifying `finding` event logged
  against them is present and legible in `events.jsonl`.

---

## Notes for the walk

- This fixture (`uat-decisions-fixture`, `C:\Users\timps\Documents\GitHub\uat_decisions_fixture`)
  exists solely to give the trial real, hand-controllable triggers on
  `LucasGoonPC` without waiting on `L5GN-Tools`'s own estate-build cadence.
  It is a fixture, not a pilot, on the same posture as `l5gn-tools-fixture`
  — walking items against it counts toward D1–D6 and D10–D13, but D7–D9 ask
  about the trial as a whole, which also includes whatever real cards the
  `estate_freshness` stage on `l5gn-tools-fixture` raises over the same
  period.
- D5 (kill mid-ruling) is destructive by nature — force-closing the server
  window at the moment of a click. Do it deliberately, not as a side effect
  of something else going wrong, so the evidence is unambiguous either way.
- D7–D9 cannot be marked complete until the trial ends (ten cards ruled).
  Everything else is walkable now and should be, incrementally, as you use
  the fixture — that's the whole reason this sheet (and its results log)
  exist ahead of the trial's end, at Tim's explicit call on 2026-08-19.
