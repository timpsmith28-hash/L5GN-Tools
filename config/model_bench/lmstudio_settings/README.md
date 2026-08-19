# LM Studio model settings -- bench-tier reference

One JSON file per model candidate, capturing the full LM Studio load-model
dialog settings as confirmed by screenshot, alongside the subset of those
settings that actually feed `run_bench_sweep.py`'s `config_fingerprint`
(via `bench_ledger.build_config_fingerprint`).

## Why this exists

`build_config_fingerprint()` only hashes 7 keys: `context_length`,
`quantisation`, `gpu_offload_layers`, `kv_cache_type`, `flash_attention`,
`batch_size`, `ttl_seconds` -- whatever is passed to `run_bench_sweep.py run`
via its `--context-length` / `--quantisation` / `--gpu-offload-layers` /
`--kv-cache-type` / `--flash-attention` / `--batch-size` / `--model-ttl`
flags. Everything else visible in LM Studio's load dialog (CPU thread pool
size, evaluation vs physical batch size as two separate numbers, max
concurrent predictions, Unified KV Cache, context checkpoints, offload-KV-
to-GPU, keep-in-memory, try mmap, seed, speculative decoding) is real
configuration that can change a run's behaviour or timing, but is invisible
to the fingerprint. Two runs with an identical `config_fingerprint` are NOT
guaranteed to have identical LM Studio settings -- only identical values for
those 7 fields.

These per-model files are the record of everything else. When a setting is
tweaked between runs (e.g. Unified KV Cache toggled on for Phi-3), it goes
in the relevant model's JSON, with a note on whether it also happens to move
one of the 7 fingerprinted fields.

## Fields

- `lmstudio_settings`: the full dialog, as confirmed via screenshot.
- `run_bench_sweep_config_args`: the best-known mapping from
  `lmstudio_settings` onto the 7 keys `run_bench_sweep.py run` actually
  accepts -- pass these as the `--context-length` etc. flags for that model.
- `config_fingerprint_from_real_run`: the real fingerprint from
  `bench_ledger.jsonl`, when a completed run exists to read it from.
- `fields_not_covered_by_config_fingerprint`: explicit list, per model, of
  what's tracked here but NOT in the hash -- read this before assuming two
  fingerprint-matching runs are otherwise identical.

## Known open question

`batch_size` (the fingerprinted field) has been mapped to LM Studio's
"Physical Batch Size", not "Evaluation Batch Size" -- the two models on file
share the same Physical Batch Size (512) but differ on Evaluation Batch Size
(1024 vs 2048), so this choice was made for cross-model consistency, not
verified against what `run_bench_sweep.py` or LM Studio's API actually do
with it. Worth settling before this file is treated as a source of truth for
fingerprint reconstruction.
