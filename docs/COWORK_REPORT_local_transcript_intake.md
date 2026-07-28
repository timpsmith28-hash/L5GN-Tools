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

**Status: acceptance met.** Code done, gate GREEN (`python verify.py`, run
both from this sandbox and by Tim on the gaming rig — see commit `cce49a2`),
and the real census now run on the gaming rig: 18 CLI + 3 subagent sessions,
48 Cowork + 2 subagent sessions, zero parse failures. Real numbers are below,
under "Real census". One finding from the real run changes a Phase 2 design
assumption — see the `entrypoint` note below; not a blocker for calling
Phase 1 closed, but a ruling Phase 2 needs before it writes classification
logic.

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

## Real census — run by Tim on the gaming rig, `python verify.py` GREEN first

```
[cli] root: C:/Users/timps/.claude/projects
  sessions:            18  (+3 subagent)
  messages:            57
  bookkeeping records: 115
  total bytes:         1,033,980
  date range:          2026-07-13T16:29:10.841Z .. 2026-07-26T20:38:37.091Z
  entrypoints seen:    claude-desktop, cli, sdk-cli
  encoded cwds:        2
  parse failures:      none

[cowork] root: .../LocalCache/Roaming/Claude/local-agent-mode-sessions
  sessions:            48  (+2 subagent)
  messages:            2,524
  bookkeeping records: 4,577
  total bytes:         76,800,069
  date range:          2026-07-08T16:42:40.930Z .. 2026-07-28T00:16:10.298Z
  entrypoints seen:    local-agent
  encoded cwds:        45
  parse failures:      none
```

**Zero parse failures across 66 real sessions and ~2,700 real records** —
the format held up outside the synthetic fixture, no STOP, no unrecognised
record type. Counts differ from the investigation note's 33 Cowork / 26 CLI
(now 48/18, spanning a wider date range including a week after that census
was taken) — expected, these stores grow, not a discrepancy to chase.

**One real finding that changes Phase 2's design, not just a number:**
every one of the 48 Cowork sessions reports `entrypoint: "local-agent"` —
not `"claude-desktop"`, the value Phase 0's one hand-picked sample showed.
`"claude-desktop"` does appear, but only inside the **CLI store** (alongside
`"cli"` and `"sdk-cli"`), consistent with Phase 0's other finding that a
session run through Cowork can land a byte-identical copy in the plain
`~/.claude/projects` tree too. So the earlier recommendation — "use
`entrypoint`, not source directory, to drive Phase 2's `source`/`account`
classification" — still holds, but the **value** to match on for a Cowork
thread is `"local-agent"`, not `"claude-desktop"` as Phase 0 assumed from
one sample. Worth Tim's explicit ruling before Phase 2 writes any
classification logic: is `entrypoint == "local-agent"` the right test for
"this thread came from the Cowork desktop app", full stop, or could a
CLI-store session also legitimately carry `"local-agent"` in some
configuration this sample set didn't hit?

## Open items carried into Phase 2

- **`auditor_readonly`/`auditor_stdlib` don't reach `chronicler/pipeline/`.**
  They only scan `l5gntools.registry.SCANNERS`. This module's read-only and
  stdlib-only compliance is currently asserted by hand (this report) and by
  the hermetic tester's mtime check, not gate-enforced the way the estate
  scanners are. Not blocking, but worth a decision before Phase 2 starts
  writing to the DB: either extend one of those auditors to cover chronicler
  pipeline modules too, or accept the weaker guarantee.
- **`entrypoint` value for Cowork threads is `"local-agent"`, not
  `"claude-desktop"`** — see "Real census" above. Needs Tim's ruling before
  Phase 2 writes `source`/`account` classification.
- **Volume, for real now:** 76.8 MB across 48 Cowork sessions / 1.03 MB
  across 18 CLI sessions, ~2,580 messages total against ~4,690 bookkeeping
  records — the brief's Phase 2 volume ruling ("a retention or truncation
  rule is a decision, not an implementation detail") can use these instead
  of the Phase 0 single-sample estimate.
