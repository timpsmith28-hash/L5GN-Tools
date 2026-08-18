# Model bench — Tasks 1 and 2

This folder tracks `docs/COWORK_BRIEF_model_bench.md`'s non-runtime
deliverables: the committed evaluation set (Task 1) and documentation for the
widened bench ledger (Task 2, code lives in
`chronicler/pipeline/bench_ledger.py`, tests in
`tests/tester_bench_ledger.py`). Task 0 (the control run) and the actual
candidate runs happen on your machine against LM Studio — nothing here runs
a model.

## Task 1 — the evaluation set (Level 1)

**Status: Level 1 only.** This is the standing evaluation set required by
`docs/COWORK_BRIEF_model_bench.md` Task 1 — a committed, ordered list of real
conversation ids, with a one-line note on why each was chosen. **Level 2
(ground truth — the claims/links a run should be scored against) is not
built.** See "What Level 2 needs, and why it's not here yet" below before
starting it.

## Why `tests/`, not `data/`

The brief allows either (`data/` "with the other committed fixtures", or
`tests/` "if the gate is ever to read it — builder's call, recorded"). This
repo's `/data/` is blanket-`.gitignore`d ("Generated scan outputs —
reproducible, not source" — see `.gitignore`), so an eval set placed there
would not actually be committed, directly contradicting the brief's own
requirement that it be "committed and stable." `tests/witness/fixtures/` is
the one existing precedent for a committed fixture tree in this repo, so
`tests/model_bench/` follows that shape.

## How the 19 conversations were selected

Selection was done from a migration snapshot of this machine's transcript
stores (see `eval_set_level1.json`'s `source` block for exact path and
timestamp), using `chronicler/pipeline/local_transcripts.py`'s own
discovery/parse/group functions — not a hand search — so the ids, message
counts and char counts are read straight off the same code the real Curator
stages will eventually walk, not estimated.

Every conversation whose `cwd` resolved to this repo (18 of them, all short,
narrow "generate markdown templates" CLI-store sessions from one afternoon)
was visible from the `cwd` field alone. The much larger and more varied set
of Cowork-store "build task" conversations — the ones that actually produced
this repo's `COWORK_BRIEF_*.md` / `COWORK_REPORT_*.md` / `DECISIONS.md`
entries — do **not** carry a usable `cwd`: Cowork sessions of this shape run
in an ephemeral cloud sandbox, so the recorded `cwd` is a generic sandbox
output path, not the repo. Those conversations were instead identified by
**title** (most build threads open with `task: docs/COWORK_BRIEF_<name>.md`
or an uploaded copy of the brief), cross-checked against the committed
`docs/COWORK_BRIEF_*.md` list. This is worth recording because a future
selector script that trusts `cwd` alone for the Cowork store will silently
miss most of the estate's real build conversations.

