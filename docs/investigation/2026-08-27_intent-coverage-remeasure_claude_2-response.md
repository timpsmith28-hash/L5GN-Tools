<!-- actioned: (none yet) -->

# Response — re-measure of the INTENT §2 coverage figure

**Measured:** 2026-08-27, `LucasGoonPC`, personal estate only (**0039** clauses 1
and 3). **Read-only throughout** (INTENT §5): every vault open was
`sqlite3 ... mode=ro` against a byte-identical copy; nothing was written to any
vault, and no pipeline stage was run.

**Prompt:** `2026-08-27_intent-coverage-remeasure_claude_1-prompt.md`.

**Containment.** No work-estate content appears below. Work-account material is
reported as counts only -- no title, no fragment, no example, no project name.

---

## The answer, first

**The headline figure is no longer true, and it has moved in the direction the
hypothesis did not predict.**

- On INTENT's own definition, the figure is now **7.8% (23 of 293)**, not 8.1%.
- Scoped as **0039** requires -- personal estate only, which is the shape this
  round was asked for -- the *baseline itself* was never 8.1%. It was
  **11.4% (27 of 236)**. INTENT's 8.1% mixes work-estate threads into a personal
  numerator's denominator.
- Like for like, on the same sources and the same grouping, coverage has fallen
  from **11.4% to 9.5%**.

**The operator's hypothesis is not supported.** Grouping is worth at most
**0.05 percentage points** here, and it is measurable to that precision. The
conversations were not regrouped between the two measurements -- every
Gemini-personal row still carries the same `group_fallback_v1` parser and all
1,062 of its `thread_grouping` review rows are still `pending`. The fall is a
**linking** result: the vault's entire evidence base was rebuilt from one signal
and the other two have never been run against it.

**And the falsification test says coverage is the wrong proxy anyway** -- for a
reason sharper than "it still can't answer." See §5.

---

## 1. The definition, fixed before the number

INTENT §2 does not state its own method, so it was recovered from the document
that produced it: `docs/archive/chronicler_investigation_2026-07-18.md`, Task 2,
which is where 1,171 / 332 / 150 / 27 / 12.8% / 8.1% all first appear together.

| Term | What was counted |
|---|---|
| **Population** | Every row in `threads`. No filter on account, source, status or date. |
| **Substantive thread** | A thread with **>= 4 messages**. This is the `threads.substantive` column's own definition, stamped in the vault as `meta.substantive_min_messages = 4` and restated in `ARCHITECTURE.md` §6 ("Vault contract ... `substantive` = >=4 messages"). |
| **Carries an evidence link** | `threads.project_confidence = 'evidence'` -- **not** "appears in the `link_evidence` table". |
| **Headline figure** | Threads at `project_confidence='evidence'`, over all threads. |

### Why the third row is `project_confidence`, not `link_evidence`

This is the one place the definition could have been chosen to flatter, so it is
settled by arithmetic rather than by preference.

`docs/archive/COWORK_BRIEF_build_round_2.md` §B.4 hands a successor SQL that
tests `thread_id IN (SELECT DISTINCT thread_id FROM link_evidence)`. That is a
*different* test, and the two can disagree. INTENT's own sentences decide which
one it used:

- "150 links across 1,171 threads (12.8%)" -- 150/1171 = 12.81%, so the 150 is a
  count of **threads**, not of evidence rows. The 2026-07-18 investigation's
  confidence table gives `evidence: 150` exactly.
- "The other 123 evidence links land on sub-4-message Takeout fragments" --
  150 - 27 = 123, so the 27 is the substantive subset **of those same 150**.

Reconciled independently against `data/vault_reader.json` (the 2026-07-17 scan,
the only surviving artefact of that vault): summing the seven repo-backed vault
projects gives **150 threads and 27 substantive threads**, every one at
`by_confidence: {evidence: N}`. The definition is confirmed, to the row.

**In the current vault the two tests agree exactly** -- 53 threads either way,
23 substantive either way -- so nothing below turns on the choice. The
reconciliation is recorded because it is what makes the comparison legitimate,
not because it changes an answer.

---

## 2. What was measured against, and one problem with it

**The vault of record for this machine** is `config/local.json` ->
`LucasGoonPC.vault` = `C:\Users\timps\Documents\chronicler_dev\chronicler.db`.
That is the first key `vault_reader._resolve_vault_path()` consults, so it is
what any scan on this rig reads today.

| | Baseline | Now |
|---|---|---|
| Path | `...\GitHub\Chronicler\chronicler.db` | `...\chronicler_dev\chronicler.db` |
| Recorded by | `data/vault_reader.json`, scanned **2026-07-17** | measured directly, **2026-08-27** |
| `meta.frozen_at` | (not carried in the scan) | `2026-07-27T18:57:39Z` |
| `user_version` | 1 | 1 |
| Threads | 1,171 | 1,172 |
| Messages | 22,004 | 10,387 |
| Accounts | claude-personal, gemini-personal, **gemini-work** | claude-personal, gemini-personal, claude-local-personal |
| `link_evidence` | 746 rows: `filename_xref` 568, `name_alias` 98, `path_mention` 80 | 165 rows: `name_alias` only |

**Integrity.** `CLAUDE.md` warns that a sandbox mount serves stale, byte-truncated
content deterministically. Both vault files were copied out of the mount and
checked before any query: `PRAGMA quick_check` = `ok`, and
`page_size x page_count` equals the on-disk byte count exactly (45,260,800 for
the live vault; 40,992,768 for the pre-finalize backup). A truncated SQLite file
fails both. The reads are sound.

### The problem, stated rather than smoothed over

