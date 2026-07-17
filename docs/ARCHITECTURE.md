# L5GN-Tools — Architecture

Design rationale for the toolkit: what it's for, how the pieces fit, and *why*
the boundaries are drawn where they are. For deploy/operate steps see
`KNIGHT_PLAYBOOK.md`; for the front-door overview see the root `README.md`.

## 1. The problem

Work sprawls across many git repos on several machines, and the *thinking* behind
that work lives in chat threads across several LLM tools and accounts. Neither
half sees the other. The goal: one honest, queryable picture that reconciles
**what the code did** against **what was discussed** — assembled on a machine that
holds everything, without either half being able to corrupt the other.

## 2. Shape: a small mesh with two roles

- **Producers** (gaming rig, work laptop) scan their own repos into an
  `estate.json` snapshot and **push** it to the consumer.
- **The consumer** (the headless *knight*) receives every estate, holds them side
  by side but **walled** (personal vs work never merge), ingests chat exports into
  the vault, and runs the interpret layer over both.

A machine's role and paths come from hostname-keyed config, so the *same repo*
behaves correctly everywhere.

## 3. The load-bearing boundary: two subsystems

The single most important design decision is that the repo contains two
subsystems with opposite guarantees, kept apart on purpose:

| | `l5gntools/` (+ scanners) | `chronicler/` |
|---|---|---|
| Role | read the estate + interpret | **build/update the vault** |
| Contract | **read-only, stdlib-only** | writer, own deps (pyyaml, embeddings) |
| Enforced by | auditors over `registry.SCANNERS` | not audited — deliberately outside |
| Can it harm a repo/vault? | no (proven read-only) | yes (it's the writer) |

Because the auditors scope themselves to `registry.SCANNERS`, vendoring a whole
writer pipeline in as `chronicler/` doesn't threaten the scanner guarantee *by
construction* — nothing in `l5gntools/` imports it, and the ingest entrypoint
runs it in a subprocess so the stdlib-only core never even imports its deps. The
read-only scanners can therefore run anywhere, against any repo, with zero setup;
the writer's weight is isolated to the one machine that ingests.

## 4. The loop (data flow)

```
PRODUCER                              KNIGHT (consumer)
 run.py build                          run.py ingest
   walk repos (read-only)               intake: unpack export zips -> raw_*
   -> data/estate.json + history/        Chronicler pipeline -> chronicler.db
 run.py deposit --push                  run.py consume
   package {estate.json, snapshot,        ingest each deposit (verify manifest,
   sha256 manifest} into outbox/<estate>  accumulate history)
   scp/rsync -> knight:estates/<estate>/  estate_diff  what the code DID
                                          vault_reader  what was DISCUSSED
                                          project_trail per-project chat trail
                                          drift         built vs discussed
```

Two independent feeds meet on the knight: the **estate** side (code, via deposit)
and the **vault** side (chat, via ingest). `drift` is where they reconcile.

## 5. Key decisions & why

- **The wall is a data dimension AND a physical separation, never trust.** Estates
  are separated by *path* (`estates/personal/` vs `estates/work/`); a producer can
  only deposit into its own namespace (guard refuses `unknown`), so a misconfig
  can't cross the streams. Chat is separated by the `account` field, carried on
  every rollup and never merged into a single figure. Two mechanisms, both
  structural.
- **Config is a shipped artifact (Docker-style).** `machines.json` is a committed
  template; real per-machine config lives in git-ignored `local.json`, scp'd out.
  Nothing machine-specific enters git; a pull never clobbers a machine's config.
- **The gate is the door.** `verify.py` (auditors + testers) runs in the pre-commit
  hook and refuses red commits; the same gate runs on push-to-deploy. Adding a
  scanner is the only extension that must satisfy the read-only/stdlib auditors.
- **The vault is frozen and asserted.** Chronicler stamps `user_version`; every
  reader opens it `mode=ro` and refuses a version it doesn't expect
  (`schema_mismatch`) rather than misinterpreting. Fresh ingest re-derives
  `substantive` so the frozen-schema contract survives new data.
- **History accumulates on the consumer.** A producer only ever sends its latest
  snapshot; the knight archives each into a per-estate `history/`, so `estate_diff`
  has a growing trail to compare even though the wire carries only "now".
- **Deposits are self-describing + verified.** Each bundle carries a sha256
  manifest; the consumer verifies it (`True`/`False`/`None`) before trusting it.
- **Consistency over cleverness.** e.g. `project_trail.latest_activity` matches
  `vault_reader`'s definition (newest of *any* thread) so `drift`'s recency can't
  silently diverge between the two tools.

## 6. The three contracts

1. **Scanner contract** — `NAME`, `DESCRIPTION`, `ESTATE_LEVEL`, `SAFETY`, and
   `scan`/`scan_estate`; read-only; stdlib + `l5gntools` only; output only via
   `common.write_json` under `data/`. Registered in `registry.py`; auditors prove it.
2. **Deposit contract** — a bundle is `{estate.json, latest snapshot, deposit_manifest.json}`
   under an outbox namespaced by estate; it lands in the matching namespace on the
   knight; `unknown` is refused.
3. **Vault contract** — `chronicler.db` at frozen `user_version`; consumers read
   `mode=ro`; "unlinked" is `project_link IS NULL`; confidence order
   `none/NULL < fuzzy < evidence < exact < manual`; `substantive` = ≥4 messages.

## 7. Trade-offs & known limits

- **Manual chat capture is a weak backup.** The close-out-prompt path
  (`chronicler/CLOSEOUT_PROMPT.md`) is a token-expensive, lossy self-report, viable
  only for short threads — not a replacement for a real export. Admin-gated
  work-Claude remains a genuine gap.
- **Linking is a separate pass.** Fresh ingest lands threads unlinked;
  `relink.py` (embeddings) ties them to projects on demand, so `drift` sees new
  threads before they're fully cross-referenced.
- **Estate vs account are related but not identical.** A work repo can be
  discussed on a personal account; per-estate reports carry the account dimension
  so the nuance is visible rather than flattened.
- **Best-effort manifest verification.** `None` (no hash) is treated as "unknown,
  proceed", not a hard failure — deposits from older producers still ingest.

## 8. Extending it

- **New scanner:** module in `l5gntools/scanners/` + import in `registry.py`. The
  auditors enforce the contract; nothing else changes.
- **New chat source:** a normalizer in `chronicler/pipeline/` + a stage in
  `run_pipeline.py` (input-gated). Keep it stdlib-only if you can, so its test runs
  in the core gate.
- **New machine:** add its hostname section to `local.json`, scp it over, done.
