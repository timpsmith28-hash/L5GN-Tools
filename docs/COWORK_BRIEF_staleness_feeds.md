# Cowork brief — Phase 1b: staleness becomes a declared feed, not a trigger type

> **Draft status:** written 2026-08-19 in the design thread that followed the
> Desk's first build round. It describes the code in front of it (`desk.py`
> at the 2026-08-19 addendum state, `project_wizard.py` at
> `MANIFEST_SCHEMA_VERSION = 1`) and must be re-verified against the tree at
> round-open like every other brief here.

**Origin:** design thread, 2026-08-19 — the Desk exists and works, and the
next thing asked of it is a third source of staleness (the work rig's
cloud-export manager). That request is the one this brief refuses to answer
the obvious way.
**Precondition — hard:** Phase 1's falsifier answered in
`docs/COWORK_REPORT_desk_stale_card.md`, with its stamped results, after ten
real cards. **Nothing in this brief is built while that trial runs** — the
trial's own stop condition ("card thresholds tuned mid-trial → stop") covers
tuning, and this round is larger than tuning. It is design work on calendar
time; it costs the trial nothing and must not touch it.
**Depends on — this repo's rulings:** **0042** (a consumer repo declares its
own runnable stages; the toolkit executes only what a committed allowlist
names, never widens what a repo can do, and **delegates freshness rather than
re-deriving it** — clause 7 is this brief's spine), **0048** (the card
anatomy; a card missing any field is not raised), **0037** (the caller names
the work, never the parameters of it; no measurement, no estimate),
**0047** (there is one process; the Desk is a module in it), **0025** and
**0036** (a loopback single-estate surface is not gated; the mesh stands
down), **0031**, **0033**.
**Ratify before code:** **0050** — *a source declares its own staleness as a
feed; the Desk consumes feeds, and a source the Desk cannot reach reads as
unknown, never as fresh* — drafted alongside this brief and entered as
`proposed`. This brief may not be built while 0050 is `proposed`.
**Deliverable:** `staleness_feed` as a declared, validated manifest section
(schema_version 2); `desk.py`'s card derivation restructured so the two
existing triggers and every future feed are **providers of the same item
shape**, not sibling `if` branches; **source-declared options, so a ruling
records which way the operator decided rather than merely that they looked**
(0050 clause 8); a feed-health line that makes an unreachable source visible;
the **workcycle feed** as this rig's first declared feed and the first real
use of the cadence clause; and the two-desk posture stated so the work rig's
instance is a copy of the contract, never a member of a mesh.

---

## The thing this round exists to prevent

`desk.py` today knows two triggers, both derived from wizard manifests and
both hard-coded in `cards()`: delegated staleness (Trigger A) and dependency
staleness (Trigger B). They were the right shape for one card type on one
fixture.

The next source of staleness is a cloud-export manager on the work rig that
already knows, on its own terms, which exports are stale. The obvious move is
a third branch in `cards()`. The move after that is a fourth for
`sf-data-service`, and a fifth for whatever follows — at which point the Desk
is the pre-registry deck again: one surface accumulating a special case per
source, each requiring a change to this repo before another repo's staleness
can be seen at all.

The seam is already proven twice in this estate: `modules.ModuleDescriptor`
turned "a tab" into a registration, and 0042 turned "a runnable stage" into a
declaration in the repo that owns the work. **The Desk should consume a
declared feed the same way.** A source declares what is stale, in data, in
its own committed manifest; the Desk renders that answer as cards and never
computes a competing one. That is 0042 clause 7 generalised from one answer
per stage to a list per repo — not a new principle, the existing one applied
one notch wider.

## The contract

### `staleness_feed` — a new, optional top-level manifest section

```jsonc
{
  "schema_version": 2,
  "repo_name": "...",
  "stages": [ ... ],                    // unchanged
  "staleness_feed": {
    "command": ["<abs interpreter>", "feed.py"],   // literal argv, no parameter slot (0042 clause 4)
    "cwd": ".",                                     // resolved contained, as stages are (0042 clause 5)
    "timeout_seconds": 20
  }
}
```

One feed per repo, not one per stage: the stage is the wrong unit for a
source whose staleness is about *data*, not about *this repo's outputs*. A
repo may declare stages, a feed, both, or neither.