**These are two different vaults, not one vault at two times.**
`C:\Users\timps\Documents\GitHub\Chronicler\` no longer exists. The current vault
is a rebuild: it holds no work account at all, it gained a source the baseline
never had, and its whole evidence base was produced by a single `relink/1.0` run
stamped `2026-07-27T21:48:20Z`.

So the comparison below is between **two measurements**, not between two states
of one store. Every figure attributed to the baseline comes from
`data/vault_reader.json`, which reconciles to INTENT's published numbers exactly
(§1). Where that artefact does not carry a breakdown, it is named as unavailable
rather than estimated.

**A second vault was deliberately not read.** `config/local.json` records a
`pull_backup` from the castle, whose declared estate is `both`. Reading it would
have put two estates in one run, which **0039** clause 1 forbids outright and
clause 2 reinforces. It is out of scope by ruling, not by reach.

---

## 3. The three numbers

### 3a. The old figure

**8.13% -- 27 of 332 substantive threads.** Headline shape: 150 of 1,171 = 12.81%.

### 3b. The old figure, scoped as this round requires

INTENT's denominator is mixed-estate. Its 332 substantive threads decompose, from
`data/vault_reader.json`:

| Account | Threads | Substantive |
|---|---:|---:|
| claude-personal | 35 | 28 |
| gemini-personal | 1,026 | 208 |
| *(work account)* | 110 | **96** |
| **Total** | **1,171** | **332** |

**29% of "the single most important figure in this estate" was work-estate.**

The numerator was not. Summing the seven repo-backed vault projects that hold all
150 evidence links gives `gemini-personal: 141, claude-personal: 9` and **zero**
on the work account -- no work-account thread carried an evidence link at
baseline. (The eight threads linked at `fuzzy`/`exact` rather than `evidence` are
where the work account appears: 7 of those 8. They are outside INTENT's numerator
by definition.)

So the personal-only baseline, on INTENT's own definition and date:

> **11.44% -- 27 of 236.**

This is the number **0039** would have had this estate publish. It is not a
correction I am entitled to make to INTENT (§7 below); it is what the same
measurement says when scoped the way the ruling requires.

### 3c. The new figure

Measured 2026-08-27 against the declared vault. Every account present is
personal, so the personal-estate scope and the whole-vault scope coincide -- the
scoping is real, not vacuous, and it happens to cost nothing here.

| | Count |
|---|---:|
| Threads (population) | 1,172 |
| Substantive (>= 4 messages) | 293 |
| Threads at `project_confidence='evidence'` | 53 |
| **Substantive threads carrying an evidence link** | **23** |

> **INTENT's shape: 7.85% -- 23 of 293.**
> Headline shape: 53 of 1,172 = **4.52%**.

Both fell. The headline fell harder than the honest figure, which is the one
thing here that moved in the flattering direction and is worth naming as such.

---

## 4. Splitting the delta: grouping or linking

The round's central question. It is separable, and it separates cleanly.

### 4a. Grouping did not change on the side the hypothesis suspected

The Gemini-personal corpus is the fallback-grouped one -- 844 of its 1,062
threads hold exactly two messages, which is what INTENT already calls
"sub-4-message Takeout fragments." If that grouping had been redone, the
hypothesis would hold. It has not been:

- **All 1,062 Gemini rows carry `parser_version = 'group_fallback_v1'`** -- one
  parser, one grouping, unchanged.
- **All 1,062 `thread_grouping` rows in `review_queue` are `pending`.** The
  baseline had 839 of them `confirmed` by the bulk sweep; the current vault has
  none. The grouping rulings were not carried forward, let alone improved on.
- **Layer C (semantic grouping) has still never formed a group** -- consistent
  with **0004** and `ARCHITECTURE.md` §7. There is no regrouping to credit.
- Gemini-personal threads went 1,026 -> 1,062 (+36) and substantive 208 -> 210
  (+2). That is **new ingest at the same granularity**, not regrouping.

**Nothing regrouped. The 8.1% was not an artefact of grouping.**

### 4b. There *is* a grouping defect, it is new, and it is worth 0.05 points

It arrived with the source the baseline did not have.
`chronicler/pipeline/ingest_local_transcripts.py` ruling 5 states it plainly:
`thread_id` **is the session's own uuid**. So each of the 71 local-transcript
rows is a **session**, not a **conversation** -- exactly the collision **0038**
was written to end. 51 of them clear the >= 4 message bar and land in the
denominator as if they were 51 conversations.

Regrouped to conversations -- Cowork sessions keyed on the `local-<uuid>`
segment their recorded `cwd` carries, sub-agent sessions folded into their parent
session, CLI sessions left as themselves -- the 71 sessions are **63
conversations**, of which **49** are substantive rather than 51.

| | Substantive | Figure |
|---|---:|---|
| As stored (session-keyed) | 293 | 7.85% |
| Regrouped to conversations | 291 | **7.90%** |

> **Delta attributable to grouping: +0.05 percentage points.**

Real, in the direction the hypothesis expected, and about forty times too small
to matter. It is a naming defect worth fixing on **0038**'s authority, not a
measurement error.

### 4c. The rest is linking, and the cause is identifiable

Strip the new source entirely and compare the corpus that existed at baseline --
same two sources, same grouping parser, personal only:

| | Baseline (2026-07-17) | Now (2026-08-27) |
|---|---:|---:|
| Substantive threads | 236 | 242 |
| Carrying an evidence link | 27 | 23 |
| **Coverage** | **11.44%** | **9.50%** |

The denominator moved by +6, all of it new ingest. **The numerator fell by 4, and
that is the whole of the change.**

Why: the current vault's evidence base is **165 rows, all `name_alias`, all
produced by one `relink/1.0` run at `2026-07-27T21:48:20Z`.** The baseline's 746
rows were 87% `filename_xref` (568) and `path_mention` (80) -- the two strongest
signals in the system. Neither has been run against this vault:
**`path_scan_log` is empty**, so `extract_path_mentions` has never taken a
watermark here at all.

**So the delta splits:**

| Cause | Effect on the figure |
|---|---|
| Estate scoping (**0039**) -- removing 96 work-estate substantive threads from a personal numerator's denominator | **+3.31 pts** (8.13% -> 11.44%), a correction to the *baseline*, not a change in the world |
| Linking -- evidence base rebuilt from one signal of three; S4/S5 never run against this vault | **-1.94 pts** (11.44% -> 9.50%) |
| New source ingested at session granularity (the local transcripts) | **-1.60 pts** (9.50% -> 7.90%), a denominator effect with a zero numerator |
| **Grouping** -- session-vs-conversation keying of that new source | **+0.05 pts** (7.85% -> 7.90%) |

**What I cannot separate, stated as a finding rather than papered over.** I can
show *that* the numerator fell and *which* producers are missing from this vault.
I cannot show what the figure would be if `xref_filenames` and
`extract_path_mentions` were run here, because running them writes, and INTENT §5
puts that outside a detection round. The counterfactual is a `--apply` decision
and it is the operator's, not this round's.

---

## 5. The falsification test -- and why it is the finding

INTENT §2: *ask the system a question only it can answer.* Both questions were
put to the vault, read-only, and to the estate's own documents.

### Q1 -- "Why was vocabulary killed as a linking signal?"

**Answerable today, but not by the linked record.** `docs/DECISIONS.md` answers
it across three entries: **0003** dropped it and named the temporal anchor as
root cause, **0015** revived it "with guards", **0041** declared it dormant
rather than deleted and gave the condition for revival.

The vault holds the answer's provenance too: 122 messages across 56 threads
mention it, and one personal-account thread records the moment the rationale was
recovered -- that it was found in `SCHEMA.md` lines 75-76, where vocabulary
*"degraded linking,"* dropped. **That thread carries `project_link = NULL`.**

So the estate answers the question because a human wrote DECISIONS. The thesis --
that the *link* makes the reasoning recoverable -- is not what answered it.

### Q2 -- "What was the reasoning behind `similarity_threshold = 0.6`?"

**The vault contains the answer. The vault cannot route you to it.**

The string appears in **10 messages across 6 threads**, and they hold a complete
answer: it was an explicit empirical guess, flagged as one in the Chronicler
design doc §12.3, alongside a closing note to *"start with the stated defaults and
retune empirically once real reconciliation/grouping output exists"* -- and it
governs nothing, because Layer C produced zero groups. One thread even records
the arithmetic (A=761, B=261, C=0).

**Every one of those 6 threads has `project_link = NULL`.** Across the whole
vault, only **9** threads mentioning either term carry a project link at all.

And the string `similarity_threshold` appears **nowhere in this repository** --
not in code, not in a doc. The design doc holding §12.3 is not here, which one of
those very threads says out loud.

### The structural reason, which is the real result

**The vault's `projects` table has 17 rows and none of them is `L5GN-Tools`.**
`config/project_registry.json` carries both `L5GN-Tools` and `L5GN Tools`; the
vault does not. So the threads that hold this estate's own reasoning -- including
both answers above, and including the thread in which INTENT §2 was drafted --
are about a project the vault has no identity for.

Their coverage is not low. **It is unreachable** — there is no target row to
link to.

**Refined after tracing the timestamps (same day).** "Unreachable" is right for
the local half and too strong for the export half, and the two have different
causes:

- **The 71 local-transcript threads were never offered to the linker at all.**
  `relink` last ran at `2026-07-27T21:48:20Z`; `ingest_local_transcripts` wrote
  those rows at `2026-07-28 00:36`. They arrived about three hours after the last
  link pass and no pass has run since. Nothing about them has been *tried*.
- **The 39 Claude-export threads were seen and not linked.** They were ingested
  at `2026-07-27 18:53`, three hours *before* that same relink run, so the linker
  did read them and produced no `l5gn-tools` link. The registry is not the
  reason: both `config/project_registry.json` and the generated
  `chronicler_dev/project_registry.json` already carry `id: l5gn-tools` with its
  aliases. The likelier causes are in `relink`'s own scoring — the registry flags
  that project `low_signal_body: true`, demoting a body-only alias hit from 0.60
  to 0.15, and `adjusted = score × time_plausibility` hard-zeroes any thread more
  than 14 days before a project's first commit.

So the missing `projects` row has two distinct explanations stacked on top of
each other, and only the first is fixed by running something.
`relink.upsert_project()` mints the row on demand when a thread wins a link, so a
single link would create it — which makes "run the linker and read what it says"
the cheapest possible next act, and it has not been done.

That is now `docs/RUNBOOK_chronicler_refresh.md`, steps 4–7.

> The brief anticipated the shape of this: *"a coverage figure that improves while
> those questions still go unanswered would mean coverage is the wrong proxy."*
> The figure did not improve -- it fell -- and the proxy is wrong anyway, in a way
> the coverage number cannot express. A vault that grew to 100% coverage of the
> threads it can name would still answer neither question.

This is **INTENT §6 failure mode 1** reading true, and reading true more sharply
than the coverage figure alone reports it. §6 is explicit about what follows:
*"Any of these is a reason to stop or cut scope. None of them is a reason to add
features."* Nothing here is a case for building anything. The cheapest honest
next act is a registry-to-vault reconciliation -- one missing row, not a feature.

---

## 6. Incidental findings, recorded because they are load-bearing

1. **`data/vault_reader.json` is 41 days stale and names a path that no longer
   exists.** It is also the only surviving evidence of the baseline vault, which
   is why this round could reconcile INTENT's definition at all. It should not be
   regenerated until someone has decided whether the record it holds is wanted --
   regenerating it destroys the only copy of the 2026-07-17 measurement.
2. **`threads.substantive` is NULL for all 71 local-transcript rows.** The
   column's schema comment promises it is *"backfilled by set_substantive.py (a
   DB-only pipeline stage that runs every pass, keeping the frozen-schema
   'substantive is always set' contract true after new ingests)."* It has not run
   since the local-transcript ingest. A reader trusting the column sees 242
   substantive threads; the message counts say 293. **This is a live instance of
   INTENT §5's "fail loud, never silently wrong" being violated quietly** -- the
   column does not fail, it under-reports by 51.
3. **All 71 local-transcript rows sit at `project_confidence='none'`**, including
   the 18 whose recorded `cwd` is a real repository path. `ingest_local_transcripts`
   ruling 2 says CLI sessions get `'exact'` from that `cwd` matched against the
   registry. Zero did. Consistent with finding §5's missing `projects` row.
4. **`review_queue` carries 364 pending `project_link` rows and 139 pending
   `link_ambiguous`** -- a 503-item human worklist, against a baseline of 136 and
   15. The queue grew 3.3x while coverage fell.

6. **The wrong resolution had already written a registry, and it was being
   preferred.** `resolve_registry_path()`'s default resolves to
   `C:\Users\timps\L5GN\.intel_sync\project_registry.json` on this rig, and
   that file exists — 521,208 bytes, dated **2026-08-01**, created by an earlier
   `build_registry` whose `write_json_atomic` did `mkdir(parents=True)` at the
   wrong path. `COWORK_REPORT_intent_evidence.md` Task B predicted precisely this
   ("running `build_registry` here would *create* a spurious
   `GitHub/L5GN/.intel_sync/` folder rather than fail") and it was recorded as a
   risk rather than fixed. It has since happened. Every run on this rig without
   `CHRONICLER_REGISTRY_PATH` reads a 26-day-old registry and links against it at
   full confidence — strictly worse than the absent case, which at least makes
   `has_registry()` false and prints a visible skip. Nothing consumed it: the
   vault's evidence is stamped `2026-07-27T21:48:20Z`, before the file existed,
   and no `run.py ingest` had run since. **A risk named in a report and left open
   became a defect on disk in eleven days**, which is the sharpest available
   argument for the `INTENT` §5 preference for structural guarantees over
   remembered ones.

5. **`verify.py` is not hermetic against the `CHRONICLER_*` environment.**
   Measured while running the refresh: with `CHRONICLER_HOME` and
   `CHRONICLER_DB_PATH` exported, `tester_census` reports 7 issues and
   `tester_review_preflight` 3 — their injected fixture machine dicts are
   overridden by the real environment. `tester_census` pops `CHRONICLER_HOME`
   and not `CHRONICLER_DB_PATH`, and the pop does not span every assertion.
   Reproduced identically on a second machine, so it is the variables and not
   the rig. Both testers' docstrings assert hermeticity. **The gate's verdict
   depends on the shell it is run from**, which means the same mechanism could
   make a fixture-based tester pass against the real vault rather than fail —
   nothing has been shown to do so, and nothing checks that it cannot. This is
   the same shape as findings 2 and 3 and as the `ingest_local_transcripts`
   defect: a check that quietly reports the wrong thing rather than failing.

None of these is a task. They are named because a measurement that reports only
its own number teaches the next reader that nothing else was seen.

---

## 6b. The refresh was run. What it measured.

**Added 2026-08-27, ~20:15, after `RUNBOOK_chronicler_refresh.md` was walked end
to end on `LucasGoonPC`.** Everything above §6b was measured *before* the
refresh. This section is what the same probe says after it. It is a **new
measurement on a changed corpus**, not a correction of the earlier one -- the
vault gained a month of Gemini material, 26 local sessions and a first-ever
`L5GN-Tools` project row between the two readings, so the pair is a before/after
of an intervention, not two attempts at the same number.

| | before | after |
|---|---:|---:|
| threads | 1,172 | 1,330 |
| substantive (>=4 msgs) | 293 | 336 |
| evidence-linked threads | 53 | 65 |
| `projects` rows | 17 | 19 |
| `threads.substantive` NULL | 71 | **0** |
| newest thread | 2026-07-27T23:52 | **2026-08-22T20:00** |
| **INTENT §2 figure** | 23/293 = **7.85%** | 35/336 = **10.42%** |
| any project link | 27/293 = 9.22% | 39/336 = 11.61% |

**Where the +12 evidence links came from.** `claude-local-personal` 0 -> 11, and
`gemini-personal` 17 -> 18. The eleven are `relink`'s auto-links, every one of
them to `l5gn-crystal-spire` on a title+body alias pair at 0.92--0.96. So the
local-transcript corpus went from **0.0% to 15.5%** coverage, and it did so
through the ordinary evidence pipeline rather than through the exact join.

**And §10e's prediction, now measured exactly.** Substantive threads by
confidence after the refresh:

| confidence | substantive threads |
|---|---:|
| `(null)` | 215 |
| `none` | 82 |
| `evidence` | **35** |
| `exact` | **4** |

Twenty-one threads gained an `exact` link from the fixed ingest. **Four of them
are substantive.** The other seventeen are sub-4-message sessions -- subagent
runs and short CLI sessions -- so they cannot enter the denominator, let alone
the numerator. That is §4b's session-vs-conversation granularity and §10e's
metric blindness compounding: the exact join is invisible to INTENT's figure
both because `evidence` excludes it *and* because most of what it links is too
short to count.

**What did not change.** The corpus still ends on **2026-08-22**, the date of the
Takeout export. Nothing from a remote Cowork session is in it, because nothing
writes them anywhere this estate can read (§10d-i). The Claude account still
holds 39 conversations, unchanged since 2026-07-20 (§10d-ii).

### 6c. A second pipeline defect, found by running the chain

`run_pipeline.run_stage` captures each stage with `capture_output=True,
text=True` and **no `encoding=`**, so Python decodes the child's stdout with
`locale.getpreferredencoding()` -- `cp1252` on Windows. The `relink` stage prints
thread titles, and this estate's titles carry emoji, so the reader thread died
with `UnicodeDecodeError: 'charmap' codec can't decode byte 0x8f`.

