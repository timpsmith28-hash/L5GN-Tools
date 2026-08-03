<!-- actioned: (none yet) -->

# Response — the knight session, 2026-08-02

**Date:** 2026-08-02 · **Model:** Claude (Cowork, design thread) ·
**Partner prompt:** `2026-08-02_knight-session_claude_1-prompt.md`

Investigation, per `docs/README.md` §4. Born frozen. Every figure below was
observed on `l5gn-castle-worker` or `LucasGoonPC` on 2026-08-02 and is quoted
from the terminal, not reconstructed.

**No work-estate paths appear in this document.** Counts and shapes only — the
finding at N1 is the reason that now matters.

---

## Headline

The maintenance succeeded: the knight pulled 28 commits, the gate held, the vault
migrated, 356 rows backfilled, and the surface served for the first time in the
estate's history.

The session's value is elsewhere. **Two scanners have never consulted the scope
guard, and the gate cannot fail when a scanner ignores it.** Every deposit taken
since 2026-07-25 carries thousands of paths from inside raw export trees —
including a `.key` and a `.pem` filename — into an artefact whose standing rule
(1.A2) is that a leaked path is a defect.

It was found by following an anomaly rather than by testing for it, which is the
fourth time that has happened and the reason the closing-remarks patterns exist.

---

## N1 — Two scanners never ask about scope

```
imports _scope:  blast_radius, doc_census, duplicate_finder,
                 env_scanner, import_scanner, todo_adr_scanner
does NOT:        file_census, workspace_scanner
```

`6d09eb3` ("scope discipline", 2026-07-25 09:32:56) added `DATA_DIR_NAMES` and
wired it into the six scanners showing the symptom. The two that weren't wired
are the two that walk the most files. `is_data_dir_name('chat_threads')` returns
`True` on both machines — the predicate is correct and simply is not consulted.

**Failure shape #2**: the fix went where the symptom appeared, not where every
caller passes. Same family as `_winlong` in `census()` but not `ingest`.

**Confirmed on current code, not inherited.** A `run.py build --fresh` on the
knight at `81d8740`, 2026-08-02T18:51Z:

```
grep -c 'chat_threads/' data/estate.json   ->  2178
```

Where it lands, measured on `LucasGoonPC` at `a202ba0`, clean tree, 2026-08-01:

| field | data-dir paths |
|---|---|
| `.projects[].file_census.at_risk[].path` | 3,592 |
| `.projects[].file_census.files[].path` | 2,516 |
| `.projects[].workspace_scanner.modules[].path` | 337 |
| `.projects[].file_census.outliers[].path` | 38 |
| `.projects[].file_census.directories[].path` | 8 |

Two honest caveats. `todo_adr_scanner.markers[].text` also matched **twice, as
false positives** — marker prose *mentioning* `raw_claude_files`, not paths.
And `outliers[]` / `summary.largest` were ratified as labelled
disclosure-by-design at D3/D4 of `UAT_toolkit_self_scan_results.md`; that ruling
concerned labelled outliers in a scanned repo, not walking data directories, and
must not be revoked while fixing this.

Briefed: `docs/COWORK_BRIEF_scanner_scope_bypass.md`.

## N2 — The gate is structurally unable to catch N1

`tests/tester_scanner_scope.py` imports exactly one scanner — `todo_adr_scanner`
— plus the `Scope` primitive. It proves the predicate is right and that one
caller honours it. **It has no way to fail for a caller that never calls.**

Green means *"todo_adr_scanner respects scope"*, not *"scanners respect scope"*.
**Failure shape #3, stacked on #2.** The remedy is in the brief's Task 2:
iterate `registry.SCANNERS` so a scanner that ignores scope cannot pass.

## N3 — The knight reaches the same leak by a second, independent route

