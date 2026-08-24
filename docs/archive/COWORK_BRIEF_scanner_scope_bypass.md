# Cowork brief — two scanners never asked about scope, and the deposits carry it

**Origin:** the 2026-08-02 knight session. Found by following an anomaly in the
knight's local `data/estate.json` back to its cause.
**Deliverable:** the scope guard applies to **every** scanner, structurally; the
gate can fail when a scanner ignores it; and the already-deposited artefacts are
dealt with by ruling rather than by hope.

**This is 1.A2 realised.** *"Even leaked paths are a defect"* is the standing rule
for the deposit artefact. Measured on 2026-08-02, the deposits on the knight
contain, by substring count:

| deposit | matches for `raw_claude_files` / `raw_gemini_files` / `Chronicler_Backup` |
|---|---|
| `estates/personal/estate.json` | **9,159** |
| `estates/work/estate.json` | **2,328** |

Contained — one operator, one tailnet, and INTENT §4 rules there is no
confidentiality boundary between Tim's own estates. Not acceptable — the
artefact does not do what it says it does, and K2/K3 (the knight as a backup
target) are exactly the transition that turns this from untidy into a disclosure.

**Read first:** `l5gntools/scanners/_scope.py`, `tests/tester_scanner_scope.py`,
DECISIONS **0010** (the wall), the 1.A2 open ruling, and
`investigation/2026-08-02_knight-roles_claude_2-response.md` (K3, K4).

---

## The diagnosis, already done — do not re-derive it

**1. Two scanners never import `_scope`.**

```
imports _scope:  blast_radius, doc_census, duplicate_finder,
                 env_scanner, import_scanner, todo_adr_scanner
does NOT:        file_census, workspace_scanner
```

`6d09eb3` ("scope discipline") added `DATA_DIR_NAMES` and wired it into the six
scanners that showed the symptom. The two that didn't were never wired — and
they are the two that walk the **most files**, which is why they are where it
matters. `is_data_dir_name('chat_threads')` returns `True` on every machine
checked; the predicate is correct and simply is not consulted.

**Failure shape #2 exactly: the fix went where the symptom appeared, not where
every caller passes.** Same family as `_winlong` landing in `census()` but not
`ingest`.

**2. The gate cannot see it.** `tests/tester_scanner_scope.py` imports exactly
one scanner — `todo_adr_scanner` — plus the `Scope` primitive. It proves the
predicate is right and that one caller honours it. **It has no way to fail for a
caller that never calls.** Green means *"todo_adr_scanner respects scope"*, not
*"scanners respect scope"*.

**Failure shape #3 stacked on #2: the blindness is structural, not incidental.**

**3. Where it lands.** On `LucasGoonPC`, clean tree, `toolkit_commit a202ba0`,
`toolkit_dirty false`, built 2026-08-01:

| path in `estate.json` | data-dir paths |
|---|---|
| `.projects[].file_census.at_risk[].path` | 3,592 |
| `.projects[].file_census.files[].path` | 2,516 |
| `.projects[].workspace_scanner.modules[].path` | 337 |
| `.projects[].file_census.outliers[].path` | 38 |
| `.projects[].file_census.directories[].path` | 8 |
| `.projects[].file_census.summary.largest` | 1 |

Two honest caveats carried from the session, so the round starts accurate:

- `todo_adr_scanner.markers[].text` also matched, **twice, as false positives** —
  that is marker prose *mentioning* `raw_claude_files`, not a path. The scanner
  is fine; the detection heuristic was loose.
- **`outliers[]` and `summary.largest` are partly ratified.** D3/D4 of
  `UAT_toolkit_self_scan_results.md` ruled `file_census`' labelled `mass[]` /
  `outliers[]` disclosure-by-design. That ruling was about *labelled outlier
  paths in a scanned repo*, **not** about walking data directories. Task 4
  exists to restate that boundary rather than quietly widen or quietly revoke it.

---

## Precondition ▸ a DECISIONS entry, because remediation is a ruling

Fixing the code is obvious. **What to do about deposits already on the knight is
not**, and nothing in the log covers it. Draft this to Tim, get it ratified,
then build.

> ## 00NN — A deposit found to carry more than its contract is replaced, never edited
>
> **Date:** 2026-08-02 · **Status:** proposed · **Builds on:** 0010 (the wall),
> 1.A2 (leaked paths are a defect), 0013 (snapshots are frozen by construction) ·
> **Source:** the 2026-08-02 scanner-scope finding
>
> **Context.** Two scanners bypassed the data-directory guard, so every deposit
> taken since carries thousands of paths from inside raw export trees. The
> artefacts are self-describing and sha256-manifested (the deposit contract), so
> a deposit cannot be edited in place without invalidating the manifest that
> makes it trustworthy — and editing it would also destroy the record of what was
> actually produced on that date.
>
> **Decision.** A deposit discovered to violate its own contract is **replaced by
> a fresh deposit from a fixed producer, and the superseded bundle is removed —
> never edited, never partially scrubbed.** The consumer's per-estate `history/`
> is treated the same way: a superseded snapshot is dropped whole.
>
> **Consequences.** The estate loses the affected history window rather than
> keeping a doctored version of it, which is the same trade `docs/README.md` §3
> makes for archived documents — testimony is either kept intact or removed, not
> corrected. The alternative, an in-place scrub, produces a manifest-valid bundle
> whose contents nobody can date, which is worse than a gap.

---

## Working rules

- Read-only scanners, stdlib-only, gate GREEN before commit.
- **Fix structurally, not at the call site.** This round exists because the last
  fix was applied per-scanner. A repeat of that pattern here is a failed round
  even if the two scanners come out correct.