**The traceback is not the damage.** `run()` prints a failing stage's diagnostic
as `(err or out).strip().splitlines()[-15:]`. A stage that fails *after* emitting
one non-`cp1252` byte therefore reports its exit code **with no tail at all** --
the chain's single diagnostic surface is the thing that breaks, and it breaks
precisely on the stage whose output a reader most needs.

It also made the run quietly misleading in the other direction: `[relink] ok --
no new rows` comes from `summarize_from_log` reading `ingestion_log`, and
`relink` writes no `ingestion_log` rows. That line says nothing either way about
whether relink did anything. The only evidence it worked is the +11 evidence
links in the database.

Fixed in draft, not applied: `encoding="utf-8", errors="replace"` on the parent
and `PYTHONIOENCODING=utf-8` in the child env --
`data/git_warden/pipeline_stage_encoding-1.msg`. `errors="replace"` is
deliberate: a diagnostic that survives slightly mangled beats one that does not
survive.

**This is the fourth member of one family in a single evening**, and the family
is the finding: `ingest_local_transcripts` writing an FK with no target,
`resolve_registry_path` writing a stale registry to a phantom path and being
silently preferred, `verify.py` returning a different verdict depending on the
shell, and now a chain whose failure diagnostics are destroyed by a character.
None of these is a linking problem. All four are **the machinery reporting
something other than what happened**, which is exactly what INTENT §5 forbids and
what §6 failure mode 2 is about. The coverage figure was never the fragile part.

