# Runbook — knight fresh vault build

**For:** the UAT thread, on the knight (`l5gn-castle` / `l5gn-castle-worker`).
**Date drafted:** 2026-07-24. **Toolkit:** run from the deployed venv
(`.venv/bin/python`), pipeline scripts included (`docs/PRODUCER_PLAYBOOK.md` §10).

---

## Why this exists (cover note)

The knight's `chronicler.db` is a **derived cache**, not a source of truth. Every
row in it is rebuildable from two inputs the estate still holds: the **chat
exports** (threads + messages) and the **local estate knowledge** (projects,
evidence). INTENT §5 states the principle directly — *"the data is irreplaceable;
the derived is free… rebuild them, never merge them."* The vault is the derived
side.

The links currently in that DB are **not** worth preserving. DECISIONS 0011 already
ruled the existing `project_link` values noise from early auto-accept testing, and
the reconciliation pass found the `projects` table carrying three generations of
identity. The only human-authored content is **13 `project_confidence='manual'`
rulings** — a number Tim has consciously accepted losing.

So a clear-and-rebuild is not a risky shortcut; it is the honest move. It also has a
bonus: **a fresh build makes the DECISIONS 0011 reset moot.** The whole reset chain
(clear `project_link`, delete legacy `projects` rows, re-key `link_evidence`) exists
to clean a dirty table. Rebuild from empty and there is nothing to clean — the fresh
build *is* the reset, done more thoroughly.

**One thing this runbook is careful about:** the DB is only disposable if its two
inputs genuinely survive on disk. Step 2 verifies that *before* Step 4 clears
anything, and Step 1 takes a restorable backup so the whole operation is reversible.

**What this runbook deliberately does NOT do:** it stops before `relink --apply`. A
fresh build re-created against the *current* registry rebuilds the same identity
mess, and against the *current* scorer re-creates the double-count (one sentence
scoring 0.997). Those two fixes — the registry ratification incl. CID-as-program,
and the relink scoring fix — are prerequisites for *good* links, and neither is in
scope here. This gets you a clean, honest, empty-then-rebuilt vault with evidence
staged; it does not get you the golden target. Stop where it says stop.

---

## Step 0 — orient

```bash
cd ~/L5GN-Tools
git pull                                   # get the latest scanner build on the box
.venv/bin/python run.py config             # confirm this machine's resolved paths
python verify.py                           # expect GREEN before touching anything
```

Note the vault path `config` reports; call it `$VAULT` below.

```bash
export VAULT=~/vault/chronicler.db         # replace with what config reported
```

---

## Step 1 — back up, verified. No backup, no clear.

This is what makes the whole thing reversible (DECISIONS 0005/0006).

```bash
.venv/bin/python run.py backup             # VACUUM INTO, off-box, keep-last-7
```

**Confirm before continuing:**

- The command reports a dated snapshot written **and** pushed off-box (or, if push
  is not configured, that a local snapshot landed — then copy it off the box by
  hand).
- Note the snapshot filename. If Step 4 goes wrong, this is what you restore.

```bash
ls -la ~/vault/backups/ | tail -3          # confirm the generation exists on disk
sqlite3 "$VAULT" "SELECT COUNT(*) FROM threads;"   # record the pre-clear thread count
```

Write the thread/message counts down — Step 5 must reproduce them.

---

## Step 2 — scan the box, and verify the two irreplaceables ARE on disk

This is the "look before you leap" step. **Do not skip to Step 4 until both inputs
below are confirmed present.**

```bash
.venv/bin/python run.py census             # consumer census: code root + vault root
```

Read the vault-root breakdown, then confirm each input directly:

### 2a — the chat exports (the big one)

The pipeline rebuilds threads + messages from the raw export inputs. Confirm they
exist:

```bash
ls -la ~/vault/chat_threads/zip_downloads/ 2>/dev/null
find ~/vault -maxdepth 3 -type d -name 'raw_*' -o -name 'zip_downloads' 2>/dev/null
```

- **Present** → `run.py ingest` will reproduce the vault. Proceed.
- **Absent** → **STOP.** The exports are the irreplaceable input; do not clear a DB
  you cannot rebuild. Locate the export zips (a rig, off-box backup, or re-export)
  first.

### 2b — the Gemini scrapes (Tim's flagged exception)

The scrape stage writes `<share_id>.json` + `manifest.jsonl` to `scraped_gemini/`,
which is **gitignored and therefore persists on the box** — the DB is not the only
copy. Confirm it survived:

```bash
find ~/vault -type d -name 'scraped_gemini' 2>/dev/null
ls -la $(find ~/vault -type d -name 'scraped_gemini' | head -1)/    # *.json + manifest.jsonl?
```

- **Present with its JSON + manifest** → the scraped threads re-ingest. Good.
- **Empty or missing** → the scraped content lives **only** in the DB. Either
  extract it before clearing (query the scraped threads out to JSON), or accept the
  loss consciously. This is the one input that is *not* guaranteed reproducible —
  decide deliberately, do not clear past it on autopilot.

