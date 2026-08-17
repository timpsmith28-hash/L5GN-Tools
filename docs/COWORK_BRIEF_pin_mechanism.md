# Cowork brief — the pin mechanism: one implementation, wired to the subject that has nothing checking it

**Origin:** DECISIONS 0045, ratified 2026-08-17.
**Deliverable:** a shared, read-only pin-verification module in `l5gntools/`, a
dry-run-by-default `run.py pin` command for writing/bumping a pin, and both
wired to the one subject that currently has a pin with no checker:
`config/mcf_conversation_map.tsv` / `config/mcf_conversation_map.tsv.sha256`
(0040 clause 4).
**Builds on:** 0045 (this mechanism, in full — not re-litigated here), 0040
clause 4 (the map's committed fingerprint), 0034 clause 1 (`l5gntools/` is
stdlib-only and read-only, unchanged), `auditor_uat_stamp.py`'s sha-resolution
pattern (reused, not reinvented).
**Read first:** DECISIONS 0045 and 0040 clause 4 in full, `config/README.md`
(the map's current travel and fingerprint story — this round is exactly the
"nothing checks this yet" line it ends on), `auditors/auditor_uat_stamp.py`
(the commit-resolution shape this reuses).

This is not a design round. 0045 already ruled the shape; this brief is that
ruling applied to one subject. Where this document makes a call 0045 left
open, it's marked **(judgement call)** so it's visible as such rather than
read as settled doctrine.

---

## Why this subject, not the other two

0045's table names three places the same shape was designed independently:

| Subject | State |
|---|---|
| `Claude_Migration` vendored parser | built, running (`vendor/PROVENANCE.md` + `vendor_check.py`) |
| `docs/README.md` travelling to other repos | designed, unbuilt (`COWORK_BRIEF_convention_scaffold.md`) |
| `config/mcf_conversation_map.tsv` fingerprint | **fingerprint committed, no checker** |

The first already works and isn't broken. The second is unbuilt — building the
mechanism *for* it before it exists would be designing in the abstract, which
is what 0045 just spent a paragraph arguing against. The third is the one
carrying a pin today that nothing verifies: `config/mcf_conversation_map.tsv.sha256`
sits in the repo, committed, and — per `config/README.md`'s own words —
*"nothing checks this yet."* This round closes that gap and, in doing so,
builds the shared mechanism the other two subjects will adopt later, each
under its own decision.

---

## Working rules

- **`l5gntools/pin.py` is read-only, stdlib-only, and belongs to the scanner
  package's contract (0034 clause 1).** `hashlib`, `re`, `subprocess` (for
  anchor resolution, same as `l5gntools/common.py:run_git`) — nothing else.
  It never writes to the artefact or the pin file. It has no opinion about
  what to do with a mismatch beyond stating it.
- **Writing or bumping a pin is not a scanner.** It changes the pin file on
  disk, so it's a `run.py` command, dry-run by default, `--apply` to write —
  the same shape `run.py scaffold` was specified with.
- **The checker is a new auditor**, wired into `verify.py`'s `AUDITORS` list,
  gating the commit — this is the mechanism reaching the subject 0045 named as
  exposed.
- Gate GREEN before commit. Logic in testable functions, per house style.

---

## Task 1 ▸ the pin file format

0045 clause 1 fixes the **field set** (origin, anchor commit where one exists,
date, host, content hash) but not the **serialization** — `PROVENANCE.md` is
markdown prose, `mcf_conversation_map.tsv.sha256` is a bare `sha256sum`-format
line. This round has to pick one for the map, and the pick has a real
constraint: **`config/README.md` documents `sha256sum -c
config/mcf_conversation_map.tsv.sha256` as the manual fallback check on a
plain Windows/git-bash machine**, with no bespoke tooling required. Breaking
that by switching to a structured format (JSON, TOML) would cost a workflow
Tim already has.

**Proposed shape — keeps the first line byte-compatible with `sha256sum -c`,
adds the rest as a `#`-prefixed comment line** (both `sha256sum` and a plain
text read ignore `#` lines):

```
c64c0d871d0c98153265e1bba67f5573ec087648a707a182c1e690c2927aa05e  config/mcf_conversation_map.tsv
# pin: origin=local anchor=<full commit sha> date=YYYY-MM-DD host=<hostname>
```

- **`origin=local`** — per 0045 clause 1, the value for an untracked file in
  this repo. (The vendored-parser and travelling-docs subjects will use
  `origin=<repo>:<path>` when they adopt this later; not built here.)
- **`anchor=`** — **(judgement call)** the map itself is never committed, so
  there's no commit that "touched" it the way `PROVENANCE.md`'s anchor works.
  The nearest true analogue is *this repo's HEAD at the moment the pin was
  written* — the commit that records "the fingerprint below was current as of
  here." That's what `run.py pin bump` will stamp. Flagging this because it's
  a different meaning of "anchor" than the cross-repo case, not because it's
  in doubt.
- **`date=` / `host=`** — new fields; today's fingerprint has neither. Per
  0045 clause 1 they're required going forward.
