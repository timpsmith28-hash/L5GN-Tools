# Chronicler — ingest subsystem (vendored)

The chat-history pipeline that **builds** the vault the toolkit reads. It is a
**writer**, and deliberately sits *outside* the toolkit's read-only, stdlib-only
scanner contract:

- Nothing in `l5gntools/` imports anything here, and the auditors only police
  `registry.SCANNERS` — so this subsystem may use pyyaml / sentence-transformers /
  playwright and write to disk without threatening the scanner guarantees.
- The core toolkit stays dependency-free. Install these deps only where you
  ingest: `pip install -e .[chronicler]` (add `.[scrape]` for the share-scraper).

## Layout
- `pipeline/` — ingest stages (normalize → reconcile → group → render) plus
  `db.py`, the schema, and `finalize_db.py`. Orchestrated by `run_pipeline.py`.
- `scrape_gemini_share.py` — standalone Gemini share-link scraper (needs playwright).

## Runtime data lives OUTSIDE the repo
Inputs/outputs (`raw_*`, `scraped_gemini/`, `vault_staging/`, the `*.db`) are
per-machine and git-ignored. Point the pipeline at them with env vars:
- `CHRONICLER_HOME` — data root holding `raw_*`, `vault_staging`, etc.
- `CHRONICLER_DB_PATH` — the SQLite vault location (defaults under `CHRONICLER_HOME`).

## Drop zone
Drop Claude / Google-Takeout export **zips** into
`CHRONICLER_HOME/chat_threads/zip_downloads/` and intake classifies each,
extracts it into the right `raw_*` dir, and moves the zip to
`zip_downloads/archive/<source>/`. Unrecognised zips are left in place. Multi-part
Takeout zips just merge into the same `raw_gemini_files/Takeout` tree.

## Running it
- `python run.py ingest [pipeline args]` — the one-command path: **intake** (unpack
  the drop zone) then the **pipeline**, in its own process, injecting
  `CHRONICLER_DB_PATH` from this machine's config `vault`. `--skip-intake` runs the
  pipeline only; other args pass through, e.g. `python run.py ingest --render-only`.
- `python run.py intake [--dry-run]` — unpack the drop zone only (classify with
  `--dry-run`).
- Or directly: `python chronicler/pipeline/run_pipeline.py` / `intake.py`.

## Known follow-ups (next increment of #16)
1. Confirm every stage resolves `raw_*` / `vault_staging` off `CHRONICLER_HOME`
   (db.py now does for the DB + root; verify the normalizers do too).
2. On the knight: set `chronicler_home` + `vault` in config so ingest updates the
   very DB `consume` reads — in place, no more scp of a snapshot. **(live test pending)**
3. ~~Fresh ingest must set `threads.substantive`~~ — **done**: `set_substantive.py`
   runs as a DB-only stage before render, recomputing the flag from message counts.
