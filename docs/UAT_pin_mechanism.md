<!-- uat: commit=c691c1e dirty=false host=LucasGoonPC walked=YYYY-MM-DD -->

# UAT — the pin mechanism (DECISIONS 0045)

Walk against `docs/COWORK_BRIEF_pin_mechanism.md`'s acceptance checks. Mark
each `[G]`/`[W]`/`[H]` per 0031 as you go — `[G]` gate-checked by
`verify.py`, `[W]` a deterministic non-gating check, `[H]` needs your
judgement. Fill in `walked=` above with the date you actually do this.

---

- [ ] **P1. `[H]`** `python run.py pin bump config/mcf_conversation_map.tsv`
  dry-runs, prints the pin line(s) it would write, touches nothing on disk.
  *(Confirmed in the report: it printed "already matches its pin ...
  nothing to do" against the real map, since the existing hash-only pin is
  current. To see the would-write output instead of the no-op path, either
  hand-edit one byte of the map first, or point the command at a copy —
  either way, confirm nothing under `config/` changes on disk afterward.)*

- [ ] **P2. `[G]`** `--apply` writes `config/mcf_conversation_map.tsv.sha256`
  in the documented format (hash line + `# pin: ...` comment line), and
  `sha256sum -c config/mcf_conversation_map.tsv.sha256` still passes by hand
  afterward. *(Test this against a copy, not the real map — this round's
  working rule was not to regenerate the real pin, so the real file is
  still the legacy hash-only shape.)*

- [ ] **P3. `[G]`** Hand-edit one byte of `config/mcf_conversation_map.tsv`
  (or a copy wired to a copy of its pin) → `auditor_conversation_map_pin`
  fails, stating both hashes; the artefact is left exactly as you edited it
  (verify with `git diff` / a byte comparison, not just the auditor's exit
  code).

- [ ] **P4. `[G]`** Rename or move the map away (simulating a fresh checkout
  with no map on disk) → `auditor_conversation_map_pin` passes clean, no
  finding. *(This is the common case on any machine that hasn't been handed
  a copy — confirm `python verify.py` stays GREEN with the map absent.)*

- [ ] **P5. `[G]`** Hand-edit the `anchor=` field in a pin's comment line to
  a sha that doesn't exist in this repo → the auditor fails, naming the
  unresolvable anchor. *(Real map's current pin has no comment line at all,
  so this needs a pin you've bumped with `--apply` first, or a hand-written
  test pin pointed at the real map's hash.)*

- [ ] **P6. `[W]`** Outside a git checkout (or with `.git` inaccessible),
  the anchor check degrades to a skip rather than a false failure —
  matches `auditor_uat_stamp`'s carve-out. *(Easiest to confirm by reading
  `l5gntools/pin.py`'s `commit_exists_resolver` and `tester_pin.py`'s
  `git-unavailable` case rather than actually removing `.git` from a working
  checkout.)*

- [ ] **P7. `[G]`** `python verify.py` GREEN with the new auditor
  registered — 11 auditors, 77 testers. *(Already confirmed once, by the
  pre-commit hook at commit time; re-run to confirm on your own machine.)*

- [ ] **P8. `[H]`** Read `l5gntools/pin.py` cold: no import outside stdlib
  (`hashlib`, `re`, `dataclasses`, `pathlib` plus the local
  `l5gntools.common`), no path that writes to the artefact or the pin file.
  Confirm `run.py pin bump` is the only place `.write_text` is called
  against a pin.

- [ ] **P9. `[H]`** Read `docs/COWORK_REPORT_pin_mechanism.md`'s "What
  wasn't exercised" section and decide whether anything there needs a
  follow-up before this is treated as done — in particular, whether you
  want `--apply` actually run against the real map now (bumping it to the
  richer format) as part of closing this round, or left for a later,
  separate act.

- [ ] **P10. `[H]`** Confirm the two gate-frozen markers added to
  `docs/COWORK_REPORT_architecture_census.md` and
  `docs/UAT_architecture_census_results.md` (both `commit=5016eb8`) are the
  right call — i.e., that round's report and results log really were
  finished and not still being actively edited when this round froze their
  gate-count claims.

---

## Notes for the walk

- The real `config/mcf_conversation_map.tsv.sha256` was **not** modified by
  this round (working rule: verify, don't regenerate). P1–P2 above are best
  walked against a scratch copy so nothing on the real pin changes as a
  side effect of walking the sheet.
- `verify.py`'s full run exceeds ~40s; if it looks like it's hung, it isn't
  — the report's "What wasn't exercised" section has the timing detail.
