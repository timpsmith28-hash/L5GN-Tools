<!-- gate-frozen: commit=c691c1e -->
# Cowork report — the pin mechanism (DECISIONS 0045)

**Pair:** `docs/COWORK_BRIEF_pin_mechanism.md`. Session 2026-08-17.
**Gate:** `python verify.py` → **GREEN, 11 auditors + 77 testers** (was 10 + 75
at `5016eb8`, this round's base commit; +1 auditor:
`auditor_conversation_map_pin`, +2 testers: `tester_pin` and
`tester_conversation_map_pin`).
**Commit:** `c691c1e` (parent `5016eb8`), 10 files changed, 866 insertions.

Builds the mechanism DECISIONS 0045 ruled: one implementation of "an
artefact that cannot live in this repository's git in its live form, plus a
committed record of which version was ratified, checked at use so drift is
detected rather than assumed absent" — applied to the one subject 0045 named
as exposed: `config/mcf_conversation_map.tsv`'s committed fingerprint (0040
clause 4), which `config/README.md` said plainly had "nothing checks this
yet."

---

## What was built

**`l5gntools/pin.py`** — read-only, stdlib-only. `parse_pin_file` reads a
pin; `verify_pin` checks an artefact against it and returns a `PinCheck`
(`state`, both hashes, `findings`); `commit_exists_resolver` mirrors
`auditor_uat_stamp`'s degrade-to-skip outside a checkout rather than
reinventing it. `hash_file`, `format_pin_line`, `format_pin_comment` are the
three primitives `run.py pin bump` composes — this module itself never
writes.

**`auditors/auditor_conversation_map_pin.py`** — wired into `verify.py`'s
`AUDITORS`. Wraps `pin.verify_pin` against
`config/mcf_conversation_map.tsv` / `.tsv.sha256`, with a small
`CLEAN_STATES` classification layer so a fresh checkout (no map at all) and
a real drift are never confused.

**`run.py pin bump <path> [--apply]`** — the only sanctioned writer, dry-run
by default. Not invoked against the real map in this round: the working
rule was to verify the map and its pin, not regenerate them, and the
existing hash-only pin already verifies clean (see below) — there was
nothing to bump.

**`tests/tester_pin.py`, `tests/tester_conversation_map_pin.py`** —
hermetic, temp-dir fixtures, injected resolver, no dependency on the real
map or this repo's git state.

