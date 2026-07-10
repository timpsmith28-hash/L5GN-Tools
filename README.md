# L5GN-Tools

Estate-level, **read-only** scanners for the L5GN project family. One toolkit at
the GitHub root that runs against any sibling folder — so the utilities that used
to be copy-pasted into every project (workspace scanner, git scanners, doc census…)
live in one place and take the target folder as a parameter.

## Design contract

- **Read-only.** Tools never write into a folder they scan. The *only* writer is
  `common.write_json`, and it is confined to `L5GN-Tools/data/`.
- **Stdlib-only.** Scanners import stdlib + this package only, so they run against
  any sibling regardless of that project's virtual-env.
- **One CLI shape.** Every tool takes `--target <name>` (a sibling folder) or
  `--all` to sweep the estate.
- **The gate is the door.** `verify.py` runs auditors + testers; the committed
  `.githooks/pre-commit` refuses red commits. (Pattern borrowed from Citadel v5 / CID.)

## Setup (per clone)

```
git config core.hooksPath .githooks     # turn the gate on
python verify.py                          # should print: verify: GREEN
```

On Windows, if the hook loses its exec bit:
`git update-index --chmod=+x .githooks/pre-commit`

## Use

```
python run.py list                        # list tools
python run.py build                       # run everything -> data/ + report.html
python run.py git_summary --all           # one tool across every project
python run.py workspace_scanner --target L5GN_Armory_v4
python run.py build --include-third-party # also include cloned repos
```

Open `report.html` (double-click) to browse the results — it is self-contained
and embeds the latest `data/estate.json`.

## Tools

| Tool | Scope | What it does |
|---|---|---|
| `workspace_scanner` | project | AST code inventory (classes/functions/imports), vendored code excluded |
| `git_summary` | project | Latest commit, branch, depth, working-tree state |
| `git_deep_history` | project | Full commit ledger + per-author / per-day stats |
| `doc_census` | project | Markdown inventory; README / CLAUDE.md / ADR presence |
| `import_scanner` | project | Import census split stdlib / third-party / local |
| `env_scanner` | project | Config-file inventory + secret-exposure flags (names only) |
| `bloat_audit` | project | Flags tracked venvs/models, big files, missing `.gitignore` |
| `todo_adr_scanner` | project | TODO/FIXME markers + ADR status census |
| `estate_status` | estate | Git dashboard row per project |
| `duplicate_finder` | estate | Same-named / byte-identical files across projects |

## Layout

```
L5GN-Tools/
  run.py               dispatcher / batch runner (CLI entry)
  verify.py            the gate (auditors + testers)
  l5gntools/
    common.py          read-only helpers + the sole writer
    registry.py        the list of scanners (single source of truth)
    report.py          aggregator + self-contained HTML viewer
    scanners/          one module per tool
  auditors/            static gate: cli-contract, read-only, stdlib-only
  tests/               behavioural gate over a temp fixture
  data/                generated output (git-ignored)
  report.html          generated viewer (git-ignored)
```

Adding a tool: drop a module in `scanners/` (with `NAME`, `DESCRIPTION`,
`ESTATE_LEVEL`, and `scan`/`scan_estate`) and add it to `registry.py`. The
auditors enforce the contract; nothing else needs editing.
