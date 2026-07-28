# Cowork report — local transcript intake

**Phase:** 0 — read one file and write down what is actually in it.
**Status:** acceptance criteria met. Both stores opened, schema compared
directly, STOP condition not triggered.
**Samples used:** all provided by Tim directly (pasted / dropped into
chat), not obtained by this session — this environment has no filesystem
access to either transcript store; both `~\.claude` and the Cowork
`LocalCache` tree are protected from mounting (confirmed by
`mcp__cowork__request_cowork_directory` refusing both paths as protected
host locations).

- `4bb6bc6c-bd7d-4ac6-ac18-e8480a477b5a.jsonl` (79,930 B, 33 records) —
  **first supplied from inside a `local_<session-id>\.claude\projects\`
  subfolder in the Cowork store**, then Tim separately screenshotted the
  plain `~\.claude\projects\C--Users-timps-Documents-GitHub-L5GN-Tools\`
  folder and the *same filename, same size, same date* was sitting there
  too. Byte-for-byte confirmed: `md5sum` on both copies is identical
  (`249e2f3b7119d02b10651cdee5a006e7`). This is a stronger finding than
  "two stores share a format" — for this session, **the Cowork store and
  the plain CLI store hold the literal same file**, not just the same
  schema. Consistent with Cowork running the same Claude Code/SDK engine
  underneath and that engine always writing to its normal
  `~/.claude/projects/<encoded-cwd>/<uuid>.jsonl` location regardless of
  which front end (desktop app vs terminal) started the session.
- `local_e165e5cc-865f-4b5a-be00-dc33fbbbdfe3.json` (71,076 B) — a
  subtree-root `local_<id>.json` file, the format the brief already expected
  to exclude.
- Twelve further `.jsonl` files pulled directly from
  `~\.claude\projects\C--Users-timps-Documents-GitHub-L5GN-Tools-docs\` (the
  plain CLI store, not Cowork-nested) — used below to confirm the schema
  match and to find the field that actually distinguishes provenance.

---

## Record types present

### The `.jsonl` file

| `type` | count | carries conversation text? |
|---|---:|---|
| `user` | 7 | 1 of 7 is a real human message (`content` is a plain string); the other 6 are `tool_result` wrapped in a one-element list — **not** conversation, these are Bash/Read output |
| `assistant` | 11 | mixed — each record's `message.content` is a list of blocks; only `text` blocks are conversation. Observed block types: `thinking` (3), `text` (2), `tool_use` (6) |
| `attachment` | 4 | no — internal bookkeeping (see below) |
| `queue-operation` | 2 | no — enqueue/dequeue bookkeeping, though `content` duplicates the first human message verbatim |
| `custom-title` | 3 | no — a title record, not a message |
| `ai-title` | 3 | no — an auto-generated title record, not a message |
| `last-prompt` | 3 | no — caches the most recent human prompt for UI display, duplicates content already in a `user` record |

So of 33 top-level records, only 8 (7 `user` + 1 `assistant` text-bearing)
carry anything a human said or Claude said back in prose. The rest is
tool traffic or bookkeeping, but — importantly — every record is **cleanly
typed**. There is no case where conversational text is chunked across
records or requires a stateful reassembler. Filtering to conversation is a
`type` + block-`type` check, not a parser problem.

One record type was **not anticipated by the brief or the investigation
note**: `attachment`, specifically `deferred_tools_delta`. It exists to log
the list of tool names becoming available mid-session (i.e. an audit trail of
tool visibility changes) and is large relative to its information content —
one `attachment` record in this sample is >150 tool names, ~7 KB, to record
zero conversational content.

### The `local_<id>.json` file

Not a message log at all — a single JSON object of session **metadata**:
`sessionId`, `cliSessionId`, `cwd`, `createdAt`/`lastActivityAt` (epoch ms),
`title`, `accountName`, `emailAddress`, `sessionType`, `parentSessionId`,
`systemPrompt`, `initialMessage`, plus config flags (`memoryEnabled`,
`skillsEnabled`, feature toggles, MCP/domain allowlists). No `messages` array,
no per-turn structure of any kind.

`systemPrompt` alone is 48,008 of the file's 71,076 bytes (68%). This
confirms the brief's existing exclusion of `local_<id>.json` — it is
bookkeeping and boilerplate, not a second representation of the conversation
worth parsing.

One thing worth noting: `sessionType: "dispatch_child"` and
`parentSessionId: "local_ditto_..."` on this sample — Cowork sessions can be
spawned as children of another session (a subagent-style dispatch), which is
a linkage the format itself records. Not needed for Phase 0, but relevant
whenever thread hierarchy comes up later.

---

## Where stable ids live

- **Session id:** `sessionId`, present on every record type in the `.jsonl`
  (top-level field, not nested). Matches the filename (`<uuid>.jsonl`).
  `local_<id>.json` carries the same value as `sessionId` and additionally
  `cliSessionId` — a **second** id. In this sample they differ
  (`local_e165e5cc-...` vs `cliSessionId: b2c893a0-...`), so the two ids are
  not interchangeable; which one a `.jsonl` filename under that session's
  `local_<id>/.claude/projects/` folder actually uses needs a same-session
  pair to confirm (not available from these two independently-drawn samples).
- **Per-record id:** `uuid` on `user`/`assistant` records only, plus
  `parentUuid` forming a linked list back to the prior record (or `null` for
  the first). The bookkeeping types (`queue-operation`, `custom-title`,
  `ai-title`, `last-prompt`) carry no `uuid` — they're session-scoped, not
  turn-scoped, so `message_id` synthesis for those isn't applicable (they'll
  simply be excluded).
- `assistant` records additionally carry `message.id` (`msg_...`, the
  Anthropic API message id) — a third id, redundant with `uuid` for this
  purpose but worth recording since `raw_ref`/synthetic-hash logic should
  prefer a source-native id where one exists, per the brief's ruling 3.

---

## Where timestamps live

- `.jsonl`: `timestamp` field, top-level, ISO 8601 with `Z` — e.g.
  `"2026-07-13T16:29:10.841Z"`. UTC, present on every message-bearing record
  (`user`, `assistant`, `queue-operation`). The bookkeeping-only types
  (`custom-title`, `ai-title`, `last-prompt`) have **no timestamp of their
  own** — ordering them relative to messages requires positional order in
  the file, not a field.
- `local_<id>.json`: `createdAt` / `lastActivityAt`, **epoch milliseconds**,
  not ISO — a different convention from the `.jsonl` and something a shared
  normalizer would need to account for if it ever touched both (it currently
  doesn't need to, since this file is excluded from ingest).

---

## Title

Three separate locations, none of them per-message:

1. `custom-title` record in the `.jsonl` (`customTitle`) — user-set, wins if
   present.
2. `ai-title` record in the `.jsonl` (`aiTitle`) — auto-generated.
3. `title` field in `local_<id>.json` — a third copy, presumably kept in
   sync with one of the above by the client, not independently verified here.

No synthesis from the first message is needed for Cowork sessions — a title
already exists, sourced from whichever record wins (recommend `custom-title`
over `ai-title` when both present, since it's the human's own label).

---

## Do the two stores differ, or is it one format?

**One format, confirmed by direct comparison — and in at least one case, the
literal same file.** Twelve genuine CLI-store `.jsonl` files (from
`~\.claude\projects\C--Users-timps-Documents-GitHub-L5GN-Tools-docs\`) were
opened and diffed against the Cowork-nested sample. Same record shape
throughout: `type`/`message`/`uuid`/`parentUuid`/`sessionId`/`timestamp`/`cwd`.

**`entrypoint` is the reliable provenance signal**, not directory location:

| `entrypoint` value | seen on | what it means |
|---|---|---|
| `"claude-desktop"` | the Cowork-nested sample, `promptSource: "sdk"` | session driven by the Cowork desktop app |
| `"cli"` | two genuine CLI-store samples, `promptSource: "typed"` | a human typed into a terminal |
| `"sdk-cli"` | two more genuine CLI-store samples | CLI invoked programmatically (e.g. by a script or another agent), not a human typing |

All three values were found **only in the plain `~\.claude\projects\` store**
in this sample — the Cowork-nested file was the only `"claude-desktop"`
example seen. That's consistent with the brief's own working assumption
(Phase 2, ruling 2: "never infer estate/source from what a thread talks
about") — `entrypoint` is exactly the kind of structural field that should
drive `source`/`account`, not the folder a file happens to sit in, especially
since the identical-file case above shows folder location isn't even a
reliable signal of *where a file exists*, let alone what wrote it.

Four more record types turned up in the genuine-CLI samples that weren't in
the first sample or the investigation note: `mode`, `permission-mode`,
`file-history-snapshot`, `system` (subtype `turn_duration` observed). All
four are pure bookkeeping — no conversation text, no timestamps worth
preserving beyond ordering. Add them to the exclusion list alongside
`attachment`.

One sample (`e99b862f-...`) is worth flagging on its own: its first `user`
record is literally `"test prompt - respond"`, but its `last-prompt` record
reads `"Review the markdown files in the docs directory..."` — a completely
different task. **This is the brief's "files grow" warning, observed
directly**: a session opened for one throwaway test was later resumed for
real work, and both live in the same `.jsonl`, in append order. Idempotency
on re-run (Phase 2's hard requirement) isn't a hypothetical concern; this
file is a real example of exactly the shape that would break a naive
re-ingest.

---

## Byte fraction: conversation vs. everything else

Measured on the one `.jsonl` sample (81,787 bytes of re-serialized JSON, close
to the 79,930-byte file size):

| Category | Bytes | Share |
|---|---:|---:|
| Conversation (`user` string content + assistant `text` blocks) | 4,284 | 5.2% |
| Tool traffic (`tool_use`, `tool_result`) + `thinking` blocks | 33,943 | 41.5% |
| Session bookkeeping (`attachment`, `queue-operation`, `*-title`, `last-prompt`) | 29,581 | 36.2% |

(Note: `thinking` blocks are lumped with tool traffic here as non-conversational,
but they're technically model output, not tool I/O — a ruling of their own if
anyone ever wants Claude's reasoning preserved rather than dropped. Recommend
dropping them; they're not what "conversation" means for this brief's purpose.)

Small sample, one session, but directionally: **conversation is a small slice
of total bytes, and it's cheap to isolate** because every byte is inside a
typed field. This is a good outcome for the brief's volume question (Phase 0
open ruling on retention/truncation) — the 333 MB figure from the census is
mostly `audit.jsonl` and tool noise already excluded by design; the
conversational layer within the *included* files is smaller still.

---

## STOP condition check

**Not triggered.** The format is tractable: one JSON object per line, cleanly
typed, conversation isolable by `type` + content-block `type` with no
stateful reassembly required, confirmed across 14 files spanning both
stores. Proceed to Phase 1.

---

## Phase 0 acceptance — status

- Record types documented, real and redacted samples included: **done**.
- Stable id locations documented: **done**.
- Timestamp locations/formats documented: **done**.
- Title location(s) documented: **done**.
- Whether the two stores differ: **done — confirmed one format by direct
  diff of 14 files; one session's file was found byte-identical in both
  stores**.
- Byte fraction conversation vs. noise: **done, one session measured (5.2%
  conversation); recommend Phase 1's census (not this report) establish this
  across the full 33+26 sessions since one sample isn't representative**.

**Recommend closing Phase 0 and proceeding to Phase 1**, carrying forward
into Phase 1's code these additions to the exclusion list beyond what the
brief already named (`audit.jsonl`, `local_<id>.json`, `.claude/tasks/*.json`):
`attachment` records (all subtypes seen: `deferred_tools_delta`,
`agent_listing_delta`), `thinking` content blocks, and the record types
`mode`, `permission-mode`, `file-history-snapshot`, `system` — all bookkeeping,
none carry conversation. And to use `entrypoint` (not source directory) as
the field driving `source`/`account` classification in Phase 2.

---

# Phase 1 ▸ a read-only reader and a census, no DB

**Status: code done, gate GREEN, real numbers not yet run** — see "What Tim
needs to do" below. This sandbox has no filesystem access to either real
store (confirmed again in Phase 0: both `~\.claude` and the Cowork
`LocalCache` tree refuse mounting as protected host locations), so the
33-Cowork/26-CLI census the brief's acceptance asks for has to be run on the
gaming rig itself, by Tim, not by this session.

## What was built

- **`chronicler/pipeline/local_transcripts.py`** — the module. Three parts:
  - `discover_cli_store(root)` / `discover_cowork_store(root)`: walk each
    store's real directory shape (Phase 0's findings) and yield a
    `TranscriptFile` per `.jsonl`, `audit.jsonl` and `local_<id>.json`
    excluded by name/shape at the walk itself, not filtered afterward.
  - `parse_session(TranscriptFile) -> ParsedSession`: parses one file into
    the in-memory shape the brief asked for — thread id, title,
    created/updated, ordered `(seq, role, content, created_at)` — using
    Phase 0's exclusion list (`attachment`, `mode`, `permission-mode`,
    `file-history-snapshot`, `system`, `queue-operation`, `last-prompt` all
    counted as bookkeeping and never turned into a message; `thinking` and
    `tool_use`/`tool_result` blocks dropped; a bad line or unrecognised
    record type is recorded in `parse_errors` and parsing continues rather
    than raising). Title comes from `custom-title` if present, else
    `ai-title`, matching Phase 0's recommendation.
  - `census(host=None) -> dict`: the report — sessions per store (top-level
    and subagent counted separately), message counts, bookkeeping-record
    counts, total bytes, date range, `encoded_cwds`, `entrypoints_seen`, and
    every parse failure by file and line. An absent or unconfigured store is
    reported with `status` set accordingly, never an exception.
  - CLI: `python3 pipeline/local_transcripts.py [--json] [--host NAME]`.
    Read-only by construction — the module calls no write/mutate filesystem
    function anywhere (checked by hand against the same forbidden-call list
    `auditors/auditor_readonly.py` uses; that auditor itself only scans
    `l5gntools.registry.SCANNERS`, so it doesn't reach chronicler pipeline
    modules — noted as a gap below, not silently relied on).

- **Config** (per the brief: "machine facts, belong beside `chronicler_home`,
  resolved like every other path"): added `cli_transcripts_home` and
  `cowork_transcripts_home` to `config/local.json` under `LucasGoonPC` with
  this rig's real paths (from the investigation note), and documented the
  same two keys in the committed `config/machines.json` template under
  `RENAME-ME-GAMING-RIG`, plus a `_transcripts_comment` explaining them
  (including the %APPDATA%\Claude wrong-turn from the investigation note, so
  nobody repeats it when filling in their own path).

- **`tests/tester_local_transcripts.py`** — hermetic: builds synthetic CLI
  and Cowork store trees in a temp dir, shaped exactly like Phase 0's real
  samples (bookkeeping records, a `thinking` block, a subagent file, an
  `audit.jsonl` and a `local_<id>.json` that must both be ignored, one line
  of deliberately malformed JSON), and asserts: discovery finds the right
  files and nothing excluded; parsing produces the right messages/title/
  bookkeeping counts/entrypoints and records the malformed line without
  raising; `census()` reports correctly for a configured-and-present store,
  an unconfigured store, and a configured-but-missing-on-disk store; and a
  source file's mtime is provably unchanged after `parse_session` runs
  (the read-only requirement, checked, not just claimed). Registered in
  `verify.py`'s `TESTERS` list, alongside `tester_md_transcript`.

- **Full gate run**: `python verify.py` — every auditor and every tester,
  including the new one, **green**. (Run from this sandbox with plain
  `python3` + `PYTHONPATH` rather than the repo's Windows `.venv`, since this
  environment can't execute a Windows venv; worth Tim re-running
  `python verify.py` properly on the gaming rig too, though nothing here is
  Windows-specific enough to expect a different result.)

## What Tim needs to do

This session cannot reach either real store, so the acceptance criterion
itself — "run on the gaming rig, output a census of the real 33 Cowork
sessions and 26 CLI ones" — has to be run by hand:

```
cd C:\Users\timps\Documents\GitHub\L5GN-Tools\chronicler\pipeline
..\..\.venv\Scripts\python.exe local_transcripts.py
```

(No `chronicler` extras needed — the module imports only `l5gntools.config`
and the stdlib, so the base editable install is enough. `--json` for a
machine-readable version if useful.)

**Please paste the output back** (or drop it as a file, same as the Phase 0
samples) so the acceptance check — session counts matching the known 33/26,
zero unexpected parse failures, byte totals in a sane range — can be closed
out against real numbers rather than the synthetic fixture. If the counts
come back different from 33/26, that's useful signal (store contents change
over time, this isn't a demand for an exact match) but worth a look together
rather than assuming the numbers are stale.

## Open items carried into Phase 2

- **`auditor_readonly`/`auditor_stdlib` don't reach `chronicler/pipeline/`.**
  They only scan `l5gntools.registry.SCANNERS`. This module's read-only and
  stdlib-only compliance is currently asserted by hand (this report) and by
  the hermetic tester's mtime check, not gate-enforced the way the estate
  scanners are. Not blocking, but worth a decision before Phase 2 starts
  writing to the DB: either extend one of those auditors to cover chronicler
  pipeline modules too, or accept the weaker guarantee.
- **Byte-fraction and volume numbers in this report are from one session.**
  The real census Tim runs above will give the true 33+26-session numbers;
  the brief's Phase 2 volume ruling ("a retention or truncation rule is a
  decision, not an implementation detail") should use those, not the Phase 0
  single-sample figures.
- Per the brief: **Phase 2 does not start until Tim has seen this Phase 1
  report and the real census output.**
