# Cowork brief — the convention travels: pinned scaffolding for any project

**Origin:** design thread, 2026-08-05, out of the docs-board generalisation
question.
**Deliverable:** a new project can be scaffolded with the `docs/` lifecycle in
place; every project carrying it declares **which pinned release** it holds; the
toolkit reports who is current, who is behind, and who has diverged — and never
edits another project's documents.
**Builds on:** ARCHITECTURE §5 (config is a shipped artifact), 0028 (stage, never
commit), 0030 (shape generated, rationale authored), the deposit manifest's
`True`/`False`/`None` verification pattern.

The methodology firmed up in this repo is already being reused by hand across
other projects, to varying degrees. This makes the reuse legible: what a project
copied, when, from which release, and whether it has been changed since.

**One shared copy was considered and rejected.** A symlink or submodule lets a
project's convention change without a commit in that project — the opposite of
every doctrine here — and a project that legitimately diverges could not express
it. `machines.json` already settled this shape: a committed source, copied
outward, verified on arrival.

**Read first:** `docs/README.md` in full (it is the artefact being shipped),
ARCHITECTURE §5, `l5gntools/deposit.py`'s manifest verification, and
`auditors/auditor_uat_stamp.py`'s sha-resolution pattern — you are reusing it.

---

## Precondition ▸ a DECISIONS entry

Draft to Tim, ratify, then build.

> ## 00NN — The docs convention travels as a pinned copy; divergence is reported, never corrected
>
> **Date:** 2026-08-05 · **Status:** proposed · **Builds on:** ARCHITECTURE §5
> (config is a shipped artifact), 0028 (the mechanical layer is automated, the
> judgement layer is not) · **Source:** design thread
>
> **Context.** `docs/README.md` is the specification the docs board implements
> and the lifecycle other projects are already copying by hand. A shared
> reference — submodule, symlink, fetched-at-runtime — would let a project's
> convention change with no commit in that project, which contradicts every
> frozen-artefact rule in this repo, and would make a deliberate local divergence
> unrepresentable.
>
> **Decision.**
> 1. **The toolkit's own `docs/README.md` is the canonical copy.** There is no
>    separate template; a template would drift from it, which is the exact
>    failure class the 2026-08-02 drift audit found twelve times.
> 2. A **pinned release** — a commit plus the content hash at that commit — is
>    declared in the toolkit. Projects hold a stamped copy naming the pin they
>    took.
> 3. **Divergence is legitimate.** A project that has edited its copy is reported
>    as modified, never corrected. The toolkit may *offer* an update; it never
>    writes into another project's `docs/` without an explicit, per-project act.
>
> **Consequences.** The estate gains an honest answer to *"which projects are on
> which version of the method"*, which today is unanswerable. The cost is that
> updates are manual per project — accepted, because the alternative is a tool
> that rewrites documents it does not own.

---

## Working rules

- **The detector is a scanner** — read-only, stdlib, registered, `write_json`
  under `data/`. The four scanner auditors must pass unexempted.
- **The scaffolder is not.** It writes into a target project, so it cannot be a
  scanner and must not be registered as one. It is a `run.py` command, dry-run by
  default.
- Gate GREEN before commit. Logic in testable functions.

## Task 1 ▸ the pin

A committed declaration in the toolkit — suggested `config/convention_pin.json`:

```json
{
  "pin": "<full commit sha>",
  "sha256": "<hash of docs/README.md at that commit>",
  "released": "YYYY-MM-DD",
  "note": "one line: what changed in this release"
}
```

**Two values because they answer two different questions.** The `pin` says
*which release* a project is on. The `sha256` says whether a copy has been
*edited since it arrived*. Independent facts, independently checked — the same
reason the deposit carries a manifest as well as a namespace.

**Bumping the pin is a deliberate act.** The toolkit's working `docs/README.md`
may sit ahead of the pinned release; that is a draft, not drift. This is the
whole point of pinning rather than deriving from HEAD: a typo fix must not mark
every project behind until someone decides it is a release.

## Task 2 ▸ the auditor — a pin cannot be fabricated

`auditors/auditor_convention_pin.py`:

- `pin` must **resolve to a real commit** in this repository.
- `sha256` must match `docs/README.md` **at that commit** — not at HEAD.
- The file must be well-formed.

Same bar as `auditor_uat_stamp`'s commit resolution: an unresolvable pin is a
violation, not a silent pass.

**It must NOT fail when the working README differs from the pinned release.**
That is the normal state between releases. Report it as information — *"working
README is ahead of pin `<sha8>`"* — so the bump is prompted, never forced.

## Task 3 ▸ the stamp, and the states

A scaffolded or updated copy carries, as its first line:

```
<!-- convention: pin=<sha8> · sha256=<hash8> · copied=YYYY-MM-DD · source=L5GN-Tools -->
```

A scanner (suggested `convention_census`) reports per project:

| state | meaning |
|---|---|
| `current` | pin matches the toolkit's pin; hash matches |
| `behind` | pin is an older release; hash matches its own pin — clean, just old |
| `modified` | pin current; hash differs — locally edited |
| `divergent` | older pin **and** edited — the case an update would clobber |
| `unpinned` | a `docs/README.md` exists with no stamp — copied before this existed |
| `absent` | no `docs/README.md` |
| `unreadable` | **could not look** — permissions, encoding, a path it could not resolve |

**`absent` and `unreadable` are different states and must never collapse.** A
scanner that reports "no convention here" when it actually failed to read is the
confident-zero class, found three times in this estate already, and this is a new
scanner walking unfamiliar directories.

**The scanner needs no git.** It compares the project's stamp against the pin
file and the file's actual hash — three local values, no history access. That is
why the hash lives in the pin file rather than being resolved from the commit.

## Task 4 ▸ scaffold a new project

`run.py scaffold <path>` — **dry-run by default, `--apply` to write.**

Creates:

```
docs/README.md              the canonical copy, stamped per Task 3
docs/INTENT.md              stub
docs/ARCHITECTURE.md        stub
docs/DECISIONS.md           stub — format preamble and the append-only rule, no entries
docs/archive/.gitkeep
docs/investigation/.gitkeep
```

**The stubs must be unmistakably stubs.** Each carries a visible
`<!-- stub: not yet written -->` marker and a single line saying what the
document is for. A stub that reads like a plausible finished `ARCHITECTURE.md` is
worse than an absent one — it is the drift class seeded at birth, and the whole
reason 0030 exists. `convention_census` should report *"trinity: 2 of 3 still
stubs"* so the state is visible rather than assumed.

`ARCHITECTURE.md`'s stub should state 0030's split up front — this file holds
rationale, shape is generated — so a new project starts on the right side of the
line rather than being corrected onto it later.

**Refuse rather than overwrite.** If `docs/` already exists, scaffold reports
what it found and exits non-zero. It never merges, never backs up and replaces,
never touches anything outside the target's `docs/`.

## Task 5 ▸ offer an update, never apply one

For a project reported `behind`: print the diff between its pinned release and
the current pin, and **stage** the replacement only on an explicit per-project
instruction — 0028's shape, applied across repository boundaries.

For `modified` or `divergent`: **refuse to stage.** Show the local edits and say
plainly that an update would discard them. A tool that silently reverts a
deliberate divergence is worse than one that does nothing.

---

## Explicitly out of scope

- Rendering other projects' boards. This is the enabling step; the generalisation
  is its own round and will be better informed once real projects carry the
  convention.
- Any change to `docs/README.md`'s **content**. This round ships it, it does not
  edit it.
- Scaffolding anything beyond `docs/` — no `verify.py`, no gate, no CI.
- Publishing this for anyone but Tim. INTENT §4 stands: single-operator, a
  pattern reused, not a product.

## Stop conditions

- **The scaffolder is registered as a scanner** → stop; it writes.
- **A template file is created beside `docs/README.md`** → stop; that is the
  drift class, reinvented.
- **`absent` and `unreadable` collapse into one state** → stop.
- **The auditor fails when the working README is ahead of the pin** → stop; it
  has turned a draft into an error and every typo now bumps every project.
- **Scaffold overwrites, merges into, or backs up an existing `docs/`** → stop.
- **An update is applied to a `modified` or `divergent` project** → stop; that is
  a tool discarding a human's deliberate work.

---

## UAT — acceptance checks (Tim walks these)

- `python run.py scaffold <tmp>` dry-runs, lists exactly the files above, writes
  nothing. `--apply` creates them.
- Run it again on the same path: **refuses**, names what it found, exits non-zero.
- The stubs read as stubs. Opening `docs/ARCHITECTURE.md` in the new project, it
  is obvious nothing has been written yet.
- `convention_census` places this repo as `current` and the new project as
  `current`.
- **Hand-edit the new project's `docs/README.md`** → reports `modified`, and an
  update **refuses** rather than reverting the edit.
- **Point it at a real project you have copied the convention into by hand** →
  reports `unpinned`, not `absent`.
- **Make a directory unreadable** → reports `unreadable`, not `absent`.
- Bump the pin with a real README change. Projects flip to `behind`. Nothing
  flips to `behind` from a commit that did not bump the pin.
- `auditor_convention_pin` fails on a fabricated pin sha and on a `sha256` that
  does not match the README at that commit. It stays green while the working
  README is ahead of the pin.
- `verify.py` GREEN.

Mark each **ready to walk**. Results log needs a uat stamp naming the commit; do
not write a `gate=` field. Mark items `[G]`/`[W]`/`[H]` per 0031 — this is the
first brief written after the layer split and should use it from the start.

---

## Reporting

`docs/COWORK_REPORT_convention_scaffold.md`, walk-sheet
`docs/UAT_convention_scaffold.md`, stamped results after the walk.

Record the ratification, the pin format and why the hash lives in the pin file,
the seven states with a real example of each where one exists, and the
`convention_census` output across every project on the rig — that census is the
first honest answer to *"which projects are on which version of the method"* and
is worth quoting in full.
