# Cowork brief — the model bench: the tier ladder is measured into existence, not declared

**Origin:** `docs/investigation/2026-08-17_quartermaster_fable_2-response.md`
(the capability ladder, §3.4) and Tim's question of 2026-08-18: *which models
actually belong on which rung, on either rig?*
**Depends on — this repo's rulings:** **0037** (measurement before estimation;
no estimate without a measurement; refuse, never clamp), **0039** (the Curator
is scoped to the machine's declared estate), **0041** (S2 vocabulary and S6
evidence scoring are dormant — this round does not revive them), **0044** (the
Curator's data-dir posture), **0049** (frontier is a sensed input, not a tier
this round can invoke).
**Deliverable:** a standing evaluation set; a widened telemetry row; a bench
that runs candidate local models over that set through a real Curator stage and
records **throughput, quality, reliability and load cost together**; and the
comparison from which a tier ladder can later be declared. **This round declares
no tiers.** It produces the evidence; the ladder is a separate ruling that cites
it.

---

## Why this round exists, and why it comes first

The vision proposes a four-rung ladder — T0 script, T1 small local, T2 large
local, T3 frontier — and plans work at "the cheapest capable tier." Today the
estate has calibration evidence for exactly one local model: `gemma-4`, 116
entries across K2 and K4 in `data/calibration_ledger.jsonl`.

**T1 has never run.** Declaring a rung nothing has been measured on is the
fabricated estimate 0037 clause 4 refuses, and every plan built on the ladder
would inherit it. So the ladder waits, and this round buys the right to declare
it.

## The one thing this round must get right

**A tier is defined by what work a model can do acceptably, not by how fast it
runs.** A model twice as quick that fails its stage's quality bar is not a
cheaper rung; it is a different failure. Any bench that reports ms/token alone
will nominate the wrong model, confidently.

K2 already carries a machine-checkable acceptance bar and has been reporting it
all along: **`quoted_source` must be a literal substring of the conversation**,
with the rejection rate in the run header. Two real runs on `10280L`:

| | 2026-08-08 | 2026-08-13 |
|---|---|---|
| conversations scanned | 37 | 37 |
| claims extracted | 1165 | 924 |
| rejected (not a literal quote) | 374 (24.3%) | 364 (28.3%) |

Same model, same endpoint, same corpus size, and **extraction volume moved 21%
between runs.**

**That 21% is an upper bound on noise, not a measurement of it.** Tim confirmed
on 2026-08-18 that **the LM Studio configuration differed between those two
runs** — so the swing mixes genuine run-to-run variance with a settings change,
and the two cannot be separated after the fact. Treating 21% as the floor would
be over-conservative in a way that costs real findings: a candidate genuinely
40% faster would be dismissed as noise.

**Nobody has ever measured what "no difference" looks like here**, which is why
Task 0 exists. The round's honesty bar stands — state the smallest difference
the bench can actually detect and refuse to read meaning into anything smaller —
but that number is now **derived from the control, not assumed from history.**

## Sizing — from real elapsed time, not guesses

Measured from the existing ledger:

| | units | elapsed | per unit |
|---|---|---|---|
| K2, 12 Aug | 68 | 2h 14m | ~2 min |
| K4, 12–13 Aug | 33 | 7h 42m | **~14 min** |
| K2, 15 Aug | 15 | 24m | ~1.6 min |

**K4 costs roughly 7× K2 per unit.** That governs the whole design:

> **Screen candidates on K2 alone. Promote only a finalist to K4.**
> Four models on medium-K2 with repeats is an evening. Four models on K4 is
> thirty-plus hours, and would tell you little K2 had not already.

Three sizes, all drawn from the same evaluation set so results compose:

- **Short — 3–4 conversations, ~12 min K2.** A smoke screen: can this model do
  the job at all, honour the JSON schema, and fit the context? A candidate that
  fails short has been tiered, cheaply.
- **Medium — 10–12 conversations, ~40 min K2.** The workhorse. Two repeats of
  four candidates is roughly one day.
- **Long — the full set, ~2.2h K2.** Finalist only. The only size producing
  numbers comparable to production runs.

## Working rules

- **One evaluation set, identical for every candidate.** A committed list of
  conversation ids, reused for every model and every repeat. Not "12
  conversations" — *these* 12, by id. Short/medium/long are nested prefixes of
  one ordered list, so a short run's items are always inside the medium run's.
- **Repeat every candidate, and counterbalance the order.** A single run cannot
  separate a model difference from the bench's own variance — which Task 0
  measures rather than assumes. And because throughput
  decays under thermal load — the reason the governor exists — a candidate that
  always runs last is penalised. Vary the order across repeats, and record
  position-in-session on every row.
