> **ARCHIVED** 2026-07-28 · completed pair · brief + report + walk-sheet + stamped results
> Superseded by: nothing — `docs/SOLO_PLAYBOOK.md` is the living output and stays in core.
> Accurate history: the docs-first method, and the three dispositions it produced (CHRONICLER_HOME
> and CHRONICLER_REGISTRY_PATH resolved as docs-only, schema_frozen.sql target routing as the one
> code fix), are the real record of why a single code change landed from a full walk.
> Stop trusting: §10's `[WORK]` profile is described throughout as "written, not walked". That is
> no longer true — it was walked on 10280L 2026-07-28; see `UAT_work_rig_solo_results.md`, which
> also corrects the shipped `config/local.json` CLI-store path (it carried the gaming rig's
> `C:/Users/timps/.claude`). The results log's `gate=` field was bumped twice to keep the gate
> green before being dropped; the in-file comment explains why. Do not reintroduce `gate=`.

# Cowork report — the solo playbook: one machine plays the whole mesh

**Pair:** `docs/COWORK_BRIEF_solo_playbook.md`. Session 2026-07-27, gaming rig
(`LucasGoonPC`), Cowork remote + Tim at the keyboard (docs-first: the walk was
executed by Tim, commands and interpretation by Cowork — see the brief's
"Approach ruling").
**Gate:** `python verify.py` → 6 auditors, 43 testers, GREEN (41 testers
before this round; +1 for the `.venv` rebuild baseline, +1 for the one code
change below — `tester_finalize_db`, 3 assertions).
**Code changes this round: one.** `chronicler/pipeline/finalize_db.py` —
`schema_frozen.sql` no longer silently writes to the repo's tracked copy
when `CHRONICLER_HOME` is a non-default (dev throwaway or real deploy)
location; see sharp edge 8. Every other finding resolved as a documentation
fix. Per the brief's own framing, this is the honest shape of an evidenced
Task C: not zero, not speculative — exactly the one change the walk actually
forced, with a tester and a named observed failure.

---

## Done vs pending

| Item | State | Note |
|---|---|---|
| Task A — walk the loop on the rig | **done** | full transcript in `UAT_solo_playbook_results.md`; every command real, every output pasted back |
| Hypothesis (outbox-as-`estates_dir`) | **confirmed yes** | `consume` read the box's own staged deposit with no push, no second host, no code change |
| Task B — `docs/SOLO_PLAYBOOK.md` | **done** | written from the transcript, not from the brief's speculation |
| Task C — code changes | **one, by evidence** | three real gaps found; two resolved as docs (CHRONICLER_HOME, CHRONICLER_REGISTRY_PATH — Tim's explicit ruling both times); one resolved as code (schema_frozen.sql target routing — Tim's explicit ruling, higher stakes: risk of silently corrupting a tracked file) |
| Task D — `[WORK]` profile | **written, not walked** | no work-laptop access this session; ready-to-walk sheet in `SOLO_PLAYBOOK.md` §10 |
| UAT | **ready to walk** | see below — marked ready, not passed, per the brief's instruction |

---

## The walk, in order

