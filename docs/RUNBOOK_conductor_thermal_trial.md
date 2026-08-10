# Runbook — the conductor throughput trial (work rig, `10280L`)

**Revised 2026-08-10.** The first version of this runbook was built around
`nvidia-smi` and a hardware temperature sensor. **There is no programmatic
temperature source on `10280L`** — see "What was tried" below. This version
measures the thing that actually matters instead: **whether sustained load makes
the work slower.**

Collects the evidence three open questions need before the conductor's governor
is built (`COWORK_BRIEF_conductor_governor.md`):

- **Q1 — is the pause in the right place?** `--cool-down` pauses *between*
  conversations. K2 calls the model once per *window*, so a single large
  conversation is a sustained burst no pause can interrupt. If throughput decays
  *within* one conversation, between-conversation pausing cannot reach the
  problem.
- **Q2 — does TTL work unattended?** Does a short `--model-ttl`, left to expire
  in the cool-down gap, free and reload the model without the manual step — and
  what does the reload cost?
- **Q3 — which lever helps?** Cool-down lowers *duty cycle*;
  `--batch-target-tokens` / `--max-window-tokens` lower *peak*.

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

**So the trial is open-loop on temperature and closed-loop on throughput.** That
is a real limitation and it must be stated in the results: this measures
*performance degradation under sustained load*, which is what throttling does to
you, not the temperature that causes it. Anything else — the chassis feeling hot
— is a subjective observation and gets recorded as one.

---

## The trap that would void the whole trial

**K2 caches per conversation.** Re-running a project with the real cache
re-extracts nothing, makes zero model calls and finishes in seconds. Every
comparison would read as "the pause fixed it" when nothing ran at all.

**Every run below uses its own `--cache` and `--out` under a scratch
directory.** Sanity check on each run: the timing log must hold one record per
in-scope conversation, and the run summary's `reextracted` count must be
non-zero.

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

**Confirm the work is actually landing on the Arc GPU** — if LM Studio is running
on CPU instead, the thermal story is different and the trial needs saying so:

```powershell
Get-Counter "\GPU Engine(*engtype_Compute)\Utilization Percentage" -Continuous -SampleInterval 5
```

Run that in a second window during Run 1. Non-trivial compute utilisation means
the iGPU is doing the work.

**Between every run, let the machine settle back to idle.** A run started hot
measures the previous run. Note roughly how long you waited.

---

## Run 1 — sustained load, no pause: does throughput decay?

```powershell
& $PY $K2 --model $MODEL --project "Pricing Model" `
    --cool-down 0 `
    --cache "$T\run1_cache.json" --out "$T\run1_claims.json" `
    --timing-log "$T\run1_timing.jsonl"
```

**What to look for:** in `run1_timing.jsonl`, does `wall_clock_seconds` rise
across the run? Raw seconds are not comparable between conversations of
different sizes, so normalise — seconds per message is a rough guide, and once
per-window timing lands (Task 1 of the successor brief) seconds per window is the
honest unit.

**The signal is the trend, not any single figure.** Eleven conversations where
the last four are consistently slower than the first four is throttling. One slow
conversation is noise.

## Run 2 — one conversation, alone: the decisive test for Q1

From `run1_timing.jsonl`, take the record with the largest
`wall_clock_seconds` and `batch_size: 1`. Build a one-row map so only it runs:

```powershell
$ROW = "<its conversation_id>"
Get-Content config\mcf_conversation_map.tsv | Select-Object -First 1 > "$T\one.tsv"
Get-Content config\mcf_conversation_map.tsv | Select-String -SimpleMatch $ROW >> "$T\one.tsv"
```

```powershell
& $PY $K2 --model $MODEL --map "$T\one.tsv" `
    --cool-down 300 `
    --cache "$T\run2_cache.json" --out "$T\run2_claims.json" `
    --timing-log "$T\run2_timing.jsonl"
```

**The cool-down will never fire** — one conversation is one group, and the pause
only happens *between* groups. That is deliberate: this is pure
intra-conversation load with every pausing mechanism structurally unable to
intervene.