---

## 6d. What the operator proposes next — recorded, not decided

Stated at the close of this round, 2026-08-27, and written down here because it
is the operator's reasoning and this file is where the exchange lives. **Nothing
below is a ruling.** A rework of this size is a `DECISIONS` entry and a brief,
neither of which this round is entitled to write.

> The evidence is already strong enough to suggest a proper rework of Chronicler
> into a database that cannot break. An earlier attempt scoped it as a mesh
> network system, which raised too many governance questions. The current
> thinking is to **focus on the local data** — the Claude Cowork sessions, which
> are what this estate actually produces — with the `claude_migration` capture
> running in the background on a schedule to keep the database synced. Daily to
> begin with, ensuring the previous day is caught up, with a refresh triggerable
> on demand.

**Why this reads as scope-cutting rather than feature-adding, which matters.**
INTENT §6 closes: *"Any of these is a reason to stop or cut scope. None of them
is a reason to add features."* A proposal to drop the mesh framing, narrow to one
source and automate the capture is a **reduction**, and §6's fifth failure mode
says so directly: *"If the manual loop stays manual, the honest move is to shrink
the system, not to add to it."* Tonight's four defects were all in machinery
serving a corpus assembled from four sources by hand. Fewer moving parts is the
sanctioned response. This is recorded as the argument *for* it, not as agreement
that it should happen.

### Questions left open, deliberately

These are not objections. They are the things a brief for this rework has to
answer, and answering them here would be this round deciding something it was not
asked to decide.