`run.py config` reports `roots: (none configured -> legacy sibling discovery)`.
The knight therefore sibling-discovers and scans **`data` and `vault` as
projects** — the vault itself is walked as if it were a repo. Its build lists
`projects, data, vault, crystal-spire, L5GN`.

So the disclosure has two causes, not one: an unconfigured consumer (knight) and
a scanner that never asks about scope (rig, which has correct roots and leaked
anyway). Fixing only the scanners leaves the knight scanning its own vault.

## N4 — The deposits, and the fifty-minute window

Both bundles on the knight, measured 2026-08-02:

| deposit | matches | generated_at | commit | dirty |
|---|---|---|---|---|
| `estates/personal/estate.json` | 9,159 | 2026-07-25T10:00:04+01:00 | `1951cfe` | true |
| `estates/work/estate.json` | 2,328 | 2026-07-25T10:23:10+01:00 | `1951cfe` | false |

The window is the sharpest detail in the session:

```
09:32:56  6d09eb3  fix(scanners): scope discipline
09:35:22  1951cfe  docs(intent): ...            <- carries the guard
10:00:04  personal deposit taken                <- 27 min later
10:23:10  work deposit taken                    <- 50 min later
```

The round that introduced scope discipline produced two deposits ignoring it
inside the hour. Not drift over weeks — the fix and the proof of its
incompleteness are effectively simultaneous.

**No deposit has been taken since.** The rig built on 2026-08-01 and never
pushed, so remediation is exactly two bundles and the knight's estate picture is
eight days stale.

Exposure is contained — one operator, one tailnet, and INTENT §4 rules there is
no confidentiality boundary between Tim's own estates. What is broken is the
artefact's promise, which matters precisely at the K2/K3 transition.

## N5 — Deck UAT item 1.2 is closed, with evidence

The backfill's note-parsing had never met a real note. It has now met 366:

```
pending rows missing candidate_project: 366
  resolved:   356
  unresolved: 10
applied: 356 row(s) backfilled.
```

`candidate_project IS NOT NULL` was **0** before the run — the first backfill
this vault has ever had. Post-run: 356. `threads` 725 and `messages` 21,684 both
unchanged, verified either side.

## N6 — A legacy note class that can never be backfilled

The ten unresolved rows are not malformed. They are a **different note format
containing no candidate project id at all**:

```
parseable:    suggest -> <id> (...)
unresolved:   Suggested project link (fuzzy, score 0.48) for title: '...'
```

Ten items inside a twenty-wide `item_id` window (1144–1163), every title an
L5GN OS thread — almost certainly output from a suggester generation predating
`5711962` ("id-key link_evidence"), and `l5gn-os` is exactly the id whose meaning
changed across 0012 and 0017.

**The tool's closing line misdirects**: *"re-run after fixing the cause (e.g. a
stale registry)"*. The registry is fine; there is nothing in these notes to
parse, and no re-run will ever resolve them. The refusal is correct behaviour;
the explanation is wrong for this class. Needs a disposition — re-derive by
re-running the suggester, or mark as a class the backfill cannot serve.

## N7 — Zero manual rulings have ever been applied

```
SELECT project_confidence, COUNT(*) FROM threads WHERE project_link IS NOT NULL;
evidence|52
```

52 evidence links, **no `manual` row of any kind**, against **1,561** rows in
`review_queue`. The write endpoint has existed since `1533ce8`. Nobody has ruled
on one.

That is the deck's own case, stated as a number, and a better argument for
finishing it than anything in the briefs.

## N8 — A backup that is not a backup

```
chronicler.db.bak                              96K   -> SELECT COUNT(*) FROM threads = 0
chronicler.db.bak-finalize-20260727T160111Z    74M   -> integrity_check ok, 725 threads
```

A valid SQLite file with schema and no data, named `.bak`, sitting beside a real
one. **The confident-zero pattern applied to backups**: it looks like a recovery
point and is not, and nothing distinguishes the two by name. K2 in the flesh.

## N9 — 232 MB of vault data inside the code repo

