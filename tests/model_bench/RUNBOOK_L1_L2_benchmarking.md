# RUNBOOK -- working the model bench, Level 1 and Level 2, in practice

Companion to `docs/COWORK_BRIEF_model_bench.md` and `tests/model_bench/README.md`.
Everything in this runbook executes on your machine against real LM Studio --
nothing here runs from the Cowork side. Read the whole thing before starting
Task 0; several steps depend on a decision you make earlier.

**Standing rules, unchanged from the brief:** never write to production
`data/calibration_ledger.jsonl`; never change K2/K4 logic, prompts or
acceptance rules; never declare a tier; `python verify.py` must be GREEN
before every commit; no measurement gets reported without a real run behind
it (ruling 0037).

---

## Step 0 -- the driver now exists: `run_bench_sweep.py`

`tests/model_bench/run_bench_sweep.py` runs K1/K2/K3/K4 as real subprocesses
(the unmodified production scripts) over a bench-scoped copy of the 19
pinned conversations, and wires the results into `bench_ledger.py`/
`bench_failures.py`/`bench_load_cost.py`. Everything it writes lives under
`data/model_bench/` -- it never opens `config/mcf_conversation_map.tsv`,
`data/knowledge_curator/`, or `data/calibration_ledger.jsonl`.

**Confirmed live, 2026-08-18: `--host` is a `config/local.json` machine-alias
key, never an LM Studio URL.** The first real `prep` run used
`--host http://127.0.0.1:1234` (an easy mistake -- `run_bench_sweep.py` also
has a separate `--endpoint` flag for LM Studio, defaulting to that same
address) and, separately, surfaced a real structural finding: even the
*real* hostname (`LucasGoonPC`) would not have worked, because
`extract_claims.py`/`knowledge_index.py` discover conversations via
`config/local.json`'s `cowork_transcripts_home` for that host -- which
points at `LucasGoonPC`'s LIVE Cowork store, and none of
`eval_set_level1.json`'s 19 pinned conversations are in it ("mapped but
absent on disk: 19"). They only exist in the `claude_migration` backup
snapshot Task 1 was actually built from.

**Fixed, already written to your `config/local.json`** (gitignored, never
committed -- a read-modify-write that preserved every existing entry): a
new `"model-bench"` host alias whose `cowork_transcripts_home` points at
`C:/Users/timps/backups/claude_migration/2026-08-18_100202/cowork-sessions`
-- the exact folder shape `local_transcripts.discover_cowork_store` expects
(`<root>/<workspace-id>/<project-id>/local_<session-id>/...`), confirmed
against that snapshot directly. Use `--host model-bench` for every
`run_bench_sweep.py` command below -- never `LucasGoonPC` for this bench,
and never a URL for `--host` anywhere. If you take a newer backup later,
update `cowork_transcripts_home`'s date-stamped folder in `config/local.json`
and re-verify all 19 ids are still present before trusting it (`scan_all_
decisions.py --root <new backup path>` finding the same ruling counts is a
reasonable proxy check).

```powershell
# once, before any model -- builds the bench map, runs K1+K3 (deterministic,
# shared across every model/repeat)
python .\tests\model_bench\run_bench_sweep.py prep --host model-bench
```