1. **A local-first design still cannot see remote Cowork sessions.** §10d-i: the
   local store stopped receiving transcripts on 2026-08-14 because the work moved
   to remote sessions that write nothing to disk, and §10d-ii: they are not in the
   account export either. Scheduling the `claude_migration` capture keeps a store
   current that no longer receives most of the work. **Does the rework accept that
   gap, or does closing it come first?** If it is accepted, the thesis is being
   scored against a record that structurally excludes the estate's current work,
   and INTENT §2 should say so rather than quote a percentage.
2. **What happens to Gemini?** It is 1,194 of 1,330 threads and the worst-covered
   source at 7.7%. Local-first implies it is frozen, retired, or demoted to a
   second class. Each is a different answer and none is implied by "focus on the
   local data".
3. **Is a daily scheduled sync a standing channel?** **0036** stood down the
   cross-machine mesh, and **0051** distinguishes *accumulation* from *frequency*
   — a schedule is precisely what it says a mirror must never become. Reading a
   store on the machine that wrote it is very likely outside both rulings, but
   that is an argument to be made in the entry, not assumed by building it.
   **0051**'s own line is the test: *"a periodic mirror is a sync with extra
   steps."*
4. **What does "cannot break" mean, concretely?** The current vault is
   `1.0-frozen` with a `user_version` every reader asserts, and it did not break
   tonight — every defect was in the code around it. A schema that cannot break is
   a claim that needs a falsifier: name the class of failure it makes impossible,
   or the phrase will be doing the work a design should.
5. **Does the measure survive the rework?** If the corpus becomes local-first, its
   natural link is `exact` (the sidecar join, §10e), and INTENT §2 counts only
   `evidence`. A rework that makes the estate more knowable while the headline
   figure stays flat — or falls, because the denominator changes shape — is the
   outcome this evening should make everyone expect. **Decide the metric before
   the build, or the build will be judged by a number that cannot see it.**
6. **Does the work-estate corpus (0051) participate?** It is out of scope for a
   personal-estate run by **0039**, and the rework has not said whether it is out
   of scope for the design.

**One thing this round would put first, offered as opinion and marked as such.**
Of everything measured tonight, the cheapest change with the largest effect is
still §10e: 44 of 62 Cowork conversations name their project in a sidecar nothing
reads. It requires no new store, no schedule and no rework — and it is the piece
a local-first design would need anyway.

---

## 7. Proposed edit to `INTENT.md` §2 -- not made

**`INTENT.md` was not edited.** Changing the estate's headline claim is the
operator's act. The exact replacement wording is below so that ratifying it is a
read and a paste.

**Revised at the close of the round.** An earlier draft of this section proposed
7.8%, measured before the refresh. The refresh then ran (§6b) and the figure is
**10.42%**. The wording below is against the post-refresh vault, and it says so,
because a number that moved because the corpus changed is not the same claim as a
number that moved because the linking improved.

Replace the paragraph beginning **"It is currently ~8% proven."** with:

> **It is currently ~10% proven.** Measured 2026-08-27 on the personal estate
> alone (**0039**), **35 of 336** substantive threads (>=4 messages, the ones
> that actually hold reasoning) carry an evidence link: **10.4%**, against
> **7.8%** before that day's refresh and **8.1%** when this figure was first
> written. Read the rise carefully: most of it is a month of un-ingested material
> finally landing, not the linking getting better. The earlier 8.1% was also
> measured over a denominator that mixed work-estate threads into a personal
> figure; scoped as **0039** requires, that same 2026-07-17 reading was 11.4%,
> which is *higher* than today. The mesh that moves the data is finished; the
> thing the mesh exists to carry is still barely connected where it counts.

Three notes on the wording, all deliberate:

- **"~8%" becomes "~10%", so `ARCHITECTURE.md` §7 goes stale in the same act.**
  It currently reads *"Coverage is currently ~8% of substantive threads (see
  INTENT §2)"*. That is a second edit, to a second trinity document, and it is
  **not** drafted here -- `CONVENTION_docs.md` §1 says a doc that contradicts the
  code is a bug in the doc, and leaving `ARCHITECTURE` at ~8% while `INTENT` says
  ~10% creates exactly that. Both move together or neither does.
- **The paragraph reports a rise and immediately undercuts it.** That is the
  point. A headline that reads "8% -> 10%" without saying the corpus grew by 158
  threads is the flattering half of the truth, and §2's whole existence is a
  correction of a flattering figure.
- **The 11.4% comparison stays in**, because it is the only like-for-like number
  in the set and it points the other way.

If the figure's *scoping* is to be corrected as well, that is a **DECISIONS**
entry rather than an INTENT edit -- **0039** already rules how a measurement is
scoped; what is missing is a ruling that the estate's published thesis figure is
scoped the same way. Not drafted here.

---

## 8. Placement -- and the class that does not exist

**`CONVENTION_docs.md` §2 has no class for a measurement.** Stated plainly, as
the brief asked, rather than solved by inventing a prefix -- §2 is explicit that
*"a new prefix is an amendment to this file, not a call made while naming a
file."*

Three candidates were considered and two rejected:

- **`COWORK_REPORT_`** -- "what a thread found." Closest in content, but
  `CONVENTION_briefs.md` §1 makes a card's state *"a function of which of the
  four files exist"*, and this round's brief was handed in chat rather than
  written to `docs/`. A report with no brief file is a half-card that
  `docs-archivist` would read as a permanently unfinished pair. Rejected.
- **`AGENDA_`** -- dated and frozen at its date, which fits. But §2 defines it as
  *"a dated snapshot of what was open"*, and a measurement is not a list of open
  items. Rejected on definition, not on convenience.
- **`docs/investigation/`** -- **used.** §5 defines the class as a thread's
  starting prompt and its final response, kept verbatim, and says outright that
  *"a Cowork round's output file is a response; the brief that opened it is a
  prompt."* It is dated, born frozen, never maintained, and outside
  `auditor_doc_claims`' scan -- which is correct here, because this document's
  counts are true of one moment and must never be edited to match a later one.
  It also has the precedent: the 2026-07-18 investigation that produced the
  original 8.1% was this same kind of document.

**One tension, named rather than hidden.** §5 says an investigation *"asserts
nothing about current truth"* and may not be deferred to for what is true now.
This document reports a measurement, which looks like a current-truth claim. The
resolution is the trinity: **this file is evidence; `INTENT.md` is where the claim
lives.** That is exactly why §7 above proposes the INTENT edit instead of making
it. If the operator reads that as a stretch, the honest alternative is an
amendment to `CONVENTION_docs.md` §2 adding a measurement class -- `BASELINE_` is
already named there as a considered-but-unused work-rig dated-snapshot class and
is the obvious candidate -- and that amendment is the operator's, not mine.