`chronicler/chat_threads/` (158 MB) plus both `.bak` files (74 MB) live inside
the git working tree, untracked. ARCHITECTURE §5 rules code and data live in
different roots.

Consequence beyond tidiness: **every artefact this machine produces is stamped
`toolkit_dirty: true`**, permanently, because the working tree can never be
clean. The deck header shows a standing amber flag that carries no information.

## N10 — The knight's docs board is empty for a config reason

`review` reports `5 projects, 0 authored documents`. `6dd70f1` added the toolkit
as a scanned root in the **gaming rig's** `local.json`; the knight's was never
updated, so `docs/` sits outside every scanned project. Code is fine; config is
missing. Worth closing, because a `both`-estate machine can host the docs board
and nothing else.

---

## What went right, recorded because it is easy to overlook

**The account-clause scoping worked in the wild, on the machine it was blocking.**
Verbatim:

```
review: queue routes DEGRADED -- Thread routes are disabled on this machine:
        unrecognised estate 'both'...
review: estate routes ENABLED -- 5 projects, 0 authored documents, engine=fts5
review: estate='both' -- NO thread is rendered on this machine (DECISIONS 0025).
        Document routes are unaffected.
```

Deny-by-default held and tightened: a machine that cannot name one estate now
serves no thread at all, where previously it refused to start. **This was the
first time the knight has ever served a surface.**

The migration path also behaved exactly as `_check_deck_schema` promised —
detect and refuse, never migrate from the web process, with the remedy named.

## A claim that did not survive

`schema_frozen.sql` was locally modified on the knight and looked like real
schema drift (55 insertions, 79 deletions). It was not: table and index **names**
are identical on both sides; the only differences are `IF NOT EXISTS` being
stripped (a `.schema` dump omits it) and `sqlite_sequence` appearing (SQLite's
own internal table). Cosmetic, discarded, diff preserved at
`~/knight_schema_drift_20260802.diff` on the knight.

Recorded so nobody re-derives the alarm.

---

## Findings

| id | finding | disposition |
|---|---|---|
| **N1** | `file_census` and `workspace_scanner` never import `_scope`; data-dir paths reach every deposit | **Briefed** — `COWORK_BRIEF_scanner_scope_bypass.md` |
| **N2** | `tester_scanner_scope` tests one scanner; cannot fail for a caller that never calls | In the brief, Task 2 — the load-bearing task |
| **N3** | Knight has no configured roots; sibling discovery scans `data` and `vault` as projects | In the brief; second independent cause |
| **N4** | Both deposits carry it; dated to a 50-minute window on 2026-07-25; two bundles only | In the brief, Task 3 |
| **N5** | Deck UAT 1.2 closed — 366 real notes, 356 resolved | **Closed.** Cite this document |
| **N6** | Legacy note class with no id; tool's remedy text misdirects | **Open — needs a disposition** |
| **N7** | Zero manual rulings ever; 1,561 queued | Record. Argues for finishing the deck |
| **N8** | `chronicler.db.bak` is an empty shell named like a recovery point | **Open** — K2 |
| **N9** | 232 MB vault data in the code root; permanent `toolkit_dirty` | **Open** — 0005, K2 |
| **N10** | Knight's `local.json` never got the toolkit root | **Open** — one config line |

### Not a finding

- **`schema_frozen.sql` drift.** Cosmetic. See above.

### What this session deliberately did not do

- **Nothing was committed on the knight.** It is a consumer; the pull was
  fast-forward only.
- **No deposit was remediated.** That is the brief's Task 3 and needs the
  ratified entry first.
- **The 232 MB was not moved.** Moving vault data during a pull is how you lose
  the one verified backup. Deliberate, separate act.
- **The ten unresolved rows were left alone**, as the tool left them.
- **No work-estate path was read into this thread**, deliberately, and that
  restraint is itself a consequence of N1.
