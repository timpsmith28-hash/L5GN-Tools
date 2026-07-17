# L5GN-Tools

One toolkit, installed on every machine in a small mesh, that builds a single
picture of a **code estate** and reconciles it against a **chat-history vault**
(Chronicler). Producers scan their repos and push snapshots to a headless
consumer (the *knight*), which holds every estate side by side — walled
personal-vs-work — and interprets them against the chat archive.

Two subsystems live here, with a deliberate boundary between them:

- **`l5gntools/` — read-only scanners.** Stdlib-only, never write into a scanned
  folder. This is the estate-inventory + interpret layer. The `verify.py` gate
  (auditors + testers, enforced by the pre-commit hook) polices that contract.
- **`chronicler/` — the ingest pipeline (a writer).** Deliberately *outside* the
  read-only/stdlib contract (its own deps: pyyaml, sentence-transformers). It
  builds and updates the vault the scanners read. See `chronicler/README.md`.

## The loop

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
python run.py deposit [--push]             # (producer) package + ship estate snapshot to the knight
python run.py consume                      # (knight) ingest deposits + run the interpret sweep
python run.py ingest [--skip-intake]       # (knight) unpack the drop zone + run the Chronicler pipeline
python run.py intake [--dry-run]           # (knight) unpack export zips only
python verify.py                           # the gate
```

## Tools

| Tool | Scope | What it does |
|---|---|---|
| `workspace_scanner` | project | AST code inventory (classes/functions/imports), vendored code excluded |
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
  run.py               dispatcher / CLI entry (build, deposit, consume, ingest, intake…)
  verify.py            the gate (auditors + testers)
  l5gntools/           read-only scanners + config, deposit, consume (stdlib-only)
    scanners/          one module per tool
  chronicler/          vendored ingest pipeline (writer; own deps) -- builds the vault
  config/              machines.json (template) + local.json (real, git-ignored)
  deploy/              push-exports.ps1 + knight systemd auto-ingest units
  docs/                KNIGHT_PLAYBOOK.md (deploy + operator guide), NEXT_SESSION_PLAN.md
  data/, report.html   generated output (git-ignored)
```

## More

- **Design rationale / how it fits:** `docs/ARCHITECTURE.md`
- **Deploy / operate the mesh:** `docs/KNIGHT_PLAYBOOK.md`
- **Ingest subsystem + drop zone:** `chronicler/README.md`
- **Auto-delivery of exports:** `deploy/README.md`
- **Roadmap / status:** `docs/NEXT_SESSION_PLAN.md`

Adding a scanner: drop a module in `l5gntools/scanners/` (with `NAME`,
`DESCRIPTION`, `ESTATE_LEVEL`, `SAFETY`, and `scan`/`scan_estate`) and register it
in `l5gntools/registry.py`. The auditors enforce the read-only/stdlib contract;
nothing else needs editing.