**This run needs per-window timing to be readable.** With only per-conversation
records it emits a single line and tells you nothing about decay *within* it. If
per-window timing is not yet built, either build it first or read this run from
the terminal progress output and the total wall-clock against Run 1's figure for
the same conversation.

**What it answers:** if throughput decays inside this single conversation,
between-conversation pausing cannot fix it, and the governor needs an
intra-conversation pause — a materially bigger change to K2. If it stays flat,
the current granularity is sufficient.

**Do this one first if you only have time for one.**

## Run 3 — same load, with the pause: does duty cycle help?

```powershell
& $PY $K2 --model $MODEL --project "Pricing Model" `
    --cool-down 90 `
    --cache "$T\run3_cache.json" --out "$T\run3_claims.json" `
    --timing-log "$T\run3_timing.jsonl"
```

**Compare per conversation against Run 1.** Same conversations, same order, so
the ratio is clean. If pausing prevents throttling, the *later* conversations
show a bigger speedup than the early ones. **A flat ratio across the run means
pausing bought nothing** — it only cost you the pause.

Record the added wall-clock too. Ten pauses at 90s is fifteen minutes, and the
planner has to budget for it.

## Run 4 — the TTL question (Q2), and the reload penalty

```powershell
& $PY $K2 --model $MODEL --project "Solution Configurator" --project "Activity Statements" `
    --model-ttl 60 --cool-down 90 `
    --cache "$T\run4_cache.json" --out "$T\run4_claims.json" `
    --timing-log "$T\run4_timing.jsonl"
```

Poll the model list in a second window:

```powershell
while ($true) { (Get-Date -Format o); curl.exe -s http://localhost:1234/v1/models; Start-Sleep 15 }
```

**Record:**

1. **Did the model leave the list during a gap and return afterwards with no
   manual step?** That is the whole question. Yes → the explicit load/unload
   controller stays dropped.
2. **What did the reload cost?** Compare the first conversation after each gap
   against the others in `run4_timing.jsonl`. That difference is the JIT reload,
   currently recorded as if it were extraction time — the measurement that
   decides whether the timing record needs a "preceded by a cool-down" field
   before the calibration ledger is built on it.
3. **Memory** — the Arc 140V's 16GB is shared system RAM, so watch overall
   system memory across the gap in Task Manager rather than a VRAM figure.

## Run 5 — peak versus duty cycle (Q3)

Read the current defaults first (`--help`), then roughly halve both:

```powershell
& $PY $K2 --model $MODEL --project "Pricing Model" `
    --cool-down 0 --batch-target-tokens 2000 --max-window-tokens 2000 `
    --cache "$T\run5_cache.json" --out "$T\run5_claims.json" `
    --timing-log "$T\run5_timing.jsonl"
```

**Compare against Runs 1 and 3.** If lowering peak preserves throughput better
than pausing does, the thermal profile should lead with the token dials and treat
cool-down as secondary — the opposite of how the design currently frames it.

---

## What to bring back

Per run: the timing log, total wall-clock, the idle settling time before it, and
your subjective note on the chassis (recorded as subjective).

Then the four answers:

- **Q1 (Run 2):** does throughput decay inside a single conversation? **Yes**
  means the governor needs an intra-conversation pause, and that is a finding
  against the successor brief's Task 3 before it is built.
- **Q2 (Run 4):** does TTL free and reload the model unattended? **No** — describe
  concretely what degraded; that description is the only thing that would justify
  building a load/unload controller.
- **Reload penalty (Run 4):** any measurable post-gap inflation means the timing
  record must carry whether a cool-down preceded it, before the ledger reads the
  field.
- **Q3 (Run 5):** which lever preserved throughput better?

Record the results in `docs/COWORK_REPORT_conductor.md` under the section
currently marked pending, and stamp `docs/UAT_conductor.md` for the `[W]` item.

---

## Cleanup

```powershell
Remove-Item -Recurse -Force "data\knowledge_curator\_thermal_trial"
```

No run above wrote to the real cache, the real `claims.json`, or `config/`.
