# Locating the Cowork / Claude Code transcript store on Windows

**Date:** 2026-07-27 · **Origin:** design thread, side investigation during the
command-deck scoping session · **Read-only.** Every figure below comes from
`run.py census --target`; no file in the store was opened or copied.

Born frozen, per `docs/README.md` §4. Nothing here asserts current truth — it
records what was found, including a wrong turn taken on the way.

---

## Why this was being looked for

Work-account chat threads are the estate's one **known, permanent gap**. Per
`COWORK_BRIEF_apply_alignment.md`: *"Work chats are the known exception — no full
export exists, so MCF/work threads stay unaligned for now and that is by design,
not a miss."* Personal Claude has a full export (`conversations.json` via the
Claude export path, already an intake source). Work does not, and will not.

If the desktop client persists transcripts locally, that gap closes from a
different direction — not by obtaining an export, but by reading what the client
already wrote to disk. **The work rig is where the benefit lands.** Personal is
where it can be *proved*, because personal has an export to check the answer
against.

---

## The find

The store is **not** at `%APPDATA%\Claude`. Claude is an MSIX / Store-packaged
app, so that path is a **virtualised view** — the packaged app sees it; a normal
process does not. The real location:

```
C:\Users\<user>\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\
    Claude\local-agent-mode-sessions\<workspace-id>\<project-id>\
```

Census of one `<workspace-id>\<project-id>` subtree (2026-07-27T21:31):
**2,714 files, 333.0 MB**, `truncated: true` (2,702 working-set files against a
2,000 cap; 585 basenames carried past it via `basenames_beyond_cap`).

### Three representations per session

| Shape | Observed size | Notes |
|---|---|---|
| `local_<session-id>.json` (subtree root) | 47 files, ~120–160 KB each | One per session; mtime tracks last activity. Cowork-specific format. |
| `local_<id>/.claude/projects/<encoded-cwd>/<uuid>.jsonl` | 1–7 MB | **Same format and same encoded-cwd convention as the CLI transcripts under `~\.claude\projects\`.** |
| `local_<id>/audit.jsonl` | up to 8.9 MB | Largest files present. Tool-call-level audit, not conversation. |

Also present per session: `.claude/tasks/<uuid>/*.json` (task-list widget state),
`outputs/`, `uploads/`. Counts of `.lock` (33), `audit-key` (34) and
`last-cleanup` (34) are consistent with the 33 sessions enumerable through the
session tooling.

### The separate CLI store

`C:\Users\<user>\.claude\projects\<encoded-cwd>\<session-uuid>.jsonl` — 26 files,
21–26 July, plus `subagents\agent-*.jsonl` nested under the sessions that spawned
them, and `~\.claude\history.jsonl`. Encoded cwds observed:
`C--Users-timps-Documents-GitHub-L5GN-Tools` and
`C--Users-timps-Documents-GitHub-L5GN-Tools-docs`.

---

## What this suggests, if it is taken forward

Recorded as reasoning, not as a decision. Nothing here has been ruled on.

1. **The `.jsonl` under `.claude/projects/` is the tractable shape.** It is
   identical between the Cowork store and the CLI store — one parser, two
   sources. `local_<id>.json` is a second format for the same content; `audit.jsonl`
   is the wrong altitude.
2. **The encoded-cwd folder name is a deterministic project link — but only for
   CLI sessions.** Those run in the repo, so the path encodes
   `…GitHub-L5GN-Tools`: provable attribution, stronger than anything S4/S5
   produces and belonging at the `exact`/`manual` end of relink's authority
   ladder rather than the fuzzy end. **Cowork sessions run in their own outputs
   directory**, so their encoded cwd resolves back to the session id and carries
   no project signal. Cowork threads would need ordinary evidence-based linking.
3. **Personal is the control group.** The personal Claude export should already
   contain every personal thread. Ingesting the local store on the personal rig
   and matching it against the export gives a **coherence check with a known-good
   answer** — what does the local store contain that the export does, what does it
   miss, and does a thread reconstructed from `.jsonl` match the exported one.
   That measurement is what would justify trusting the same path on the work rig,
   where no export exists to check against.
4. **Estate is a real ruling, not a mechanical one.** These files sit on the
   personal rig, but the threads inside them discuss work projects. The deposit
   wall (0010) governs estates *on disk* and does not answer this. It would need
   deciding before ingest, not after.

---

## The wrong turn, kept

The first census — `--target "C:\Users\timps\AppData\Roaming\Claude"` — returned
**0 files**, and this was initially read as a **scanner defect**: the hypothesis
was that `os.walk`'s default `onerror=None` was silently swallowing a
`PermissionError`, making an unreadable tree indistinguishable from an empty one,
in the same family as the honest-truncation work in `6d09eb3`. A fix and a tester
were drafted.

That was wrong. The reasoning rested on "the tree demonstrably contains files" —
evidence drawn from virtualised paths reported *inside* the packaged app, not from
the real filesystem. `%APPDATA%\Claude` genuinely holds nothing.
`AppData\Local\Claude` holds exactly one file (`Logs\chrome-native-host.log`,
2.9 KB). **The census was correct both times and was second-guessed on bad
evidence.** No scanner change is warranted.

A second suspected defect — a census writing its output to
`…\local_<id>\uploads\census.json` instead of `L5GN-Tools\data\` — was also
withdrawn. `TOOLKIT_ROOT`, `DATA_DIR` and `l5gntools.__file__` were checked
directly and all resolve to the repo; the path seen was a chat file-attachment
location, not a write target.

What survives is weaker and not a code change: **a census pointed at an
MSIX-redirected path returns a confident zero with no hint that redirection is in
play.** That is a Windows behaviour, worth a line in a playbook's sharp-edge list
if anyone censuses a packaged app's data again. It is not a toolkit fault.

---

## Commands used

```powershell
Get-ChildItem C:\Users\timps -Recurse -Include *.jsonl -ErrorAction SilentlyContinue |
  Select-Object -First 40 FullName, Length, LastWriteTime

.\.venv\Scripts\python run.py census --target "<path>"

.\.venv\Scripts\python -c "import l5gntools.common as c; print(c.TOOLKIT_ROOT); print(c.DATA_DIR); import l5gntools; print(l5gntools.__file__)"
```