- Per the brief: **Phase 2 does not start until Tim has ruled on the
  `entrypoint` question above.** *(Ruled — see below: `entrypoint == "local-agent"`
  for Cowork, but Phase 2 ended up not needing this at all — see "Attribution,
  reworked" below.)*

---

# Phase 2 ▸ ingest into the dev vault, behind `--apply`

**Status: code done, gate GREEN (`python verify.py`), not yet run against the
real dev vault.** Two rulings Tim gave directly (content sensitivity:
conversation records only; attribution: CLI exact / Cowork evidence) are
built in. Everything below is dry-run-by-default and untested against real
data — the acceptance walk (dev vault gains real threads, re-run changes
nothing, an appended transcript adds only new messages) still needs Tim to
run it, same shape as Phase 1's real census.

## What was built

- **`chronicler/pipeline/ingest_local_transcripts.py`** — the writer.
  `python3 pipeline/ingest_local_transcripts.py [--apply] [--host NAME]`,
  dry-run by default (writes are rolled back, not committed, unless
  `--apply`). Writes through the standard `db.get_connection()` /
  `CHRONICLER_HOME` mechanism — **point `CHRONICLER_HOME` at the dev vault
  before running this**, nothing in the code enforces that, same as every
  other normalizer.

- **`source = "claude-local"`** — the new value (ruling 3), one parser for
  both stores, permanently distinct from export-derived `source='claude'`
  even on the personal estate where both will describe the same thread.
  **`account = f"claude-local-{estate}"`**, estate read from
  `l5gntools.config.machine()["estate"]` only — the module refuses to run
  (`SystemExit`) if the machine has no estate configured or it's still the
  template default `"unknown"`, rather than writing threads into a wall the
  estate can't see through.

- **`thread_id`** = the session's own uuid, stable across runs.
  **`message_id`** = the record's own `uuid` when present (every real
  user/assistant record has one), else `sha256(f"{thread_id}:{seq}")[:32]` —
  a synthetic id that's stable across re-runs because it's derived from
  position, not randomness, so a re-parsed file never gets a second id for
  the same conceptual message.

- **Idempotency**: every run re-parses the full file (not incrementally) and
  upserts every thread/message via `ON CONFLICT ... DO UPDATE`, same shape
  as `normalize_claude.py`. Correct by construction for a store that only
  ever grows: unchanged files write the same rows back; a file with new
  lines appended adds exactly the new messages, because identity is the
  record's own uuid, not its line position.

