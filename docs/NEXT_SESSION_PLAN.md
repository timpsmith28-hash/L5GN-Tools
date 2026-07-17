# L5GN-Tools — Build Plan & Status

Living roadmap for the estate + chat-vault toolkit across the three-machine mesh
(gaming rig, work laptop, headless knight). Read top-to-bottom for where we are.

## Locked decisions (unchanged)

- **Knight holds both estates**, walled by path (`personal/` vs `work/`), never merged.
- **Transport = direct rig → knight push** (rsync/scp/Syncthing). No cloud in the pipe.
  Gemini exports are pulled from Drive onto the rig first, then pushed with everything else.
- **Diff history = append-only dated snapshots** in `data/history/` + a `latest` pointer.
  "What changed since last sync" = diff of the two most recent snapshots.
- **Machine config = hostname-keyed** (`config/machines.json`) + gitignored `config/local.json`.
- **Account wall is a data dimension**, never a merged figure (claude-personal / gemini-personal / gemini-work).
- **Chronicler DB is frozen** (`user_version 1`, `schema_version 1.0-frozen`); the toolkit only *reads* it.
- **Read-only + stdlib contract holds for scanners**; writers (deposit, and later Chronicler ingest) live outside it.

## Done (committed d3116af and prior)

- **Machine-config keystone** — `l5gntools/config.py`, hostname-keyed roots with legacy fallback, `run.py config`.
- **Estate snapshots + `estate_diff`** — `build` deposits dated `data/history/` snapshots; `estate_diff` reports moved HEADs / new commits / doc + wiki_shard deltas / added-removed projects.
- **Chronicler DB freeze** — P1–P3 + `schema_version` applied on the work rig; frozen `chronicler.db` in place.
- **Interpret layer (reads the frozen vault, `mode=ro`, `user_version` guard):**
  - `vault_reader` — per-project chat rollups joined to the estate, account-walled.
  - `project_trail` (S7) — per-project discussion trail, newest-first, confidence-ranked.
  - `drift` (S8) — talked-not-built / built-not-discussed / discussed-not-present.
- **Author-identity folding** — `config/authors.json` collapses git aliases in `git_deep_history`.
- Gate: `verify.py` GREEN across 4 auditors + 11 testers; pre-commit hook enforced.

Confirmed on real data (LucasGoonPC): `vault_reader` ok (1171 threads, `user_version 1`);
`present_in_estate` correctly flips True for repos on the machine and False for those elsewhere;
`drift` split 3 talked-not-built / 4 discussed-not-present.

## Remaining

### Phase 4 — stand up the mesh
- **#11 rig → knight deposit/push** — writer (not a scanner): package this machine's
  `estate.json` + latest snapshot into a namespaced outbox (`work/` vs `personal/` from
  config), with a manifest (sha256 + meta); push to the knight via config `push_target`
  (rsync/scp), only into the machine's own namespace. Refuse to deposit an `unknown` estate.
- **#12 knight ingest + consumer orchestration** — land deposits under `estates/{personal,work}/history/`
  per config `estates_dir`; point `estate_diff` + `vault_reader` at the right per-estate dir;
  a consumer entrypoint runs the interpret sweep (estate_diff → vault_reader → project_trail → drift).
- **#13 end-to-end mesh verify (+ optional schedule)** — dry-run the full loop; confirm the
  walls hold at every hop; then optionally schedule the nightly knight sweep.

### Supporting
- **#14 work-Claude export mitigation** — admin-gated; interim `.md`-looping, future shared work vault.
- **#15 toolkit version stamp** — git SHA into `estate.json` + report header, for cross-machine version parity; pair with a deploy/versioning crash course.
- **#16 assimilate Chronicler** — vendor the ingest pipeline into the repo as its own writer
  subsystem (own deps: pyyaml, sentence-transformers), outside the read-only scanner contract
  (auditors already scope to `registry.SCANNERS`). One repo, one deploy, one version on the knight.

## The loop (why it composes on the knight)
- estate scanners / `estate.json` → what the code **is**
- `estate_diff` → what the code **did** since last sync
- `vault_reader` / `project_trail` → what was **discussed** + which threads link to which repo
- `drift` → the reconciliation: discussed vs built vs present
