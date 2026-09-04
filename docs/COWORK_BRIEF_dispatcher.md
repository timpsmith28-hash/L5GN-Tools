# Cowork brief — Phase 4: the Dispatcher — the Conductor learns the ladder, rulings learn to execute

> **Draft status:** written 2026-08-17, three phases ahead of its build.
> This is the most speculative brief in the set and says so: **D-F is
> deliberately not drafted here** — it must be written against the code and
> the ruling corpus that exist when this round opens. Re-verify everything;
> expect this brief to be rewritten, and treat that rewrite as the round's
> first task.
>
> **Amended 2026-08-19 (design thread).** D-B was redrafted before
> ratification and landed as **0049**, which removes the frontier envelope
> outright: *there is no spend envelope, and no plan is refused on a spend
> number*. The envelope was one of this brief's five tasks, one of its
> working rules, a stop condition, a UAT check and a reporting line — all
> struck below, and the strike is recorded rather than silently absorbed,
> because a reader comparing this brief to the vision it came from should be
> able to see that a piece was ruled out rather than forgotten. What replaces
> it is not a smaller budget: it is an **observation** mechanism (0049
> clauses 3–5), and its home is Phase 3, beside the Curator's linking work,
> not here. The round shrinks to ladder + escalation + promotion.
>
> **Amended 2026-09-04 (design thread, Cards C and D).** **Task 3 —
> promotion detection — is struck and carved out to `Card D`,
> `COWORK_BRIEF_promotion_step.md`**, which builds it against the Desk's real
> ruling corpus rather than waiting on Phases 2 and 3. The strike is recorded
> rather than silently absorbed, on the same reasoning as the 0049 strike
> above: a reader of either brief should find the other, and two live briefs
> specifying one mechanism means the second one built wins by accident.
>
> **One substitution inside the carve-out, named.** Task 3 wanted *"the policy
> as a ledger event with parent citations"*; there is no ledger — it is Phase 2
> — so Card D writes a tracked, machine-appended standing-rulings file instead,
> keeping the ledger row's shape (parent citations by fingerprint and
> timestamp, appended, never edited, staged never committed) so that Phase 2's
> migration is a reader change and not a redesign. **That widening is argued in
> Card D's brief, not here.**
>
> **What this leaves for Phase 4:** the ladder, escalation, and **policy
> execution** — the planner consulting ratified policies, and a policy-taken
> step logged as such. Card D produces standing rulings and deliberately makes
> nothing act on them; Task 4 below is where they acquire consequence. The
> renewal card that 0048 clause 5 requires is sequenced immediately after Card
> D and is not Phase 4's either.

**Origin:** `docs/investigation/2026-08-17_quartermaster_fable_2-response.md` Phase 4; the vision's economic-router
core (§3.4, §5).
**Precondition:** Phases 2 and 3 closed; a ruling corpus of real Desk events
exists (promotion detection is meaningless without one); the INTENT §4
reconciliation from Phase 0 survived — if promotion was cut there, Tasks 3–4
below are void and this brief shrinks to Tasks 1–2. **And one more, added
2026-08-19:** `COWORK_BRIEF_model_bench.md`'s Task 0 control has been taken
and its **detectable-difference floor** reported. Task 1's ladder cannot
declare an acceptance check per tier without knowing the smallest difference
the bench can actually see; a tier boundary drawn inside the instrument's own
noise is a fabricated distinction, which is the failure 0037 clause 4 already
refuses in the estimation case.
**Depends on — this repo's rulings:** **0037** (every clause — this round is
its generalisation, not its replacement), **0042** (manifest execution
posture), **0031**, **0033**, **0048** (D-A as ratified: the card anatomy),
**0049** (D-B as ratified and redrafted: no envelope, no refusal on a spend
number), **0050** (staleness and other card sources are declared feeds — an
escalation card is a raised item, not a new branch), D-C/D-E as ratified, and
**D-F — drafted and ratified at round-open** (the tier ladder and escalation
posture as a named widening of 0037/0042).
**Deliverable:** the Conductor's planning generalised across the tier ladder
(T0 script / T1 small local / T2 large local / T3 frontier); escalation
proposals as cards; ~~policy promotion and~~ — **struck, Card D** — policy
execution with one-act revocation.
~~the frontier envelope as a budget object~~ — **struck, 0049.** The
Conductor's disciplines — ratified plans, declared parameter schemas,
measurement before estimation, refuse-don't-clamp, stop-on-failure — apply
unchanged at every tier.

---

## Working rules

- **Tier is declared where stages are declared** — the stage-table /
  manifest layer, per 0042's single-declaration-point rule. A stage without
  a declared tier plans as its most expensive plausible tier, loudly.
- **Escalation is proposed, never taken.** A stage failing its acceptance
  check raises a card: the failure evidence, the next tier up, the cost in
  all three currencies where measured. The operator (or a ratified policy)
  rules. This is 0049's judgment-that-unblocks route made mechanical — and,
  when the tier above is T3, what the card authorises is a **prepared
  handoff**, never a call (0049 clause 1).