### 2c — the number you are agreeing to

```bash
sqlite3 "$VAULT" "SELECT COUNT(*) FROM threads WHERE project_confidence='manual';"
```

Expect ~13. That is the human-authored content the clear discards. Confirm you are
still content to lose it (you have already said so; this just makes it a number).

---

## Step 3 — decision gate

Proceed to Step 4 **only if all three are true:**

- [ ] Step 1 backup exists off-box and is noted.
- [ ] Step 2a chat exports confirmed on disk.
- [ ] Step 2b scrapes confirmed on disk **or** their loss consciously accepted.

If any is false, stop here. A migrate-in-place is the fallback, but it is more work
than a rebuild and this runbook does not cover it.

---

## Step 4 — clear and rebuild the vault

```bash
# The clear: move the live DB aside rather than delete it (belt and braces —
# Step 1 already has the off-box copy, this is the on-box one).
mv "$VAULT" "${VAULT}.pre-fresh-$(date +%Y%m%dT%H%M%SZ)"
mv "${VAULT}-wal" "${VAULT}-wal.old" 2>/dev/null || true
mv "${VAULT}-shm" "${VAULT}-shm.old" 2>/dev/null || true

# Rebuild from the exports: backup(skipped, just cleared) -> intake -> pipeline.
.venv/bin/python run.py ingest --skip-backup
```

`ingest` unpacks the drop zone and runs the Chronicler pipeline against the raw
exports, creating a new `chronicler.db` from scratch. `--skip-backup` because Step 1
already took one and the old DB is moved aside, not present to back up.

If the scrapes need re-ingesting and `ingest` did not pick them up automatically,
run the scrape intake per `KNIGHT_PLAYBOOK.md` §10.3 before the pipeline.

---

## Step 5 — verify the rebuild reproduced the inputs

```bash
sqlite3 "$VAULT" "SELECT COUNT(*) FROM threads;"     # compare to Step 1's count
sqlite3 "$VAULT" "SELECT COUNT(*) FROM messages;"
sqlite3 "$VAULT" "PRAGMA journal_mode;"              # must be 'wal' (DECISIONS 0014)
sqlite3 "$VAULT" "SELECT COUNT(*) FROM threads WHERE project_link IS NOT NULL;"  # expect 0
```

- Thread/message counts should land at or above Step 1's numbers (the exports are
  the same or newer). A **lower** count means the ingest missed inputs — investigate
  before proceeding; do not paper over it.
- `project_link` should be **0** — a fresh vault has no links yet. That is correct:
  this is the clean slate.

---

## Step 6 — build the registry and run the evidence producers DRY. Then STOP.

```bash
.venv/bin/python chronicler/pipeline/build_registry.py --report-aliases
.venv/bin/python chronicler/pipeline/build_inventory.py --force
.venv/bin/python chronicler/pipeline/xref_filenames.py          # dry-run (default)
.venv/bin/python chronicler/pipeline/extract_path_mentions.py   # dry-run (default)
```

Read the dry-run tables. This is the honest stopping point for the fresh-build
session.

### ⛔ Do NOT run `--apply` or `relink --apply` in this session.

Two prerequisites are not met, and applying without them rebuilds the exact problems
the fresh build was meant to escape:

1. **The registry is not ratified.** `build_registry` above uses whatever
   `config/project_registry.json` is on the box. Until the reconciliation list +
   CID-as-program ruling land, applying links rebuilds the three-generation identity
   mess on clean data.
2. **The relink scorer is unfixed.** The double-count (a filename hit + a path
   mention from one sentence scoring 0.997, out-voting three independent sources) is
   still live. Applying now bakes bad scores into a fresh vault.

Leave the evidence **staged in dry-run**. The vault is now clean, honest, and ready
for the golden-path work — registry ratification, scorer fix, then apply — in a
later session.

---

## If it goes wrong — restore

```bash
# on-box copy moved aside in Step 4:
mv "${VAULT}.pre-fresh-<timestamp>" "$VAULT"
# or restore the Step 1 off-box backup per KNIGHT_PLAYBOOK.md.
sqlite3 "$VAULT" "SELECT COUNT(*) FROM threads;"   # confirm the old state is back
```

Nothing in this runbook is destructive until Step 4, and Step 4 moves rather than
deletes. The DB you started with is recoverable from either the on-box `.pre-fresh`
copy or the Step 1 off-box snapshot.

---

## Recording it

If you walk this as UAT, the results log needs a uat stamp or the gate refuses the
commit (`docs/README.md` §3):

```
<!-- uat: commit=<sha> dirty=<bool> host=l5gn-castle-worker walked=<YYYY-MM-DD> gate=<Na/Mt> -->
```

Record the before/after thread counts, which inputs were confirmed on disk, whether
the scrapes survived, and that the session stopped before `--apply`.
