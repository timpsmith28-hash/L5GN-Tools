<!-- uat: commit=071e77b dirty=true host=10280L walked=2026-07-28 -->
<!-- dirty=true is not sloppiness: the walk began on a clean 071e77b and
     modified chronicler/pipeline/local_transcripts.py mid-walk, because Part 4
     found a defect that had to be fixed before Parts 4-6 could run at all. That
     fix has since landed on the gaming rig as a1f9169 with its testers. Recording
     the walk as clean would misrepresent which tree the later parts ran against.
     gate= omitted per the disposition in docs/UAT_solo_playbook_results.md. -->

# Results log — the work rig, solo (`10280L`, walked 2026-07-28)

Partner to `docs/UAT_work_rig_solo.md`. First walk of `SOLO_PLAYBOOK.md`
§10/§11, and the first time any of this ran on the work estate.

Evidence, not acceptance beyond what is stated. Machine: `10280L`, Windows user
`tim.smith`, repo at `C:\Users\tim.smith\Github\L5GN-Tools`, throwaway vault at
`C:\Users\tim.smith\Documents\chronicler_dev`. Loopback only throughout; nothing
deposited off the machine.

---

## Headline

**Mostly successful, and the failure it found was worth the trip.** The estate
now has work-account chat threads in a vault for the first time — 91 sessions,
1,982 messages, ingested from a store that has no export and never will.

One defect blocked the middle of the walk and was fixed in place: a Cowork
session path exceeded Windows' 260-character `MAX_PATH`, and `Path.is_dir()`
swallowed the resulting `OSError` and returned `False`, so both stores reported
**zero sessions and looked simply empty**. Same "confident zero" class as the
MSIX finding on the gaming rig, reached by a different route. Details in the
commit message for `a1f9169`.

---

## Part 0 — prerequisites

- [x] **0.1** Solo setup performed on `10280L` today: venv, `pip install -e .`
  and `.[review]`, `git config core.hooksPath .githooks`, throwaway
  `chronicler_dev` created, config entry extended.
- [x] **0.2** Cowork package folder: **`Claude_pzs8sxrjxfjjc`** — the same
  identifier as the gaming rig. Full root:
  `C:\Users\tim.smith\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\local-agent-mode-sessions\6f82d751-d365-4553-84c0-cf75ec3144fa\180fc069-95dc-48a5-9418-dc0b2ecbd38b`
- [x] **0.3** CLI store confirmed under `C:\Users\tim.smith\.claude\projects`.
  **Finding:** the shipped `config/local.json` initially pointed at
  `C:/Users/timps/.claude/projects` — the *gaming rig's* path — and the census
  correctly reported `status: configured but not found on disk` rather than
  guessing. The honest-reporting behaviour worked; the shipped config was wrong.
  Corrected on the machine.
- [x] **0.4** Work-rig-local throwaway `CHRONICLER_HOME`, not shared with any
  other rig.

## Part 1 — solo build stands up

- [x] **1.1** venv + both installs.
- [x] **1.2** `python verify.py` → **GREEN on `10280L`**, all auditors and
  testers. No Windows-only failures on this machine this time.
- [x] **1.3** Gate run in a shell without `CHRONICLER_HOME` /
  `CHRONICLER_REGISTRY_PATH` set.
- [x] **1.4** `run.py config` → `host=10280L`, `estate=work`.

## Part 2 — estate-scoped visibility (0025)

The round that could only be walked here. **All passed.**

- [x] **2.1 Loopback enforced structurally.** Verbatim:

  > `review: refusing to bind '0.0.0.0' -- this machine's declared estate is
  > 'work', and DECISIONS 0025 requires a work-estate surface to bind loopback
  > only (127.0.0.1 / ::1 / localhost). Run with --host 127.0.0.1.`

- [x] **2.2 Loopback serves.** `--host 127.0.0.1` started and bound, printing
  `review: estate='work' -- rendering only that estate's threads (DECISIONS 0025)`.
- [x] **2.4 The wall from the other side.** No personal-account data anywhere;
  the estate clause resolved to the work allowlist, so absence is the filter's
  doing rather than an empty coincidence.
