# The gate was green in the sandbox and red on the rig — a leaked sqlite handle

**Date:** 2026-07-27 · **Origin:** command-deck migration round, at the commit step ·
**Fixed in:** `00d590d` (`chronicler/review/core.py`)

Born frozen, per `docs/README.md` §4. Evidence, not a maintained document.

---

## What happened

`tester_deck_migration` was written and gated **green** by a Cowork build thread
running in a Linux sandbox. Run on the gaming rig (Windows), the same tester at
the same commit failed — twice, deterministically:

```
[FAIL] tester_deck_migration: gate raised PermissionError: [WinError 32]
The process cannot access the file because it is being used by another process:
'C:\Users\timps\AppData\Local\Temp\tmpq7v11hub\unmigrated.db'
```

The pre-commit hook refused the commit. Correctly.

## Root cause — the endpoint, not the test

`chronicler/review/core.connect()` opened the vault, then ran the deck-schema
check **outside any try/except**:

```python
conn = _connect(db_path)
_check_deck_schema(conn)   # raises DeckSchemaNotMigratedError -- conn never closed
return conn
```

On the refusal path the connection object was abandoned still open. The tester
exercises exactly that path (item 5: *"core's refusal path fires on an unmigrated
DB"*), inside a `tempfile.TemporaryDirectory()`, so cleanup tried to delete a
file sqlite still had open.

## Why only Windows

POSIX allows unlinking a file that a process still holds open — the directory
entry goes, the handle stays valid, the space is reclaimed on close. Windows
refuses. So on Linux the temp dir cleaned up silently and the leaked handle was
**invisible**; on Windows the same leak was a hard error.

Windows didn't cause the bug. It refused to hide it.

## Why it mattered beyond the test

`app._connect` delegates to `core.connect` from **every route handler**:

```python
def _connect(db_path):
    # Delegates to core.connect -> l5gntools.dbsafe ... (DECISIONS 0014)
    return core.connect(db_path)
```

So against an unmigrated vault, every HTTP request to the deck leaked one open
sqlite connection. Not a test artefact — a per-request resource leak on a
surface reachable by any tailnet device, in the code path that fires precisely
when something is already wrong.

## The fix, in the product

```python
conn = _connect(db_path)
try:
    _check_deck_schema(conn)
except Exception:
    conn.close()
    raise
return conn
```

**The tester was not changed.** It was right. A weaker version — closing the
connection itself, or using a fixed path instead of `TemporaryDirectory` —
would have passed on both platforms and left the leak in place. It failed for
exactly the reason it existed.

## What this says about the gate

**The sandbox gate and the rig gate are not the same gate.** Everything the
suite checks about logic is platform-independent; everything it incidentally
checks about *OS resource lifetime* is not. A green sandbox run means the logic
holds. It does not mean file handles are released.

This is the second time in one day a Linux-shaped assumption met Windows and
lost — the other being MSIX path virtualisation making `%APPDATA%\Claude` look
empty (`2026-07-27_cowork-transcript-store.md`). Different mechanisms, same
shape: the developing environment and the running environment disagree about
the filesystem, and the disagreement is silent on one side.

Consequence worth stating plainly: **a Cowork thread's "gate GREEN" is provisional
until the gate has run on the machine that owns the files.** The commit hook on
the rig is the real gate; the sandbox run is a fast pre-check.

## Blast radius — not measured, listed

Fourteen testers combine `TemporaryDirectory` with an sqlite connection and
could in principle hit the same class of failure if any code path they exercise
abandons an open handle:

`tester_backfill_candidate_project`, `tester_backup`, `tester_dbsafe`,
`tester_deck_migration`, `tester_extract_path_mentions`, `tester_md_transcript`,
`tester_project_trail`, `tester_registry_tiers`, `tester_relink_apply`,
`tester_review`, `tester_serve`, `tester_set_substantive`, `tester_vault_reader`,
`tester_xref_filenames`.

All fourteen currently pass on Windows, so no other leak is *known*. They are
listed because "passes today" and "closes its handles on every path" are not the
same statement, and only the error paths are likely to differ — an exception
raised between open and close is the shape that produced this one.

No change was made to any of them. Recorded so a future Windows-only failure in
this list is recognised as a family, not a novelty.