- **Bench measurements go to their own ledger file**, never
  `data/calibration_ledger.jsonl`. `make_ledger_feeder(path, stage=...)` already
  takes a path, so this needs no schema change. A candidate model's numbers
  entering the population the planner estimates real work from is this round's
  worst possible output.
- **Hold `cool_down_preceded` constant within a comparison.** All 116 existing
  entries are `false`; the partition `summarize` treats as mandatory has never
  been populated. Task 4 measures load cost deliberately — but a *throughput*
  comparison must not straddle it by accident.
- **Read-only.** The Curator stages stay read-only; the bench adds no write path
  to any vault table.
- **Per-machine, because the hardware differs.** The same model on the gaming rig
  and `10280L` is two measurements, not one. `config/machines.json` already
  carries per-machine settings and is where a per-rig ladder would live.
- Gate GREEN before every commit. `git commit -F <file>`, never `-m` with
  embedded newlines.

## Embeddings are not a rung — stated once, so it is not re-litigated

An embedding model (Nomic or similar) does retrieval, not generation. It cannot
stand in for a small generative model on a classify-or-extract stage, so it is
not a cheaper rung of this ladder; it is a different axis entirely.

It is also not neutral ground: `ARCHITECTURE` §3 records the embeddings
dependency as dormant, and **0041** declared S2 vocabulary and S6 evidence
scoring dormant rather than deleted. Reviving embeddings must argue with 0041
directly. **Out of scope here**, and if wanted later it is its own brief, not a
rung added quietly to a ladder.

---

## Task 0 ▸ the control — measure "no difference" before measuring any difference

**The first run is the incumbent against itself.** `gemma-4`, one fixed config,
one fixed prompt fingerprint, the medium evaluation set, repeated at least three
times with the order varied. No candidates, no comparison — just the same thing,
done again.

What that buys, and nothing else can:

- **The real noise floor**, uncontaminated by a config change. Every later claim
  ("model B is faster than model A") is only meaningful as a multiple of this.
- **Proof the bench is stable** before it is trusted to judge anything. If the
  control's own spread is wide, the instrument is the problem and no candidate
  result taken with it means anything.
- **The first entries ever written with `config_fingerprint` and
  `prompt_fingerprint` attached** — the incumbent's baseline, finally
  identifiable rather than a bare `model_id`.

**This is not overhead; it is the measurement the estate has been missing.** The
116 production entries cannot serve as a control because they carry no config
identity — they may span several configurations and there is no way to tell now.

**Report the control's spread before any candidate runs**, and state the
detectable-difference floor derived from it. If the control's own p25–p75 spans
30%, the bench cannot honestly report a 20% difference between models, and that
constraint should be known before an evening is spent producing one.

## Task 1 ▸ the evaluation set — the round's most reusable output

Not a bench fixture. **A standing evaluation set**, built once and reused by
every later feature that touches a model — this round's candidates, the next
model released, and any change to a prompt or a stage. The point, in Tim's
words: benchmark a model for a given task *without waiting on a full completion
run*. That is what the major benchmark suites do; this one is narrower and
therefore more useful, because it is scoped to work this estate actually does.

Two levels, and the difference matters:

