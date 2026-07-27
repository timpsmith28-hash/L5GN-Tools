<!-- gate-frozen: commit=6d09eb3 -->

# Cowork report — scanner bug fixes

Pair: `docs/COWORK_BRIEF_scanner_bugfixes.md`. Session 2026-07-24, on top of
`23b5ffa`. **BUILD, then STOP — nothing committed; everything staged for Tim's
review.**

`python verify.py` — **GREEN**, 6 auditors + **30** testers at this build (two
testers added this session: `tester_scanner_scope`, `tester_report_selfcheck`).
*(Frozen build-time count, written `**N**` so it is not re-touched as later briefs
add testers — the estate's convention for historical gate figures.)*

| Task | State | What landed |
|---|---|---|
| A — honour `.gitignore`, skip data/chat dirs | **green** | shared `Scope` filter, reused across five content scanners |
| B — per-scanner cap + report self-validation | **green** | honest `capped()`, payload anomaly audit, fail-loud self-check |
| C — recognise "Open questions" as PENDING | **noted, not built here** | folds into governance B1 (records the requirement, per the brief) |

---

## Task A — scanners stopped reading the walled data

The 18:22 work-rig build truncated because `todo_adr_scanner` walked
`chat_threads/…`, `raw_claude_files/conversations.json` and export JSON and
scraped every "TODO"-shaped substring out of the transcripts inside them — two
failures at once: report bloat, and a doctrine breach reaching into exactly the
personal chat content the estate is built to wall off.

The fix is one shared scope filter, not five ad-hoc ones. `l5gntools/scanners/_scope.py`
holds a `Scope` object that **reuses `file_census`'s single `.gitignore`
implementation** (`_git_lookup` / `status_of`) rather than adding a second one,
as the brief required. It excludes three things and counts each:

- **gitignored** — resolved through `file_census`, the estate's one ignore parser;
- **vendored** — bundled deps / model weights (`common.is_vendored`);
- **data / chat dirs even when not gitignored** — `raw_*`, `chat_threads/`,
  `vault_staging/`, `Takeout/`, `*_files/`, `conversations`. Data-dir wins over
  the gitignore reason so the report says the doctrine thing ("we did not read
  your chat archive"), not the incidental one.

Every content-walking scanner now routes through it: `todo_adr_scanner` (the one
that broke), plus `doc_census`, `env_scanner`, `import_scanner` and
`duplicate_finder` — the "audit the rest" list from the brief. Each emits a
`scope` block: `{"skipped_paths": N, "skipped_by_reason": {...}}`. The skip count
is itself the governance signal.

`todo_adr_scanner` also stops treating a `.json` under a data path as a marker
source — that path never reaches the reader now, because the whole tree is out of
scope before the file is opened.

### Proof on a Chronicler-shaped fixture

The work rig isn't mounted in this session, so the 298-marker case was
reproduced synthetically: a git project with `chronicler/raw_claude_files/`
gitignored and stuffed with 298 `TODO`-shaped lines, plus one real
`# TODO` in `src/a.py`.

| | markers |
|---|---:|
| **Before** (walked the chat archive) | **299** |
| **After** (scope filter) | **1** |

`scope` reported `skipped_by_reason: {"data_dir": 1}`, and the one surviving
marker is `src/a.py` — the real one. No path under `raw_*` appears in the output.
On Tim's real estate the equivalent full-estate run should drop the Chronicler
`todo_adr` count from the hundreds into the low tens; that measured number is a
UAT check for the walk (needs the work rig).

---

## Task B — the report can now fail its own job loudly

Two guards, because a scoped scanner can still overwhelm the renderer, and the
18:22 file proved the worst case: an **unparseable** report that reads as
complete until you try to use it.

**Honest caps.** `common.capped(items, cap)` returns `(kept, truncated, count)` —
the same contract `file_census` already used. `todo_adr_scanner` now caps its
marker list at 500 and always carries the true `marker_count` and a `truncated`
flag. Never a silent slice.

**Payload anomaly audit.** `report._payload_audit` measures every
(project, scanner) payload as it assembles the feed and records any over 500 KB,
or any that hit its honest cap, into `estate.anomalies`. The HTML viewer renders
these as a warning banner at the top — "298 markers from one project" becomes a
visible line, not a detail. A capped payload is labelled *capped* (honestly
truncated); an oversized one is labelled *oversized* (review the source).

**Self-validation, fail loud.** After writing `report.html` and `estate.json`,
`build_all` re-reads both from disk and re-parses them — the data feed as JSON,
and the report's embedded `DATA` block pulled back out of the written page. If
either does not parse, it raises and `run.py build` exits non-zero, naming the
largest payload as the likely culprit. A broken governance artifact is now a red
build, not a file on disk that looks finished.

`tester_report_selfcheck` drives all of this hermetically: honest truncation, a
valid report passing, a truncated embedded block failing *with* the culprit
named, a malformed feed caught, and the anomaly audit flagging oversized + capped
while leaving a normal payload alone.

---

## Task C — recorded, not built

Per the brief, Task C (an `## Open questions` / `## Open decisions` heading
contributes to a project's PENDING tier) is a one-line addition folded into the
governance brief's B1, "recorded here so it is not lost; it does not need its own
build." It is on the governance run's task list and is implemented there, not in
this session.

---

## Files touched

Build:

- `l5gntools/scanners/_scope.py` — **new.** Shared scope filter + skip census.
- `l5gntools/scanners/todo_adr_scanner.py` — scope filter, honest marker cap,
  `scope` report.
- `l5gntools/scanners/{doc_census,env_scanner,import_scanner,duplicate_finder}.py`
  — routed through `Scope`; each emits a `scope` block.
- `l5gntools/common.py` — `capped()` helper.
- `l5gntools/report.py` — `_payload_audit`, `validate_report`, `extract_embedded_data`,
  `_self_validate`; `estate.anomalies`; viewer anomaly banner.
- `run.py` — `build` fails loud on a broken-report `RuntimeError`.

Tests:

- `tests/tester_scanner_scope.py` — **new.** Task A behaviour.
- `tests/tester_report_selfcheck.py` — **new.** Task B behaviour.
- `verify.py` — both registered.

Docs (gate-count maintenance, sanctioned by `UAT_file_census.md`: "correct it if
you add a tester"):

- `docs/COWORK_REPORT_file_census.md`, `docs/COWORK_REPORT_intent_evidence.md`,
  `docs/UAT_file_census.md`, `docs/UAT_intent_evidence.md` — the live plain-text
  gate claim moved 28 → 30 testers. Frozen historical mentions (written `**N**`)
  were left untouched.

---

## Assimilation list (carried forward)

- **`Scope` is the estate's one scope authority now.** Any future content scanner
  should build a `Scope` rather than re-deriving ignore/vendor/data-dir rules.
- **The data-dir family is data-driven** (`DATA_DIR_NAMES` / prefixes / suffixes
  in `_scope.py`) — extend it there, not per scanner.
- **Archive candidates surfaced again:** `file_census` and `intent_evidence` are
  completed pairs whose live gate line I had to hand-edit this session. Each edit
  is a small argument that these pairs belong in `docs/archive/` (frozen
  testimony, exempt from `auditor_doc_claims`). Recommend archiving them so future
  gate-count changes stop touching finished reports. **Not moved — needs Tim's
  ratification** (`docs-archivist` proposes, never moves).

---

## UAT

Walk-sheet: `docs/UAT_scanner_bugfixes.md`. Consolidated run list:
`docs/UAT_cowork_run_2026-07-24.md`. The results log Tim produces from the walk
needs a uat stamp (`docs/README.md` §3). Nothing commits until then.
