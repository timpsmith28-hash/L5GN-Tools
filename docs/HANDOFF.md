# L5GN-Tools — Handoff

Prime a fresh thread with this. It's the state of the world + how to continue.

## TL;DR

L5GN-Tools is complete and live: a small mesh that reconciles **what the code did**
(git estate) against **what was discussed** (chat vault), assembled on a headless
consumer. The core mesh loop runs end-to-end and the gate is green (5 auditors +
19 hermetic testers, enforced by a pre-commit hook). The infrastructure is done;
what remains is real but scoped — see `docs/DECISIONS.md` for what's been decided and
`docs/NEXT_SESSION_PLAN.md` is retired (archived as a completed plan). For *why* the
system is shaped as it is, read `docs/INTENT.md` and `docs/ARCHITECTURE.md`; for
what's changed lately, `docs/CHANGELOG.md`.

> **Honest status:** the mesh that moves data is finished; the thing it exists to
> carry — chat-to-project linkage — covers ~8% of substantive threads. That number,
> not "complete," is the real state (INTENT §2). "Done" means the plumbing; the
> payload is early.

## The system in one screen

Two subsystems, opposite guarantees, kept apart on purpose:

- **`l5gntools/` — read-only, stdlib-only scanners** (the estate inventory +
  interpret layer). Auditors prove the contract over `registry.SCANNERS`.
- **`chronicler/` — the ingest pipeline (a writer)** with its own deps
  (pyyaml, sentence-transformers). Builds/updates the vault. Deliberately outside
  the scanner contract; nothing in `l5gntools/` imports it.

The loop: producers `build` an `estate.json` and `deposit --push` it to the knight;
the knight `ingest`s chat export zips into `chronicler.db` and `consume`s the
deposits, running `estate_diff` (what was built) / `vault_reader` +
`project_trail` (what was discussed) / `drift` (the reconciliation). Full rationale
in `docs/ARCHITECTURE.md`.

## The mesh

| Machine | hostname | role | notes |
|---|---|---|---|
| Gaming rig | `LucasGoonPC` | producer, estate `personal` | pushes to knight; runs Chronicler pipeline for now |
| Work laptop | (unset) | producer, estate `work` | **not set up yet** — the last mesh gap |
| Knight | `l5gn-castle-worker` | consumer, estate `both` | Ubuntu + GPU; holds vault + both estates, walled; auto-ingests |

Key paths on the knight: vault `/home/l5gn/vault/chronicler.db`; deposits
`/home/l5gn/vault/estates/{personal,work}/`; chat drop zone
`/home/l5gn/vault/chat_threads/zip_downloads/`. Transport is scp/rsync over the
`l5gn-castle` ssh alias. Auto-ingest is a systemd `.path` unit watching for a
trigger file dropped by `deploy/push-exports.ps1`.

## Commands

```
run.py config | list | build | <tool> --target NAME | --all      # producer
run.py deposit --push                                             # producer -> knight
run.py consume                                                    # knight: interpret
run.py ingest [--skip-intake] | intake [--dry-run]               # knight: chat -> vault (venv Python)
python verify.py                                                  # the gate
```

## Conventions & contracts

- **Config:** `machines.json` is a committed template; real per-machine config in
  git-ignored `config/local.json` (keyed by hostname), shipped by scp. Docker-style.
- **Wall:** estates separated by path (`personal/` vs `work/`), a producer can only
  deposit its own namespace; chat separated by the `account` field, never merged.
- **Vault:** frozen at `user_version = 1`; readers open `mode=ro` and refuse a
  mismatched version; unlinked = `project_link IS NULL`; `substantive` = ≥4 msgs.
- **Deposit:** `{estate.json, latest snapshot, sha256 manifest}` per namespace.
- **The gate is the door:** never commit red; the pre-commit hook runs `verify.py`.

## Where everything is documented

- `README.md` — front-door overview + tool list.
- `docs/ARCHITECTURE.md` — design rationale, boundaries, decisions, trade-offs.
- `docs/KNIGHT_PLAYBOOK.md` — deploy + operator guide (install, push-to-deploy, ingest).
- `chronicler/README.md` — ingest subsystem + drop zone; `CLOSEOUT_PROMPT.md` for manual capture.
- `deploy/README.md` — auto-delivery (push script + systemd auto-ingest).

## Open threads

Status of these lives in `docs/DECISIONS.md`; this is a pointer list, not the source
of truth. Build round 1 (2026-07-18) landed the Datasette read surface, off-box
backup, the doc-claims auditor, the scrape stage, and **folded `relink` into the
pipeline** — so the old "relink is the sharpest edge" item is done. Remaining:

1. **Knight-side confirmation for round 1** — install chromium on the knight
   (`playwright install chromium && playwright install-deps`; confirmed *absent*
   2026-07-18), confirm `project_registry.json` resolves where `relink` expects, and
   run the first scrape+ingest so the backup pre-flight and relink stage exercise live.
2. **The DB write endpoint** (DECISIONS 0007 stage 2) — the narrow Tailscale-bound
   review surface for the ~19 pending rulings. Its existence is the precondition for
   removing sync-back (DECISIONS 0008).
3. **Work-laptop producer setup** — add its hostname to `local.json` (role work,
   roots, push_target) and do its first `deposit --push`; then reports cover both
   estates and the wall gets exercised for the first time.
4. **Nightly `consume` timer** on the knight (cron/systemd) — optional automation.
5. **Low-risk hardening** the audit flagged: `estate_diff` where `curr` has no
   `git_summary`; intake same-second archive collision; deposit/consume subprocess
   paths untested end-to-end.
6. **Manual chat capture is a backup only** — the close-out prompt is token-expensive
   and lossy on long threads (see `CLOSEOUT_PROMPT.md`); admin-gated work-Claude
   stays a real gap.
7. **Deferred, separate toolset:** a self-hosted git-backed notes vault (DECISIONS
   0009) — not part of Chronicler, revisit as its own thread.

## Next design topic (seed): shard planning to a chat thread

Goal under debate: do design/planning from phone or desktop in a normal chat
thread (free-form, mobile, no session-budget pressure), while the *building* stays
in the tooled environment (Cowork/Code, repo + mesh access). Sync the two by
refreshing the chat's project from these `.md` docs periodically.

Questions to work through in the new thread:
- **Split of labour:** what belongs in chat (design, decisions, capture, triage)
  vs. tooled sessions (code, tests, deploy, anything touching the repo/mesh)?
- **Sync mechanism & cadence:** which `.md`s are the source of truth the chat
  project reloads (ARCHITECTURE + this HANDOFF + NEXT_SESSION_PLAN?), how often,
  and who updates them — does a tooled session end by writing decisions back into
  these docs so the chat thread re-primes cleanly?
- **Drift risk:** how to avoid the chat thread and the repo diverging (the same
  "talked-not-built" problem this toolkit exists to catch, applied to itself).
- **Capture loop:** chat-thread decisions -> a short `.md` -> into the repo on the
  next tooled session, so nothing agreed on mobile gets lost.

Handy meta-note: this is exactly the built-vs-discussed reconciliation the toolkit
does — you'd be dogfooding `drift` on your own workflow.