- **A policy is a ruling that executes with citation.** ~~Promotion detection
  reads ruling events only — three matching rulings on a card shape raise
  the "promote?" card;~~ **struck 2026-09-04, Card D** — and note that the
  struck clause fixed the threshold at three without a count behind it, which
  is the fabricated distinction 0037 clause 4 refuses; Card D ratifies N
  against the corpus instead. What stands: a ratified policy cites its parent
  rulings by event id; revocation is one act and takes effect at the next
  plan, not the next edit. A policy whose parents cannot be traced from the
  record that holds it is a defect.
- ~~**The envelope is honest about being self-reported.**~~ **Struck, 0049.**
  No plan is refused on a spend number, and no surface here sums one. If
  spend events exist at all, they are records, not a budget, and nothing in
  this round reads them to decide anything.
- **Calibration precedes estimation at every tier**, spread not just mean —
  the T2 ledger discipline extended, never shortcut. No measurement, no
  estimate, stated plainly (0037 clause 4). **A tier's acceptance threshold
  may not be set finer than the bench's detectable-difference floor**; where
  it would be, the check says "indistinguishable at this bench" rather than
  picking a number.
- **T3 is never invoked by the toolkit.** For work, structurally out of
  scope; for personal, v1 keeps the human in the loop — a T3 step in a plan
  is a *prepared handoff* (assembled context, stated question, spend event
  on completion), not an API call. Direct invocation, if ever wanted, is
  its own decision with its own entry.

## Tasks

1. **The ladder declared.** Tier + acceptance check per stage across the
   stage table and wizard manifests (schema_version bump, per the manifest's
   own versioning rule — note the manifest will already be at v2 or later
   from `COWORK_BRIEF_staleness_feeds.md`, so this is a further bump, not a
   first one). Plans state their tier mix and three-currency cost. **Each
   acceptance check cites the bench floor it was set against**, or states
   that no measurement exists and therefore no threshold was set.
2. **Escalation cards.** Failure → card with evidence and costed next-tier
   option; ruled through the Desk; run/cost events on every outcome.
3. ~~**Promotion detection.** The repetition detector over ruling events; the
   "promote?" card; the policy as a ledger event with parent citations.~~
   **Struck 2026-09-04, carved out to Card D** —
   `COWORK_BRIEF_promotion_step.md`. This round inherits standing rulings; it
   does not detect or write them. Task 4 below still owns what a ratified
   policy *does*.
4. **Policy execution.** The planner consults ratified policies when
   drafting plans (a policy-authorised card shape plans without raising);
   every policy-taken step is logged as such; revocation walked, one act.
5. ~~**The envelope.**~~ **Struck, 0049** — a figure nothing observes must
   not be given the authority to refuse a plan. Nothing replaces it in this
   round; the observation mechanism that took its place (recurring asks
   surfaced as findings, 0049 clauses 3–5) belongs to Phase 3.

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
- **A plan is refused, delayed, or altered on the basis of a spend number →
  stop** (0049 clause 2). This replaces the struck envelope stop condition,
  and inverts it: the failure to watch for is no longer "the envelope stops
  saying it is self-reported" but "an envelope reappears at all", under any
  name — allowance, budget, cap, quota.
- An acceptance threshold is set finer than the bench's measured
  detectable-difference floor → stop; that is a fabricated distinction, and
  it will route work to a tier on noise.

## UAT — sketch (rewrite at round-open)

- `[G]` 0037's full existing walk, re-run unchanged, green at every tier.
- ~~`[G]` Promotion fires only at the declared repetition threshold; the
  policy cites its parents; revocation walked mid-week and honoured at the
  next plan.~~ **Struck, Card D** — the first two clauses are Card D's walk.
  What survives here is its second half, restated as this round's own:
  `[G]` a standing ruling written by Card D is **honoured at the next plan**,
  and a revocation walked mid-week is honoured at the plan after it.
- `[G]` ~~An over-envelope plan refuses with the stated remedy.~~ **Struck,
  0049.** Replaced by its inverse: `[G]` **no plan anywhere in the round is
  refused or altered on a spend number**, and a search of the round's diff
  for a budget-shaped object finds none.
- `[H]` **One real week of policy-planned overnight windows**: was the
  morning state comprehensible without reading a log (the conductor brief's
  own honest test), and did estimate-versus-actual hold across tiers?
- `[H]` **The 2am test, asked of the whole loop**: could you debug a
  policy-planned, escalated, multi-tier night alone? If not, this shipped
  too big — shrink it, per the plan's standing risk 3.

## Reporting

`docs/COWORK_REPORT_dispatcher.md` + walk-sheet + stamped results. Record:
D-F as ratified; the ladder as declared, with the bench floor each acceptance
check was set against; ~~every policy promoted during the round with its
parents~~ (**struck, Card D** — replaced by: every standing ruling this round
*acted on*, with the plan it changed); ~~the envelope's first month of self-reported spend~~ (struck,
0049); and estimate-versus-actual per tier — still the most useful number on
any page.
