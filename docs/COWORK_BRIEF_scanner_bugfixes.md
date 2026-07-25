# Cowork brief — scanner bug fixes (the report must be able to police itself)

**Origin:** design thread, 2026-07-24. The full-estate work-rig run (host `10280L`,
commit `23b5ffa`, generated 18:22) **truncated mid-write** and would not parse. The
cause is a finding: `todo_adr_scanner` mined 298 "TODO"-like strings out of
Chronicler's gitignored chat-archive JSON, bloating the report until it broke. A
governance report you cannot parse fails its own job. These are bugs, not features —
they run **before** `COWORK_BRIEF_governance_scanners.md`.

**Read first:** `l5gntools/scanners/todo_adr_scanner.py`, `l5gntools/common.py`
(`iter_files`, `is_vendored`), `l5gntools/scanners/file_census.py` (it already knows
how to read `.gitignore`), `l5gntools/report.py`.

## Working rules

- **BUILD, then STOP.** Nothing commits. Everything staged for Tim's review.
- `python verify.py` **GREEN** before you report; every fix gets a hermetic tester.
- Read-only, stdlib-only. `--no-optional-locks` on any git call.

---

## Task A — scanners must honour `.gitignore` and skip data/chat dirs

`todo_adr_scanner` walked `chat_threads/raw_claude_files/conversations.json`,
`raw_gemini_files/Takeout/…` and project export JSON — **gitignored data the wall
doctrine says stays out of scope** — and scraped every "TODO"-shaped substring from
inside chat transcripts. This is two failures at once: it inflates the report with
non-code noise, and it reaches into exactly the personal chat content the estate is
built to keep walled.

`file_census` already resolves `.gitignore` and classifies vendored/ignored trees.
**Reuse that**; do not add a second ignore implementation.

1. Every content-walking scanner (`todo_adr_scanner` first, then audit the rest —
   `doc_census`, `env_scanner`, `duplicate_finder`, `import_scanner`) skips:
   - anything matched by the project's `.gitignore`,
   - vendored trees (`is_vendored`),
   - known data/chat directories even when not gitignored — `raw_*`,
     `chat_threads/`, `vault_staging/`, `Takeout/`, `*_files/`.
2. `todo_adr_scanner` should only scan **source and doc** files, never data blobs.
   A `.json` under a `raw_*` or export path is data, not a marker source.
3. Report, per scanner, how many paths were skipped and why — the skip count is
   itself a governance signal ("we did not read your chat archive").

**Tester:** a synthetic project with a gitignored `raw_claude_files/x.json` full of
"TODO" strings and a real `src/a.py` with one TODO — assert the scanner returns
exactly one marker and records the data dir as skipped.

---

## Task B — per-scanner output cap + report self-validation

Even scoped correctly, an unbounded scanner can bloat the report past what the
renderer can emit. The 18:22 file truncated mid-JSON and silently produced an
**unparseable governance artifact** — the worst failure class, because it looks like
a report until you try to use it.

1. **Cap** each list-producing scanner (markers, at-risk, duplicates…) at a sane
   ceiling with an explicit `truncated: true` + true count when hit — the same
   honest-truncation contract `file_census` already uses. Never a silent cut.
2. **Self-validate the emitted report.** After writing `report.html` / `estate.json`,
   re-parse the embedded `DATA` block and confirm it is valid JSON. If it is not,
   **fail loud** — exit non-zero, name the scanner whose payload broke it — rather
   than leaving a broken report on disk that reads as complete.
3. A size guard: if any single scanner's payload exceeds a threshold, flag it in the
   report as an anomaly (298 markers from one "project" is a signal, not a detail).

**Tester:** feed the writer an oversized payload; assert it either caps honestly or
fails loud, and that a well-formed report passes the self-check.

---

## Task C — recognise "Open questions / decisions" sections (extends governance B1)

The governance brief's B1 teaches the scanner that `DECISIONS.md` is a decision
record. This transcript adds a second shape: both r141 docs carry explicit **"Open
questions"** sections holding pending design decisions (four-eyes vs typed phrase,
persisting the gate report, rollback). That is decision-record content the scanner
should count as **PENDING**, wherever it appears — not only in `DECISIONS.md`.

Fold into B1 when that brief runs: an `## Open questions` / `## Open decisions`
heading in any doc contributes to the project's PENDING tier. Keep it mechanical —
count the section's presence and its list items, do not parse the prose.

**This task is a one-line addition to the governance brief, recorded here so it is
not lost; it does not need its own build.**

---

## Suggested order

A → B. Both are rig-runnable, no knight. A is the more urgent — it stops the tool
mining walled chat data, which is a doctrine breach as well as a bug. C rides into
the governance brief.

If the budget is tight, **A alone is a successful session** — a report that stays
inside its own scope and stays parseable.

---

## UAT — acceptance checks (Tim walks these)

- **A:** a full-estate run that includes Chronicler produces a `todo_adr` marker
  count in the low tens, not the hundreds, and the report never lists a path under
  `raw_*` / `chat_threads` / `Takeout`.
- **A (doctrine):** confirm no chat-transcript text appears anywhere in the report.
- **B:** the report always parses — re-open `estate.json` and `report.html`'s DATA
  block; both are valid JSON. Force an oversize case and confirm it caps or fails
  loud rather than truncating.
- **C:** ValidationAutomation's `docs/DECISIONS.md` and an r141-style "Open
  questions" section both contribute to a visible PENDING count.

Mark each **ready to walk**, never "passed".

---

## Reporting

Report tasks green vs pending, the before/after marker counts for a Chronicler-
inclusive run, the skip-count output, and the **UAT walk-list**. Write the report as
`docs/COWORK_REPORT_scanner_bugfixes.md` and the walk-sheet as
`docs/UAT_scanner_bugfixes.md`; the results log needs a uat stamp or the gate refuses
the commit. Nothing commits — everything staged.
