# Cowork brief — apply alignment: the golden moment (chats linked to projects & programs)

**Origin:** design thread, 2026-07-25. This is the brief that reaches the **Golden
UAT point** — a fully-synced mesh with chat threads indexed and aligned to their
projects and programs. Everything to date has *prepared* this; this brief *lands*
it. **Work chats are the known exception** — no full export exists, so MCF/work
threads stay unaligned for now and that is by design, not a miss.

**This is a knight operation, executed by Tim (or the UAT thread) on `l5gn-castle`,
not built by a Cowork sandbox** — the sandbox has no route to the vault. A Cowork
thread may prepare the verification queries and the acceptance sheet; the walk is
on the box.

**Read first:** `RUNBOOK_knight_fresh_build.md`, `RUNBOOK_refresh_and_deposit.md`,
`WORKSHEET_registry_ratification_2026-07-25.md`, `COWORK_REPORT_intent_evidence.md`,
`docs/DECISIONS.md` 0005/0006 (backup), 0011 (reset), 0012 (tiers).

---

## Hard preconditions — refuse to `--apply` unless ALL are true

These are gates, not suggestions. If any is unmet, stop at the dry-run.

1. **Scorer fixed.** `COWORK_BRIEF_relink_scoring.md` A/B/C are landed, committed,
   and their UAT walked. The `world_graph.json` case scores ≈0.97, not 0.997, and
   no auto-link rests on a single origin. **Applying with the old scorer bakes the
   double-count into `evidence`-locked rows.**
2. **Registry ratified.** `WORKSHEET_registry_ratification_2026-07-25.md` rulings
   are applied to `config/project_registry.json` — including **CID-as-program** —
   and `build_registry.py` re-run so the live registry is the ratified one. You
   align *to* a settled registry or you re-create the identity mess.
3. **Clean identity base.** Either the knight **fresh build** is done
   (`RUNBOOK_knight_fresh_build.md` — empty `link_evidence` / `project_link`, which
   makes the 0011 reset moot and the Finding-3 re-key unnecessary), **or** the 0011
   reset + `link_evidence.project` re-key have been run against the existing DB.
   Fresh build is the recommended path.
4. **Crystal Spire `first_seen`** is set in `config/project_registry.json` (the
   history reset zeroed its time-plausibility; without it every Crystal Spire
   filename hit is annihilated by `time_plausibility`).
5. **Backup taken** — `run.py backup`, verified off-box (0005/0006). Reversibility
   is what makes `--apply` safe.

State each precondition as met/unmet at the top of the results log before any
write. An unmet gate is a hard STOP, logged, not walked past.

---

## Task 0 ▸ KNIGHT — backup, and prove the two irreplaceables

Per `RUNBOOK_knight_fresh_build.md`: `run.py backup`, verified off-box; confirm the
chat exports and `scraped_gemini/*.json` + `manifest.jsonl` are on disk (the vault
is a *derived* cache — this is what lets you rebuild rather than merge). If either
input is absent, **STOP** — do not clear past it.

---

## Task 1 ▸ KNIGHT — re-derive evidence LIVE (the gotcha)

Every S4/S5 number in the reports was a **dry-run against a 4-day-old snapshot**
(`L5GN-Castle/data/Chronicler_Backup/chronicler.db`), *not* the live vault.
Re-derive against the live DB before anything is judged:

```bash
cd ~/L5GN-Tools
.venv/bin/python chronicler/pipeline/build_registry.py        # ratified registry (Precond 2)
.venv/bin/python chronicler/pipeline/build_inventory.py       # census -> file_inventory
.venv/bin/python chronicler/pipeline/xref_filenames.py        # S4 -> link_evidence
.venv/bin/python chronicler/pipeline/extract_path_mentions.py # S5 -> link_evidence
```

Confirm `link_evidence` is populated from **this** run and that `link_evidence.project`
values are **registry ids**, not folder names (the Finding-3 check — a fresh build
guarantees it; a reset-only path must verify it here).

---

## Task 2 ▸ KNIGHT — relink DRY-RUN is the GO/NO-GO gate

The dry-run decision table is the acceptance artifact — the step that got skipped
the pass that ran `--apply` first. It is **not** optional.

