# Cowork brief — Phase 0: the Quartermaster frame is ratified before anything is built

**Origin:** vision thread, 2026-08-17 (`docs/investigation/2026-08-17_quartermaster_fable_2-response.md`
— vision and plan, consolidated), off a cold read of the estate at `174e57e` and Tim's
four rulings of the same date.
**Depends on:** DECISIONS **0031** (findings, never verdicts), **0033**
(propose, ratify, execute) — this brief is 0033 applied to a framing.
**Deliverable:** the INTENT append landed after Tim's editing pass, and two
DECISIONS entries — D-A and D-B from the plan — entered as `proposed`,
re-read, and ratified or refused. **No code.** A documentation round, on
purpose: every later phase cites these two entries, so they must exist before
any brief that leans on them is built.

---

## Working rules

- INTENT's own rules govern the append: no facts, no counts, no "currently
  implemented as." The tension notes in the draft
  (`INTENT_append_quartermaster.md`) are editing instructions and must not be
  committed.
- The DECISIONS entries take the next free numbers (0048+ as of `174e57e`;
  confirm against the log at commit time). The plan's D-A/D-B lettering is
  cited in each entry's Source line so the cross-reference survives.
- Ratification is a re-read on a different day than the drafting. Same-sitting
  ratification of your own framing is the rubber stamp 0033 exists to prevent.

## Tasks

1. **INTENT §8 and §4 — both landed 2026-08-18, ahead of this brief.** §8
   carries the narrowing with its cost stated; §4's bullet is amended to point
   at it rather than softened to fit. Task 1 is now **verification, not
   authoring**: read both cold and confirm the amendment is one you would
   defend. The original task text follows for the record: resolve the
   tension with §4's *"nothing closes, links, or reopens without a human."*
   The draft's reconciliation — a policy **is** a human ruling, made once,
   explicitly, revocable in one act — either convinces on re-read or the
   promotion mechanism is cut from the frame (and Phase 4 shrinks
   accordingly). Do not soften §4 to fit; that sentence has receipts.
2. **Enter D-A** (the unit of throughput is a decision; the card anatomy is
   fixed: question, trigger, evidence-with-provenance, costed options,
   default, expiry; silence is an input with a stated consequence).
   **Name `default` and `expiry` as declared-now-inert**: no policy engine
   exists, so every v1 default is `hold` and expiry only re-labels a card
   `aged`. Ratifying them anyway is deliberate — but a field identical on
   every card for months trains the eye past it, so their going live later is
   a change the operator should be told to expect.
   **Policies carry a sunset.** A standing ruling expires unless renewed, and
   renewal is a card carrying that policy's own firing record as evidence. A
   policy that has authorised nothing since the week it was made answers its
   own renewal question. This is preferred to a policy-watching actor for
   INTENT §5's reason: prefer *can't* to *shouldn't*.
3. **Enter D-B**, redrafted 2026-08-18 — the vision's version was a budget
   the toolkit cannot enforce, and is replaced rather than trimmed:

   > **D-B — Frontier conversations are a sensed input. The system moves
   > repeated work down-tier; it does not budget spend it cannot see.**
   >
   > The toolkit does not invoke frontier models, so frontier spend happens in
   > vendor interfaces, outside any ledger. A budget object refusing plans on a
   > self-reported number governs nothing — the mechanism cannot observe the
   > spending it claims to bound.
   >
   > What the estate does have is the conversations themselves: already
   > ingested, already mined for claims. So:
   >
   > 1. **The toolkit invokes no frontier model.** A frontier step in any plan
   >    is a prepared handoff — assembled context and a stated question — never
   >    an API call.
   > 2. **There is no spend envelope and no plan is refused on a spend number.**
   >    A figure nothing observes must not be given the authority to refuse.
   > 3. **The conversation corpus is a sensed input for down-tier
   >    opportunities.** Recurring asks — work of a shape that keeps coming
   >    back — are surfaced as findings.
   > 4. **A down-tier proposal names the local capability that would replace
   >    the ask, and the evidence it can.** Without both, it is a wish.
   > 5. **Success is the recurrence declining in the corpus**, observed — never
   >    a claimed saving, and never the label on a purchase.
4. **Commit `docs/investigation/2026-08-17_quartermaster_fable_2-response.md` and `docs/investigation/2026-08-17_quartermaster_fable_2-response.md` to `docs/`**
   with a header note naming what each is allowed to claim: the vision is a
   want (INTENT-adjacent), the plan is a proposal whose phases each require
   their own brief and ratification.

## Explicitly out of scope

- Any code, any schema, any module. The first line of code belongs to
  Phase 1's brief and lands only after this round closes.
- D-C through D-F. Each is drafted inside the phase that needs it, against
  the code in front of it, per the plan.

## Stop conditions

- A fact appears in the INTENT append → stop; move it to ARCHITECTURE or cut.
- D-A or D-B is ratified in the same sitting it was drafted → stop.
- The §4 tension is left unresolved but the append commits anyway → stop.

## UAT — acceptance checks (Tim walks these)

- `[H]` **The §4 reconciliation, read cold a day later: does it convince?**
  If not, promotion is cut from the frame here, cheaply, rather than from
  Phase 4's built code, expensively.
- `[H]` **Read D-A's card anatomy against a real recent decision you made**
  (any one from the last fortnight). Would that decision have fit the
  anatomy? If it wouldn't, the anatomy is wrong now, before a surface
  hard-codes it.
- `[H]` **Read D-B against your last three frontier spends.** Which of the
  two legitimate purchases was each? If any was neither, is the rule right
  and the spend wrong, or the reverse? Answer honestly; the rule only earns
  ratification if you'd accept it binding you.
- `[G]` INTENT contains no facts after the append; DECISIONS numbering is
  sequential; both new entries carry Source lines naming the vision thread.

## Reporting

`docs/COWORK_REPORT_quartermaster_frame.md`: the append as landed, both
entries' final numbers, and — most importantly — what the editing pass
*changed* from the drafts, since that delta is the first real test of whether
this frame survives contact with its operator.