- **Attribution, reworked from what the brief/Phase-0-report assumed:**
  the ruling said "CLI's encoded cwd names the repo," but decoding
  `encoded_cwd` back to a real path is **ambiguous** — the encoding
  (`:`/`\`/`/` → `-`) is one-way, and a folder like `L5GN-Tools` already
  contains a `-`, so you can't tell where the path separator was. Rather
  than decode, this Phase 2 pass added a field to `local_transcripts.py`'s
  parser: `ParsedSession.cwd`, the session's **real, un-encoded** `cwd`,
  read straight off a `user`/`assistant`/`system` record's own `cwd` field
  (present in every real sample — Phase 0 already saw it, just hadn't been
  captured). Attribution matches that real path's segments against the
  project registry using the exact same compact/alias-matching rule
  `extract_path_mentions.py` already uses for path-mention evidence, so
  there's one matching convention in the codebase, not two. CLI sessions
  that match get `project_confidence='exact'` directly; **Cowork sessions
  are never attempted** regardless of what their `cwd` says (ruling 2) —
  they land `project_confidence='none'`, `review_status='pending'`, and
  fall through to the ordinary evidence pipeline later.
  An `'exact'` link, once written, is protected from being overwritten by a
  weaker result on a later run (e.g. if the registry temporarily loses an
  alias) — tested directly, not just asserted.

- **`entrypoint == "local-agent"` turned out not to be needed for
  attribution or classification** — `source`/`account` come from which
  store's directory `local_transcripts.py` discovered the file under
  (`ParsedSession.store`, `"cli"` or `"cowork"`), same as Phase 1's census
  already reported it, not from `entrypoint`. The earlier open question
  (which literal `entrypoint` string means "Cowork") turned out to be a
  Phase 1 census-labelling question, not a Phase 2 ingest-routing one —
  worth noting in case a future phase (e.g. Phase 3's coherence check) still
  wants `entrypoint` as a cross-check, since it remains stored implicitly
  via `raw_ref` -> re-parse if ever needed, just not persisted as its own
  column.

- **`tests/tester_ingest_local_transcripts.py`** — hermetic. Builds a
  synthetic registry, CLI store, and Cowork store, monkeypatches
  `get_connection`/`init_db`/`resolve_registry_path`/`machine` to point at a
  throwaway DB and registry, and proves (not just asserts): dry-run writes
  zero rows; a CLI session with a real `cwd` matching the registry gets
  `project_confidence='exact'` with the right `project_link`; a Cowork
  session with an equally-matchable `cwd` gets no link at all; message ids
  are source-native when available and a stable synthetic hash when not; a
  bookkeeping-only session (zero conversation messages) is skipped, never
  written as an empty thread; running twice with no new data changes
  nothing; appending one new line to a source file and re-running adds
  exactly one new message and zero new threads; an `'exact'` link survives a
  re-run even when the registry match is simulated to fail; a missing
  estate config raises `SystemExit` rather than writing into an
  unclassified account; and the source file's mtime is unchanged throughout
  (read-only, checked not claimed). Registered in `verify.py`.

- **Full gate**: `python verify.py` — green, including both new testers.

## What Tim needs to do

This sandbox has no real dev vault and no real project registry to ingest
into safely, so — same shape as Phase 1 — the acceptance walk needs running
by hand, with `CHRONICLER_HOME` pointed at the dev vault
(`config/local.json` already has it: `C:/Users/timps/Documents/chronicler_dev`):

```
cd C:\Users\timps\Documents\GitHub\L5GN-Tools\chronicler\pipeline
..\..\.venv\Scripts\python.exe ingest_local_transcripts.py
# review the dry-run output, then:
..\..\.venv\Scripts\python.exe ingest_local_transcripts.py --apply
# re-run to confirm idempotency for real:
..\..\.venv\Scripts\python.exe ingest_local_transcripts.py --apply
```

Worth checking in the output: how many CLI sessions land `exact`-linked
(there are only 2 encoded cwds in the real CLI store, both under
`L5GN-Tools`, so this should be a clean, small, checkable number) and that
the second `--apply` run reports the same session/message counts as the
first. **Please paste the output back** so Phase 2's acceptance — "dev vault
gains the threads; a second run changes nothing; a run after appending to a
transcript adds only the new messages" — closes out against the real vault,
not just the synthetic fixture.

## Real ingest — run by Tim against the dev vault (`chronicler_dev/chronicler.db`)

First attempt ran against the wrong DB — `CHRONICLER_HOME` is a shell
environment variable, not read from `config/local.json` automatically, and
wasn't set, so `db.py` fell back to its repo-local default
(`chronicler/chronicler.db`, gitignored, harmless but not the dev vault).
Corrected and re-run with `$env:CHRONICLER_HOME` set:

```
sessions:          71  (0 exact-linked)
messages:          2596
```
Two consecutive `--apply` runs reported **identical counts** — idempotency
holds on the real vault, not just the synthetic fixture. `0 exact-linked` is
expected, not a defect: `L5GN-Tools` is the toolkit itself, scanning its
sibling projects — it isn't a tracked entry in its own
`project_registry.json`, so a CLI session run inside this repo has nothing
to match. (Message count crept from 2,594 -> 2,596 across the wrong-DB and
corrected runs — the Cowork store's date range runs right up to the moment
of testing, consistent with a live session gaining lines between commands,
not a counting defect.)

**Phase 2 acceptance met**: dev vault gained 71 real threads / 2,596
messages; a second `--apply` changed nothing; the earlier hermetic tester
already proved the "file grows -> only new messages added" case directly.
Full gate green throughout (`python verify.py`, including the pre-commit
hook's own gate run).

## Open items carried into Phase 3

- **Dedupe against the export** (ruling 6) is explicitly not attempted here.
  Once real Cowork/CLI threads and the existing `source='claude'`
  export-derived threads both sit in the dev vault, Phase 3's coherence
  check is where overlap gets measured and a dedupe rule falls out of that
  measurement — not invented ahead of the data.
- **Empty-thread skip is a judgement call, not a brief requirement**: a
  session with zero conversation messages (pure bookkeeping) is skipped
  entirely rather than written with zero messages. Seemed obviously right,
  flagging in case Tim wants those tracked some other way (e.g. a
  "discovered but empty" count somewhere) rather than silently dropped.
- Per the brief: **Phase 3 does not start until Tim has seen this Phase 2
  report and the real ingest output.**
