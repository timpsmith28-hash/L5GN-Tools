# UAT walk-sheet — the work rig, solo (`10280L`)

**Take this with you.** Self-contained: every command, what to record, and where
to stop. Covers four rounds at once, because the work laptop is the only machine
that can walk any of them — estate-scoped visibility (0025), the MCF registry,
local transcript intake Phase 4, and the deck against real MCF data.

**Machine:** `10280L`, solo, **loopback only**, MCF/work estate only.
**Governing decisions:** 0010 (deposit wall), 0023 (gate on shared surfaces),
**0025** (visibility is scoped by surface; a solo box may read its own estate on
loopback), 0012 (three tiers).
**Playbook:** `SOLO_PLAYBOOK.md` §10/§11 — *both marked "written, not walked"*.
You are the first walk of that section as well as of these items.

Mark items as walked with evidence. Results go in
`docs/UAT_work_rig_solo_results.md` with a uat stamp (`commit`, `host=10280L`,
`walked=<date>`) — **no `gate=` field**.

---

## Before you start — one non-technical check

This creates a **durable local database of MCF chat content** on a corporate
machine, and ingests work material into a store that didn't previously exist.
That is a different thing from reading your own files. Satisfy yourself it's
within what you're permitted to do with that material before Part 4 runs, not
after. Everything here stays on the machine — no deposit, no push, loopback
only — but "it never left the laptop" is an argument you want to have decided in
advance rather than reconstructed later.

---

## Part 0 ▸ prerequisites — check these before anything else

The report flags these as genuinely unresolved. **If Part 0 isn't satisfied,
Parts 4–6 cannot run at all.**

- [ ] **0.1** `config/local.json`'s `10280L` entry currently carries only
  `role`/`estate`/`roots`/`push_target` — **no `vault`, `estates_dir` or
  `chronicler_home`.** Solo setup (`SOLO_PLAYBOOK.md` §3–§10) has to happen on
  this machine first. Record whether it was already done or done today.
