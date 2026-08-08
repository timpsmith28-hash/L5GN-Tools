# L5GN-Tools

One toolkit that builds a single picture of a **code estate** and reconciles
it against a **chat-history vault** (Chronicler), standalone on one machine
by default: `run.py app` (or `run.py window` for a desktop shortcut) scans,
ingests, and serves the deck in one process, one port, no second box.

A cross-machine mesh mode still exists for whoever wants it — producers scan
their repos and push snapshots to a headless consumer (the *knight*), which
holds every estate side by side, walled personal-vs-work — but it is opt-in
now, not the default (DECISIONS 0036): see "Mesh mode" below.

Two subsystems live here, with a deliberate boundary between them:

- **`l5gntools/` — read-only scanners.** Stdlib-only, never write into a scanned
  folder. This is the estate-inventory + interpret layer. The `verify.py` gate
  (auditors + testers, enforced by the pre-commit hook) polices that contract.
- **`chronicler/` — the ingest pipeline (a writer).** Deliberately *outside* the
  read-only/stdlib contract (its own deps: pyyaml, sentence-transformers). It
  builds and updates the vault the scanners read. See `chronicler/README.md`.

## Running it (standalone, the default)

```
run.py build      walk your repos (read-only) -> data/estate.json + history/
run.py ingest     unpack chat export zips -> Chronicler pipeline -> chronicler.db
run.py app        serve the deck: queue + estate + docs board + UAT + Curator +
                   Datasette, one process, one port
run.py window     'app' plus a desktop window (or use the .bat shortcut)
```

One machine, its own repos, its own vault. No push, no drop zone, no second
box.

## Mesh mode (opt-in)

The original shape — producers scanning and pushing snapshots to a headless
consumer (the *knight*) — still exists, mothballed rather than removed
(DECISIONS 0036). It is off by default; `deposit` / `consume` / `intake`
refuse with a stated remedy until a machine's config sets `"mesh": true`:

```
producer rig                        knight (consumer)
  run.py build      --.               .-- run.py ingest  (chat export zips -> vault)
   estate.json        \             /     run.py consume  (interpret deposits + vault)
  run.py deposit ----> scp/ssh ---> estates/{personal,work}/
                                        estate_diff  what changed since last sync
                                        vault_reader what was discussed
                                        project_trail per-project chat trail (S7)
                                        drift        built-vs-discussed (S8)
```

See `docs/archive/KNIGHT_PLAYBOOK.md` / `docs/archive/PRODUCER_PLAYBOOK.md`
for the full operator's guide to standing this back up.

Each machine knows its **role** (`producer` / `consumer`) and paths from config
keyed by hostname. `config/machines.json` is a committed template; the real
per-machine config lives in `config/local.json` (git-ignored, shipped by scp).

## Setup (per clone)

```
git config core.hooksPath .githooks      # turn the gate on
python run.py config                       # show this machine's resolved role/paths
python verify.py                           # should print: verify: GREEN
```

Copy an example from `config/machines.json` into `config/local.json`, rename the
key to your hostname (`run.py config` shows it), and fill in real paths. Ingest on
the knight also needs `pip install -e '.[chronicler]'` in a venv.

## Commands

```
python run.py list                         # list scanners
python run.py build [--all --include-third-party]   # scan -> data/estate.json + snapshot + report.html
python run.py <tool> --target NAME | --all          # one scanner
python run.py config                       # this machine's resolved config
python run.py app [--port N] [--host H]    # the deck: one process, one port
python run.py window                       # 'app' + a desktop window
python run.py ingest [--skip-intake]       # unpack the drop zone (mesh only) + run the Chronicler pipeline
python verify.py                           # the gate
```

Mesh-only, refuse with a stated remedy unless `"mesh": true` (see "Mesh mode" above):

```
python run.py deposit [--push]             # (producer) package + ship estate snapshot to the knight
python run.py consume                      # (knight) ingest deposits + run the interpret sweep
python run.py intake [--dry-run]           # (knight) unpack export zips only
```

## Tools

| Tool | Scope | What it does |
|---|---|---|
| `workspace_scanner` | project | AST code inventory (classes/functions/imports), vendored code excluded |
| `file_census` | project | Three-tier file inventory; names the untracked, un-ignored at-risk set |
| `git_summary` | project | Latest commit, branch, depth, working-tree state |
| `git_deep_history` | project | Commit ledger + per-author (alias-folded) / per-day stats |
| `doc_census` | project | Markdown inventory; README / CLAUDE.md / ADR presence |
| `import_scanner` | project | Import census split stdlib / third-party / local |
| `env_scanner` | project | Config-file inventory + secret-exposure flags (names only) |
| `bloat_audit` | project | Flags tracked venvs/models, big files, missing `.gitignore` |
| `todo_adr_scanner` | project | TODO/FIXME markers + ADR status census |
| `estate_status` | estate | Git dashboard row per project |
| `duplicate_finder` | estate | Same-named / byte-identical files across projects |
| `estate_diff` | estate | Diff two estate snapshots: moved HEADs, new commits, doc deltas |
| `vault_reader` | estate | Read-only rollup of the Chronicler vault, joined to estate projects |
| `project_trail` | estate | Per-project chat discussion trail, newest-first (S7) |
| `drift` | estate | Talked-not-built / built-not-discussed / discussed-not-present (S8) |

`vault_reader` / `project_trail` / `drift` read the frozen vault (`mode=ro`,
`user_version` guard) and carry the work/personal account wall as a data dimension.

## Layout

```
L5GN-Tools/
  run.py               dispatcher / CLI entry (app, window, build, ingest; mesh-only:
                        deposit, consume, intake)
  verify.py            the gate (auditors + testers)
  l5gntools/           read-only scanners + config, deposit, consume (stdlib-only)
    scanners/          one module per tool
  chronicler/          vendored ingest pipeline (writer; own deps) -- builds the vault
    review/            the deck: FastAPI app, module registry, launcher, static/
  config/              machines.json (template) + local.json (real, git-ignored)
  deploy/              push-exports.ps1 + knight systemd auto-ingest units (mesh mode)
  docs/                the trinity; see docs/README.md for the map
    archive/           retired docs, stamped (incl. the mesh playbooks); investigation/
                        raw thread exchanges
  data/, report.html   generated output (git-ignored)
```

## More

- **Design rationale / how it fits:** `docs/ARCHITECTURE.md`
- **Mesh mode (opt-in):** `docs/archive/KNIGHT_PLAYBOOK.md` / `PRODUCER_PLAYBOOK.md`
- **Ingest subsystem + drop zone:** `chronicler/README.md`
- **Auto-delivery of exports (mesh mode):** `deploy/README.md`
- **Doc map / archiving convention:** `docs/README.md`
- **Status:** derived, not documented — `python verify.py`, `git log`, the DB

Adding a scanner: drop a module in `l5gntools/scanners/` (with `NAME`,
`DESCRIPTION`, `ESTATE_LEVEL`, `SAFETY`, and `scan`/`scan_estate`) and register it
in `l5gntools/registry.py`. The auditors enforce the read-only/stdlib contract;
nothing else needs editing.