**Confirmed live, 2026-08-18: this bench round runs on 17 of the 19 pinned
conversations, not 19.** `cli:430c5135...` and `cli:e99b862f...` are
CLI-store conversations, and K0/K1 (and K2/K4, which share the same
`discover_conversations` call) only ever discover the Cowork store --
`bootstrap_conversation_map.py`'s own docstring says so directly: "K0
works the Cowork store only; CLI sessions are never MCF conversations."
That's a structural pipeline boundary, not a config problem, so no
`cowork_transcripts_home` value will ever resolve those two. `run_bench_
sweep.py` now excludes them by default (`build_bench_map`'s `EXCLUDED_CLI_
IDS`) so `prep`'s report reads clean. Extending K2/K4 to discover the CLI
store too is a real idea for a future round -- flagged, not built, since
it would be a K2/K4 logic change and this round's stop condition forbids
that.

**Verify before moving on:** the printed report should show `mapped but
absent on disk:  0` against the 17-conversation map. If it doesn't, stop
and compare -- don't proceed into Step 1 against a map that's silently
scanning fewer than 17.

The rest of this runbook's Steps 1-2 now map directly onto its `run` /
`switch-cost` / `cold-start` subcommands -- see each step below.
`switch-cost`/`cold-start`/`run` all still take `--host model-bench` too
(K2/K4 use the same `cowork_transcripts_home` lookup as K1).

---

## Step 1 -- Task 0: the control run (must run before any candidate)

The brief's own stop condition: no candidate model result means anything
without a control baseline from the incumbent (`gemma-4`) run against
itself.

1. Confirm LM Studio is up and `gemma-4` is the only model loaded (a clean
   baseline -- no residency effects from a second model).
2. Run `prep` once (Step 0), then:

   ```powershell
   python .\tests\model_bench\run_bench_sweep.py run --model "gemma-4" `
       --host model-bench --repeats 3 --cool-down-preceded false `
       --context-length 8192 --quantisation Q4_K_M
   ```

   `run` already varies conversation order between repeats (repeat 0 keeps
   `eval_set_level1.json`'s pinned order; repeats 1+ use a seeded shuffle,
   seed = repeat index, so it's reproducible, not a silent unrecorded
   shuffle) -- this is what lets Task 5's `detectable_difference_floor` mean
   anything; three identical-order runs would understate real variance.
   Fill in `--context-length`/`--quantisation`/etc. from LM Studio's actual
   load settings for `gemma-4` -- these become the run's `config_fingerprint`,
   so get them right before running, not after.
3. `--cool-down-preceded` is a sanity-check flag the script prints back at
   you -- the ledger's real `cool_down_preceded` field comes from each
   TIMING line itself (whether K2/K4's own `--cool-down` sleep fired), not
   from this flag. Pass whatever actually happened so the printed note
   matches reality.
4. **Verify:** `bench_ledger.load_entries(bench_ledger.DEFAULT_BENCH_LEDGER_PATH)`
   should show >= 3 entries per `(model_id="gemma-4", config_fingerprint)`
   pair.
5. Do not proceed to Step 2 until this is done. A candidate run with no
   control to compare against is evidence you can't use.

---

## Step 2 -- candidate sweeps

Your model list on the gaming rig: **Gemma 4 E4B** (the incumbent -- confirm
this is what `gemma-4` in Task 0 actually refers to before treating it as
the same model), **Gemma 4 E2B Instruct**, **Llama 3.2 3B Instruct**, and
**Phi 3 Mini 4k Instruct** are real K2/K4 candidates. **Nomic Embed Text
v1.5 is an embedding model, not a chat-completion model -- it cannot run
K2/K4 at all** (`extract_claims.py`/`match_claims.py` both POST to
`/v1/chat/completions`); leave it out of any `run`/`switch-cost` command.

For each candidate model:

1. In LM Studio, unload the previous model and load the candidate (or use
   `switch-cost` below, which does the loading for you via the API).
2. If this is a switch from the previous model in your sweep order:

   ```powershell
   python .\tests\model_bench\run_bench_sweep.py switch-cost `
       --from-model "gemma-4" --to-model "Gemma 4 E2B Instruct" `
       --host model-bench --context-length 8192 --quantisation Q4_K_M
   ```

   If this candidate has never been loaded yet this session (no prior model
   to switch FROM), unload everything in LM Studio first, then:

   ```powershell
   python .\tests\model_bench\run_bench_sweep.py cold-start `
       --model "Gemma 4 E2B Instruct" --host model-bench `
       --context-length 8192 --quantisation Q4_K_M
   ```

3. Run the sweep, same shape as Task 0, `config_fingerprint` inputs held
   equal to the control where the setting is genuinely comparable:

   ```powershell
   python .\tests\model_bench\run_bench_sweep.py run --model "Gemma 4 E2B Instruct" `
       --host model-bench --repeats 3 --cool-down-preceded false `
       --context-length 8192 --quantisation Q4_K_M
   ```

   If a setting can't be held equal (e.g. a candidate's native context
   window is smaller than `gemma-4`'s), record that explicitly rather than
   silently passing the same `--context-length` under a fingerprint that no
   longer describes what actually ran.
4. **Verify:** after each model, `bench_ledger.known_configurations(...)`
   should show the new model_id with the same `config_fingerprint` shape as
   the control (modulo any explicitly-recorded difference from step 3).
5. Move to the next candidate. Nothing here ranks or judges -- you're just
   accumulating comparable measurements.

---

## Step 3 -- Level 2 scoring: does the model extract the right claims?

`level2_ground_truth.json` currently covers 6 rulings across 11
conversations, only 2 of which are in the pinned 19-conversation eval set
(`local_602a1aed`, `local_0cfd772f`). Two honest options, pick one before
scoring:

- **(a) Score only against the 2 in-eval-set items' conversations.** Thin,
  but keeps Level 2 strictly nested inside Level 1. Not enough items to
  draw a real conclusion from yet.
- **(b) Treat Level 2 as its own broader corpus** (the 11 conversations
  referenced in `level2_ground_truth.json`, most of which are outside the
  pinned 19) and run K2 over those specifically for this scoring pass, in
  addition to the Step 2 sweep. More signal, at the cost of Level 2 no
  longer being a strict subset of Level 1 -- which is already true today,
  so this just makes the scope explicit rather than pretending otherwise.

Whichever you pick, for each `(model, conversation)` pair in scope:

1. Run K2's claim extraction on that conversation (same config as Step 2).
2. For each `level2_ground_truth.json` item whose `conversation_id` matches,
   check whether the model's extracted claims cover the same content as
   `claim_text`/`quoted_substring` -- this is a manual judgment call today
   (no automated scorer exists yet; text-similarity matching against a
   36-item set is small enough to eyeball, but say if you want a scorer
   built once volume grows).
3. Tally, per model: `hits / total_items_in_scope`, and separately note any
   claim the model surfaced that ISN'T in the ground truth -- that's not
   automatically wrong (Level 2 is not exhaustive; the README says as
   much), but a claim that actively contradicts a `quoted_substring` is
   worth flagging as a real miss.
4. Record the tally somewhere reviewable (a simple CSV or markdown table
   per model is fine) -- this isn't a `bench_report.py` field yet either;
   `quality_from_k2_report`'s `correctness_rate` is explicitly `None` in
   the code today because this scoring didn't exist when Task 5 was built.
   Wiring the Step 3 tally into `correctness_rate` is a natural next step
   once you've run this once or twice and trust the process.

---

## Step 4 -- cross-conversation synthesis: the case studies

This is a genuinely different kind of test from Steps 1-3 -- K2/K4 operate
on one conversation at a time, so this can't run through the pipeline as-is.
It's closer to a direct prompt-and-grade exercise:

1. Pick one case study (start with `0009` -- it's the smallest, good for a
   first dry run of the process itself).
2. Give the candidate model the raw content of every conversation the case
   study's `timeline` cites (not the case study file itself -- that would
   be handing it the answer).
3. Ask it to reconstruct the story: what happened, in what order, and what
   `DECISIONS.md` ruling it maps to.
4. Grade against the case study's `timeline` -- did it find the same
   events, in the right order, without inventing ones that aren't there?
   The `why_this_is_a_good_benchmark_item` section in each case study file
   names the specific trap to watch for (e.g. 0017's "concluding it was
   lost rather than drafted-but-unratified" from reading only one
   conversation).
5. Work up through the tiers (0009/0008 -> 0018/0026 -> 0012/0017) as
   confidence in the process builds. This is expensive per item (multiple
   full conversations in context per test), so budget accordingly --
   probably not something you run 3x per model the way Steps 1-2 do.

---

## Step 5 -- assemble the comparison

Once Steps 1-2 (and as much of 3-4 as you've done) have real data:

```python
from chronicler.pipeline import bench_report as br

rows = [
    br.build_row(source="bench", host=..., model_id="gemma-4", stage="K2",
                 cool_down_preceded=False, config_fingerprint=..., prompt_fingerprint=...,
                 bench_entries=..., failure_entries=..., load_cost_entries=..., k2_report=...),
    # one row per (model, config) unit, control included
]
print(br.render_markdown_table(rows))
```

`compare_medians(a, b)` will tell you `"a_faster"`, `"b_faster"`,
`"indistinguishable"`, or `"insufficient_data"` for any pair -- never a
tie-broken guess. `detectable_difference_floor(control_row)` tells you how
small a difference Task 0's own repeated runs could actually detect, which
is the number to hold any candidate's margin against before treating it as
real.

---

## Step 6 -- what this round does NOT produce

No tier gets named. No candidate gets recommended. The output of this
runbook is a filled-in comparison table plus whatever Level 2 / synthesis
tallies you've built -- evidence for a future round to rule on, not a
ruling itself.
