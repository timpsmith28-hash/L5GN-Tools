# L5GN-Tools — Status & Next Steps

The **rolling status board**: what's true right now and what to pick up next.
Not the system explainer (`ARCHITECTURE.md`), not the priming doc (`HANDOFF.md`),
not the ops guide (`KNIGHT_PLAYBOOK.md`). If those disagree with this file about
*status*, this file wins; if they disagree about *design*, they win.

Last verified against the estate: 2026-07-17 (read of `verify.py`, `tests/`,
`auditors/`, `config/machines.json`, git log).

## Where we are

**All 16 planned tasks are done.** The three-machine mesh runs end to end:
LucasGoonPC (personal producer) `build` → `deposit --push` (scp over the
`l5gn-castle` ssh alias) → the knight (`l5gn-castle-worker`, consumer) verifies the
manifest, accumulates history, and runs the walled interpret sweep against the
vault. Nothing is half-built; everything below is optional.

- **Phases 1–4 (#1–#13):** machine config, `estate_diff`, the vault interpret
  layer (`vault_reader` / `project_trail` / `drift`), author folding, deposit
  (namespaced + manifest + scp/rsync), knight ingest + consume, live round-trip.
- **#14 — work-Claude export mitigation:** landed as markdown-transcript ingest
  + `chronicler/CLOSEOUT_PROMPT.md`. **Caveat:** this is a *backup*, not a fix —
  token-expensive and lossy on long threads. Admin-gated work-Claude is still a
  genuine gap.
- **#15 — toolkit git-SHA stamp** in `estate.json` / report. Done.
- **#16 — Chronicler assimilated.** Vendored as a walled *writer* subsystem
  (own deps: pyyaml, sentence-transformers; deliberately outside the read-only
  scanner contract, which scopes to `registry.SCANNERS`). Drop-zone intake,
  `substantive` maintained on ingest, `run.py ingest` / `intake`, and
  `deploy/push-exports.ps1` + a systemd `.path` watcher for auto-ingest.
  **The vault now lives and updates ON the knight** — the DB is no longer scp'd
  as a snapshot.

**The gate:** `verify.py` registers **5 auditors + 19 testers**, all hermetic,
enforced by the pre-commit hook. (19 is the count in `verify.py`'s `TESTERS` list
— if you change it, change this line. `auditor_doc_claims` now checks exactly this
claim against the code, so a stale number here fails the gate.)

## Bear in mind

- **Only the personal estate deposits.** The work laptop isn't set up, so the
  knight holds `personal/` only and `work/` is empty. Reports cover one estate.
- **Fresh chat lands unlinked.** `relink.py` (embeddings) is a separate pass, so
  `drift` / `project_trail` see new threads before they're tied to projects.

## Next steps (all optional, none blocking)

1. **Fold `relink` into ingest** — the sharpest edge. A relink stage after
   normalize, behind the embeddings dep, closes the unlinked-threads window.
   Highest-value follow-up.
2. **Work-laptop producer setup** — add its hostname to `local.json` (role
   `producer`, `estate: work`, `roots`, `push_target`), first `deposit --push`.
   The knight then holds both estates and reports go walled-but-complete.
3. **Nightly `consume` timer** on the knight (cron/systemd) — playbook §6.
4. **Low-risk hardening** the audit flagged:
   - `estate_diff` where `curr` has no `git_summary`
   - intake same-second archive collision
   - deposit/consume subprocess paths untested end to end
5. **Complete the personal Gemini share-URL scrapes** and run the pipeline (now
   runs on the knight directly).

## Ground truth

- **Knight:** vault `/home/l5gn/vault/chronicler.db`; deposits
  `/home/l5gn/vault/estates/{personal,work}/`; per-estate `reports/`; chat drop
  zone `/home/l5gn/vault/chat_threads/zip_downloads/`.
- **Deploy:** push-to-deploy bare-repo hook (playbook §4b) → `git push knight main`.
- **Config:** `config/machines.json` is a committed **template only**; real
  per-machine config in git-ignored `config/local.json`, keyed by hostname,
  shipped by scp.
- **Gate:** `python verify.py` → `verify: GREEN`. Never commit red.

## Keeping this file honest

This doc is the one most likely to rot, because it's the only one that makes
claims with numbers in them. Rule of thumb: **a session that changes status ends
by editing this file.** If you're reading it cold, spend thirty seconds checking
the tester count and the git log against the claims above before trusting it —
that check is what caught the last drift.
