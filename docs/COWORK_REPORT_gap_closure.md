# Cowork report — gap_closure

Against `docs/COWORK_BRIEF_gap_closure.md` and its walk-sheet
`docs/UAT_gap_closure.md`. Built **2026-08-27** on `LucasGoonPC`, in
`C:\Users\timps\Documents\GitHub\L5GN-Tools`.

Testimony about a moment. The numbers were true when written and are not claims
about now.

**Four of six tasks landed. Task 3 is stopped and Task 3b is held.** Nothing was
committed by the thread (**0028** clause 3); three commit messages are drafted
under `data/git_warden/` and the commands are handed back.

---

## 0. What the brief got wrong about the tree

The brief's draft-status note says every "already exists" claim was checked while
drafting, and asks that they be re-verified as the round's first act. They were.
**Six claims had moved, and one of them voided a whole task.** This section is
first because the brief says it is the most valuable line in the report.

**1. The mirror was not where the brief said, then was.** The brief names
`…\wizforge-mirror-2026-08-26_Unpacked\WizForgeAnalytics\docs\`. The path under
`GitHub\WizForge\WorkRig_Snapshots\` holds **bundles only** — `MANIFEST.md` and
two `.bundle` files, Steps 8–10 of `RUNBOOK_wizforge_mirror.md` never run. The
stop condition *"a named convention file is not where this brief says → stop for
that task"* tripped for **Tasks 1, 2, 4 and 5**, and the round halted there and
reported. The operator then named the real location — a **second**
`WorkRig_Snapshots` tree under `Documents\Backups\` — where the unpacked
`WizForgeAnalytics\docs\` does exist with all four convention files. **The stop
was correct and it was retracted on evidence, not on a guess.** Two snapshot
trees with the same name in two places is the finding worth keeping.

**2. The five skills are already tracked.** This voids Task 3a. Detail in §3.

**3. `CLAUDE.md`'s debt line *"Skills are not tracked in this repo yet"* is
false**, for the same reason.

**4. Task 6's stated model is wrong.** The brief says `run.py` registers
subcommands with `sub.add_parser(...)` and names `pin bump` at line 886 as the
nearest model. `run.py`'s top level is a single positional `command` argument and
a flat `if args.command == …` chain; the `sub.add_parser` at 886 is **inside**
`_cmd_pin`, and `pin` is intercepted *before* argparse runs. The correct model is
`render-architecture`, and that is what was followed.

**5. `CLAUDE.md`'s command table is wrong, and the brief inherited it.** Both say
`python run.py architecture`. **No such command exists.** The scanner is
`architecture_census`, and `run.py render-architecture` regenerates both the JSON
and the doc from one scan. By `CLAUDE.md`'s own rule — *"if this file and the
thing it points at disagree, the thing it points at wins and this file is the
defect"* — the map is the defect.

**6. The brief's spine figures are wrong.** It states `0025` (×10), then `0007`,
`0013`, `0032`, `0033`, `0040` at ×5 each. The generator measures **`0040` at
×7**, not ×5, and the brief omits `0042` and `0045`, which are also ×5. `0025`
at ×10 is correct. §6 has the list.

Two smaller ones: the brief's widening says *"`skills/` holds `SKILL.md` files
and nothing else"*, which was already untrue when written — `skills/dtr/` also
holds `dtr.skill`. And the work rig's conventions each carry a **§8** the brief's
section inventory never mentions.

## 1. Per convention adapted — what transferred, what changed, what was declined

All four were read from
`…\Backups\WizForge\WorkRig_Snapshots\wizforge-mirror-2026-08-26_Unpacked\WizForgeAnalytics\docs\`,
**one named file per task and no other**, under **0051** clause 1(b). Each
adoption is named in its own header with origin repo, origin file and date
(**0057** clause 7).

### `docs/CONVENTION_decisions.md` (Task 1)

**Transferred close to whole:** their §1 (one log, one place), §2 (the entry
shape — metadata line and four sections, *"What would show this wrong"*
mandatory, concrete, and **not retrofitted**), §4 (append-only, and the freeze
attaching at **acceptance, not commit**), §5 (the five status values), §7
(superseding, stating which clauses survive), §8 (starting a log where none
exists), §9 (propose and ratify; a thread never ratifies), §10 (what is not
enforced).

**Changed:**

- **Scope** — theirs opens *"every repo in the estate"*, meaning MCF. Ours is
  this repo.
- **§3 rewritten entirely, and the brief's instruction on it declined.** The
  brief says *"Prefix is `l5gn-`"*. **No such prefix exists.**
  `CONVENTION_commits.md` §5 declares none, and **0043** settles the ambiguity
  the other way: a bare number means this repo's log, and another repo's ruling
  carries that repo. The work rig's own §3 says *"a prefix that
  `CONVENTION_commits.md` §5 does not carry may not be invented"* — so
  inventing `l5gn-` would have broken the very rule being adopted. §3 states the
  bare-number rule, cites 0043 for the mechanism, and **reproduces none of its
  examples**, which also clears the walk-sheet's grep for `wfa-`/`sfds-`.
- **§0 restated.** Theirs recounts a ruling citing a convention that was never
  written. Ours was found differently — by the workflow map on 2026-08-26,
  finding `decision-scribe` carrying the entry format in its own text, which
  **0052** clause 3 forbids. Both are named.
- **§5 and §6 carry this repo's real practice rather than theirs.** Forty-six
  entries carry a bare `accepted` with no date and three carry `accepted <date>`;
  the date is required going forward and **the bare ones are not retrofitted**.
  Supersession is recorded on the **superseding** entry here (`Supersedes:` /
  `Amends:`), the opposite of their 0026 clause 1 — adopting theirs would have
  required editing frozen bodies to backfill fragments, which §4 forbids. The
  cost is stated: a reader of a superseded entry sees no warning.
- **`0036` carries no `**Status:**` field at all.** Found while surveying; it is
  frozen, and §5 names it so a tool counting status lines expects 56 across 57.

**Declined:** their **§6** ("a living register is not a decisions log") entire.
It rules on `ValidationAutomation`, which does not exist on this side of the
wall, and its own closing paragraph admits it binds a repo that did not ask.
Nothing of it is carried, not even as a caution — and the header says so.

### `docs/CONVENTION_briefs.md` (Task 2)

**Transferred close to whole:** their §0 (a brief is a request frozen at the
moment of asking), §2 (brief and walk-sheet are one act, written before the
build), §3 (the parts of a brief), §4 (`[G]`/`[H]`, *"every `[H]` is a cost,
count them"*, and an `[H]` forced by an awkward design being a **design
finding**), §5 (the report), §8 (what is not enforced).

**Changed:**

- **§1 replaced.** Theirs is `<NN>_<slug>`, numbered per project from a
  `REGISTRY_projects.md`. This repo has neither, and the brief forbids inventing
  them. Ours is `COWORK_BRIEF_<slug>.md`, and §1 says in terms that no numbering
  or registry is to be introduced to make the adaptation symmetrical.
- **§6 corrected on the gate.** Theirs says *"no MCF repo has a gate"* and
  forbids a `gate=` field. Verified here: `git config --get core.hooksPath`
  returns **`.githooks`**, `.githooks/pre-commit` runs `verify.py`, and this
  repo's uat stamp **does** carry `gate=`, checked by `auditor_uat_stamp`. §6
  states what is true here and keeps `gate=` optional.

**Added, and it is ours rather than theirs:** §3 item 1 — **a brief opens with
where it is (repo and host) and what to read first.** Marked in the document as
not adopted. `COWORK_BRIEF_gap_closure.md` is the worked example, and the
evidence for the rule is that its opener was added after it was drafted without
one.

**Declined:** their **§7**, the orientation-round pattern for seven migrating
repos. Not this repo's situation.

**The gap is closed.** `brief-scribe` line 12 read *"There is no written
convention for briefs yet… That gap is real and this skill is the drift risk
until it closes."* The line is now false. **The skill itself is unedited** —
correcting it is Task 3b, which is held.

### `docs/CONVENTION_docs.md` (Task 4)

**Promoted from `docs/README.md`:** §2 (doc classes) and §3 (the archiving
convention, the archive stamp, the uat stamp, the gate-frozen marker, and why
`auditor_doc_claims` stops at the archive door) — the promotion the brief asked
for. **§1's precedence rule, §4's `investigation/` rules including the
acknowledgement stamp, and §5's two retired classes came with them**, because
each is a rule that existed nowhere else and leaving any of them behind would
have failed the walk-sheet's *"`docs/README.md` no longer holds a rule that
exists nowhere else."* `docs/README.md` went from **14,179 bytes to 2,376** and
is now a map and a set of pointers.

**Borrowed, each marked at the point it appears:** their **§0** (*"a document
earns its place by holding something that cannot be derived"* — it states
**0030** better than this repo stated it); the **shape** of their §2 class
table; their **§2a entire** (a skill is the procedure, the document is the
authority, and a skill that restates the spec is a second copy of the rule);
their **§6** (no status boards, no handoff or priming documents), merged with
this repo's own version, which reached the same rule from its own autopsies.

**Two additions that are ours:** §2's **generated prefix** — a leading
underscore means generated, never hand-edited, regenerated in the commit that
caused it — which the source has no equivalent for and which `_decisions_map.md`
now needs. And §2a's closing paragraph tying **0057** clause 5 to the thin-skill
rule: a thin skill refuses to hold the rule, a stopping skill refuses to guess
it.

**Declined:** their `context/` section, their `PROMPT_` class and
`docs/prompts/`, their `CONSULTANT_` class, and their §7 repo skeleton. The
first is §5's decision below; the rest are other estates' furniture.

**No rename is demanded by the class table.** Every prefix in it has a real file
in `docs/` today, and the four unused ones are marked unused. `SOLO_PLAYBOOK.md`
is the single unclassified file and is **named rather than renamed** — renaming a
file to satisfy a convention written after it is not something this estate does.

### `docs/CONVENTION_gitignore.md` (Task 5)

**The mechanism transferred; the contents did not**, which is what the brief
asked for. Carried across: block first, two marker lines, nothing above the
lower marker edited locally, and **exceptions expressed as a commented negation
below the line** — because git applies patterns in order and a negation above its
pattern silently does nothing, does not error and does not warn. Their reasoning
on secrets is carried in full, including the cost: **extensions and exact names
only, never `*secret*`-style substring patterns**, which match anywhere in a path
and would swallow a `CONVENTION_secrets.md` or a `token_parser.py` — and
therefore **a file named `salesforce_credentials.txt` passes the baseline.**

**Declined from their block:** the data-export extensions (`*.csv`, `*.tsv`,
`*.xlsx`, `*.xlsm`, `*.xls`), because bare path-independent rules would ignore
such a file anywhere and this repo is a toolkit where a fixture is plausible;
`context/**`, because §5 of `CONVENTION_docs.md` decided there will be no
`context/`; and `data/git_warden/`, which is already covered here by `/data/`.

**The one thing the block adds: this repo has no secrets rules at all.** No
`.env`, no `*.pem`, no `*.key`. That gap is the reason to adopt it.

**`.gitignore` itself was not touched**, as the brief requires. §3 of the
document says exactly what the file would have to change, and that change is its
own round.

## 2. Task 3a — stopped, and why

**The brief's premise is false.** It treats the five skills as "configured
copies" outside the repo and `skills/` as a new home needing a deliberate
widening. Git:

```
$ git ls-files .claude/skills/
.claude/skills/brief-scribe/SKILL.md
.claude/skills/commit-scribe/SKILL.md
.claude/skills/consultant-docs/SKILL.md
.claude/skills/decision-scribe/SKILL.md
.claude/skills/docs-archivist/SKILL.md
```

**All five are already tracked.** Copying them into `skills/` byte-identical
would therefore have produced **two tracked copies of the same five files in one
repo** — precisely what **0057** clause 1 forbids and what this round exists to
prevent. The task as written is a `git mv`, not a copy.

Which direction the move runs is a second question, and it is not this round's
to answer. `.claude/skills/` is the path Claude Code loads project skills from,
and all five were live in the session that built this round. **`skills/` is not a
load path**: `dtr` sits there with a packaged `dtr.skill` beside it and was **not
loaded**. The two directories are doing different jobs — one publishes, one
loads — and `skills/` being the publication surface is consistent with **0057**
clause 1 and with `dtr` as precedent. But the move has a live side-effect: **the
moment it lands in the working tree the five stop loading**, before anything is
committed.

The brief's own out-of-scope list says a convention covering the repo's root
layout is a later round. **So Task 3a is stopped, nothing was created, moved or
edited, and no `sha256` list is offered** — a fingerprint for a copy that should
not be made would be evidence for the wrong thing.

**Consequence for the round's deliverable:** *"five skills tracked under
`skills/`"* is not met, and cannot be met without settling the
publish-versus-load split. **`skills/` is not created**, so the brief's one
deliberate widening was not taken.

## 3. Task 3b — held

Held by the operator, and by the brief, until **0057** ratifies. **No skill file
was edited.** What each skill's declared authority would resolve to after Tasks
1, 2 and 4 — the useful half of the answer — is §4.

## 4. Per skill: the authority, and whether it resolves

Measured against the tree as it stands after this round, **without any skill
being edited**. "Resolves" means the file the skill names now exists here.

| skill | authority it names today | resolves now? |
|---|---|---|
| `commit-scribe` | `docs/CONVENTION_commits.md` | **yes** — already did |
| `docs-archivist` | `docs/README.md` §3 | **no longer** — §3's rules moved to `CONVENTION_docs.md` §4 this round |
| `brief-scribe` | none; carries the format in its own text | **n/a** — `CONVENTION_briefs.md` now exists for it to cite |
| `decision-scribe` | none; carries the format in its own text | **n/a** — `CONVENTION_decisions.md` now exists for it to cite |
| `consultant-docs` | `docs/Consultants/` | **no** — the directory does not exist |

Three things follow, and the third is the round's most awkward result.

**`brief-scribe` and `decision-scribe` now have real authority to resolve to**,
which was Tasks 1 and 2's point. Neither cites it yet; that edit is 3b.

**`consultant-docs` is left stopping, and no convention was invented to satisfy
it.** That is **0057** clause 5 working as designed. The work rig **retired**
this class (`wfa-0025` clause 6) and `CONVENTION_docs.md` §7 names the debt
rather than discharging it. A `CONSULTANT_` class with zero instances is the
work rig's own named anti-pattern and this round declined to import it.

**Task 4 broke `docs-archivist`'s pointer.** It cites `docs/README.md` §3, and
§3 no longer holds those rules. The skill is unedited because 3b is held, so
**between this round and 3b, `docs-archivist` points at a section that still
exists but no longer decides anything** — a pointer landing somewhere plausible
and wrong, which is the exact failure the brief's opening section says the round
exists to prevent. It was produced *by* the round. It is recorded here rather
than patched, because patching it is 3b's job and doing it early would put an
uncommittable edit in a held task's territory.

## 5. The `docs/investigation/` decision

**It survives.** No `context/` is created. Reasoning is in `CONVENTION_docs.md`
§5 in full; in short:

1. **Theirs was retired before it was ever populated** (their §2). Ours holds
   thirteen files spanning 2026-07-10 to 2026-08-19. Retiring an empty class
   costs nothing; retiring a populated one is a migration, and this round
   migrates nothing.
2. **The classes hold different material.** Their `context/` is for what the
   estate **did not author**. Their own §5 says nothing the estate authored is
   ever filed there, and that an investigation is the estate's own work. Ours
   would not be eligible under their own rule.
3. **`context/` is gitignored; these files are tracked and cited.** DECISIONS
   entries name investigation files as the source of their reasoning. Moving
   cited evidence into an ignored directory leaves it on one machine — a
   consequence their convention names and does not solve.
4. **The acknowledgement stamp has no equivalent there.** Retiring the folder
   would retire a working mechanism to adopt one that was never used.

**What would show this wrong**, recorded before the answer is known: count the
files in `docs/investigation/` that are **not** a prompt-and-response exchange
this estate ran. **It is already two of thirteen** —
`2026-08-19_downtier_recurrence_probe.py` is a script, and
`Work_Claude_UAT_chat_20260728.md` carries neither the date-first naming nor the
`1-prompt`/`2-response` suffix. **Two is a warning; four is the answer.**

## 6. The generator's counts

`python run.py decisions-map` → `docs/_decisions_map.md`, 53,705 bytes.

- **Entries: 57.**
- **Orphans: 23**, including `0029`, `0030`, `0036` and `0043` as the brief
  predicted — all load-bearing and unreachable by following citations.
- **Spine:** `0025` **×10**; `0040` **×7**; then `0007`, `0013`, `0032`, `0033`,
  `0042`, `0045` at **×5** each. **The brief said `0040` was ×5 and omitted
  `0042` and `0045`.** `0040`'s seven citers are `0041, 0044, 0045, 0046, 0049,
  0055, 0056`, each distinct.
- **Status:** 46 `accepted`, 3 `accepted <date>`, 7 `proposed` (0051–0057),
  1 with **no status field at all** (`0036`). 56 status lines across 57 entries.
- **Falsifiers:** 10 of 57 entries carry a *What would show this wrong* section.
  The map **links to every one and quotes none.**
- **Dangling citations: none.** Every number cited resolves to an entry.
- **Cross-repo citations inside a `Builds on` window: none.**
- **Deepest thread: 10 entries, across 12 distinct chains**, merged
  position-wise as `0010 → 0025 → 0027/0032 → 0033/0038 → 0037/0040 →
  0042/0044/0045 → 0050/0051/0052/0053 → 0054 → 0055 → 0056`. The brief's stated
  thread is the same spine, extended by 0054–0056 which postdate it.

**Determinism verified.** Run twice against an unchanged log the output is
byte-identical, `cmp` clean, on every cut including the final one. **No commit sha, timestamp or host is stamped**, which
is a deliberate difference from `docs/_architecture_shape.md`: that file's
contract is provenance, this one's is reproducibility, and the two cannot both be
had.

**A defect was found and fixed during the build.** The first cut of the
cross-repo detector matched *"any word followed by a space"* before a number, so
`0025 and 0036` in 0050's citation window read as a cross-repo citation of 0036
and **silently dropped a real edge**. It is now an explicit list of repo
qualifiers, with a comment saying why: an unknown qualifier now shows up as an
ordinary edge rather than vanishing. This is worth recording because it is the
same class of failure as the round's subject — something plausible and wrong,
rather than something that fails loudly.

## 7. Stop conditions that tripped

- **`grep -c "^## 00" docs/DECISIONS.md` returns 57.** Precondition held.
- **The mirror was unreadable at the path named → tripped for Tasks 1, 2, 4 and
  5.** The round halted and reported. Retracted when the operator named the
  actual location; all four then ran. §0 has the detail.
- **Task 3a and 3b would land in one commit → did not arise.** Task 3a is
  stopped for a different reason and 3b is held.
- **A skill's authority does not exist after Tasks 1, 2 and 4 → `consultant-docs`.
  No convention was invented.** Left stopping, debt named.
- **An adaptation requires importing the work rig's card numbering or registry →
  avoided**, and the brief's `l5gn-` prefix instruction was declined for a
  related reason (§1).
- **A baseline rule would newly ignore a file git already tracks → not yet
  cleared.** The two `git ls-files` checks are outstanding; §8 carries them.
- **The generator finds a duplicate entry number → no.** The check is
  implemented and raises rather than papering over it.
- **Summarising a DECISIONS entry → refused by construction.** Titles and
  numbers only; falsifiers linked, never quoted.

## 8. Evidence still outstanding

Three answers this report does not have, all requiring git on Windows because a
sandbox mount may not be asked what git holds:

1. **`git ls-files` against the block's patterns**, which is the stop condition
   in §7 that has not cleared. Until it returns nothing, `CONVENTION_gitignore.md`
   §2's block is drafted rather than adopted.
2. **`git check-ignore -v` output for every rule in the block**, which the
   walk-sheet requires quoted here. The one rule already verified:
   `git check-ignore -v data/git_warden` → **`.gitignore:2:/data/	data/git_warden`**.
   The secrets rules will return nothing, which is correct — `.gitignore` is not
   edited this round, so they are not yet in force.
3. **Whether 0054–0057 are committed** or only in the working tree.
   `git status --porcelain` shows `docs/DECISIONS.md` as modified, so the
   precondition's word *"committed"* is unverified. The count of 57 is verified
   on disk either way.

**`verify.py` was not run.** It resolves commit shas and therefore asks git
questions, so it belongs on Windows. It is in the handback.

## 9. Notes for whoever reads this cold

**The working tree was already dirty before this round.** `git status` showed
`docs/DECISIONS.md`, `docs/COWORK_BRIEF_gap_closure.md`, `docs/UAT_gap_closure.md`
and ten files under `docs/archive/` modified, and `CLAUDE.md`, four
`CONVENTION_*.md` and `skills/` untracked. **The commit split handed back covers
only this round's files** and deliberately leaves the rest alone.

**`CLAUDE.md` is untracked.** It is the map, it carries the environment hazards,
and git is not following it. Two of its claims are wrong (§0 items 3 and 5) and
neither was corrected, because editing it was not this round's business.

**`.gitattributes` sets `* text=auto eol=lf`.** Every doc checked in this round
is LF on disk, so `CLAUDE.md`'s hazard *"the working tree is CRLF on Windows"* is
at best imprecise for `docs/`. The line-ending discipline was followed anyway and
cost nothing.

**The mirror's `MANIFEST.md` has an empty HEAD column**, with both HEADs dumped
as loose lines beneath the table. And `RUNBOOK_wizforge_mirror.md` Step 6 warns
about a stray `GitHub\WizForgeAnalytics\` derivative that **does not exist**.

**`docs/AGENDA_wave1_thread_briefs_2026-08-27.md` exists in both `docs/` and
`docs/archive/`.** Live and archived at once. Not touched.
