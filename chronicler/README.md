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

## Running it
- `python run.py ingest [pipeline args]` — runs `run_pipeline.py` in its own
  process, injecting `CHRONICLER_DB_PATH` from this machine's config `vault`.
  Extra args pass straight through, e.g. `python run.py ingest --render-only`.
- Or directly: `python chronicler/pipeline/run_pipeline.py`.

## Known follow-ups (next increment of #16)
1. Confirm every stage resolves `raw_*` / `vault_staging` off `CHRONICLER_HOME`
   (db.py now does for the DB + root; verify the normalizers do too).
2. On the knight: set `CHRONICLER_HOME` + `vault` in config so ingest updates the
   very DB `consume` reads — in place, no more scp of a snapshot.
3. Fresh ingest must set `threads.substantive` on new rows (a finalize-added
   column; see `pipeline/SCHEMA.md`) so the frozen-schema contract still holds.
