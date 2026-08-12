# Runbook — the conductor throughput trial (work rig, `10280L`)

**Revised 2026-08-11, for Addendum 2's fixed instrument.** The first
revision (2026-08-10) measured wall-clock per conversation/window. That
instrument turned out to be broken: `token_count` on a window record is
*input* tokens only, so wall-clock conflates a slow (loaded) call with a
verbose (long-output) one. Real data from the first pass showed a 24×
apparent swing — 7,972 input tokens in 14.6s versus 2,596 in 111.7s — driven
entirely by how much the model *wrote*, not by machine load. **Do not read
`wall_clock_seconds` alone as a throughput figure. Ever.** See
`docs/COWORK_BRIEF_conductor_governor.md`'s Addendum 2 and
`docs/COWORK_REPORT_conductor_governor.md` for the full account.

**The fix is built and committed** (`b81357e`): `extract_claims.py` now
captures the LM Studio response's `usage` block and derives
**`generation_ms_per_token`** — independent of output length, the number
this trial should actually read. It appears in the new per-**window**
timing record (`--window-timing-log`), alongside the existing
per-conversation one. **Use `generation_ms_per_token`, never
`wall_clock_seconds`, for every comparison below.**

Collects the evidence three open questions still need before the
conductor's governor is built:

- **Q1 — is the pause in the right place?** `--cool-down` pauses *between*
  conversations. K2 calls the model once per *window*, so a single large
  conversation is a sustained burst no pause can interrupt. If throughput
  decays *within* one conversation, between-conversation pausing cannot
  reach the problem. **Still open** — this is the run the fixed instrument
  exists for.
- **Q2 — does TTL work unattended?** **Already answered: yes**, per the
  design thread — TTL frees and reloads the model unattended during the
  cool-down gap, and the load/unload controller stays dropped. Run 4 below
  is now optional/confirmatory: worth one clean re-run with the fixed
  instrument to quantify the reload penalty precisely, not to re-litigate
  whether it works.
- **Q3 — which lever helps?** Cool-down lowers *duty cycle*;
  `--batch-target-tokens` / `--max-window-tokens` lower *peak*. **Still
  open** — not run in the first pass.

---

## Before anything else: check the KV cache offload setting