- `mcf_conversation_map.tsv.sha256` still ends in `.tsv.sha256`, so the
  existing `.gitignore` pattern (`/config/*conversation_map.tsv`, which stops
  at `.tsv` per `config/README.md`) keeps tracking it with no change needed.

## Task 2 ▸ `l5gntools/pin.py` — reading and verifying

```python
@dataclass
class PinRecord:
    sha256: str
    artefact_path: str      # repo-relative, as recorded in the sha256sum line
    origin: str              # "local" or "<repo>:<path>"
    anchor: str | None
    date: str | None
    host: str | None

def parse_pin_file(path: Path) -> PinRecord | None: ...

@dataclass
class PinCheck:
    state: str        # see table below
    recorded_hash: str | None
    actual_hash: str | None
    findings: list[str]

def verify_pin(pin_path: Path, artefact_path: Path,
                commit_exists=None) -> PinCheck: ...
```

States — same discipline convention_scaffold's brief already specified for
`convention_census`, reused rather than re-derived:

| state | meaning |
|---|---|
| `matches` | hash and anchor both check out |
| `mismatch` | artefact present, hash differs — **both hashes stated**, nothing touched (0045 clause 2) |
| `artefact-absent` | pin exists, artefact doesn't — **normal**, not a failure: the map travels by hand and a fresh checkout won't have it |
| `unpinned` | artefact exists, no pin file — this repo currently has no case of this, but the state must exist so it isn't confused with `artefact-absent` |
| `pin-malformed` | pin file present but doesn't parse |
| `anchor-unresolvable` | `anchor=` is set, git is available, and the sha does not resolve — **a violation, not a silent pass (0045 clause 3)** |
| `git-unavailable` | anchor check skipped because there's no `.git` to ask — not a failure, mirrors `auditor_uat_stamp`'s degrade-to-skip outside a checkout |

`verify_pin` never writes. A `mismatch` finding names both hashes and stops
there — no auto-repair, per 0045 clause 2, mirroring `vendor_check.py`'s
"reported, not repaired" line exactly.

## Task 3 ▸ `auditors/auditor_conversation_map_pin.py`

Wraps `pin.verify_pin` against `config/mcf_conversation_map.tsv` +
`config/mcf_conversation_map.tsv.sha256`, registered in `verify.py`'s
`AUDITORS`.

- `artefact-absent` and `git-unavailable` → **pass, no finding.** A checkout
  without the map on it is the documented normal state (`config/README.md`),
  not a defect.
- `mismatch`, `anchor-unresolvable`, `pin-malformed` → **fail the gate**, one
  finding each, stating what's wrong and both hashes where relevant.
- **Never touches `config/mcf_conversation_map.tsv` or its `.sha256`.** This
  auditor reports; the map's regeneration remains entirely outside this
  round's — and this mechanism's — reach, per the working rule already in
  place: *"Do not modify config/mcf_conversation_map.tsv or its .sha256 — your
  job is to verify them, not to regenerate them."* This auditor is what makes
  that job real.

## Task 4 ▸ `run.py pin bump <artefact-path>` — dry-run by default

- Computes the artefact's current hash, resolves current HEAD, host
  (`socket.gethostname()`, same source `machines.json` keys on), today's date.
- **Dry-run prints the pin line(s) it would write** and, if a pin already
  exists, a diff against it. Nothing touches disk.
- `--apply` writes.
- **Refuses if the artefact doesn't exist.** There's nothing to pin.
- Does **not** decide *whether* a bump is warranted — that's 0045 clause 5's
  *"working ahead of a pin is a normal state, not an error"*. This command is
  invoked deliberately, by a human who has just ratified a map change, the
  same moment `config/README.md` already names: *"re-hash it whenever you
  ratify a change to the map, in the same commit."* `run.py pin bump` replaces
  the manual `sha256sum`/`certutil` step that instruction currently describes
  — it does not replace the human decision that a ratification happened.

## Task 5 ▸ tests

- `pin.py`: pure-function tests against fixture files — matching hash,
  mismatched hash (both stated in the finding), missing artefact, missing pin,
  malformed pin, unresolvable anchor with an injected resolver (mirroring
  `auditor_uat_stamp`'s `commit_exists=None` injection so the tester doesn't
  need a real repo).
- `auditor_conversation_map_pin.py`: `artefact-absent` passes clean: the
  auditor must be green on a fresh checkout with no map on disk at all — the
  common case.
- `run.py pin bump`: dry-run writes nothing; `--apply` writes; refuses on a
  missing artefact; a second bump with no artefact change reports "matches,
  nothing to do" rather than rewriting the date/host for no reason
  **(judgement call — flag if Tim wants every bump to restamp date/host
  unconditionally instead).**

---

## What this leaves for `convention_scaffold`

Its brief's Task 1 (a pin file: pin sha + content hash) and Task 2 (an
auditor that resolves the pin against the commit) are **superseded** by this
round's `l5gntools/pin.py` and the `auditor_conversation_map_pin.py` pattern —
that round should call the shared reader/verifier rather than write its own,
the same way this round didn't reinvent `auditor_uat_stamp`'s sha-resolution.