- No work-estate paths in any report, walk-sheet or commit message. Counts and
  shapes only. (F-2, and this round is the reason it now matters.)

## Task 1 ▸ make scope structural, not per-scanner

Wire `Scope` into `file_census` and `workspace_scanner` — but **first ask whether
a scanner should be able to walk a tree without consulting scope at all.**

The six-of-eight split is the finding. If the walk itself lived in one shared
helper that every scanner uses, this defect would have been impossible rather
than merely absent. Say in the report whether that refactor is right, and if you
decline it, say why the per-scanner import is the honest answer.

Whatever the shape: `file_census` and `workspace_scanner` must skip data
directories, and their skips must appear in the same scope accounting the other
six already report.

## Task 2 ▸ the tester iterates the registry — this is the load-bearing task

`tester_scanner_scope` must stop importing one scanner by name and instead
iterate **`registry.SCANNERS`**, asserting for each that a planted data directory
is not read.

That single change converts *"someone remembered to test this scanner"* into
*"a scanner that ignores scope cannot pass the gate"* — INTENT §5's *prefer
"can't" to "shouldn't"*, applied to the gate's own coverage.

**Ship this even if Task 1 slips.** A red gate naming the two offenders is worth
more than a green one that never looked.

## Task 3 ▸ measure and remediate what has already shipped

**The exposure is already dated — do not re-derive it.** Measured on the knight,
2026-08-02:

| deposit | generated_at | commit | dirty |
|---|---|---|---|
| `estates/personal/estate.json` | 2026-07-25T10:00:04+01:00 | `1951cfe` | true |
| `estates/work/estate.json` | 2026-07-25T10:23:10+01:00 | `1951cfe` | false |

Both from **one commit, one morning**. And the window is the finding's sharpest
detail: `6d09eb3` — the scope-discipline commit — landed at **09:32:56**;
`1951cfe` is **09:35:22**, two and a half minutes later and carrying the guard;
the two violating deposits were taken **25 and 48 minutes after that**. The
round that introduced scope discipline produced deposits ignoring it before the
hour was out, because the two scanners it didn't touch are the two that walk
everything.

**No deposit has been taken since.** The rig built on 2026-08-01 (`a202ba0`) and
never pushed, so the knight's estate picture is eight days stale — separately
worth a line in the report, and it means remediation is **exactly two bundles**,
not a history.

- Count, per deposit and per `history/` snapshot, how many paths come from inside
  data directories. **Counts and top-level shapes only** in the report — never
  the paths.
- Remediate per the ratified entry: rebuild on a fixed producer, re-deposit,
  remove the superseded bundles. The work bundle needs the work rig; sequence
  accordingly rather than leaving one estate fixed and one not.
- **Confirm the fresh deposit is clean by the same measurement.** A remediation
  nobody re-measured is a claim, not a fix.

## Task 4 ▸ restate the disclosure boundary that was already ruled

D3/D4 accepted labelled `outliers[]` / `mass[]` paths as disclosure by design.
That ruling stands and must not be revoked by accident while fixing this.

State plainly, in the report: for each path-bearing field in `file_census` and
`workspace_scanner`, whether it is **deliberate disclosure** (ratified, labelled,
kept) or **scope bypass** (fixed). `at_risk[]`, `files[]` and
`modules[]` look like the second; `outliers[]` and `summary.largest` look like
the first. Decide each one and name it.

---

## Stop conditions

- **The fix is a per-scanner patch with no structural answer** → stop. That is
  this defect's own cause, applied a second time.
- **The registry-iterating tester passes on the first run before Task 1 lands** →
  stop; it isn't testing what it claims, since two scanners are known to fail.
- **Any work-estate path reaches a report, a walk-sheet, a commit message or a
  chat thread** → stop. That is the defect committed by hand.
- **A deposit is edited in place** rather than replaced → stop; the manifest and
  the ruling both forbid it.

## Explicitly out of scope

- The knight's stale local `data/estate.json` — it never travels; it is fixed by
  a re-census after the scanners are.
- The Historian / Shadow work, the sync-back removal (A2), the architecture
  census. All separately briefed.
- Widening or narrowing what `file_census` measures. This round changes **where
  it looks**, never what it reports about what it finds.

---

## UAT — acceptance checks (Tim walks these)

- `file_census` and `workspace_scanner` skip data directories, and their skips
  appear in the scope accounting beside the other six scanners.
- **`tester_scanner_scope` iterates `registry.SCANNERS`.** Verify by deleting the
  scope call from one scanner by hand and confirming the gate goes **red** and
  names it. Restore, confirm green.
- A fresh `run.py build` on `LucasGoonPC` produces an `estate.json` with **zero**
  data-directory paths in `at_risk[]`, `files[]`, `directories[]` and
  `modules[]`.
- The ratified `outliers[]` disclosure still behaves as D3/D4 described — not
  silently removed along with the defect.
- Deposits on the knight are **replaced**, not edited; superseded bundles gone;
  the fresh ones measure clean.
- No work-estate path appears anywhere in the round's output.
- `verify.py` GREEN.

Mark each **ready to walk**. Results log needs a uat stamp naming the commit; do
not write a `gate=` field.

---

## Reporting

`docs/COWORK_REPORT_scanner_scope_bypass.md`, walk-sheet
`docs/UAT_scanner_scope_bypass.md`, stamped results after the walk.

Record the ratification, the structural decision from Task 1 (and the reasoning
if the shared-walk refactor was declined), the before/after counts per deposit,
the dating of the exposure, and the Task 4 field-by-field boundary.

An acknowledgement line belongs on
`investigation/2026-08-02_knight-roles_claude_2-response.md` (K3/K4) once this
lands, per `docs/README.md` §4 — that investigation predicted this class of
disclosure two hours before it was found.
