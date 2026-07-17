# L5GN-Tools — Handoff

Prime a fresh thread with this. It's the state of the world + how to continue.

## TL;DR

L5GN-Tools is complete and live: a small mesh that reconciles **what the code did**
(git estate) against **what was discussed** (chat vault), assembled on a headless
consumer. All 16 planned tasks are done, the three-machine loop runs end-to-end,
and the gate is green (4 auditors + 18 hermetic testers, enforced by a pre-commit
hook). Nothing is half-built; what remains is optional polish.

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

## Open threads (all optional, none blocking)

1. **Fold `relink` into ingest** — the sharpest edge: fresh chat lands *unlinked*,
   so `drift`/`project_trail` see it before it's tied to projects. A relink stage
   (behind the embeddings dep) after normalize would close it. Highest-value follow-up.
2. **Work-laptop producer setup** — add its hostname to `local.json` (role work,
   roots, push_target) and do its first `deposit --push`; then reports cover both estates.
3. **Nightly `consume` timer** on the knight (cron/systemd) — optional automation.
4. **Low-risk hardening** the audit flagged: `estate_diff` where `curr` has no
   `git_summary`; intake same-second archive collision; deposit/consume subprocess
   paths untested end-to-end.
5. **Manual chat capture is a backup only** — the close-out prompt is token-expensive
   and lossy on long threads (see `CLOSEOUT_PROMPT.md`); admin-gated work-Claude
   stays a real gap.

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