**Still that round's own work, untouched by this one:**

- Task 3's stamp *inside a copied `docs/README.md`* and its seven-state
  `convention_census` table (`current` / `behind` / `modified` / `divergent` /
  `unpinned` / `absent` / `unreadable`) — richer than this round's states
  because it's comparing *two* things (the toolkit's pin vs. the target
  project's copy), not one artefact against its own pin. This round's states
  table is a subset; that round's stays as specified.
- Task 4, the scaffolder itself (`run.py scaffold`) — writing a *new* project's
  `docs/` tree is unrelated to pin verification.
- Task 5, offering (never applying) an update across a repository boundary.
- The precondition DECISIONS entry that brief drafts is now **redundant with
  0045** and should be dropped — 0045 already rules the mechanism; that round
  no longer needs to re-argue it, only cite it.

So `convention_scaffold`'s scope shrinks to: adopt `l5gntools/pin.py` for its
pin-comparison primitive, keep its own census/scaffold/offer-update logic,
drop its own precondition-DECISIONS task.

**Not touched by this round, either:** `Claude_Migration`'s `vendor_check.py`.
0045's consequences name it as a future adopter *"under its own 0001"* — a
separate repo, a separate decision. Out of scope here.

---

## Explicitly out of scope

- Regenerating or editing `config/mcf_conversation_map.tsv` or its `.sha256`
  in any way other than through `run.py pin bump --apply`, invoked by a human
  who just ratified a change. This round verifies; it does not curate.
- Rewriting `Claude_Migration`'s `vendor_check.py` to call this mechanism —
  that repo's own decision, not this one's.
- Building the travelling-docs pin (`convention_scaffold`'s Task 1/2 subject)
  — unbuilt, and 0045 doesn't ask for it to be built now, only for its design
  to converge on this mechanism when it is.
- Any change to `docs/README.md` or the docs-lifecycle convention itself.

## Stop conditions

- **The auditor fails on a fresh checkout with no map on disk** → stop;
  `artefact-absent` must be a clean pass, not a violation — this is exactly
  the confident-zero/false-failure distinction 0045 clause 5 and
  `convention_scaffold`'s `absent`/`unreadable` split both already established.
- **A mismatch is silently repaired** (pin rewritten, or artefact touched) →
  stop; 0045 clause 2 is categorical.
- **`run.py pin bump` writes without `--apply`** → stop.
- **`l5gntools/pin.py` gains a non-stdlib dependency, or writes to disk** →
  stop; 0034 clause 1 is unweakened by 0045, and clause 4 is explicit that
  reading lives in `l5gntools/` precisely because it doesn't write.
- **An unresolvable anchor passes clean when git is available** → stop; 0045
  clause 3 sets the same bar as `auditor_uat_stamp` and the `gate-frozen`
  marker — this is not optional here either.
- **`config/mcf_conversation_map.tsv` or its `.sha256` is edited by anything
  in this round outside `run.py pin bump --apply`** → stop.

---

## UAT — acceptance checks (Tim walks these)

- `python run.py pin bump config/mcf_conversation_map.tsv` dry-runs, prints
  the pin line(s) it would write, touches nothing on disk. **[H]**
- `--apply` writes `config/mcf_conversation_map.tsv.sha256` in the format
  above; `sha256sum -c config/mcf_conversation_map.tsv.sha256` still passes by
  hand. **[G]**
- Hand-edit one byte of `config/mcf_conversation_map.tsv` (or touch its mtime
  and change a character) → `auditor_conversation_map_pin` fails, stating
  both hashes; the file itself is left exactly as edited. **[G]**
- Rename the map away (simulating a fresh checkout with no map) →
  `auditor_conversation_map_pin` passes clean, no finding. **[G]**
- Hand-edit `anchor=` in the `.sha256` comment line to a sha that doesn't
  exist in this repo → auditor fails, names the unresolvable anchor. **[G]**
- Outside a git checkout (or with `.git` inaccessible) the anchor check
  degrades to skip rather than a false failure, matching
  `auditor_uat_stamp`'s carve-out. **[W]**
- `verify.py` GREEN with the new auditor registered. **[G]**
- Read `l5gntools/pin.py` cold: no import outside stdlib, no path that writes
  to the artefact or the pin file. **[H]**

Mark items `[G]`/`[W]`/`[H]` per 0031 — `[G]` gate-checked by `verify.py`,
`[W]` a deterministic non-gating check, `[H]` needs a human's judgement.
Results log needs a uat stamp naming the commit.

---

## Reporting

`docs/COWORK_REPORT_pin_mechanism.md`, walk-sheet `docs/UAT_pin_mechanism.md`,
stamped results after the walk. Record: the pin format decided (and the
`sha256sum -c` compatibility reasoning, since that constrained the choice),
the states table with a real example of `matches` and `artefact-absent` from
this rig, and the exact diff to `convention_scaffold`'s scope so that round
can be re-briefed against a smaller Task 1/2 rather than rebuilding what
already exists here.