1. **Rig confirm.** Commit `5e5fee2`, host `LucasGoonPC`. `.venv` was found
   broken (`Activate.ps1` missing, `python.exe` absent from `Scripts\`,
   silently falling back to Windows Store Python). Rebuilt from scratch:
   `pip install -e .` + `.[chronicler]` + `.[viewer]`. `verify.py` GREEN
   before and after (6 auditors, 41 testers) — the stdlib-only core passed
   even against Store Python, but `ingest` would have failed on the pyyaml
   import had this gone unnoticed.
2. **Throwaway `CHRONICLER_HOME`** created at
   `C:\Users\timps\Documents\chronicler_dev\`. `config/local.json`'s
   existing `LucasGoonPC` entry extended in place with `vault`/
   `estates_dir`/`chronicler_home`, `estates_dir` pointed at this box's own
   `data\outbox` — the hypothesis under test.
3. **`census` → `build` → `deposit` (stage only) → `consume`.** All four ran
   clean. `census` confirmed role-only routing (producer domain, no
   consumer-domain check — expected, not a bug). `consume` confirmed the
   hypothesis directly: swept `data\outbox`, found `personal`,
   `manifest_verified: True`, no push, no second host, no code change.
4. **`ingest`.** Real Claude export (`data-e9e581a0-…-batch-0000.zip`,
   25/07/2026) and Gemini takeout (`takeout-20260719T101209Z-1-001.zip`,
   19/07/2026) copied into the throwaway intake drop. Classified correctly,
   pipeline ran 6/9 stages, real numbers: +39 Claude threads, +7033 Gemini
   activity rows, 1101 threads rendered.
5. **`finalize_db.py --apply` — sharp edge 1, confirmed directly, not just
   cited from the existing docs.** Ran `consume` *before* finalizing on
   purpose to reproduce the exact failure: `vault: schema_mismatch`,
   `drift=needs_inputs`, no cause named. `finalize_db.py --apply` fixed it;
   `consume` re-run clean (`vault: ok`, real drift computed).
6. **The registry — two real findings, both new this round.**
   - **Finding A (sharp edge 6):** `finalize_db.py --apply`, run bare, opened
     the wrong DB (`chronicler\chronicler.db` inside the repo, not the
     throwaway home) and failed with `no such table: threads` — a real error
     that doesn't name the actual cause (`CHRONICLER_HOME` unset in that
     shell). Root cause: `run.py`'s subcommands set `CHRONICLER_HOME` for
     their pipeline *subprocess* only (`_chronicler_env()`); a direct
     `python chronicler\pipeline\X.py` call is a fresh process with no such
     env. Every pipeline script the existing playbooks tell you to run
     directly has this same implicit prerequisite, undocumented as a
     precondition (only reactively, for one script, in
     `KNIGHT_PLAYBOOK.md`'s troubleshooting table).
   - **Finding B (sharp edge 7, the most important finding of the round):**
     with `CHRONICLER_HOME` set but `CHRONICLER_REGISTRY_PATH` unset,
     `build_registry.py --report-aliases` declared it would write to
     `C:\Users\timps\L5GN\.intel_sync\project_registry.json` — Tim's **real,
     pre-existing curated registry**, entirely outside the throwaway
     boundary. Root cause: `resolve_registry_path()` derives the registry
     location via `CHRONICLER_ROOT.parent.parent` — a fixed two-levels-up
     hop from `CHRONICLER_HOME`, assuming the real folder depth
     (`…\GitHub\L5GN\Chronicler`). A throwaway home at a different depth
     doesn't error or land empty; it silently found a real file. Because the
     step run was `--report-aliases` (dry-run-only), nothing was actually
     written — but the walk-sheet's next step (`build_registry.py` with no
     flags) **does** write, and would have written into that real file had
     the env var not been set first. Fixed by setting
     `$env:CHRONICLER_REGISTRY_PATH` explicitly before writing — confirmed
     the write target then landed correctly inside the throwaway home, with
     the curated *content* (aliases) unchanged, because that's read from a
     separate, legitimately shared authoring source.
   - **Disposition, Tim's explicit ruling both times: docs-only, not code.**
     Both are now stated as required prerequisites in
     `SOLO_PLAYBOOK.md` §5.7/§8 sharp edges 6–7, not patched in `db.py`. A
     code-level fix (clearer error naming the cause; a warning when the
     derived registry path resolves outside the configured
     `CHRONICLER_HOME`) was considered for each and explicitly deferred —
     not forced once the documentation closes the gap.
7. **`build_inventory.py` / `build_activity.py`.** First attempt (right
   after the dry-run-only registry step) correctly failed with `registry
   missing: … (run build_registry.py first)` — confirming dry-run truly
   writes nothing. After the real (non-dry-run) `build_registry.py` write:
   both ran clean, 8 built, 18 concept projects, 31 `MISSING` (other-
   machine/MCF projects genuinely absent from this box's own deposit).
8. **`xref_filenames.py` / `extract_path_mentions.py` (dry-run).** Both
   clean: 1987 filename-xref rows / 304 threads; 270 path-mention rows / 146
   threads. Neither wrote (confirmed by their own "nothing written" line).
9. **`relink.py --out … ` (dry-run only, no `--apply`).** 1100 threads
   scanned: 53 auto-link, 364 suggestion, 139 ambiguous, 0 downgrade, 544
   no-op. `[DRY RUN] Nothing written.` confirmed.
10. **`serve`.** DECISIONS 0013 confirmed directly, not just cited: the
    served page's own banner states *"Snapshot, not live … re-launch `run.py
    serve` to refresh."* Browsed at `http://192.168.0.12:8001/`, 15,330 rows
    across 11 tables.
11. **`git status` — sharp edge 8, the code-change finding.** Confirmed
    `chronicler/pipeline/schema_frozen.sql` (a **tracked** file) modified —
    52 deletions, 81 insertions — after step 5's `finalize_db.py --apply`
    ran against the throwaway vault. `finalize_db.py` dumps its frozen
    schema to a path fixed relative to its own script location
    (`Path(__file__).parent / "schema_frozen.sql"`), never respecting
    `CHRONICLER_HOME`. Reverted immediately (`git restore`); confirmed clean
    before touching anything else. This one was ruled a code fix, not
    docs-only — see "Task C" below.

Full command-by-command transcript: `docs/UAT_solo_playbook_results.md`.

---

## seed_suppress, confirmed still holding

Not the focus of this round, but observed directly in the
`build_registry.py --report-aliases` output: `l5gn-castle-repo`'s alias list
shows only `'L5GN-Castle'`, no bare `'Castle'` — the `b7c2390` fix from the
golden close-out (`COWORK_REPORT_apply_alignment.md`) is confirmed live and
unregressed.

---

## Task C — code changes: one, by evidence

Per the brief's explicit framing (§ "Approach ruling"), code changes only
where the walk proves them necessary — this walk proved three real gaps,
disposed of individually rather than defaulted:

- **Sharp edge 6 (`CHRONICLER_HOME`) — docs-only**, Tim's explicit ruling.
- **Sharp edge 7 (`CHRONICLER_REGISTRY_PATH`) — docs-only**, Tim's explicit
  ruling.
- **Sharp edge 8 (`schema_frozen.sql` target) — code fix**, Tim's explicit
  ruling, the one case where a documentation note couldn't close the gap: a
  `git add -A` or IDE auto-stage doesn't read playbooks, and the risk was a
  tracked file silently carrying dev-vault noise into a real commit.
  `finalize_db.frozen_schema_target()` now only writes the repo's tracked
  copy when `CHRONICLER_HOME` is the true default (unset); any explicit
  override writes next to that vault instead, with `--freeze-repo-schema` as
  the deliberate escape hatch. Tester: `tests/tester_finalize_db.py` (3
  assertions, registered in `verify.py`). Gate re-confirmed GREEN after the
  change: 6 auditors, 43 testers.

None of these three were authorised or added speculatively — each is traced
to a specific, reproduced failure in the walk transcript. The three
"anticipated candidates" the brief listed in advance (census role-routing on
a genuinely-both box; a local-staging path if the hypothesis failed; a
clearer error when `estates_dir` is unset) were all explicitly **not**
forced: census role-routing behaved exactly as documented (producer-domain-
only, stated as expected in sharp edge 6, not a defect); the hypothesis
held, so no local-staging path was needed; and `estates_dir` was never unset
in this walk. The one change that *did* land was not on that anticipated
list at all — it was found live, not predicted.

**A note on `auditor_doc_claims` fallout.** Adding the new tester bumped the
live gate count from 42 to 43 testers, which turned two pre-existing docs
(`docs/UAT_repo_tier_producers.md`, `docs/UAT_repo_tier_producers_results.md`
— both from an unrelated prior round, quoting a raw gate-count claim of six
auditors and forty-two testers with no `gate-frozen` marker) red under
`auditor_doc_claims`.
Fixed by adding `<!-- gate-frozen: commit=22df436 -->` to both (the commit
that actually finalized their content) — per the brief's own Reporting
instruction ("If any new doc quotes a gate count, give it the gate-frozen
marker at the time of writing"), and per the auditor's own documented
purpose (a frozen build-time count is history, not a live claim). Not a
finding of this round's brief — an unrelated pre-existing gap this round's
tester count happened to surface.

**A second live finding while re-verifying on the rig.** Running `python
verify.py` in the *same* PowerShell window where `$env:CHRONICLER_HOME` and
`$env:CHRONICLER_REGISTRY_PATH` were still set (from walking §5) failed
`tester_census` with four assertion failures, all pointing at the throwaway
`chronicler_dev` path instead of the tester's own hermetic temp directory —
a real environment leak, not a code defect: PowerShell env vars persist for
the rest of the shell session, and `tester_census` doesn't isolate against
inherited environment. Cleared both vars, re-ran, GREEN. Recorded as sharp
edge 9 in `SOLO_PLAYBOOK.md` — docs-only (a stated rule: never run
`verify.py` or commit in a shell where these were set for a dev walk).

---

## Task D — `[WORK]` profile

Written into `SOLO_PLAYBOOK.md` §10, marked "written, not walked" throughout
— no work-laptop access this session. Covers: the combined config shape
(existing `10280L` entry extended the same way as `LucasGoonPC`'s), the
namespace-guard wall discipline (DECISIONS 0010, stated as structural not
formal), the TOTP visibility gate (DECISIONS 0023), and the sharpened
registry-shipping problem (employer codenames, sharp edge 3). Every item is
explicitly a walk-sheet for Tim to execute on `10280L`, not a claim of
having been run.

---

## UAT — acceptance checks (Tim walks these)

- **`[DEV]` loop.** Following `SOLO_PLAYBOOK.md` alone on the rig, clone →
  served read surface — **ready to walk** (this session *was* that walk, but
  a second independent pass following only the finished document, not this
  report, is the actual acceptance check).
- **Honest failure.** Deliberately skipping `finalize_db.py --apply` and
  confirming the troubleshooting entry names the resulting
  `schema_mismatch` correctly — **done, during this walk** (§5 step 5 above;
  the failure was reproduced on purpose, not accidentally).
- **Isolation.** The dev vault is provably separate from anything the knight
  owns — **confirmed with two caveats surfaced and fixed**: the registry was
  not isolated until `CHRONICLER_REGISTRY_PATH` was set explicitly (sharp
  edge 7), and the frozen-schema dump was writing into a tracked repo file
  until the code fix (sharp edge 8). No push target ever pointed at the
  throwaway home; both gaps were caught before any real damage (nothing
  written outside the throwaway boundary in the registry case; the tracked
  file was reverted with `git restore` before commit in the schema case).
- **`[WORK]` profile.** Reads correctly against the laptop's real layout —
  **ready to walk**, not yet executed (Task D).
- **No silent code creep.** One code change this round, traced above to its
  exact justifying failure (sharp edge 8) with a tester
  (`tests/tester_finalize_db.py`) — satisfied by evidence, not by having
  nothing to trace.

Mark each **ready to walk**, not "passed" — per the brief's instruction, the
results log needs a uat stamp before the gate accepts the commit.

---

## Files changed

- **Docs (new):** `docs/SOLO_PLAYBOOK.md`, `docs/UAT_solo_playbook.md`
  (walk-sheet), `docs/UAT_solo_playbook_results.md` (stamped transcript),
  this report.
- **Docs (fixed, unrelated pre-existing gap surfaced by this round's tester
  count):** `docs/UAT_repo_tier_producers.md`,
  `docs/UAT_repo_tier_producers_results.md` — `gate-frozen` marker added
  (commit `22df436`).
- **Code:** `chronicler/pipeline/finalize_db.py` — `schema_frozen.sql`
  target routing (sharp edge 8).
- **Tests:** `tests/tester_finalize_db.py` (new, 3 assertions),
  `verify.py` (registered the new tester).
- **Config (rig-local, gitignored, not committed):** `config/local.json` —
  `LucasGoonPC` entry extended with `vault`/`estates_dir`/`chronicler_home`.
- **Environment (rig-local, not committed):** `.venv` rebuilt from scratch
  (was broken); `chronicler_dev/` throwaway home created under
  `C:\Users\timps\Documents\`.

`git status` confirmed clean (only `docs/UAT_solo_playbook.md` untracked)
after `git restore chronicler/pipeline/schema_frozen.sql` reverted the
dev-vault contamination found mid-walk. Everything above needs `git add`
before commit — not yet committed as of this report.