**`docs/investigation/`'s own falsification counter (§5) is unaffected.** Both
files added here are prompt-and-response exchanges this estate ran, correctly
named. The count of non-conforming files stays at two of fifteen.

---

## 9. What was not done, and what it would cost

| Not done | Why |
|---|---|
| Read the castle vault (`pull_backup.source`) | Its declared estate is `both`; reading it puts two estates in one run. **0039** clause 1. |
| Ran `xref_filenames` / `extract_path_mentions` against this vault | They write. INTENT §5: detection and action are different programs. This is the counterfactual §4c names as unresolvable from here. |
| Ran `verify.py` | No code changed. The sandbox has no configured hostname (`python run.py config` reports `NOT CONFIGURED`), so the gate must be run on `LucasGoonPC` regardless. |
| Edited `INTENT.md` or `ARCHITECTURE.md` | Forbidden by the brief; proposed in §7 instead. `ARCHITECTURE.md` §7's "~8%" is still true and needs no edit. |
| Ran `git commit` | Forbidden by the brief and by **0028** clause 3. Message drafted to `data/git_warden/intent_coverage_remeasure-1.msg`. |
| Regenerated `data/vault_reader.json` | It is the only surviving record of the baseline vault (§6.1). Regenerating destroys it. |

---

## 10. Slices — where the coverage actually is

Added the same day, at the operator's request: the aggregate figure hides more
than it reports. Same definition throughout (§1), same read-only vault, personal
estate only.

### 10a. By source — the Claude export is the best-covered corpus in the estate

| Account | Threads | Substantive | Substantive + evidence | Coverage |
|---|---:|---:|---:|---:|
| `claude-personal` (the export) | 39 | 32 | 6 | **18.8%** |
| `gemini-personal` (Takeout) | 1,062 | 210 | 17 | 8.1% |
| `claude-local-personal` (CLI + Cowork) | 71 | 51 | **0** | **0.0%** |
| *Claude, both sources combined* | 110 | 83 | 6 | 7.2% |

**The Claude export covers at more than twice the estate average.** It is the
smallest corpus and the best-linked one -- 39 threads carrying 32 substantive,
against Gemini's 1,062 threads carrying 210. Per-thread, the export is denser and
cleaner, and `name_alias` finds it.

**The local-transcript source is at hard zero and cannot be otherwise.**
`ingest_local_transcripts` ruling 2 says outright that Cowork sessions never get a
direct link, and CLI sessions get `'exact'` only from a `cwd` matched against the
registry -- which failed for all 18 that had a real repository `cwd` (finding
6.3). So the single largest block of substantive Claude material in the vault, 51
threads, is structurally unlinkable today.

**Targeting Claude alone does not rescue the figure** -- 6 of 83 is 7.2%, below
the 7.85% estate figure -- because the 51 zero-coverage local threads outweigh
the 32 well-covered export threads. The export slice is the only one that reads
well, and it is the slice that has stopped being refreshed (§10d).

### 10b. By month — coverage goes to zero, and stays there

| Month | Substantive | + evidence | Coverage | *of which Claude* |
|---|---:|---:|---:|---|
| 2026-05 | 93 | 9 | 9.7% | 3 subst, 2 linked |
| 2026-06 | 133 | 14 | **10.5%** | 20 subst, 4 linked |
| 2026-07 | 67 | **0** | **0.0%** | 60 subst, **0** linked |

By half-month, the collapse is sharper than a monthly view shows:

| Fortnight | Substantive | + evidence | Coverage |
|---|---:|---:|---:|
| 2026-05, 1–15 | 32 | 0 | 0.0% |
| 2026-05, 16–31 | 61 | 9 | 14.8% |
| 2026-06, 1–15 | 83 | 4 | 4.8% |
| 2026-06, 16–30 | 50 | 10 | **20.0%** |
| 2026-07, 1–15 | 28 | 0 | 0.0% |
| 2026-07, 16–31 | 39 | 0 | 0.0% |

**The most recent evidence-linked substantive thread in the vault is dated
2026-06-23.** Nothing has linked since. The estate's peak was 20% in late June
and the reading has been zero for every fortnight after it.

July is where the toolkit's own build happened, and July is 60 substantive Claude
threads at zero coverage. The composition says why: 51 of them are
local-transcript rows that cannot link by construction, and the other 9 are
export threads about a project the vault has no row for (§5).

### 10c. By project — coverage is bimodal, not thin

This is the most useful slice and it contradicts the shape of the headline
figure. Coverage is not "8% of threads, spread thinly." It is **four projects at
100% and everything else at zero.**

| Project (vault `projects` row) | Threads | Substantive | Substantive + evidence |
|---|---:|---:|---:|
| Citadel MicroIDE | 15 | 10 | **10** |
| L5GN Journal / Universal Content Pipeline | 28 | 9 | **9** |
| L5GN_Armory_v4 | 2 | 2 | **2** |
| Crystal Spire | 4 | 2 | **2** |
| L5GN-Continuous-Ingestion-Daemon | 3 | 2 | 0 |
| L5GN-Crystal-Spire | 1 | 1 | 0 |
| L5GN Crystal Spire | 1 | 1 | 0 |
| smelt-gateway | 3 | 0 | 0 |
| L5GN Mesh Network | 1 | 0 | 0 |
| **(no project row at all)** | **1,114** | **266** | **0** |

Read it as three groups:

1. **Four projects the `name_alias` signal found: 23 of 23 substantive threads
   linked, 100%.** Where the signal fires at all, it is not thin -- it is
   complete. That is the strongest evidence in this document that the linking
   layer works when it has a target.
2. **Four more with a project row and no evidence link** -- 4 substantive
   threads linked at `manual`/`exact` instead. (27 substantive threads carry a
   `project_link` of any kind; 23 of those are at `evidence`.)
3. **266 substantive threads with no project at all** -- 91% of the substantive
   corpus. These are not weakly linked. They are unaddressed.

Two defects visible in the table itself, both depressing coverage without any
linking failure:

- **`Crystal Spire`, `L5GN-Crystal-Spire` and `L5GN Crystal Spire` are three
  rows for one project.** Threads split across them, and only the first carries
  evidence links.
- **There is no `L5GN-Tools` row**, which is §5's finding seen from the project
  side: the estate's own build threads are the largest unlinked block and have
  nowhere to link to.

**On estates:** every project above is `l5gn` scope. There is no second estate in
this vault to slice by, and slicing by the other one is what **0039** clause 1
forbids in a single run. The scope dimension has one value here and carries no
information.

### 10d. Freshness — the corpus stops a month before today