The first pass's 10 August data showed a **persistent** ~36% degradation
(58ms/token → 79–98ms/token, by LM Studio's own `eval time` logs) that
**survived an overnight cold start** — not a thermal signature (heat
recovers overnight; a config state doesn't). The most plausible cause named
in the addendum is **`Offload KV Cache to GPU: Disabled`** in LM Studio's
model load settings, silently routing the KV cache to host RAM.

**Check this setting before Run 1.** If it's off, that alone may explain
most of what looked like throttling last time, and every run below should
be done with it **on**, noted explicitly which state it was in. If you want
a clean before/after, one deliberate run with it disabled is useful data —
just label it, don't let it contaminate a run meant to isolate cool-down or
peak-token effects.

---

## What was tried for a temperature reading, and why there is none

Recorded so nobody spends this afternoon again:

| Route | Result on `10280L` |
|---|---|
| `MSAcpi_ThermalZoneTemperature` (WMI, `root\wmi`) | **Not supported** — firmware does not populate the ACPI zone |
| `Get-Counter "\Thermal Zone Information(*)\Temperature"` | **Object not found** — same gap, different access path |
| LibreHardwareMonitor / HWiNFO / Open Hardware Monitor | **Blocked.** They load WinRing0 (CVE-2020-14979), which is on Microsoft's vulnerable-driver blocklist; `Win32_DeviceGuard.SecurityServicesRunning` returns `2, 3, 4, 7`, so Memory Integrity is enforcing and the driver cannot load |
| Dell Command \| Monitor (`root\dcim\sysman`) | **Namespace exists but is empty** — only `__*` / `CIM_*` system classes, no `DCIM_*`. The provider is not installed |
| `nvidia-smi` | **Not applicable** — the GPU is an Intel Arc 140V (16GB shared), no NVIDIA adapter |

**So the trial is open-loop on temperature and closed-loop on throughput.**
That is a real limitation and it must be stated in the results: this
measures *performance degradation under sustained load*, which is what
throttling does to you, not the temperature that causes it — and, per the
first pass, is also what a persistent config state does to you, which looks
identical on a throughput-only instrument. Anything else — the chassis
feeling hot — is a subjective observation and gets recorded as one.

---

## The trap that would void the whole trial

**K2 caches per conversation.** Re-running a project with the real cache
re-extracts nothing, makes zero model calls and finishes in seconds. Every
comparison would read as "the pause fixed it" when nothing ran at all.

**Every run below uses its own `--cache` and `--out` under a scratch
directory.** Sanity check on each run: the timing log must hold one record
per in-scope conversation, and the run summary's `reextracted` count must
be non-zero.

---

## Setup

From the repo root on `10280L`, in PowerShell:

```powershell
$T = "data\knowledge_curator\_thermal_trial"
New-Item -ItemType Directory -Force -Path $T | Out-Null
$PY = ".venv\Scripts\python.exe"
$K2 = "chronicler\pipeline\extract_claims.py"
curl.exe http://localhost:1234/v1/models
$MODEL = "<the model id from that list>"
```

The same model in every run, or nothing is comparable.

**Every run should pass `--window-timing-log` now** — it's the only source
of `generation_ms_per_token`, and Run 2 is unreadable without it:

```powershell
--timing-log "$T\runN_timing.jsonl" --window-timing-log "$T\runN_windows.jsonl"
```

**Confirm the work is actually landing on the Arc GPU** — if LM Studio is
running on CPU instead, the thermal story is different and the trial needs
saying so:

```powershell
Get-Counter "\GPU Engine(*engtype_Compute)\Utilization Percentage" -Continuous -SampleInterval 5
```

Run that in a second window during Run 1. Non-trivial compute utilisation
means the iGPU is doing the work.

**Between every run, let the machine settle back to idle.** A run started
hot measures the previous run. Note roughly how long you waited.

**Reading a `runN_windows.jsonl` file:** each line is one window's record.
`usage_available` should be `true` on every line if LM Studio is returning
`usage` (it should — check one line by hand if unsure). The number to plot
or eyeball per conversation is `generation_ms_per_token`, in call order.
`cool_down_preceded: true` marks the one window per gap that paid a JIT
reload — expect it inflated, and expect it explained by that flag, not
folded into "conversation N was just slow."

---

## Run 1 — sustained load, no pause: does throughput decay?

```powershell
& $PY $K2 --model $MODEL --project "Pricing Model" `
    --cool-down 0 `
    --cache "$T\run1_cache.json" --out "$T\run1_claims.json" `
    --timing-log "$T\run1_timing.jsonl" --window-timing-log "$T\run1_windows.jsonl"
```

**What to look for:** in `run1_windows.jsonl`, does `generation_ms_per_token`
rise across the run, in window/call order? This is the number the first
pass didn't have — it removes the output-length confound entirely, so a
rising trend here is a real candidate for throttling (or the KV-cache
config state, if that setting was off — see above).

**The signal is the trend, not any single figure.** Eleven conversations
where the last four are consistently slower than the first four is a real
finding. One slow conversation is noise.

## Run 2 — one conversation, alone: the decisive test for Q1

From `run1_windows.jsonl` (not the conversation-level file — you need a
conversation with several windows), find a `conversation_id` with multiple
records and a high total token count. Build a one-row map so only it runs:

```powershell
$ROW = "its_conversation_id_with_no_angle_brackets"
Get-Content config\mcf_conversation_map.tsv | Select-Object -First 1 | Set-Content -Encoding utf8 "$T\one.tsv"
(Get-Content config\mcf_conversation_map.tsv | Select-String -SimpleMatch $ROW).Line | Add-Content -Encoding utf8 "$T\one.tsv"
```

**Two traps here, both hit in the first live attempt:**

1. `$ROW` is a literal value, not a placeholder — don't copy the angle
   brackets from this doc into it, or `Select-String` matches nothing and
   `one.tsv` ends up with just the header.
2. **`>`/`>>` write UTF-16LE on Windows PowerShell.** K2 opens the map file
   as `utf-8-sig` (`knowledge_index.load_map`), so a `>`-written map fails
   with `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in
   position 0`. Always pipe through `Set-Content -Encoding utf8` /
   `Add-Content -Encoding utf8` instead, as above. Also note `Select-String`
   returns `MatchInfo` objects, not plain text — pull `.Line` before piping,
   or the row written is the object's string form, not the TSV row.

**Verify before running K2 against it:**

```powershell
Get-Content "$T\one.tsv"
```

Should be exactly two lines: the header, then the one matched row.

```powershell
& $PY $K2 --model $MODEL --map "$T\one.tsv" `
    --cool-down 300 `
    --cache "$T\run2_cache.json" --out "$T\run2_claims.json" `
    --timing-log "$T\run2_timing.jsonl" --window-timing-log "$T\run2_windows.jsonl"
```

**The cool-down will never fire** — one conversation is one group, and the
pause only happens *between* groups. That is deliberate: this is pure
intra-conversation load with every pausing mechanism structurally unable to
intervene.

**This run is now fully readable.** `run2_windows.jsonl` holds one record
per window of this single conversation, each with its own
`generation_ms_per_token`, `window_index` and `windows_total`. Plot or list
`generation_ms_per_token` by `window_index` in order.

**What it answers:** if `generation_ms_per_token` climbs across the
windows of this ONE conversation, throughput decays *within* a
conversation, between-conversation pausing cannot fix it, and the governor
needs an intra-conversation pause — a materially bigger change to K2, and a
finding against Task 3 as currently scoped, to raise before building it. If
it stays flat, the current granularity (pausing between conversations) is
sufficient.

**Do this one first if you only have time for one — it's the blocker on
Task 3.**

## Run 3 — same load, with the pause: does duty cycle help?

```powershell
& $PY $K2 --model $MODEL --project "Pricing Model" `
    --cool-down 90 `
    --cache "$T\run3_cache.json" --out "$T\run3_claims.json" `
    --timing-log "$T\run3_timing.jsonl" --window-timing-log "$T\run3_windows.jsonl"
```

**Compare `generation_ms_per_token` per conversation against Run 1** (not
wall-clock — the first pass's −2.3% conclusion here was read off wall-clock
and is suspect for exactly the reason this whole revision exists). Same
conversations, same order, so the ratio is clean. If pausing prevents
throttling, the *later* conversations show a bigger improvement in
`generation_ms_per_token` than the early ones. **A flat ratio across the
run means pausing bought nothing** — it only cost you the pause. If the KV
cache setting was the real cause of the first pass's drop, expect THIS run
to also show little benefit from pausing alone, and that itself is a
useful, different finding from Q3's dial comparison below.

Record the added wall-clock too. Ten pauses at 90s is fifteen minutes, and
the planner has to budget for it — that part of the original reading is
still valid; wall-clock is fine for *elapsed time*, just not for
*throughput*.

## Run 4 — the TTL question (Q2, already answered — confirmatory only), and the reload penalty

Q2 itself doesn't need re-answering — skip this run entirely if time is
short. Worth doing once if you want the reload penalty quantified with the
real instrument instead of guessed at:

```powershell
& $PY $K2 --model $MODEL --project "Solution Configurator" --project "Activity Statements" `
    --model-ttl 60 --cool-down 90 `
    --cache "$T\run4_cache.json" --out "$T\run4_claims.json" `
    --timing-log "$T\run4_timing.jsonl" --window-timing-log "$T\run4_windows.jsonl"
```

**Record:**

1. **The reload penalty, precisely.** In `run4_windows.jsonl`, filter to
   `cool_down_preceded: true` — that's exactly the one window per gap that
   paid the JIT reload. Compare its `generation_ms_per_token` (and raw
   `wall_clock_seconds`, which now legitimately isolates the reload cost
   since it's the ONLY window flagged) against the non-flagged windows in
   the same conversation. That's the number Task 2's ledger would need to
   partition on, now measured rather than assumed.
2. **Memory** — the Arc 140V's 16GB is shared system RAM, so watch overall
   system memory across the gap in Task Manager rather than a VRAM figure.

## Run 5 — peak versus duty cycle (Q3)

Read the current defaults first (`--help`), then roughly halve both:

```powershell
& $PY $K2 --model $MODEL --project "Pricing Model" `
    --cool-down 0 --batch-target-tokens 2000 --max-window-tokens 2000 `
    --cache "$T\run5_cache.json" --out "$T\run5_claims.json" `
    --timing-log "$T\run5_timing.jsonl" --window-timing-log "$T\run5_windows.jsonl"
```

**Compare `generation_ms_per_token` trend against Runs 1 and 3** (again,
not wall-clock — a smaller window is naturally faster in wall-clock terms
regardless of load, which is exactly the confound `generation_ms_per_token`
removes). If lowering peak preserves `generation_ms_per_token` better than
pausing does, the thermal profile should lead with the token dials and
treat cool-down as secondary — the opposite of how the design currently
frames it, and a legitimate outcome per the brief.

---

## What to bring back

Per run: the timing + window-timing logs, total wall-clock, the idle
settling time before it, the KV-cache-offload setting it was run under, and
your subjective note on the chassis (recorded as subjective).

Then the three still-open answers:

- **Q1 (Run 2):** does `generation_ms_per_token` climb across the windows
  of one conversation? **Yes** means the governor needs an
  intra-conversation pause — a finding against Task 3 before it's built.
  **No** means the current between-conversation granularity is sufficient,
  and Task 3 can proceed as scoped.
- **Q3 (Run 5):** which lever — cool-down or the token dials — preserves
  `generation_ms_per_token` better? This sets which dial the thermal
  profile leads with.
- **Reload penalty (Run 4, optional):** the measured `generation_ms_per_token`
  / `wall_clock_seconds` delta on `cool_down_preceded: true` windows versus
  the rest, now precisely isolated instead of estimated.

Record the results in `docs/COWORK_REPORT_conductor_governor.md`, in a new
section under Addendum 2 (or a new addendum, if the findings are
substantial enough to change Task 3's design again — follow the same
append-and-supersede convention the brief itself uses). Stamp
`docs/UAT_conductor_governor.md`'s two open Addendum 2 items (`[W]`/`[H]`)
once walked.

---

## Cleanup

```powershell
Remove-Item -Recurse -Force "data\knowledge_curator\_thermal_trial"
```

No run above wrote to the real cache, the real `claims.json`, or `config/`.
