# Configuration convention

**Status:** authored, not enforced, and **not yet true**. Unlike
`CONVENTION_commits.md` -- which described a convention already 82% kept --
most of this file describes a shape the repo does not currently have. Every
section marks what holds today and what does not, because a convention that
reads as a description of the present when it is a description of an intent is
the same defect as a doc claiming a file is committed when it is not (§1).

**Scope:** this repo, plus any tool packaged out of it (§5). MCF repos may
adopt it; nothing here reaches across a repo boundary except by a named
adoption, the way `Claude_Migration` **0001** adopts a list from here.

**Cites:** 0012 (scope declared on the producer's root), 0020 (`is_project`,
personal rig only), 0031 (a non-gating surface reports findings, never a
verdict), 0036 (the mesh stood down; nothing runs unbidden), 0040 clause 4
(the map's committed fingerprint), 0042 clause 2 (the allowlist is a reviewed
edit), 0043 (a ruling from another repo is cited with its repo), 0045
(verification reports, never repairs), 0048 clause 4 (a field with one
possible value trains the eye past it), 0050 (a source declares its own
staleness; unreachable reads as unknown), 0051 (containment by construction),
0052 (a convention lives in the repo, not in whoever is typing), 0053 clause 5
(authorship is declared per artefact).

---

## 1. What this fixes, measured

Read from the working tree on 2026-08-25.

| | |
|---|---|
| distinct config keys, across 4 host sections | **13** |
| precedence ladders **documented** | **1** |
| precedence ladders **implemented**, for the same class of value | **4** |
| environment variables that outrank config | **4** |
| resolution paths for `project_registry.json` | **2**, under different env vars |
| runtime writers into `config/local.json` | **2** |
| documents asserting a config file's tracked or travel status **wrongly** | **4** |

**The four ladders.** `l5gntools/config.py`'s docstring states one order.
The code implements four:

| site | order |
|---|---|
| `scanners/vault_reader._resolve_vault_path` | config, then env, then a sibling-path guess |
| `chronicler/review/core.resolve_registry_path` | env, then derived, then the repo copy |
| `backup.py`, `census.py`, `scrape.py` | env, then config |
| `chronicler/pipeline/db.py:45,48` | env, then a hardcoded default -- **at import time**, config never consulted |

`db.py` is the one that cannot be fixed by agreement: its constants are
evaluated when the module loads, before `config.machine()` could be called at
all. The others disagree because nothing made them agree.

**Two resolvers for one file.** `project_registry.json` is resolved by
`resolve_registry_path` under `CHRONICLER_REGISTRY_PATH`, and independently by
`build_registry.GROUPS_PATH` under `CHRONICLER_REGISTRY_GROUPS`. Both default
to the same repo copy, so they agree until someone sets one of them.

**`config/local.json` is written by the running machine.**
`chronicler/pipeline/governor.set_profile` and
`chronicler/review/curator_control.set_curator_model` both read-modify-write
it. Both are careful -- they preserve every other key rather than blind-writing
-- and both are undone by the file's own instruction to itself:

> `"Maintain it here on the gaming rig and ship with: scp config/local.json <host>:L5GN-Tools/config/local.json"`

A whole-file `scp` destroys a governor profile learned on the knight and a
curator model chosen on the work rig. `curator_control.set_curator_model`'s
docstring says *"this never writes anything that travels"*; the file it writes
travels by `scp`, just not by git. That is the fourth wrong claim.

**The other three wrong claims** all concern
`config/project_wizard.allow.json`, which is untracked (`.gitignore:25`) and
is described as committed by `config/README.md`'s tracked-files table, by its
own `_comment` (*"Committed, per-host repo allowlist"*), and by 0042 clause 2
(*"a reviewed, committed edit"*). `.gitignore`'s own comment already records
that the clause was narrowed and *"wants its own entry rather than living only
in this comment"* -- that debt is noted here, not discharged by this file.