The operator's suspicion is correct, and the cause is not the export cadence
alone.

| Store | Last ingested into the vault | Newest content it holds |
|---|---|---|
| Claude export (`conversations.json`, 51.4 MB) | 2026-07-27 18:53, one batch, 39 threads | **2026-07-17** |
| Gemini Takeout | 2026-07-27 18:53–18:54, two batches | 2026-07-19 |
| CLI + Cowork transcripts | 2026-07-28 00:36–00:37, 142 batches | 2026-07-27 |

**The newest row in the vault is `2026-07-27T23:52:14Z` -- 31 days before this
measurement.** The Claude export is staler still: its newest conversation
predates the export file itself by ten days.

What sits in that hole, measured from the repo rather than guessed at:

> **31 of this estate's 55 DECISIONS entries -- 0026 through 0057 -- are dated
> 2026-07-28 or later.** Every one was reasoned out in a thread the vault has
> never seen: **0038** (the conversation/session/thread ruling), **0039** (the
> estate scoping this round ran under), **0051** (the containment it observed),
> and the whole Quartermaster frame.

**More than half the estate's ruling corpus has no chat provenance in the vault.**
That is an intake problem sitting upstream of every coverage number here.

### 10d-i. The local transcript store stopped growing on 2026-08-14

Measured against the operator's own backup lineage at
`C:\Users\timps\backups\claude_migration` -- four snapshots, `2026-08-14`,
`2026-08-18_100202`, `2026-08-22_153527` and `2026-08-27_164914`, the last taken
during this round.

**The capture is sound.** Today's `capture.log` records 3,491 files /
505,197,047 bytes copied from the correct packaged path
(`...\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\local-agent-mode-sessions`
-- not the MSIX-virtualised `%APPDATA%` view `machines.json` warns about), plus
464 files / 7,250,981 bytes from the CLI store, with *"every file seen by the
walk was copied."* Nothing is being missed by the backup.

**The thing being backed up is what stopped.** Across all four snapshots:

| Snapshot | Distinct session transcripts | Exact bytes |
|---|---:|---:|
| 2026-08-14 | 89 | 128,266,448 |
| 2026-08-18 | 89 | 128,266,448 |
| 2026-08-22 | 89 | 128,266,448 |
| 2026-08-27 | 89 | 128,266,448 |

**Identical to the byte, thirteen days apart.** Not one new session transcript,
and not one byte appended to an existing one, since 2026-08-14. The Cowork
conversation sidecars agree: 62 conversations, `lastActivityAt` running
2026-07-08 to **2026-08-14** (48 in July, 14 in August), the newest titled
*"L5GN Tools Pipeline design"*. Only the CLI store is still live -- its newest
session file was appended 2026-08-26, and it is a session the vault already
holds.

The explanation is visible in the same snapshot: `remote-session-spaces.json`,
refreshed today. **The work moved to remote Cowork sessions, which run in a cloud
container and write no transcript to the local store at all.** This round is
itself one of them. So the local-transcript intake is not stale by neglect --
**it has been capturing an abandoned store, silently, for thirteen days**, which
is precisely the failure INTENT §5 forbids: *"a stale schema fails; it doesn't
lie."* This one lies. Nothing in the estate went red.

**What is recoverable today.** Against the vault, the snapshot holds **23
sessions never ingested** -- 17 of them from August -- forming **19
conversations, 18 of them substantive**, and up to 9,796 raw records (an upper
bound; the parser strips tool traffic). That is the last thirteen days of local
work still on disk. Everything after 2026-08-14 is not on this disk in any form.

### 10d-ii. The Claude export is not stale — the account is empty after 2026-07-20

**Added 2026-08-27 evening, after a fresh export was taken.** This revises the
reading in §10d and it revises it in the worse direction.

A new export was requested and downloaded the same evening (manifest
`created_at: 2026-08-27T19:37:53Z`). Anthropic has changed the export *format*:
instead of one archive it now delivers a manifest plus three category zips —
`conversations-000.zip` (a single `conversations.json`), `projects-000.zip`
(`projects/<uuid>.json` × 9) and `light_metadata-000.zip` (`users.json`,
`login_history.json`). The layout still maps one-to-one onto what
`normalize_claude.py` expects, so nothing in the pipeline needs changing.

**The payload is byte-for-byte the same corpus.** Compared against the
2026-07-27 capture:

| | 2026-07-27 export | 2026-08-27 export |
|---|---:|---:|
| `conversations.json` size | 51,367,337 | 51,367,337 |
| conversations | 39 | 39 |
| uuids present in one and not the other | — | **0** |
| shared uuids whose `updated_at` or message count differ | — | **0** |
| total `chat_messages` | 922 | 922 |
| newest `updated_at` | 2026-07-20T13:41:31Z | 2026-07-20T13:41:31Z |

Only the serialisation differs (the md5 changes; the size does not).

**So the export was never the stale thing.** The Claude account holds 39
conversations and has produced none since 2026-07-20. §10d treated the export as
a manual step that had lapsed; it had not lapsed, there was nothing to fetch.
Requesting a fresh export cannot close the August gap, and no cadence of
requesting one ever will.

That collapses the two remaining hopes for the gap into one place. The August
work exists only as Cowork and CLI sessions; the local store stopped receiving
them on 2026-08-14 (§10d-i); and they are not in the account export either,
because they were never claude.ai conversations. **The corpus this estate can
currently reach ends on 2026-08-14 by construction, not by neglect** — and the
thesis in INTENT §2 is being scored against a record that structurally excludes
the estate's own current work. That is the fact §6 failure mode 1 should be read
against, ahead of any coverage figure.

The Gemini side is different and does refresh: the 2026-08-27 Takeout carries
`My Activity.json` at 33.5 MB against the vault's 30.4 MB, so there is genuinely
new Gemini material to ingest.

### 10d-iii. A thread that quotes the registry matches every project at once

**Observed in the first real `relink` dry run, 2026-08-27.** Several threads score
`adjusted = 1.000` for `universal-content-pipeline` on **nine** distinct body
aliases simultaneously, with `citadel-microide` second at 0.990 on five. Their
titles are `task: COWORK_BRIEF_solo_playbook.md`, `# Task list — close out the
golden UAT pass`, `build task: docs/cowork_brief_tool...` — that is, they are
**L5GN-Tools threads that paste a project list or the registry itself**, so every
curated alias in the estate appears in their body and `combine()` compounds them
toward 1.0.

The scoring is behaving exactly as specified; the input is a document *about*
the projects rather than a conversation *within* one. Nothing in the signal set
distinguishes "this thread discusses project X" from "this thread contains a list
that names project X".