**Level 1 — pinned inputs (this round's floor).** An ordered, committed list of
conversation ids with a one-line note on why those: breadth of project, spread
of length, and the known-hard cases deliberately included. Short and medium are
prefixes of it. This level supports throughput and the machine-checkable
acceptance bar — **well-formedness, not correctness.**

**Level 2 — ground truth (start small, grow).** For a subset, the claims that
*should* be extracted; for a handful, the project each *should* link to. This is
what lets a run be scored for being **right** rather than merely well-formed —
the difference between "produced valid-looking claims" and "found the claims
that matter."

Level 2 need not be complete to be useful. A dozen items answers *"did this
candidate miss the obvious ones?"*, which no rejection rate can reach. Build it
by hand from conversations whose answer is already known — **this repository's
own build conversations are the strongest candidates, because their ground truth
is in `DECISIONS.md` and can be checked rather than remembered.**

Record for each ground-truth item **who decided it and when**. An eval set whose
answers nobody can defend is a benchmark measuring agreement with a past guess.

**Where it lives:** under `data/` with the other committed fixtures, or `tests/`
if the gate is ever to read it — builder's call, recorded. It must be
**committed and stable**; an evaluation set that drifts silently makes every
comparison across time meaningless, which would waste every run taken against it.

## Task 2 ▸ widen the telemetry row — most of it already exists

The `TIMING_WINDOW` record already carries far more than the ledger keeps:

```
conversation_id · project_id · window_index · windows_total · token_count
model_id · cool_down_preceded · usage_available · prompt_tokens
completion_tokens · generation_ms_per_token · wall_clock_seconds
```

The ledger keeps **four**. `prompt_tokens`, `completion_tokens`,
`wall_clock_seconds` and `token_count` are emitted and discarded. So "complete
telemetry" is largely a widening of the row, not new instrumentation.

Add to the bench ledger row, in priority order:

1. **`prompt_fingerprint`** — `extract_claims.prompt_fingerprint()` already
   exists (sha256 over the system prompts) and is in no ledger. **Without it a
   prompt change is indistinguishable from a model change**, which would
   silently invalidate every comparison taken from here on. Highest-value field
   in this task.
2. **`config_fingerprint`** — a short hash over the model's *settings*:
   context length, GPU offload layers, quantisation, KV-cache type, flash
   attention, batch size, and the TTL/auto-unload state. `model_id="gemma-4"`
   says nothing about any of it, and the existing 116 entries may span several
   configurations with no way to tell now. **The comparable unit is
   `(model, config, prompt)`, not model** — and `summarize` should partition on
   it exactly as it already partitions on `cool_down_preceded`, so mixed
   configurations become visible rather than silently pooled.
3. **The discarded numerics** — `prompt_tokens`, `completion_tokens`,
   `token_count`, `wall_clock_seconds`. Wall-clock per conversation is the
   number a plan budget actually needs; ms/token is the number that compares
   models. Keep both.
4. **`position_in_session`** and the host — for the order-effect rule above.
5. **Time to first token**, where the endpoint exposes it. Throughput is the
   right metric for overnight sweeps; **TTFT is what an interactive surface
   feels**, and one number cannot serve both.

**Note for the record: no `seed` is sent.** `DEFAULT_TEMPERATURE = 0.0` removes
most sampling variance, but batching and GPU kernels are not bit-deterministic,
so repeats stay mandatory. If the endpoint accepts a seed, sending a fixed one
is cheap and worth doing — record whether it was honoured, since not every
backend obeys.

## Task 3 ▸ the failure taxonomy

A failed run is data, not an error to retry away — but only if the *kind* is
recorded. At minimum, distinguish:

- **context overflow** — the conversation did not fit; a capability limit
- **schema violation** — could not honour `response_format: json_schema`; a
  capability limit of a different kind
- **refusal** — declined the task
- **timeout** — too slow to finish inside the stage's limit
- **transport/endpoint error** — not the model's fault at all

Collapsing these into "failed" destroys the signal that assigns tiers: a model
that overflows on long conversations but is excellent on short ones has told you
its rung and its restriction. **A candidate that fails is tiered, not
disqualified.**

## Task 4 ▸ load cost — the ladder's hidden tax, never yet measured

Nothing in this estate has measured what it costs to *start* using a model, and
the ladder's whole premise depends on it.

- **Cold start:** seconds from request to first token on a model just loaded,
  versus steady state. This is what `cool_down_preceded` was designed to isolate,
  and it has **zero true entries** across all 116 measurements on any rig.
- **Switch cost:** seconds to unload model A and load model B. **If moving
  T1→T2 mid-plan costs 90 seconds, a plan that alternates tiers can be slower
  than one that never leaves T2** — which would make the ladder actively
  harmful, and is the single finding most likely to change Phase 4's design.
- **Residency:** can two candidate models be VRAM-resident at once on this rig?
  A ten-minute test, not a benchmark, and it decides whether tier-switching is
  cheap or catastrophic.
- **TTL interaction:** LM Studio's auto-unload-if-idle changes all of the above.
  Record the setting; it is part of `config_fingerprint`.

## Task 5 ▸ the comparison, and what it may claim

A rendered table — throughput, quality, reliability and load cost side by side,
spread stated, per machine, per `(model, config, prompt)`.

`gemma-4`'s existing 116 production entries are the incumbent baseline, shown as
such and **labelled production rather than bench**, since they were not taken
over the evaluation set and carry no config fingerprint.

**The report states plainly what the numbers do and do not support**, including
the detectable-difference floor from the run-to-run spread. Two candidates
indistinguishable within their spread are reported as indistinguishable — not
tie-broken by preference.

### The decision matrix this feeds

The conductor cannot route on throughput alone. Per `(stage, model, config,
prompt)` it needs:

| column | source | status before this round |
|---|---|---|
| throughput — median + p25/p75 ms/token | ledger | have |
| unit cost — median wall-clock per conversation | timing record | emitted, discarded |
| quality — acceptance rate; correctness where ground truth exists | K5 report / eval set | **absent** |
| reliability — failure rate by kind | run outcome | **absent** |
| load cost — cold start, switch seconds | nothing | **never measured** |

Routing then reads: **the cheapest model whose quality clears this stage's
declared bar.** Without the quality column the matrix can only pick the fastest,
which is how a system ends up routing to a model that produces confident rubbish.

---

## Explicitly out of scope

- Declaring the tier ladder, or writing a tier onto any stage. That ruling comes
  after these numbers exist and cites them.
- Any change to K2/K4 logic, prompts, or acceptance rules. Changing the stage
  while benchmarking models measures neither. (Recording the prompt fingerprint
  is not changing the prompt.)
- Embeddings (above), any T3 involvement, any planner or Dispatcher change.
- Fixing the empty `cool_down_preceded` partition in production — Task 4
  measures load cost in the bench; production stays as it is.
- Model *selection* as policy. The bench informs a decision; it does not make one.

## Stop conditions

- **Bench runs write to `data/calibration_ledger.jsonl`** → stop; the planner's
  estimates would inherit a candidate's numbers.
- **A tier is named in code or config during this round** → stop.
- **Candidates compared across different corpora, machines, prompts or configs
  without saying so** → stop.
- **A model is recommended on throughput without a quality number** → stop;
  that is the round's whole point.
- **Only one run per candidate, or a fixed candidate order across repeats** →
  stop; neither can carry a claim against the control's measured spread.
- **Any candidate is run before Task 0's control has been taken and its spread
  reported** → stop; a comparison against an unknown floor is not a comparison.
- **A failure is recorded without its kind** → stop (Task 3).
- **Any K-stage gains a write path** → stop (0039).
- **An embedding model is entered as a candidate rung** → stop (0041).

## UAT — acceptance checks (Tim walks these)

Mark each `[G]` / `[W]` / `[H]` per 0031.

- `[W]` **Task 0's control, read first**: the incumbent's own spread across
  repeats, and the detectable-difference floor derived from it, stated before
  any candidate ran.
- `[G]` The evaluation set is a committed ordered list; short and medium are
  prefixes of long; two runs of one model read the same conversations.
- `[G]` Bench output lands in the bench ledger; `data/calibration_ledger.jsonl`
  is byte-identical before and after a bench session.
- `[G]` Every row carries `prompt_fingerprint` and `config_fingerprint`;
  changing one LM Studio setting changes the config fingerprint.
- `[G]` Every reported model carries throughput **and** quality, with spread
  across repeats and its position-in-session recorded.
- `[G]` A deliberately unsuitable candidate (too small a context) reports
  `context overflow` as its failure kind, not a bare error.
- `[W]` **Cold start versus steady state, measured** — and the model-switch cost
  between two candidates, stated in seconds.
- `[W]` **Two models resident at once: yes or no**, on this rig, stated plainly.
- `[W]` Run incumbent `gemma-4` through the bench and compare against its
  production numbers. Broadly agree? A large gap means the bench is measuring
  something other than real work, and **that outranks every candidate result.**
- `[H]` **Read the comparison and say which rungs you can honestly declare.** If
  the answer is "T0 and T2 only — T1 has no credible candidate", that is a good
  outcome and the ladder ships with three rungs and a stated gap.
- `[H]` **Was any candidate fast enough to matter and good enough to trust?**
  The ladder only pays if a real rung exists below `gemma-4`. If none does, say
  so — the Dispatcher's plans then have fewer options and more honest ones.
- `[H]` **Does the switch cost change your view of the ladder?** If alternating
  tiers costs more than it saves, Phase 4 plans single-tier by default and this
  round has saved it from a wrong design.

Results log needs a `uat` stamp naming the commit; do not write a `gate=` field.

## Reporting

`docs/COWORK_REPORT_model_bench.md`, walk-sheet `docs/UAT_model_bench.md`,
stamped results.

Record: the evaluation set and why those conversations; the widened row as
landed; every candidate with its config fingerprint, throughput, quality,
failure kinds and load cost across repeats; the incumbent comparison; which
rungs the evidence supports and which it does not; and — most useful of all for
the round that declares the ladder — **Task 0's control spread and the
detectable-difference floor derived from it**, since that number sets the limit
on how small a model difference this estate can ever honestly claim to see —
and it is the first time the estate will have measured its own noise rather
than inferring it from two confounded runs.