**And the committed template teaches a wrong path.** `local.json.example`
carries `D:/Work/Github/MCF` for the work rig. That path has never existed on
that machine; the correct root is `C:/Users/tim.smith/Github/MCF`, and the
correction was found on the consumer, which held it while the authoring rig
did not. Nothing on either side could have shown the divergence, because the
file that carries it is untracked on both.

**What none of this is.** No defect above was caused by carelessness. Each one
is what happens when four independent questions are answered by a single
tracked-versus-untracked binary. §2 separates them.

---

## 2. The five layers

Configuration is not one thing. Two questions generate the layers, and the
second is the one the old shape never asked:

1. **Does the value vary?** Per estate, per machine, per person.
2. **Who is entitled to decide it?** The code, the estate, the machine, the
   operator.

`role` and `cowork_transcripts_home` both vary per machine, and answer 2
differently: we decide the first; only the machine can know the second. Any
split that separates only on question 1 puts them together, which is how a
path for a machine nobody here has ever seen came to be typed on this one.

| Layer | Authority | Travels by | May be edited by |
|---|---|---|---|
| **Tool policy** | the code | shipping the code | a commit to this repo |
| **Estate policy** | the estate's author | `git pull` | a reviewed, committed edit |
| **Machine facts** | derivation, human-confirmed (§3) | never ships | the machine it describes |
| **Operator facts** | the person | never ships | that person |
| **Estate corpus** | *not configuration* (§7) | hand-carried, fingerprinted | its declared author |

**Tool policy** is true for anyone running this code anywhere: the `scope`
vocabulary, schema versions, the `default` role, what `producer` and
`consumer` mean. It ships with the code and no install edits it.

**Estate policy** is true for *this* estate: which hosts exist, their `role`
and `estate`, the scope tag on each root (0012 -- declared on the producer,
never inferred from nesting), which host authors which artefact. Tracked, so
it arrives by `git pull` and a consumer cannot be behind it without a failed
pull saying so.

**Machine facts** are what only the machine can know. See §3: most of this
layer should stop being configuration.

**Operator facts** belong to a person rather than a machine or an estate:
identity and git aliases, tenant, where their backups go, which model they
prefer. This layer is new. It is here because on 2026-08-24 a tool built out
of this repo was run by a second operator on a machine this estate has never
configured, and it worked -- which proves the layer exists and that nothing
currently names it.

**Estate corpus** is the registry, the conversation maps and the wizard
allowlist. §7 argues these are not configuration at all and explains what
follows from saying so.

---

## 3. Machine facts are derived, not configured

**The rule: derive, report, confirm, override.** A machine fact is discovered
by the code, shown to the human, and used only once confirmed. A configured
value is the *override* for when derivation fails, and it records why it was
needed. Configuration is never the first source for a fact the machine can
observe about itself.

This is not new doctrine. It is `Claude_Migration`'s, stated in
`app/capture.py`:

> **Resolve, don't assume** -- store roots are enumerated from
> `%LOCALAPPDATA%\Packages`, shown to the human, and overridable; never
> silently guessed.

and its counterpart in `resolve_stores()`: *"Never guesses: what is returned is
what was found, including 'nothing'."* Multiple installs are reported and the
run proceeds; that is 0031's witness posture applied to path resolution.

Compare this repo's instruction for the same value, in `machines.json`:

> *"The packaged-app id in the Cowork path is per-install; find it by browsing
> to `%LOCALAPPDATA%/Packages` and looking for the `Claude_*` folder."*

One tool enumerates the directory. The other asks a human to enumerate it and
type the answer into a file, on a different machine from the one being
described. The second is why a wrong path can persist unnoticed, and the first
is why an unconfigured machine belonging to someone outside this estate ran the
tool successfully on the first attempt.