### The item shape the feed prints

Stdout, one JSON object (not a bare array — a wrapper leaves room to version
the payload without a second schema fight):

```jsonc
{
  "feed_version": 1,
  "generated_at": "2026-08-19T08:15:00Z",
  "items": [
    {
      "key": "activity_statements",              // stable within this repo; the fingerprint's second component
      "kind": "staleness",                       // staleness | pending_decision; default "staleness"
      "label": "Monthly activity statements",
      "state": "stale",                          // stale | fresh | unknown
      "observable_since": "2026-08-06T00:00:00Z",// when this became true — the latency clock's anchor
      "evidence": [                              // shown verbatim; never re-derived
        "last statement: 2026-07-05 (July period)",
        "August period due by 2026-08-05 — 14d overdue"
      ],
      "options": [                               // OPTIONAL; the defaults below apply when absent
        {"id": "rebuild", "label": "Rebuild now",
         "action": {"repo_key": "…", "stage_key": "…"}},
        {"id": "snooze",  "label": "Snooze", "requires": "until"},
        {"id": "dismiss", "label": "Dismiss", "requires": "reason"}
      ]
    }
  ]
}
```

**Field by field, against 0048's anatomy** — because the point of a contract
is that a feed cannot produce a card the Desk would have to fake a field for:

- `key` — stable, source-owned. The Desk fingerprints
  `(repo_key, "feed", key)`. A feed that renames a key raises a new card and
  resolves the old one, and that is correct: the source changed its mind
  about what the thing is.
- `state` — a **verdict from the source**, not a number the Desk thresholds.
  0042 clause 7: the source answers the question about itself. Only `stale`
  raises a card. `unknown` raises nothing but is counted in feed health
  (below).
- `observable_since` — **mandatory when `state` is `stale`.** It is the only
  honest answer to *when did this become observable*, which is Phase 1's
  latency clock. Today `desk.py` recovers this by parsing `generated_at=` out
  of a delegated freshness string; the feed contract makes it a declared
  field instead of a regex against prose. **An item without it is not a card**
  — 0048 clause 2, enforced at parse rather than at render.
- `evidence` — a list of strings, shown verbatim, each line a fact the source
  is prepared to stand behind. No structure imposed: the Desk is not going to
  parse them, and the moment it does, the second freshness engine 0042
  forbids has been built by accident.
- `options` — **the ruling vocabulary belongs to the card** (0050 clause 8).
  Absent, the item gets the staleness default set (`rebuild` / `snooze` /
  `dismiss`), which is what Triggers A and B produce today and must keep
  producing unchanged. Present, it replaces that set entirely, and
  `POST /api/desk/rule` validates the submitted ruling **against the options
  that card actually offered** rather than against `VALID_RULINGS`. This is
  the difference between recording *"I ratified this"* and *"I dismissed a
  notification"*, and the distinction is not cosmetic: promotion detection
  (Phase 4, 0048 clause 5) reads ruling verbs and reasons, so a vocabulary
  that flattens every non-run outcome into `dismiss` destroys the signal
  before it is ever collected. The `requires` key names a field the ruling
  must carry (`until`, `reason`) — the existing refusals in `rule()`,
  declared per option instead of hard-coded per verb.