- [ ] **0.2** Find the Cowork packaged-app folder name: look under
  `C:\Users\<you>\AppData\Local\Packages\` for the `Claude_*` entry (gaming rig
  is `Claude_pzs8sxrjxfjjc` — the suffix may differ). **Write it down.**
- [ ] **0.3** Confirm the CLI store: `C:\Users\<work-username>\.claude\projects`.
  The Windows account name is probably not `timps`. **Write it down.**
- [ ] **0.4** A **work-rig-local throwaway** `CHRONICLER_HOME`. Never share one
  across rigs (§11).

0.2 and 0.3 feed `cli_transcripts_home` / `cowork_transcripts_home` in this
machine's config entry.

---

## Part 1 ▸ solo build stands up

- [ ] **1.1** `.venv` built, `pip install -e .` **and** `pip install -e .[review]`.
- [ ] **1.2** `python verify.py` → **GREEN on this machine.** Do not assume it —
  the gate was green on Linux and red on Windows once already today
  (`docs/investigation/2026-07-27_gate-green-on-linux-red-on-windows.md`). A
  red gate here is a finding, not a nuisance: record the failure verbatim.
- [ ] **1.3** Run `verify.py` in a shell where `CHRONICLER_HOME` /
  `CHRONICLER_REGISTRY_PATH` are **not** set (solo sharp edge 9 — they leak into
  `tester_census`). Use a separate window for the walk below.
- [ ] **1.4** `python run.py config` reports `host=10280L`, `estate=work`.

---

## Part 2 ▸ estate-scoped visibility (0025) — only walkable here

The whole reason this round exists. Record the exact messages.

- [ ] **2.1 Loopback is enforced structurally.**
  `python run.py review --host 0.0.0.0` → **must exit non-zero and name 0025.**
  Paste the message. If it binds, **stop the walk** — that is the load-bearing
  half of 0025 and everything below assumes it holds.
- [ ] **2.2 Loopback works.** `python run.py review --host 127.0.0.1` starts and
  serves.
- [ ] **2.3 An undeclared estate refuses.** Temporarily blank/junk `estate` in
  this machine's config; `run.py review` must refuse to serve, naming the
  reason. **Restore it afterwards.**
- [ ] **2.4 The wall, from the other side** — the check the dev vault could never
  answer. No `*-personal` thread appears anywhere in the deck. There should be
  none present at all, so also confirm *the filter is the reason*: check
  `account_clause_for_estate("work")` resolves to the `%-work` clause, rather
  than concluding it from an empty result.

---

## Part 3 ▸ the MCF-only registry

- [ ] **3.1** `python chronicler/pipeline/build_registry.py --estate work`
  (§11) produces a registry scoped to this estate.
- [ ] **3.2 Disclosure check:** open it and confirm it contains **MCF projects
  only** — no personal projects, no `L5GN` programme entries. This is the point
  of the scoped registry: the work box never holds your personal project list.
- [ ] **3.3** `CHRONICLER_REGISTRY_PATH` points at it, explicitly (solo sharp
  edge 7 — an unset registry path derives by hopping two levels up from
  `CHRONICLER_HOME` and can silently find a *different real file*).
- [ ] **3.4** Record the link-target count — `run.py review` prints it at start.

---

## Part 4 ▸ local transcript intake, Phase 4

In the walk shell, with `CHRONICLER_HOME` and `CHRONICLER_REGISTRY_PATH` set:

```powershell
.\.venv\Scripts\python chronicler\pipeline\local_transcripts.py           # census
.\.venv\Scripts\python chronicler\pipeline\ingest_local_transcripts.py    # dry-run
.\.venv\Scripts\python chronicler\pipeline\ingest_local_transcripts.py --apply
.\.venv\Scripts\python chronicler\pipeline\ingest_local_transcripts.py --apply   # idempotency
```

- [ ] **4.1** Census finds both stores and reports session/message counts.
  **Record them** — this is the first measurement of how much work-side chat
  history actually exists.
- [ ] **4.2** Dry-run writes nothing.
- [ ] **4.3** `--apply` lands threads with **`account = "claude-local-work"`** —
  the estate resolved from this machine's config, never from content. If it says
  `-personal`, **stop**: the label is what 0025 uses to decide visibility.
- [ ] **4.4 Idempotency.** The second `--apply` reports identical counts. This is
  the requirement that matters most — these files grow.
- [ ] **4.5** Source files unmodified — check mtimes on a couple of `.jsonl`
  files before and after.
- [ ] **4.6** Exact-links: expect **0 until Part 3's registry exists**; after it,
  CLI sessions whose cwd names an MCF repo should link. Record which, if any.

---

## Part 5 ▸ the deck against real MCF data — the actual test

```powershell
.\.venv\Scripts\python chronicler\pipeline\relink.py --out data\relink_work_dryrun.txt
.\.venv\Scripts\python chronicler\pipeline\relink.py --apply
.\.venv\Scripts\python run.py review --host 127.0.0.1
```

- [ ] **5.1** Read the dry-run table **before** applying. Record auto-link /
  suggestion / ambiguous / no-op counts.
- [ ] **5.2** The deck shows MCF projects with pending counts, grouped.
- [ ] **5.3 The real question:** with cleaner, better-defined projects than the
  personal estate, does the grouping *feel* right? Are the batches coherent —
  does one project's batch read as one topic? This is the judgement the whole
  deck exists to serve, and MCF is the dataset that can answer it.
- [ ] **5.4** Rule a batch: tick, Confirm, and check counts update.
- [ ] **5.5** Rival case on MCF data, if one appears — the `→ <other>` button.
- [ ] **5.6** Note anything the deck *should* show you and doesn't.

---

## Part 6 ▸ the item that gates the knight — free second chance

Deck UAT **1.2** is still open: the backfill's note-parsing has never met a real
note. The dev vault couldn't exercise it. **This vault can**, after Part 5's
relink apply:

```powershell
.\.venv\Scripts\python -c "import sqlite3,os; c=sqlite3.connect(os.environ['CHRONICLER_HOME']+r'\chronicler.db'); n=c.execute('update review_queue set candidate_project=NULL, rival_project=NULL').rowcount; c.commit(); print('nulled', n)"
.\.venv\Scripts\python chronicler\pipeline\backfill_candidate_project.py
```

- [ ] **6.1** The dry-run recovers candidates from `note` prose alone. **Record
  the resolved / unresolved split**, and any unresolved reasons verbatim.
- [ ] **6.2** `--apply`, then confirm the deck renders the same as before the
  null — i.e. the recovery was faithful, not merely non-empty.

This is the evidence that decides whether the backfill can be trusted on the
knight's ~500 live rows.

---

## Stop conditions

- **2.1 fails** (binds beyond loopback) → stop everything below it.
- **Any personal-account data appears** → stop, record, do not continue.
- **Gate red on this machine** → record verbatim; it's a real finding, and a
  Windows-only failure is a known family (see the investigation note).
- **4.3 labels threads `-personal`** → stop before Part 5.

## Not walkable here

Anything knight-side: the live vault, deposit/consume, the mesh. Nothing in this
sheet pushes, deposits, or reaches another machine.