**Two docs gate-frozen, one regenerated** — registering the new auditor
moved the live gate count from 10+75 to 11+77, which staled two docs' live
"10 auditors + 75 testers" claims that had not yet earned a `gate-frozen`
marker: `docs/COWORK_REPORT_architecture_census.md` and
`docs/UAT_architecture_census_results.md`, both from the immediately
preceding round. Frozen at `5016eb8` (this round's base commit) — the exact
move `docs/COWORK_REPORT_correctness_sweep.md` got in that same commit, for
the same reason. `docs/_architecture_shape.md` regenerated via `run.py
render-architecture` so `auditor_architecture_current` stays green against
the new file set.

---

## The pin format decided

0045 clause 1 fixed the field set; this round had to pick the
serialization, and `config/README.md` already documented a real constraint:
`sha256sum -c config/mcf_conversation_map.tsv.sha256` is the hand-fallback
check on a plain Windows/git-bash machine, with no bespoke tooling. Breaking
that by switching to JSON or similar would cost a workflow already in use.

Chosen shape keeps the first line byte-identical to what `sha256sum -c`
expects, and adds the rest of 0045's fields as a `#`-prefixed comment line —
ignored by both `sha256sum` and a plain read:

```
<hex sha256>  <repo-relative artefact path>
# pin: origin=local anchor=<full commit sha> date=YYYY-MM-DD host=<hostname>
```

The map's *own* pin file on disk right now is the legacy hash-only shape
(no comment line) — it predates this mechanism and this round's working
rule forbade touching it (verify, don't regenerate). `l5gntools.pin`
handles that correctly: a pin with no comment line parses fine, with
`origin`/`anchor`/`date`/`host` all `None`, and verifies as `matches` with
no anchor check attempted. The richer format only appears once a human runs
`run.py pin bump --apply` on a live artefact.

**`anchor=` for a `local`-origin pin is a different kind of anchor than the
cross-repo case.** The map itself is never committed, so there's no commit
that "touched" it the way `Claude_Migration`'s `PROVENANCE.md` anchors to
the origin repo's last-touching commit. `run.py pin bump` stamps this
repo's HEAD at the moment the pin is written — the closest true analogue,
flagged as a judgement call in the brief and unchanged since.

---

## States, with real examples from this rig

Ran directly against the live repo (not a fixture) to get real evidence
rather than asserting the states abstractly:

| state | example from this rig |
|---|---|
| `matches` | `config/mcf_conversation_map.tsv` against its own `.sha256`: recorded and actual hash both `c64c0d87…aa05e`, zero findings. |
| `artefact-absent` | Pointed the same pin at a nonexistent path (`config/does_not_exist.tsv`): `state=artefact-absent`, zero findings — the fresh-checkout case, since the real map travels by hand per `config/README.md` and most checkouts of this repo won't have one. |
| `mismatch` | Exercised in `tester_pin` only (drifted a temp-dir fixture's bytes) — both hashes named, "reported, not repaired" cited in the finding. Not reproduced against the real map, which is untouched. |
| `unpinned` | Exercised in `tester_pin`/`tester_conversation_map_pin` only — no real case exists in this repo today. |
| `absent` | Exercised in `tester_pin` only. |
| `pin-malformed` | Exercised in `tester_pin` only. |
| `anchor-unresolvable` | Exercised in both testers with an injected `False` resolver — a violation, never a silent pass, per 0045 clause 3. |
| `git-unavailable` | Exercised in both testers with `commit_exists=None` — mirrors `auditor_uat_stamp`'s degrade-to-skip. |

`run.py pin bump config/mcf_conversation_map.tsv` (dry-run, no `--apply`)
against the real map printed:

```
pin bump: config/mcf_conversation_map.tsv already matches its pin at
.../config/mcf_conversation_map.tsv.sha256 (sha256 c64c0d87...) -- nothing
to do.
```

— the no-op-bump behaviour flagged as a judgement call in the brief,
confirmed working as specified: a matching artefact produces no diff to
apply, rather than restamping date/host for no reason.

---

## What this leaves for `convention_scaffold`

As scoped in the brief: that round's Task 1 (a pin file) and Task 2 (an
auditor resolving the pin against a commit) are superseded — it should call
`l5gntools.pin` for its comparison primitive rather than write its own
reader/verifier, the same way this round reused `auditor_uat_stamp`'s
sha-resolution shape instead of reinventing it.

Still entirely that round's own work: Task 3's stamp inside a *copied*
`docs/README.md` and the seven-state `convention_census` table (`current` /
`behind` / `modified` / `divergent` / `unpinned` / `absent` / `unreadable`)
— richer than this round's states because it compares two things (the
toolkit's pin vs. a target project's copy) rather than one artefact against
its own pin; Task 4, the scaffolder; Task 5, offering (never applying) an
update across a repository boundary. Its precondition-DECISIONS task is now
redundant with 0045 and should be dropped — cite 0045, don't re-argue it.

`Claude_Migration`'s `vendor_check.py` was not touched. 0045's consequences
name it as a future adopter "under its own 0001" — a separate repo, a
separate decision, out of scope here.

---

## What wasn't exercised

- `run.py pin bump --apply` was never run against the real map in this
  session — the working rule forbade regenerating `config/mcf_
  conversation_map.tsv.sha256`, and the dry-run path (which is exercised,
  against the real file, above) already proves the tool reads the artefact
  and pin correctly. The `--apply` write path itself is only exercised in
  `tester_pin`'s temp-dir fixtures (`format_pin_line`/`format_pin_comment`
  round-trip test) and — implicitly — by `run.py pin bump`'s own file-write
  call, which is not separately gated (there is no `tester_run.py`; `run.py`
  commands are thin CLI shells over the tested modules, consistent with how
  `_cmd_backup`, `_cmd_conductor` etc. are tested elsewhere in this repo).
- The `host=` field's real value on this rig is unconfirmed: `run.py pin
  bump` reads `l5gntools.config.hostname()` (`socket.gethostname()`), and
  which hostname that resolves to depends on which process runs it — the
  Windows checkout directly vs. this session's device-bridge execution
  path reported different values during development. Not a defect in the
  mechanism (it records whatever the invoking host actually is, honestly);
  worth knowing before reading too much into a `host=` value later.
- Full `verify.py` runs past this environment's 45-second command ceiling
  end-to-end from a single invocation; GREEN was confirmed via the
  pre-commit hook's own full run at commit time (transcript shows all 11
  auditors and 77 testers `[ OK ]`, ending "verify: GREEN -- all gates
  passed"), not by a separately captured standalone log.

---

## Concurrent edits on the rig

Partway through this session the working tree picked up unrelated,
in-progress changes on the machine itself — `docs/ARCHITECTURE.md`,
`docs/DECISIONS.md` modified, and a `ui_witness` doc pair staged for a move
into `docs/archive/`. None of that is this round's work. `git commit` was
run with an explicit pathspec naming only this round's ten files, so those
other changes were left exactly as found, still uncommitted, for separate
review.