The 19 were picked by hand against three criteria stated in the brief
(Task 1, Level 1): **breadth of project** (14 L5GN-Tools + 3 Crystal Spire +
2 CLI-store L5GN-Tools — a second, unrelated repo is represented, not just a
second folder of this one), **spread of length** (499 chars to 1,010,341
chars — roughly three orders of magnitude), and **known-hard cases
deliberately included** (a 1M+ char conversation almost certain to overflow
a local model's context window; a 2-message off-topic troubleshooting
exchange with nothing worth extracting; a CLI-store session, which has a
different record shape than the Cowork store's). Each entry's `why` field in
`eval_set_level1.json` states its specific reason for inclusion — see that
file for the per-item rationale, not repeated here.

Short/medium/long are literal ordered prefixes of the 19 (4 / 12 / 19), per
the brief's "short and medium are nested prefixes of one ordered list"
working rule — reordering the list without updating the tier counts would
break that guarantee.

## Before running the bench: re-resolve the ids

These ids were read from an `.md`-dated snapshot
(`claude_migration/2026-08-14`), not the live store. A transcript store can
rotate or prune between snapshot and bench run. **Confirm every id in
`eval_set_level1.json` still resolves on the machine the bench actually runs
on before using it** — a missing id is one of the brief's own stop
conditions in spirit ("candidates compared across different corpora ...
without saying so"), even though it isn't listed verbatim. If an id has
gone missing, replace it and record the replacement and why here, rather
than quietly shrinking the set.

## What Level 2 needs, and why it's not here yet

The brief is explicit that Level 2 ground truth must be defensible: "Record
for each ground-truth item **who decided it and when**. An eval set whose
answers nobody can defend is a benchmark measuring agreement with a past
guess." `docs/DECISIONS.md`'s ~50 numbered rulings are not filed by which
build conversation produced them, and a grep for the relevant
`COWORK_BRIEF_*` filenames against `DECISIONS.md` found no direct textual
link. Matching a specific ruling (with its exact wording and number) back to
the specific conversation and turns that produced it requires actually
reading each candidate conversation and cross-referencing it against
`DECISIONS.md` by content and date, not filename — real per-item work, not
something to approximate quickly.

Building it properly, for the conversations flagged `"why"` above as Level 2
candidates (the 9 items with a matching `docs/COWORK_BRIEF_*.md`):

1. Open the conversation (via the migration snapshot or live store) and the
   matching `docs/DECISIONS.md` entries from around the same date.
2. For each claim that conversation should yield, write the claim text, the
   literal quoted substring from the conversation it must come from (K2's own
   acceptance bar — a literal substring, not a paraphrase), and the
   `DECISIONS.md` ruling number it corresponds to if one exists.
3. Record who made that call (the person walking the conversation) and the
   date, next to the claim — not left implicit.
4. Start with a dozen items across 2-3 conversations, per the brief ("Level 2
   need not be complete to be useful... a dozen items answers *did this
   candidate miss the obvious ones?*"), rather than trying to cover all 9 at
   once.

This is the natural next slice of Task 1 and was intentionally left for a
follow-up pass rather than rushed — inventing plausible-looking ground truth
here would be exactly the "estimate without a measurement" 0037 refuses,
applied to the eval set itself.

## Task 2 — the widened bench ledger

`chronicler/pipeline/ledger.py` (production) is deliberately narrow: four
fields, because it feeds the planner's real estimate and the brief says
outright that a candidate's numbers leaking into that population is "this
round's worst possible output." So Task 2's wider row lives in a new,
separate sibling module — `chronicler/pipeline/bench_ledger.py` — rather than
widening `ledger.py` itself. It is structurally incapable of writing to
`ledger.DEFAULT_LEDGER_PATH`: its own default
(`DEFAULT_BENCH_LEDGER_PATH = data/model_bench/bench_ledger.jsonl`) is a
different file under a different directory, and every write function takes
`path` as a *required* argument — there is no optional fallback that could
coincide with the production path by a missing keyword argument.

**What it adds, against Task 2's own priority list:**

1. `prompt_fingerprint` — computed by calling
   `extract_claims.prompt_fingerprint()` (the existing function, not
   duplicated), once per bench session.
2. `config_fingerprint` — `bench_ledger.build_config_fingerprint(settings)`
   hashes a settings dict the same way `prompt_fingerprint()` hashes the
   prompts (sha256 hex, canonical JSON). `CONFIG_FINGERPRINT_FIELDS` in the
   module names the shape Task 2 asked for (context length, GPU offload
   layers, quantisation, KV-cache type, flash attention, batch size,
   TTL/auto-unload) — the bench harness is responsible for actually reading
   these off LM Studio and building the dict; this module only canonicalises
   and hashes whatever it's given.
3. The discarded numerics (`prompt_tokens`, `completion_tokens`,
   `token_count`, `wall_clock_seconds`, `usage_available`) — parsed straight
   out of the real `TIMING_WINDOW`/`TIMING_CLAIM` line text via
   `parse_timing_line()`. No K2/K4 code was touched to get these; K2/K4
   already compute and print every one of them (Addendum 2), this module
   just stops discarding them.
4. `position_in_session` and `host` — supplied once per bench session by the
   caller (the bench harness), because neither K2 nor K4 has any notion of
   either. `host` defaults to nothing — pass `l5gntools.config.hostname()`
   explicitly, per the brief's "per-machine, because the hardware differs"
   rule.
5. `time_to_first_token_ms` — **NOT implemented.** See "What's blocked" below.

**How it wires in**, mirroring `ledger.make_ledger_feeder`'s own contract
exactly:

```python
from chronicler.pipeline import bench_ledger
from chronicler.review import curator_control

feeder = bench_ledger.make_bench_ledger_feeder(
    bench_ledger.DEFAULT_BENCH_LEDGER_PATH,
    stage="K2",
    host="LucasGoonPC",
    config_fingerprint=bench_ledger.build_config_fingerprint({
        "context_length": 8192, "gpu_offload_layers": 30,
        "quantisation": "q4_0", "kv_cache_type": "f16",
        "flash_attention": True, "batch_size": 512,
        "ttl_seconds": 300, "auto_unload": True,
    }),
    position_in_session=2,  # this candidate's slot in this repeat's order
)
curator_control.run_stage("K2", project_id=..., on_timing_line=feeder)
```

Build a **fresh feeder per candidate run** — `host`/`config_fingerprint`/
`position_in_session` are baked in at construction, so reusing one feeder
across two candidates would mislabel the second candidate's rows with the
first's config.

**Summarising** (`bench_ledger.summarize`) partitions on five keys, not
`ledger.summarize`'s three — `model_id`, `stage`, `cool_down_preceded`,
`config_fingerprint`, `prompt_fingerprint` all have to match — per the
brief's "the comparable unit is (model, config, prompt), not model."
Returns both `median_ms_per_token` (with spread) and
`median_wall_clock_seconds`, per Task 2 item 3 ("keep both").

### What's blocked, and why it wasn't forced

Two things Task 2 mentions are genuinely not implementable without touching
K2/K4's own code, which the brief's "Explicitly out of scope" section
forbids this round ("Any change to K2/K4 logic ... Changing the stage while
benchmarking models measures neither"):

- **Time-to-first-token (item 5).** `extract_claims.call_lmstudio` makes a
  plain, non-streaming request. Capturing TTFT means observing when the
  first streamed token arrives, which requires changing how K2/K4 call the
  model. `time_to_first_token_ms` is still a field on every bench entry
  (always `None` this round) so a future round that revisits this stop
  condition needs no ledger schema migration.
- **Seed / seed-honoured (the brief's closing note under Task 2).** No seed
  is currently sent to the endpoint at all; recording whether one was
  honoured needs K2/K4 to send one first. Not added as a field this round —
  unlike TTFT, the brief doesn't list it in Task 2's numbered priorities, so
  there's no "always None" placeholder for it; a future round would add the
  field when it adds the capability.

Both are real gaps against the full brief, not oversights — they're the
direct consequence of the round's own stop condition on K2/K4 changes,
applied consistently rather than quietly worked around.
