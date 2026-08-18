# Cowork brief — Phase 4: the Dispatcher — the Conductor learns the ladder, rulings learn to execute

> **Draft status:** written 2026-08-17, three phases ahead of its build.
> This is the most speculative brief in the set and says so: **D-F is
> deliberately not drafted here** — it must be written against the code and
> the ruling corpus that exist when this round opens. Re-verify everything;
> expect this brief to be rewritten, and treat that rewrite as the round's
> first task.

**Origin:** `docs/investigation/2026-08-17_quartermaster_fable_2-response.md` Phase 4; the vision's economic-router
core (§3.4, §5).
**Precondition:** Phases 2 and 3 closed; a ruling corpus of real Desk events
exists (promotion detection is meaningless without one); the INTENT §4
reconciliation from Phase 0 survived — if promotion was cut there, Tasks 3–4
below are void and this brief shrinks to Tasks 1–2 and 5.
**Depends on — this repo's rulings:** **0037** (every clause — this round is
its generalisation, not its replacement), **0042** (manifest execution
posture), **0031**, **0033**, D-A/D-B/D-C/D-E as ratified, and **D-F —
drafted and ratified at round-open** (the tier ladder and escalation posture
as a named widening of 0037/0042).
**Deliverable:** the Conductor's planning generalised across the tier ladder
(T0 script / T1 small local / T2 large local / T3 frontier); escalation
proposals as cards; policy promotion and execution with one-act revocation;
the frontier envelope as a budget object. The Conductor's disciplines —
ratified plans, declared parameter schemas, measurement before estimation,
refuse-don't-clamp, stop-on-failure — apply unchanged at every tier.

---

## Working rules

- **Tier is declared where stages are declared** — the stage-table /
  manifest layer, per 0042's single-declaration-point rule. A stage without
  a declared tier plans as its most expensive plausible tier, loudly.
- **Escalation is proposed, never taken.** A stage failing its acceptance
  check raises a card: the failure evidence, the next tier up, the cost in
  all three currencies where measured. The operator (or a ratified policy)
  rules. This is D-B's first purchase route made mechanical.
- **A policy is a ruling that executes with citation.** Promotion detection
  reads ruling events only — three matching rulings on a card shape raise
  the "promote?" card; a ratified policy cites its parent rulings by event
  id; revocation is one act and takes effect at the next plan, not the next
  edit. A policy the ledger cannot trace to its parents is a defect.
- **The envelope is honest about being self-reported.** Frontier spend
  events are operator-entered (or operator-confirmed) estimates and say so
  on every surface that sums them; a plan that would exceed the envelope
  refuses, per the refuse-don't-clamp rule.
- **Calibration precedes estimation at every tier**, spread not just mean —
  the T2 ledger discipline extended, never shortcut. No measurement, no
  estimate, stated plainly (0037 clause 4).
- **T3 is never invoked by the toolkit.** For work, structurally out of
  scope; for personal, v1 keeps the human in the loop — a T3 step in a plan
  is a *prepared handoff* (assembled context, stated question, spend event
  on completion), not an API call. Direct invocation, if ever wanted, is
  its own decision with its own entry.

## Tasks

1. **The ladder declared.** Tier + acceptance check per stage across the
   stage table and wizard manifests (schema_version bump, per the manifest's
   own versioning rule). Plans state their tier mix and three-currency cost.
2. **Escalation cards.** Failure → card with evidence and costed next-tier
   option; ruled through the Desk; run/cost events on every outcome.
3. **Promotion detection.** The repetition detector over ruling events; the
   "promote?" card; the policy as a ledger event with parent citations.
4. **Policy execution.** The planner consults ratified policies when
   drafting plans (a policy-authorised card shape plans without raising);
   every policy-taken step is logged as such; revocation walked, one act.
5. **The envelope.** A budget object beside the thermal profiles in
   machine config; spend events drawn against it; refusal walked.

## Explicitly out of scope

- Direct frontier API invocation from the toolkit, any tier's auto-
  escalation without a ratified policy, cross-machine anything (0036),
  scheduling-as-cadence (still a human-started budget, 0037's boundary),
  and distillation artifacts (Phase 5).

## Stop conditions

- A caller-supplied parameter reaches a subprocess; a clamp instead of a
  refusal; a plan executes unapproved — 0037's stops, verbatim, at every
  tier → stop.
- Anything escalates a tier without a ruling or a cited policy → stop.
- A policy exists whose parent rulings cannot be listed from the ledger →
  stop.
- Revocation takes more than one act, or a revoked policy influences a
  plan → stop.
- The toolkit invokes a frontier endpoint directly → stop.
- The envelope's self-reported nature disappears from any surface that
  shows it → stop (a precise-looking number nobody measured is the
  fabricated window 0037 forbids).

## UAT — sketch (rewrite at round-open)

- `[G]` 0037's full existing walk, re-run unchanged, green at every tier.
- `[G]` Promotion fires only at the declared repetition threshold; the
  policy cites its parents; revocation walked mid-week and honoured at the
  next plan.
- `[G]` An over-envelope plan refuses with the stated remedy.
- `[H]` **One real week of policy-planned overnight windows**: was the
  morning state comprehensible without reading a log (the conductor brief's
  own honest test), and did estimate-versus-actual hold across tiers?
- `[H]` **The 2am test, asked of the whole loop**: could you debug a
  policy-planned, escalated, multi-tier night alone? If not, this shipped
  too big — shrink it, per the plan's standing risk 3.

## Reporting

`docs/COWORK_REPORT_dispatcher.md` + walk-sheet + stamped results. Record:
D-F as ratified; the ladder as declared; every policy promoted during the
round with its parents; the envelope's first month of self-reported spend;
and estimate-versus-actual per tier — still the most useful number on any
page.