**What this changes in practice.** `cli_transcripts_home`,
`cowork_transcripts_home`, `push_transport` and `backup_transport` are all
derivable -- the last two already are, auto-picked by platform, with config as
an explicit override. That is the correct shape; it simply has not been applied
to the paths.

**A derived value must still be reported.** 0050's posture is that a source
declares its own staleness and one it cannot reach reads as *unknown*, never
as fresh. A derivation that silently falls back to a guess breaks that. Report
what was found, including nothing.

**Not true today.** Nothing in this repo derives a store root. Every path in
the machine layer is typed.

---

## 4. One precedence ladder

**Exactly one order, everywhere, for every value:**

```
tool policy  <  estate policy  <  operator file  <  machine file  <  environment
```

Environment variables sit at the top and are a **debugging override only**.
They are the right tool for pointing a run at a different vault for an hour;
they are never where a value lives. Every value resolved from the environment
must be reported as such by §6's origin rule, so a run configured by a stale
shell is visible rather than mysterious.

**A value is resolved once, at the edge, and passed inward as an argument.**
No module reaches for `machine()` in the middle of its work. This is the
property that produced §1's four ladders by its absence: every call site that
resolves configuration for itself invents its own order, and nothing can force
those orders to agree. `Claude_Migration` has the property --
`discover_cowork_store(root)`, `build_pack.py --snapshot <path>`, everything
downstream a pure function of what the edge resolved -- and it is the larger
half of why that repo is the more legible of the two.

**Not true today.** Four ladders, and `db.py` resolves at import time.

---

## 5. The packaging boundary

**A tool packaged out of this repo carries no estate configuration, and
reaching for it fails loudly rather than working quietly.**

This is already built, and this section promotes it from one repo's good
instinct to a rule. `Claude_Migration/vendor/l5gntools/config.py` is a stub
package that exists only to satisfy a static import; its `machine()` raises
immediately if it is ever called. `vendor/PROVENANCE.md` states why: the
vendored module's module-level `from l5gntools.config import machine` runs on
load whether or not `machine()` is used, so vendoring the file alone moves the
failure rather than removing it. The stub *"exists as a loud failure mode, not
a working implementation"*.