- `action` — an option's optional half, and its optionality is the
  interesting part. When present it must name an **existing `(repo_key,
  stage_key)` pair from a validated manifest in this host's allowlist**,
  checked at feed-parse time; the button posts the wizard's existing execute
  route with exactly that pair. When absent, choosing that option **records
  the decision and runs nothing** — a first-class outcome, not a lesser one
  ("the statement is overdue; the fix is not a button"; "I ratified the
  entry; the edit is mine to make"). The Desk gains no execution path either
  way (0037, 0042; Phase 1's own standing stop condition).

### Cadence, because two of the real sources are cadence-shaped

The mtime-and-dependency triggers can express *"B is older than A"*. They
cannot express *"the monthly statement was due on the 5th"* or *"the nightly
sync should have run last night"* — and the first two work-rig sources that
matter are exactly those. Rather than teach the Desk a calendar, the contract
puts cadence where 0042 already puts freshness: **in the source**. A
cadence-shaped feed item is an ordinary item whose `state` its own source
computed from its own schedule, and whose `evidence` lines say the schedule
out loud. The Desk holds no cron, no expected-interval field, and no opinion
about the 5th of the month.

The cost, stated: a source with a broken clock reports confidently wrong
staleness and the Desk repeats it. That is the same trade 0042 clause 7 took
knowingly, and the mitigation is the same — the answer is quoted verbatim
with its source named, so a wrong card is legibly *that source's* wrong
answer rather than an anonymous system claim.

### The workcycle feed — this rig's first declared feed

The obvious first source is not a cloud export or an MCF registry. It is
**this repo's own governance cycle**: a DECISIONS entry drafted and awaiting
its ratifying re-read is a decision the operator has already committed to
making, on a known schedule, with the evidence sitting in a file. The Desk
was built to carry exactly that, and until now it has been pointed only at
build outputs.

**Why it belongs in this round and not a later one.** 0033 requires the
re-read to happen *on a different day than the drafting* — so the item's
`observable_since` is **the drafting date plus one day**, and the card
genuinely cannot be raised before then. That is a schedule the source
computes from its own rule, which is the cadence clause's first real
exercise, available on the personal rig today rather than waiting on the work
rig's statements and syncs. Where a ruling carries no cooling-off requirement,
the same field takes no offset and the item is raisable immediately — one
mechanism, two cases, no special-casing.

**Scope: one item type.** Entries whose status line reads `proposed`. Not
open briefs, not unstamped walk sheets, not archivable pairs — each is
arguably decision-shaped and each would need its own argument, and 0048's bar
is that a surface earns its place by the decisions it moves, one at a time.
Volume is naturally low and matches the operator's real cadence, which is the
whole reason this is a safe first feed.

**Where the dates come from, and the cost of that choice.** The entry's own
`**Date:**` line for drafting, and the status line for ratification — the
convention the log now carries in practice (`**Status:** accepted
2026-08-19`, stamped on 0048 and 0049 at their ratification). Read verbatim
from the file, shown verbatim on the card. The alternatives were git first-commit
time (honest, but blind to an uncommitted entry, and shallow histories make it
unreliable next door) and file mtime (wrong outright — the whole file changes
on every append). **Stated cost:** an in-file date is self-reported and can be
backdated, deliberately or by typo, and the Desk will believe it. That is the
same trade as every other feed here, it makes the round's own UAT trivially
controllable, and it is the field a human reads when they ask the same
question by hand.

**The card ratifies nothing.** Flipping `proposed` → `accepted` is a hand-edit
to `DECISIONS.md`, and Phase 2 makes hand-editing that file a *defect* once it
inverts to a render. So every option on this card is action-less in this
round: `ratify`, `refuse`, `hold`. The ruling records **which way the operator
decided**; the operator makes the edit. When Phase 2's authoring path exists,
`ratify` gains an action that writes a ruling event — the card type improves
at exactly the moment the ledger lands, with no redesign.

**Divergence is self-correcting, and that is the point.** If the ruling says
`ratify` and the file still says `proposed`, the feed keeps reporting it and
the card re-raises. Cards derive; the file is the truth; the ruling is a record
of intent, never an authority over the source (0050 clause 8's closing
sentence, and the reason it closes that way).

**A pleasing consequence worth naming:** the first card this feed raises is
the ratification of **0050** — the ruling that makes feeds possible. It will
be sitting on the board the morning after the entry was drafted, which is
also the first time the Desk has been the reason a decision happened on time
rather than a place where one was recorded afterwards.

**And a practical one:** it is the trial's signal problem answered. The
fixture yields exactly one fingerprint (the 2026-08-19 addendum's N=1
finding, and addendum (b)'s recurrence bug on top of it). A workcycle feed
produces a fingerprint per pending entry, on the operator's own cadence, all
of them real decisions.

### A source that cannot be reached is `unknown`, never fresh

The failure mode this contract must not have is a silent one: a feed command
that times out, exits non-zero, or prints unparsable output produces **no
cards and therefore an empty, reassuring Desk**. `desk.py` today has exactly
this shape for delegated freshness (`if fr.get("error"): continue` — "a
failed delegated command is not evidence of staleness", which is true, and
incomplete).

So: the Desk renders a **feed-health line** naming every declared feed and
its last outcome — `ok (7 items, 0.4s)`, `timed out after 20s`,
`exit 2: <first line of stderr>`, `unparsable: <reason>`. Not a card (a
broken feed has no `observable_since` and would fail the anatomy), but never
invisible either. INTENT §5's fail-loud rule, applied to the one thing an
empty desk cannot distinguish from good news.

## Two desks, one contract, no mesh

The work rig runs **its own Desk instance**, against its own allowlist, its
own manifests, its own sidecar — loopback, single estate, exactly as 0025
permits and 0036 requires. What crosses between rigs is **the feed schema and
the card anatomy**; what never crosses is data, events, cards, or a network
call in either direction. No aggregation view, no "both desks" page, no
shared events file, not now and not as a follow-up.

This is Phase 5's extraction pattern arriving early, and that is acceptable
precisely because of what it consists of: a JSON shape and a local Python
process. Phase 5 still owns the extraction — the packaged contract, the
runner, the import-direction auditor. This round only establishes that the
same shape runs in two places without either knowing about the other.

Recorded consequence: **the two rigs will drift.** The work rig's feed
implementations will teach things the personal rig's contract does not know,
and there is no mechanism here to sync them — deliberately, because the
alternative is a mesh. The reconciliation is a human reading both and
amending the contract in this repo, which is Phase 5's job and is named here
so it is not discovered as a surprise.

## Working rules

- **The Desk computes no staleness.** It renders declared answers. Any
  arithmetic on a feed's numbers beyond parsing an ISO-8601 timestamp is the
  second freshness engine, and it is forbidden (0042 clause 7).
- **The feed runs under the existing containment.** Same allowlist gate, same
  `resolve_contained` on `cwd`, same literal-argv rule, same read-only
  posture. A feed command is a *read*; if a feed's command mutates anything
  it is a defect in that repo, and the toolkit's non-widening rule (0042
  clause 6) is what keeps that from being the toolkit's problem.
- **Feeds are polled on render, with a timeout, and never in the background.**
  The Desk is visited, in v1 (Phase 1's own scope line). Two feeds at 20s
  worst case is a 40s tab; measure it in Task 4 and, if it is bad, the answer
  is a per-render budget with the *overrun stated on the health line*, not a
  cache that quietly ages.
- **Existing fingerprints do not change.** Trigger A and Trigger B keep
  fingerprinting `(repo_key, stage_key, trigger_kind)` exactly as they do
  today. The restructure is internal; the trial's event history must remain
  joinable to the cards it describes. A fingerprint scheme change here would
  silently orphan Phase 1's entire corpus.
- **Cards are still derived, never stored**; events are still the only thing
  written; the sidecar is still the ledger's seed (Phase 2 migrates it,
  feeds included).
- UTF-8 explicit, UTC ISO-8601.

## Tasks

1. **Ratify 0050**, re-read on a different day than drafting (0033). If it
   refuses, this brief is void and the third source gets a third branch,
   knowingly, with that ruling written down.
2. **Schema version 2.** `parse_manifest` gains `staleness_feed` validation
   with the same accumulate-then-refuse discipline it already uses; the
   version literal moves in one place; **v1 manifests still load** (the
   section is optional and its absence is not an error) — or they do not, and
   this brief says which and why at build time rather than discovering it.
   The fixture manifest in this repo gains a feed with two hand-made items,
   one with an `action` and one without, so the round has something to render
   before any real source is wired.
3. **The provider restructure in `desk.py`.** `cards()` becomes a loop over
   providers returning a common item shape: the manifest-derived provider
   (today's Triggers A and B, behaviour unchanged, fingerprints unchanged)
   and the declared-feed provider. `_make_card` fills the D-A anatomy from
   an item and is the single place a card is assembled. **No new module** —
   this is a hundred lines inside the existing one, and a `desk/` package for
   two providers is the over-generalisation the estate keeps not making.
4. **Source-declared options.** The `options` list as specified above;
   `POST /api/desk/rule` validates against the offered options rather than
   `VALID_RULINGS`; `requires` replaces the hard-coded `dismiss`-needs-reason
   and `snooze`-needs-until refusals with the same refusals declared per
   option. **Triggers A and B keep their exact current vocabulary and
   behaviour** by supplying the default set — the trial's rulings must stay
   comparable across this change.
5. **The workcycle feed.** A read-only command in this repo emitting one item
   per `proposed` DECISIONS entry: `observable_since` = the entry's own
   `**Date:**` plus one day (0033's re-read rule), evidence quoting the
   entry's number, title, date and first context sentence, options
   `ratify` / `refuse` / `hold`, no actions. It parses the status convention
   the log actually uses — `proposed`, and `accepted <date>` for a ratified
   one — and it reports `unknown` rather than guessing if a status line does
   not match either shape.
6. **Feed health.** The health line as specified above; `GET
   /api/desk/cards` returns it alongside `cards`; the view renders it where
   an empty desk would otherwise read as "all clear". Measure and record
   per-feed wall clock — the first honest number about what a feed costs.
7. **A `feed_error` event.** Appended when a declared feed fails, at most
   once per feed per distinct error per day (the "a render that changes
   nothing writes nothing" rule, applied to failures). This is the corpus
   that will later answer *how often was the Desk blind*, which no other
   record would hold.

## Explicitly out of scope

- Any real work-rig source. The wiring order below is intent, not this
  round's tasks; each source is its own small round on the rig that owns it.
- ~~A second card type from a feed that is not staleness-shaped.~~ **Amended
  in drafting:** the workcycle feed *is* non-staleness, and the options
  extension it needs is now Task 4 here rather than
  `COWORK_BRIEF_validation_ratify.md`'s Task 2. That brief keeps the harder
  half — a decision whose consequence is a **write-back**, with the digest
  and the parameter problem — and inherits the vocabulary rather than
  inventing it. The extension is still required to be general and names
  nothing source-specific; it is simply proved here first, against a source
  that cannot damage anything if the shape is wrong.
- Any workcycle item type beyond `proposed` entries — open briefs, unstamped
  walk sheets, archivable pairs. Each needs its own argument that it moves a
  decision.
- Any write to `DECISIONS.md`, in this round or by this card type.
- Background polling, notification, scheduling, push.
- Any aggregation across machines, any network listener, any shared store.
- Retiring Triggers A and B, or changing their behaviour or fingerprints.
- Per-item cost estimates. The run marker still records no duration; "no
  measurement, no estimate" (0037 clause 4) holds unchanged.

## Stop conditions

- The Desk thresholds, recomputes, or overrides a feed's `state` → stop.
- A card is raised from an item with no `observable_since` → stop (0048
  clause 2).
- A failing or unreachable feed produces a silent, empty Desk → stop; that is
  the one failure this round exists to make impossible.
- An `action` reaches the execute route without having been validated against
  a manifest stage the allowlist already permits → stop (0037, 0042).
- A feed's command acquires a parameter slot, or accepts anything from a
  request → stop (0042 clause 4).
- Existing fingerprints change → stop; Phase 1's corpus is the trial's whole
  output.
- Anything in this round writes to `DECISIONS.md`, or flips a status line →
  stop. The card records the decision; the operator makes the edit; Phase 2
  owns the authoring path.
- A ruling is accepted for an option the card did not offer → stop; the
  vocabulary is the card's (0050 clause 8).
- Triggers A and B's ruling vocabulary changes → stop; the trial's rulings
  must stay comparable across this round.
- Any cross-machine read, write, or call appears → stop (0036).
- A `desk/` package, a plugin registry, or a feed-type dispatch table appears
  for two providers → stop; it is one loop.

## UAT — acceptance checks (Tim walks these)

- `[G]` A feed declaring one `stale` item with `action` and one without
  raises exactly two cards; the first offers the run button, the second
  offers hold/snooze/dismiss only.
- `[G]` An item missing `observable_since` raises **no card**, and the reason
  is visible on the health line rather than nowhere.
- `[G]` A feed command that exits 1, times out, and prints garbage — three
  runs — each produce a health line naming which, and no cards; `feed_error`
  events appear once per distinct error, not once per render.
- `[G]` An `action` naming a stage that is not in a validated, allowlisted
  manifest is refused at parse; the item still raises its card, without the
  button.
- `[G]` Triggers A and B raise the same fingerprints as before the
  restructure, against the trial's own events file.
- `[G]` A v1 manifest (no `staleness_feed`) loads and behaves exactly as it
  does today.
### The UAT fixture — a second allowlisted repo

The workcycle feed is testable today without touching the real
`DECISIONS.md`, because **the dates come from the file**: a dummy entry in a
throwaway repo, with its `**Date:**` line set by hand, drives every branch of
the cadence rule. Setup notes, so the walk is honest rather than convenient:

- The fixture needs its own `wizforge.manifest.json` declaring the feed, and
  an entry in `config/project_wizard.allow.json` — a reviewed, committed edit
  like any other (0042 clause 2). Name the repo key so it reads as a fixture
  (`uat-decisions-fixture`), the same posture the allowlist's own comment
  already takes about `l5gn-tools-fixture`: **a fixture, not a pilot.**
- **This changes the trial's card population mid-trial.** It is not a
  threshold tune and not forbidden, but it must be recorded in
  `docs/UAT_desk_stale_card.md` with its date, so Phase 1's numbers stay
  separable before and after.
- **Separability comes free**: the fingerprint hashes `(repo_key, …)`, so
  every UAT event carries a fixture repo key and can be excluded from the
  trial corpus at analysis time. No second events file, no new mechanism —
  provided the repo key is unmistakable.

- `[G]` An entry dated **yesterday** with `**Status:** proposed` raises a card
  today; the same entry dated **today** raises none (0033's re-read rule,
  enforced by the source's own arithmetic).
- `[G]` Editing the fixture entry's status to `accepted 2026-08-20` makes the
  card stop deriving on the next render, and the log records a `resolution`.
- `[G]` A `ratify` ruling is accepted and recorded with its verb; submitting
  `rebuild` against the same card is **refused** — that option was never
  offered.
- `[G]` Ruling `ratify` while the fixture file still says `proposed` leaves
  the card raised on the next render. The ruling is a record, not an
  authority.
- `[G]` A malformed or missing status line reports `unknown` on the health
  line and raises no card — never a guess.
- `[H]` **Write one feed for something you actually care about** — anything,
  it does not have to be an MCF source. Was the contract enough to say what
  you meant, or did you want a field it does not have? Every want is a
  finding, and one of them will be the sixth field this contract is missing.
- `[H]` **The tab's wall clock with feeds polling.** Is it still a place you
  open casually? A Desk that takes ten seconds to load is patrolled less,
  which is the failure mode the whole programme is trying to remove.

Results log needs a `uat` stamp naming the commit; do not write a `gate=`
field.

## Wiring order, recorded as intent (not this round's work)

From the work rig's own report and the operator's project summaries; the
sequencing reasoning is the part worth keeping, and it belongs to whoever
holds that rig:

1. **`sf-data-service`** — its requirement registry is a feed that already
   exists in some form. The prototype, because the least new thinking per
   unit of signal.
2. **`ValidationAutomation`** — the strongest test the contract will get,
   because it is *not* staleness-shaped. Its brief is separate and its
   discovery step is real (`COWORK_BRIEF_validation_ratify.md`).
3. **`cli-engine`** — the reference template for MCF workstreams, so whatever
   its feed looks like is what the rest will copy. Worth doing early enough
   that the copy is deliberate.

Three findings from the work-rig report worth raising as their own cards
once a Desk runs there — noted so they are not lost, not scheduled here:
`PricingModelisation` existing beside `PricingModel` (duplicate or remnant —
a tidy ruling); two MCF folders with no git at all; several repos with 1–2
commit histories, which is precisely why the **feed** contract matters more
on that estate than on this one — mtime-and-git triggers have almost nothing
to read there.

## Reporting

`docs/COWORK_REPORT_staleness_feeds.md`, walk-sheet
`docs/UAT_staleness_feeds.md`, stamped results.

Record: 0050 as ratified (and what the re-read changed); the schema v2 delta
and the v1 compatibility decision; the provider restructure with proof that
fingerprints survived; the first measured per-feed wall clock; every field
the `[H]` feed-writing walk wished for; and the two-desk posture as landed,
including anything about it that already feels like it wants to be a mesh.