- [ ] **2.3 Undeclared-estate refusal** — **not walked.** Blanking the estate
  was skipped in the interest of time. Covered hermetically
  (`tester_review`'s `both`/absent/junk case); still worth 30 seconds on a
  future visit.

## Part 3 — the MCF-only registry

- [x] **3.1 / 3.2** `build_registry.py --estate work` produced a scoped registry
  at `C:\Users\tim.smith\Documents\chronicler_dev\project_registry.json`.
- [x] **3.4** **18 link-target ids** — reported by `run.py review` at startup.
  The disclosure property holds: the work box carries MCF projects only, not the
  full curated registry.
- [x] **3.3** `CHRONICLER_REGISTRY_PATH` set explicitly.

## Part 4 — local transcript intake, Phase 4

- [x] **4.1 Census** — and this is where the walk stopped. Both stores reported
  `sessions: 0`, `messages: 0`, `parse failures: none`, **and no access-error
  line**. That last detail is what killed the permission-wall theory: the walk
  completed with zero `OSError`s, so nothing was blocking it — it genuinely
  found nothing. The cause was structural: a path of 441 characters before the
  filename, the encoded-cwd segment folding the whole path back into itself.
  Fixed with an extended-length (`\\?\`) prefix.
  - **Second finding, from the same fix.** The first attempt applied the guard in
    `census()` only. `ingest_local_transcripts.py` builds its own root
    independently, so it kept reporting 4 sessions (the CLI store alone) while
    the census correctly reported 49 cowork sessions / 1,957 messages. Moving the
    guard onto the discovery functions themselves closed it — a caller-side fix
    invites exactly one caller forgetting.
- [x] **4.2** Dry-run wrote nothing.
- [x] **4.3** `--apply` → **`account 'claude-local-work'`**, **91 sessions
  (0 exact-linked), 1,982 messages.** The label came from the machine's declared
  estate, never from content.
- [x] **4.4 Idempotency** — second `--apply` reported **identical** counts
  (91 / 1,982).
- [x] **4.6** 0 exact-linked, as predicted: CLI sessions on this machine ran in
  repos the work registry does not yet name.
- [ ] **4.5** Source-file mtimes not explicitly captured before/after. The code
  is read-only by construction and hermetically asserted; not evidenced here.

## Part 5 — the deck against real MCF data

- [x] **5.2** `relink.py --apply` → **62 thread(s) changed / queued**; the deck
  served on loopback showing real MCF repos: `activitystatements-repo`,
  `wizforgeanalytics-repo`, `validationautomation-repo`, `solconfig-repo`,
  `tsstoassets-repo`, `churnlevelindictor-repo`.
- [x] **5.4** Batch ruling exercised — `POST /api/rule/batch` 200, followed by
  `GET /api/queue/projects` and further project batches.
- [ ] **5.1** The dry-run decision table was produced
  (`data\relink_work_dryrun.txt`) but its auto-link / suggestion / ambiguous /
  no-op counts were **not transcribed into the log**. Recoverable from the file
  on that machine if wanted.
- [ ] **5.3 The judgement call** — whether MCF's cleaner project definitions make
  the batches read as coherent topics — **not recorded**. This is the item the
  whole trip was for and it is the one with no deterministic check, so it needs
  Tim's own words rather than an inference from the server log.
- [ ] **5.5** Rival case on MCF data — not reported.

## Part 6 — the knight-gating backfill item

- [ ] **6.1 / 6.2 — not walked.** The `backfill_candidate_project` output in the
  session is the hermetic tester's fixture (`ghost-project`), not a run against
  the work vault. **Deck UAT item 1.2 therefore remains open**: the note-parsing
  recovery has still never met a real note, and it is still the item gating the
  knight's ~500 live rows. The work vault now has 62 queued rows and could
  answer it in two commands.

## Also observed

`run.py consume` on this machine: `(vault: no_vault)`,
`[work] ingest=ingested verified=True snap=estate-2026-07-28.json |
estate_diff=insufficient_history | drift=needs_inputs` — expected on a box with
one snapshot and no shared vault; recorded, not chased.

---

## Disposition

**0025 is walked and holds.** Estate-scoped visibility, the loopback refusal and
the MCF-scoped registry all did what the decision said they would, on the machine
the decision was written for. That pair can close.

**Transcript intake Phase 4 is walked**, with the MAX_PATH defect found, fixed
and now tester-pinned at `a1f9169`.

**The deck's own acceptance is only half recorded.** It served real MCF data and
took rulings, but 5.3 — does the grouping actually sharpen the thinking on a
well-defined dataset — is unanswered in writing, and it is the question the deck
exists to answer. Worth adding in Tim's own words before the deck pair closes.

Still open after this walk: 2.3, 4.5, 5.1, 5.3, 5.5, and Part 6 (deck 1.2).