The consequence is that handing that tool to someone outside this estate
shipped no host list, no paths and no project names -- by construction, not by
luck (0051's standard: bounded by construction rather than by intention).

**Three properties a packaged tool must have:**

1. **No estate or operator layer.** If the code cannot run without one, the
   dependency is the defect.
2. **Estate-shaped imports stubbed to raise.** Not defaulted, not silently
   empty. A quiet default on a stranger's machine produces a confident answer
   about an estate that is not there -- the same failure `UnknownHostError`
   refuses here.
3. **Vendored code pinned, never forked**, with the origin commit and a
   content hash recorded, and the hash re-checked at run time and *reported*
   rather than repaired (0045). `Claude_Migration` **0005** and its
   `pack_builder/vendor_check.py` are the reference implementation.

**Cross-repo citation.** `Claude_Migration` **0001** adopts a named list of
this repo's rulings, and anything not on that list does not bind there. That
is the mechanism this estate otherwise lacks: method that crosses a boundary
usually leaves no trace, because a convention adopted whole cites nothing. Any
future package out of this repo declares its adopted list the same way. The
repo prefix for that log is not yet registered under 0043 and should be.

**True today**, in `Claude_Migration` only. Nothing in this repo states it.

---

## 6. The key registry

Every key declares its layer. **A key in the wrong layer is a defect whether
or not it currently works**, and a key not listed here is not configuration
yet -- adding one is an edit to this table, not a decision made at the moment
a value is needed.

Layers: **T** tool policy · **E** estate policy · **M** machine fact ·
**O** operator fact · **C** corpus, not configuration (§7).

| Key | Lives today | Belongs | Note |
|---|---|---|---|
| `role` | `local.json` | **E** | We decide it; it varies per host |
| `estate` | `local.json` | **E** | |
| `mesh` | either file | **E** | Flag, 0036. Wants a stated lifecycle |
| `authors` | either file | **E** | Becomes an artefact declaration -- §7 |
| `roots[].scope` | `local.json` | **E** | 0012: declared on the producer's root |
| `roots[].is_project` | `local.json` | **E** | 0020 |
| `roots[].path` | `local.json` | **M** | The key §1's divergence was in |
| `cli_transcripts_home` | `local.json` | **M** | Derivable -- §3 |
| `cowork_transcripts_home` | `local.json` | **M** | Derivable -- §3 |
| `chronicler_home` | `local.json`, env | **M** | |
| `vault` | `local.json`, env | **M** | |
| `estates_dir` | `local.json` | **M** | |
| `code_root` | `machines.json` | **M** | |
| `urls_file` | `local.json` | **M** | Already an override, correctly |
| `push_transport` | `local.json` | **M** | Already derived; override only |
| `backup_transport` | `local.json` | **M** | Already derived; override only |
| `governor_profiles` | `local.json`, **runtime-written** | **M** | Learned on the machine; destroyed by a whole-file ship |
| `push_target` | `local.json` | **O** | Names a person's vault |
| `backup_target` | `local.json` | **O** | |
| `pull_backup.*` | `local.json` | **O** | |
| `curator_models` | `local.json`, **runtime-written** | **O** | A choice, over a machine capability |
| `authors.json` aliases | tracked | **O** | Git identity. Estate-wide today; wrong the moment a second person commits |
| `_hostname` | injected | **T** | |
| `_matched` | injected | -- | Always `True`; 0048 clause 4 says remove it |
| `project_registry.json` | `config/` | **C** | §7 |
| `project_wizard.allow.json` | `config/` | **C** | §7, and 0042 clause 2's debt |
| `*_conversation_map.tsv` | `config/` | **C** | §7, 0040 clause 4 |
| `model_bench/lmstudio_settings/*` | `config/` | **C** | Fixtures |
| `wizforge.manifest.json` | repo root, **tracked** | **M** | Tracked, with four hardcoded absolute paths to one machine's venv -- the inverse of `local.json`'s defect |
| `CHRONICLER_HOME` | env | override | §4 |
| `CHRONICLER_DB_PATH` | env | override | §4 |
| `CHRONICLER_REGISTRY_PATH` | env | override | §4 |
| `CHRONICLER_REGISTRY_GROUPS` | env | override | Second resolver for one file -- §1 |

**Origin is reported.** Every resolved value can name the layer and file it
came from, and a command exists to print all of them. `git config
--show-origin` and `npm config ls -l` are the reference behaviour. Absent it,
a divergence between two machines is discoverable only by two people putting
documents side by side, which is how §1's stale root was actually found.

**Malformed configuration fails loudly.** Today `config._load` returns `{}` on
malformed JSON and never raises, so a typo is indistinguishable from an absent
file -- `config/README.md` records this as deliberate. It should not survive:
`UnknownHostError` and INTENT §5 refuse confident-empty everywhere else in
this repo, and this is the same failure in a quieter coat. An unknown key
should be as loud as a malformed file, because a misspelled key is the silent
failure that remains once malformed JSON is caught.

**Not true today.** No origin reporting and no key validation. The layer column
is a target: today every key in the first four groups sits in one of two files
with no layer distinction at all, so the table describes where each *belongs*,
not where each *is*.

---

## 7. The estate corpus is not configuration

`project_registry.json`, both conversation maps and
`project_wizard.allow.json` live in `config/` and are not configuration. They
are **curated data with a review lifecycle**, and the tell is that each has
properties no actual config key has:

- a ratification fingerprint committed beside it (0040 clause 4)
- a declared author, per artefact (0053 clause 5)
- a resolution order of its own (`resolve_registry_path`)
- disclosive content -- real project names, employer codenames, conversation
  titles -- which is what forced them out of git in the first place

No key in §6's table has any of those. Configuration's job is to resolve
*where these files are found*; it is not the place they live.

**What follows from saying so.** Moved out of `config/` into a folder of their
own, three things resolve at once. `config/` becomes small enough to hold in
one's head. The disclosure problem stops being a configuration problem and
becomes a containment problem, where 0051 already has the vocabulary for it.
And `authors` stops being a config key competing for a home in a
tracked-versus-untracked argument, and goes back to being what 0053 clause 5
actually describes -- a declaration about artefacts. That last one dissolves
the open question the work task force raised in
`2026-08-25_REPLY_harness_census`: once `authors` is estate policy and travels
by `git pull`, *"no host declares it"* and *"the declaration has not arrived
yet"* stop being the same input.

It also ends the collision between `authors.json` (git identity aliases, an
operator artefact) and the `authors` key (artefact authorship, estate policy),
which today sit in one folder meaning two unrelated things.

**Not true today.** All four remain in `config/`.

---

## 8. What travels, and how

| Layer | Mechanism | If it is missing |
|---|---|---|
| Tool policy | ships in the repo | the code is broken |
| Estate policy | `git pull` | a failed pull says so |
| Machine facts | derived on the machine; never shipped | derivation reports what it found, including nothing |
| Operator facts | authored by that person; never shipped | that person is not configured, reported as such |
| Estate corpus | hand-carried, fingerprinted, per 0040 clause 4 | reported as unknown, never as current (0050) |

**No layer is ever shipped by whole-file overwrite.** A file that one machine
writes at runtime (§1) and another machine overwrites wholesale cannot keep
anything, and the loss is silent on both ends. This is the single rule that
would have prevented §1's divergence, and it is a rule about *transport*
rather than about care.

**Nothing here is a channel, and nothing here runs unbidden.** 0036 stood down
the mesh because a standing channel keeps running whether or not anyone decided
it should. Layers travel when a person decides they should, except estate
policy, which travels by the `git pull` a person runs.

---

## 9. Not a gate -- and what a gate would cost

Nothing enforces this file. `verify.py`'s auditors do not read it, and exactly
one of the thirteen -- `auditor_conversation_map_pin` -- touches `config/` at
all, covering one artefact's fingerprint rather than any configuration. No
auditor reads a config file's contents, and none checks a claim made *about*
one, which is why `config/README.md`'s wrong tracked-files table survived and
why the same class of error was found by a consumer rather than here.

Enforcement is available and cheap, in this order:

1. **An auditor that reads §6's table** and reports any key present in a layer
   the table does not permit. Purely mechanical, and it generalises the
   question 0053 raises about one key into a rule about all of them.
2. **An auditor over `config/README.md`'s claims** -- tracked-versus-untracked
   is checkable against `git ls-files` and would have caught all four of §1's
   wrong claims the day they were written.

Both **report**; neither gates. 0053's own finding is that a check which can go
red without a defect belongs outside the gate, and a config layering complaint
on a half-migrated tree is exactly such a check.

**Not built, deliberately, for now.** The table has to be true before something
enforces it, and today the layers it names do not exist as files. An auditor
written first would be red on every run, which trains the eye past it (0048
clause 4).

---

## 10. The check, before you add or move a config value

1. **Can the machine observe it?** Then it is not configuration -- derive it,
   report it, and take an override only if derivation fails (§3).
2. **Who is entitled to decide it** -- the code, the estate, the machine, the
   person? That answer is the layer, not "does it vary per machine" (§2).
3. **Does it have an author, a fingerprint, or disclosive content?** Then it is
   corpus, not configuration (§7).
4. **Add it to §6's table.** A key not in the table is not configuration yet.
5. **Resolve it at the edge and pass it inward.** Never reach for `machine()`
   mid-call-graph (§4).
6. **Would a packaged tool need it?** If yes, it belongs in tool policy. If it
   would need the estate layer, the dependency is the defect (§5).
