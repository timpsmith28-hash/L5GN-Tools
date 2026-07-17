# L5GN-Tools — Status & Next Steps

## Where we are (proven this session)

The three-machine mesh works **end to end**: LucasGoonPC (personal producer)
`build` → `deposit --push` (scp over the `l5gn-castle` ssh alias) → the knight
(`l5gn-castle-worker`, consumer) ingests (manifest-verified), accumulates
history, and runs the walled interpret sweep against the frozen vault. After a
fresh build+deposit, `drift` reads correctly: **4 discussed_not_present /
3 talked_not_built**. `verify.py` GREEN (13 testers) on all three machines.

**Phases 1–4 complete (#1–#13):** machine config, estate_diff, the vault
interpret layer (vault_reader / project_trail / drift), author folding, deposit
(namespaced + manifest + scp/rsync), knight ingest + consume, and the live
round-trip. Playbook: `docs/KNIGHT_PLAYBOOK.md`.

### Two things to bear in mind
- **Only the personal estate deposits so far.** Work-laptop producer isn't set up
  yet (final step) — until then the knight holds `personal/` only; `work/` is empty.
- **The knight runs a *copied* `chronicler.db` snapshot.** The Chronicler pipeline
  still runs on a rig and the DB is scp'd over. **End goal: the vault lives and
  updates ON the knight** — that's what #16 delivers.

## Next steps (reordered — Chronicler first)

1. **#16 — Assimilate Chronicler into the toolkit (NOW the priority).** Vendor the
   ingest pipeline into the repo as its own *writer* subsystem (own deps: pyyaml,
   sentence-transformers; deliberately outside the read-only scanner contract,
   which already scopes to `registry.SCANNERS`, so nothing there is threatened).
   Target end-state: the knight ingests new Claude/Gemini exports + share-scrapes,
   updates `chronicler.db` in place, and `consume` reads it live — no more scp of
   a snapshot. Likely split: (a) boundary/deps/entrypoint design, (b) vendor
   `pipeline/`, (c) a `run.py ingest` command, (d) a separate gate for ingest deps.
2. **Finish the chat-data path.** Complete the personal Gemini share-URL scrapes,
   run the pipeline; once #16 lands this runs on the knight directly.
3. **Work-laptop producer setup (final step).** Rename its `machines.json` entry to
   its hostname, set `roots` + `estate: work` + `push_target`; `deposit --push` →
   the knight gains the **work** estate; reports then cover both, walled.
4. **#15 — toolkit git-SHA version stamp** (small; cross-machine version parity).
5. **#14 — work-Claude export mitigation** (admin-gated; interim `.md` looping).
6. **Optional — schedule** nightly `consume` on the knight + periodic `deposit`
   on rigs (playbook §6).

## Ground-truth locations
- Knight: vault `/home/l5gn/vault/chronicler.db`; deposits `/home/l5gn/vault/estates/{personal,work}/`; per-estate `reports/`.
- Deploy: push-to-deploy bare-repo hook (playbook §4b) → `git push knight main`.
- Config: role/roots in `config/machines.json` (committed); paths/push_target in `config/local.json` (git-ignored).