```bash
.venv/bin/python chronicler/pipeline/relink.py --out data/relink_dryrun.txt
```

Read the table. GO requires all of:

- **Auto-link count is sane** and each rests on **≥ 2 independent origins** (Task B
  of the scoring brief) — spot-check the top 10.
- No auto-link is the old 0.997 single-sentence pattern.
- Ambiguous/suggestion volume is reviewable, not a flood (the collapse/roll-up
  rules holding).
- Breadcrumbs read correctly — a match on `smelt-gateway` shows as its parent
  project/program, CID rolls up to the **program**.

If it doesn't hold, **STOP at dry-run** and hand the table back. NO-GO is a valid,
expected outcome and costs nothing.

---

## Task 3 ▸ KNIGHT — apply, only on GO

```bash
.venv/bin/python chronicler/pipeline/relink.py --apply
```

Single write transaction; winners become `evidence` (idempotent — a re-run skips
them). Manual/exact/evidence rows are never touched.

---

## Task 4 ▸ KNIGHT — verify the alignment landed clean

Run against the live vault and record the output in the results log:

```sql
-- one identity scheme only: every linked project_link resolves to a registry id
SELECT project_link, COUNT(*) FROM threads
WHERE project_link IS NOT NULL
  AND project_link NOT IN (SELECT project_id FROM projects) GROUP BY 1;   -- expect empty

-- no legacy title-case / folder-name rows resurrected (0011)
SELECT project_id, name FROM projects
WHERE project_id GLOB '*[A-Z ]*' AND source_system_id IS NULL;            -- expect empty

-- thread counts per project look plausible, no project split across two ids
SELECT p.name, COUNT(t.thread_id) threads FROM projects p
LEFT JOIN threads t ON t.project_link = p.project_id
GROUP BY 1 ORDER BY threads DESC;
```

Then regenerate the read surface (`run.py build`; `run.py serve` / `report.html`)
and confirm threads appear under their projects and programs — the browsable proof
of the golden state.

---

## Task 5 ▸ KNIGHT — deposit / consume so the aligned vault is the source of truth

Close the loop per `RUNBOOK_refresh_and_deposit.md`: the knight's now-aligned vault
is the mesh's truth; confirm both estates consumed `verified=True` and the wall held
(MCF under `estates/work/`, never merged).

---

## Stop conditions & rollback

- Any precondition unmet → stop before Task 3.
- Dry-run NO-GO → stop, hand back the table, do not apply.
- Anything unexpected post-apply → restore from the Task 0 backup (that is why it
  exists) and re-run the dry-run.

Nothing here edits repo code — it applies *derived* state to the vault, all of it
reproducible from the backup and the two irreplaceable inputs.

---

## UAT — acceptance checks (Tim walks these)

- **Golden:** open the read surface; personal-estate chat threads appear aligned to
  their projects and programs, breadcrumbs correct, CID threads rolling to the CID
  **program**.
- **Provenance:** a spot-check of auto-linked threads — is each plausibly *about*
  the project it linked to (the S4 judgment check from `UAT_intent_evidence` C.1)?
- **No over-count:** no auto-link rests on a single sentence / single origin.
- **Identity:** the Task 4 queries return the expected empties — one scheme, no
  resurrected legacy rows, no split projects.
- **Wall:** work/MCF threads are **not** aligned (expected — no export) and the
  personal/work deposit wall held.

Mark each **ready to walk**, never "passed". The results log **must carry a uat
stamp** (`commit`, `host=l5gn-castle`, `walked`, and `gate=` if observed) or the
gate refuses the commit — that is `auditor_uat_stamp` doing its job on the highest-
stakes acceptance in the system.

---

## Reporting

Write the report as `docs/COWORK_REPORT_apply_alignment.md`, the walk-sheet as
`docs/UAT_apply_alignment.md`, and the stamped results as
`docs/UAT_apply_alignment_results.md`. Record: preconditions met/unmet, the live
S4/S5 counts, the dry-run GO/NO-GO decision and why, the applied counts, the Task 4
query outputs, and the UAT walk-list. Nothing commits until Tim reviews — and this
one closes a lot of open pairs, so its archiving sweep is the natural follow-up.
