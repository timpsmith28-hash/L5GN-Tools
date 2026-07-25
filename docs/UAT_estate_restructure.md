# UAT walk-sheet — estate restructure

Pair: `docs/COWORK_BRIEF_estate_restructure.md` → `docs/COWORK_REPORT_estate_restructure.md`.
Gate: `python verify.py` **GREEN**, 6 auditors + **37** testers (frozen). **Nothing
deleted, nothing committed.** Status: **partially executed** — 5 of 9 estate repos
moved, 4 locked, assets deferred to Tim. Mark each **ready to walk**, never "passed".

## Done this session

- [ ] **0.** `estate_fingerprint.py` captured every repo before any move; no two share a
  `root_commit_sha`; L5GN-Castle root `832863248d5c` (remote `l5gn-mesh-vertex-3_v0`).
- [ ] **1.** Disposition table verified against real contents; `server-hub-iso`
  reclassified vendor (Tim's ruling); `PROJECTS_REVIEW.md` promoted to
  `docs/investigation/2026-07-10_projects-review.md`.
- [ ] **2a.** `GitHub\L5GN\` created; 5 repos moved (L5GN-Archive, L5GN-Armory,
  L5GN-Armory_v2, L5GN_Armory_v4, L5GN_Managed_Workspace); each moved git repo's
  `rev-parse HEAD` matches its pre-move value.

## Blocked / handed to Tim

- [ ] **2b.** Move the 4 locked repos (L5GN-Castle, CID, L5GN-Crystal-Spire,
  mesh-vertex-3_prod) after closing the daemon / containers / editors that hold them;
  verify each HEAD against the fingerprint. *(Ask me to retry once freed.)*
- [ ] **V.** Move vendor assets to `vendors\` — **not** `all-MiniLM-L6-v2` until
  `CITADEL_MINILM_PATH` is updated (CID dependency).
- [ ] **S.** Secure `l5gn.com.key.txt` / `.pem.txt` in `L5GN-server-hub-iso`, then move
  it to `vendors\`.
- [ ] **Sc.** Move `test_folder`, `L5GN-Crystal-Spire.zip` to `scratch\`.

## After the estate is whole (do NOT do earlier)

- [ ] **4-cfg.** `config/local.json` `LucasGoonPC.roots` → `…/GitHub/L5GN`; do this only
  once all 9 repos are in `L5GN\`, or the scan drops the unmoved ones.
- [ ] **5.** `run.py build` shows the same project list, all scope `l5gn`, no
  vendor/scratch entries; `run.py deposit` staged only (not pushed).
- [ ] **3.** Tim states the knight/Castle topology before any backup is planned.
- [ ] **Struct.** `GitHub\` ends with `L5GN\`, `L5GN-Tools` (until moved last),
  `.obsidian`; Obsidian opens and cross-repo search works; moved repos open in the IDE
  with full history.

---
*Ready-to-walk sheet. The 4 locked moves + asset moves are Tim's. Results log needs a
uat stamp (`docs/README.md` §3).*