**They are saved only by the ambiguity guard** — two candidates within
`LEAD_MARGIN` of each other are declared AMBIGUOUS rather than auto-linked. So
the highest-confidence wrong answers in the estate are withheld by a tie, not by
a rule that understands why they are wrong. Had one alias family happened to
dominate, a thread about the toolkit would have auto-linked to the Universal
Content Pipeline at 1.000 and been indistinguishable from a correct link.

This is INTENT §5's *"a plausible wrong answer is the worst thing this system can
produce"*, and §6 failure mode 2, arriving with a concrete instance rather than
as a worry. It is a scoring finding, not a coverage one, and it wants its own
round — the obvious candidates being to damp an alias family that fires N times
in one thread (the `SIGNAL_COUNT_CAP` that today contains only `vocabulary`), or
to treat a thread that matches more than K distinct projects as evidence of a
list rather than of a subject.

### 10e. An exact conversation→project join exists, natively, and is unread

Every Cowork conversation carries a `local_<uuid>.json` sidecar beside its
folder. All 62 hold `title`, `cliSessionId`, and -- the point -- a
**`userSelectedFolders`** array naming the directories the operator attached to
that conversation:

| `userSelectedFolders` names | Conversations |
|---|---:|
| a path under `...\GitHub\L5GN-Tools` | **37** |
| `...\GitHub\L5GN-Crystal-Spire` | 7 |
| the `GitHub` root only (no single project) | 2 |
| non-project paths (Desktop, Downloads) | 1 |
| empty | 15 |

**44 of 62 conversations (71%) name a specific project directory.**

`ingest_local_transcripts` ruling 2 concludes that *"Cowork sessions never get a
direct link -- their cwd encodes the session's own outputs dir, no project
signal."* That is true of the **session's** `cwd` and was correctly observed. It
is not true of the **conversation's** sidecar one level up, which names the repo
outright. The ruling is right about the evidence it looked at and wrong about the
conclusion, and **0038** is exactly why: session and conversation are different
things, and the project identity lives on the second.

This is the "join of record" **0040** says a source is entitled to when it
carries a stable id natively -- and it is sitting unread, for the corpus with the
worst coverage in the estate (§10a: 0.0%).

**And here is the sting.** Reading it would take substantive threads carrying a
project link from 27 to roughly 65 -- but at `project_confidence='exact'`, which
is *stronger* than `evidence` and which **INTENT's numerator does not count**
(§1). The headline figure would not move. The estate's own scoreboard cannot see
the single largest, cheapest improvement available to it.

That is the same lesson as §5 arriving from the other direction: **coverage
measured as `evidence`-confidence threads is the wrong proxy**, and it is wrong
in both directions at once -- blind to reasoning it already holds but cannot
address, and blind to a link type better than the one it counts.

**None of this is a case for building anything** (INTENT §6). The order matters
and is the opposite of the obvious one: **re-running the local ingest first makes
the number worse** -- roughly 23/311 ≈ 7.4% -- because every local thread lands
unlinkable. The target has to exist before the material arrives: an `L5GN-Tools`
row in the vault's `projects` table, and the sidecar read. Then ingest.

---

## Appendix — the queries, so this is reproducible

Run against a read-only copy of `config/local.json` -> `LucasGoonPC.vault`.

```sql
-- the substantive view, from message counts rather than the column
-- (the column is NULL for the 71 local-transcript rows; see finding 6.2)
CREATE TEMP VIEW mc AS
  SELECT t.thread_id, t.account, t.substantive, t.project_confidence,
         COALESCE(m.n, 0) AS n
    FROM threads t
    LEFT JOIN (SELECT thread_id, COUNT(*) n FROM messages GROUP BY thread_id) m
      ON m.thread_id = t.thread_id;

SELECT COUNT(*) FROM mc;                                    -- 1172  population
SELECT COUNT(*) FROM mc WHERE n >= 4;                       --  293  substantive
SELECT COUNT(*) FROM mc WHERE project_confidence='evidence';--   53  evidence-linked
SELECT COUNT(*) FROM mc
 WHERE project_confidence='evidence' AND n >= 4;            --   23  the numerator

-- the two candidate definitions agree in this vault
SELECT COUNT(*) FROM mc
 WHERE n >= 4 AND thread_id IN (SELECT thread_id FROM link_evidence);  -- 23

-- grouping is unchanged on the Gemini side
SELECT account, parser_version, COUNT(*) FROM threads GROUP BY 1,2;
SELECT type, status, COUNT(*) FROM review_queue GROUP BY 1,2;

-- the evidence base is one signal from one run
SELECT signal, producer_version, COUNT(*), MIN(produced_at), MAX(produced_at)
  FROM link_evidence GROUP BY 1,2;
SELECT COUNT(*) FROM path_scan_log;                         --    0  S5 never ran here

-- the structural finding
SELECT COUNT(*) FROM projects;                              --   17
SELECT name FROM projects WHERE name LIKE '%Tool%';         --  'L5GN Tools Mobile' only
```

Baseline figures throughout are read from `data/vault_reader.json`
(`totals.by_account`, `unlinked.by_account`, and the per-project `by_confidence`
rollups), which reconciles to INTENT's published 1,171 / 332 / 150 / 27 exactly.

### The slice queries (§10)

```sql
-- 10a by source
SELECT account, COUNT(*), SUM(n>=4),
       SUM(CASE WHEN n>=4 AND project_confidence='evidence' THEN 1 ELSE 0 END)
  FROM mc GROUP BY 1;

-- 10b by month (and by fortnight, splitting on substr(created_at,9,2) < '16')
SELECT substr(created_at,1,7), SUM(n>=4),
       SUM(CASE WHEN n>=4 AND project_confidence='evidence' THEN 1 ELSE 0 END)
  FROM mc WHERE created_at IS NOT NULL GROUP BY 1 ORDER BY 1;

-- 10c by project
SELECT COALESCE(p.name,'(unlinked)'), COUNT(*), SUM(n>=4),
       SUM(CASE WHEN n>=4 AND mc.project_confidence='evidence' THEN 1 ELSE 0 END)
  FROM mc LEFT JOIN projects p ON p.project_id = mc.project_link
 GROUP BY 1 ORDER BY 3 DESC;

-- 10d freshness
SELECT account, MAX(created_at) FROM threads GROUP BY 1;
SELECT source, account, COUNT(*), MIN(imported_at), MAX(imported_at), SUM(rows_new)
  FROM ingestion_log GROUP BY 1,2;
```

The August hole is counted from `docs/DECISIONS.md`: entries whose `**Date:**`
line is later than the vault's newest row (`2026-07-27`).
