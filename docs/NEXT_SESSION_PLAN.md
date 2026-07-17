# L5GN-Tools — Next-Session Build Plan

Hand this back next session and say "run the sequence." Everything below is
agreed; no open design questions block Phases 1–2.

## Locked decisions

- **Knight holds both estates**, walled by path (`personal/` vs `work/`), never merged.
- **Transport = direct rig → knight push** (rsync/scp/Syncthing). No cloud in the pipe.
  Gemini exports are pulled from Drive onto the rig first, then pushed with everything else.
- **Diff history = append-only dated snapshots** in `data/history/estate-YYYY-MM-DD.json`
  + a rolling `latest` pointer. "What changed since last sync" = diff of the two
  most recent snapshots. No separate state file.
- **Machine config = hostname-keyed**, committed + gitignored local override.
  Replaces `resolve_targets`' "estate root = toolkit's parent folder" inference
  (the cause of the too-shallow work-rig scan).
- **vault_reader = read-only `sqlite3` (`mode=ro`) scanner**, stdlib, emits to `data/`.
  Carries the same work/personal wall as the estates.
- **Drive upload = scrubbed** (was a SharePoint-vs-Drive bakeoff, not part of the plan).
- **Chronicler stays on the work rig** — finish it there; the toolkit only *reads* its output.

## Sequence

### Phase 1 — Machine-config keystone (unblocked)
1. Add `config/machines.json` (committed, keyed by `socket.gethostname()`) and
   `config/local.json.example`; gitignore `config/local.json` (paths/secrets/push target).
2. Add `l5gntools/config.py`: load machines.json → select by hostname → overlay local.json;
   expose `roots`, `role`, `estate`, `vault`, `estates_dir`.
3. Refactor `common.resolve_targets` / `ESTATE_ROOT` to read roots from config,
   **falling back to current sibling behavior if no config present** (nothing breaks on the gaming rig today).
4. `python verify.py` stays GREEN; add a config-selection test.

### Phase 2 — estate_diff scanner (unblocked)
5. On `build`: also write `data/history/estate-YYYY-MM-DD.json` + update `latest` pointer.
6. Add `l5gntools/scanners/estate_diff.py` (estate-level): read two most recent snapshots,
   emit → moved HEADs + commit subjects (`git_deep_history`), doc hash deltas (`doc_census`),
   new/removed projects, `wiki_shards` changes → `data/estate_diff.json`.
7. Register in `registry.py`; verify GREEN; test with two hand-made snapshots.

### Phase 3 — vault_reader (deferred until vault schema freezes, ~days)
8. Spec + build against Chronicler §5 schema: read-only `sqlite3` `mode=ro`,
   emit thread/project/message rollups + `project_link` join into workspace/duplicate_finder
   inventory, respect account/estate wall → `data/vault_reader.json`.

### Phase 4 — rig → knight push pipeline (after 1–3)
9. Deposit contract: each rig pushes **only** into its declared namespace
   (work rig → `work/`, gaming rig → `personal/`); target derived from machine config, not memory.
10. Push mechanism (rsync/scp/Syncthing) triggered post-`build`; Gemini pulled to rig first.

## The loop (why this composes on the knight)
- estate scanners / `estate.json` → what the code **is**
- `estate_diff` → what the code **did** since last sync
- `vault_reader` → what was **discussed** + which threads link to which repo
