# Convention — documents

**Scope: this repo, `L5GN-Tools`.** It is the authority `docs-archivist`,
`decision-scribe` and `consultant-docs` cite under **0052** clause 3; where a
skill and this file disagree, this file wins and the skill is amended.

**Status: `proposed`.** It may be read and followed now; it is not authority to
cite until it is ratified by a re-read on a later day.

**Promoted from `docs/README.md`**, which is where this convention was written
and worked while filed as a folder map. §2 (doc classes) and §3 (the archiving
convention, the stamps, and why the auditor stops at the archive door) are the
promotion the round asked for. **§1's precedence rule, §4's `investigation/`
rules and §5's retired classes came with them**, because each is a rule that
existed nowhere else and leaving it behind would have left the README holding
authority. `docs/README.md` is reduced to a map and a set of pointers in the same
commit, per **0052** clause 2: a rule copied into a second file is the copy a
later reader will believe.

**Adopted from:** repo `WizForgeAnalytics`, file `docs/CONVENTION_docs.md`, read
from the `wizforge-mirror-2026-08-26` snapshot on **2026-08-27** under **0051**
clause 1(b). Four things are borrowed and are marked at each: its **§0**
governing rule, the **shape** of its §2 class table, its **§2a** entire, and its
**§6**. Everything else here is this repo's own, and its `context/`, `PROMPT_`,
`CONSULTANT_` and repo-skeleton sections are **not** adopted — see §5 and §7.

---

## 0. The governing rule

*(Adopted, WizForgeAnalytics `CONVENTION_docs.md` §0 — it states **0030** better
than this repo has stated it.)*

**A document earns its place by holding something that cannot be derived.**

Rationale cannot be derived — it lives in a document. Status *can* be derived,
from the filesystem, `git log`, `verify.py` and the decisions log — so it does
not. No status boards, no handoff documents, no next-session primers (§6).

## 1. The core set

Maintained, edited in place. If one contradicts the code, that is a bug in the
doc. `INTENT` / `ARCHITECTURE` / `DECISIONS` are **the trinity**; where a brief,
a report or an archived doc disagrees with the trinity, the trinity wins.

| Doc | Holds | Goes stale when |
|---|---|---|
| `INTENT.md` | Why the system is worth building. Wants, not facts. | The reason changes — not on a schedule |
| `ARCHITECTURE.md` | What the system *is*, as built — and **why the boundaries sit where they do** | The shape changes |
| `DECISIONS.md` | Append-only *why* behind each ruling. Never edited; superseded by a later entry | Never — entries are frozen by construction |
| `SPEC_Chronicler.md` | The linking/skillset spec for the ingest side | The spec is executed or superseded |

**`INTENT` / `ARCHITECTURE` / `DECISIONS` are the trinity. Where a brief, a
report or an archived doc disagrees with the trinity, the trinity wins.**

Also core, but transient: **the live round** — its brief, its report and its
walk-sheet. All three leave core `docs/` together the moment the pair completes
(§4).

`KNIGHT_PLAYBOOK.md` and `PRODUCER_PLAYBOOK.md` were archived 2026-08-08
(**0036**) — the mesh they operate is mothballed, not removed. Neither may carry
a `gate-frozen` marker's exemption while maintained; see §4.

## 2. Doc classes, and the prefix that carries them

**A document's class is carried by its filename prefix, not by its directory.**
Documents live flat in `docs/`.

| Prefix | Class | Maintained? |
|---|---|---|
| `INTENT` / `ARCHITECTURE` / `DECISIONS` | the trinity (§1) | maintained in place |
| `README` | a folder's own map | maintained in place |
| `CONVENTION_` | a rule this repo owns | maintained in place |
| `RUNBOOK_` / `SPEC_` | reference beyond the trinity | maintained in place |
| `COWORK_BRIEF_` | the request handed to a thread | **frozen at writing** |
| `COWORK_REPORT_` | what a thread found or built | **frozen at writing** |
| `UAT_` | the walk-sheet, and its `_results` log | walk-sheet mutable while walked; results frozen, unless declared `INTERIM` (§4) |
| `AGENDA_` | a dated snapshot of what was open | **frozen at its date** |
| `_` (leading underscore) | **generated**; never hand-edited (**0030**) | regenerated, never edited |

Every prefix above has at least one file in `docs/` today. **`BASELINE_`,
`CATALOGUE_`, `HANDOVER_` and `CONSULTANT_` are unused here** and are listed
only so a reader knows they were considered: the first three are the work rig's
dated-snapshot classes, and `CONSULTANT_` waits on the debt named in §7.
`SOLO_PLAYBOOK.md` carries no prefix and is the one unclassified file in `docs/`;
it is named here rather than renamed, because renaming a file to satisfy a
convention written after it is the kind of tidying this estate does not do.

**Classified 2026-08-28, without a prefix and without a rename.** It was left
unclassified because nobody had said what class it was in, which is a different
problem from it having no prefix. The operator's framing, recorded as his:

> the same family as `RUNBOOK_` — but a slightly different layer. A runbook
> covers a **procedure**; a playbook was originally designed to cover
> **everything the operator needs**, and that is a hard gap to maintain.

That distinction is real and it carries its own failure mode, which is why it is
written down rather than folded into `RUNBOOK_`. **A procedure doc is complete
when its procedure is; an operator-complete doc is never complete, and it decays
without anything looking wrong** — no step is missing, because no step was ever
promised. It is the only class here whose staleness is invisible by construction,
and it should be read with that in mind rather than trusted the way a runbook is.

**No `PLAYBOOK_` prefix is created, and the reason is not inertia.** A prefix
with one instance would need that instance renamed to be true, and
`SOLO_PLAYBOOK.md` is cited by name in `docs/archive/` — by
`COWORK_BRIEF_solo_playbook.md`, its report and its walk-sheet, all of them
**frozen under §4**. Renaming would either break those citations or require
editing frozen documents to preserve them. The class is worth naming; the prefix
is not worth that. **If a second playbook is ever written, this decision is
reopened rather than inherited** — two instances would make the prefix worth its
cost, and this paragraph is the note to the person who writes the second one.

**A new prefix is an amendment to this file**, not a call made while naming a
file.

### The generated prefix

A leading underscore means **generated**: `_architecture_shape.md`, and
`_decisions_map.md` once it lands. **0030** governs — an authored file carries
rationale, a generated file carries shape, and a generated file is never
hand-edited. It is regenerated **in the same commit as the change that caused
it** (`CONVENTION_commits.md` §6), never in a tidy-up afterwards. Every such file
states in its own header that it is generated and names the command that writes
it.

### The permitted subdirectories

Two, and no others:

- `docs/archive/` — retired documents, stamped (§4)
- `docs/investigation/` — raw prompt-and-response exchanges (§5)

Anything else in `docs/` is a file, not a folder.

## 2a. A skill is the procedure; the file is the authority

*(Adopted, WizForgeAnalytics `CONVENTION_docs.md` §2a, entire. It is **0057**
clauses 3–6 with the reasoning behind them, and the reasoning is the part this
repo did not have written down.)*

**The document is the authority; a skill wrapping it is the procedure.** A skill
lives in the plugin directory, outside every repo — not in git, not diffable, not
reviewable — which is exactly the mis-filing that put `docs-archivist`'s
authority in a README section.

So a skill may be saved for ergonomics, and it must stay **thin**: point at the
authority, do not restate it. **A skill that restates the spec is a second copy
of the rule, and the copy is what a thread will believe.**

This repo adds one thing the source does not: **0057** clause 5 says a skill that
cannot *read* its authority stops, rather than falling back on its own text. A
thin skill and a stopping skill are the same discipline seen from two sides —
the first refuses to hold the rule, the second refuses to guess it.

## 3. The card

A unit of work is a **card**, identified by a `<slug>` shared by up to four
files. Its shape and its rules are `CONVENTION_briefs.md` §1 and are not restated
here. What matters to this file is that **the card's state is a pure function of
which of the four files exist** — which is why filenames are a tooling contract
and not a naming preference, and why `docs-archivist` can detect a finished pair
at all.

## 4. The archiving convention

### When a doc is archivable

A doc leaves core `docs/` when it is *finished*, not when it is *old*. Three
routes in:

1. **Completed pair.** A brief plus its report, where the work is built **and the
   operator has walked the UAT**. `verify.py` green proves the code works; it
   cannot prove the code does what was asked. Only the human walking the
   acceptance checks closes a pair. A pair with a green gate and an unwalked UAT
   is **not** archivable. This is a convention, not an enforced gate (§7).
2. **Superseded.** A later doc, or a DECISIONS entry, now holds the truth this
   one held. Name the successor in the stamp.
3. **Retired by class.** The doc is a kind of doc this repo has decided not to
   keep — status boards and handoff or priming docs, both derivable and both
   demonstrably rotted. See §6.

### The stamp

Every archived file gets a blockquote stamp prepended **above** its original
`# Title`, leaving the body untouched. The body is evidence; do not edit it —
say what is wrong with it in the stamp instead.

```
> **ARCHIVED** YYYY-MM-DD · <disposition> · <pair status>
> Superseded by <successor> · Original purpose: <one line — what it was for>
> <what to trust and what not to: which parts are accurate history, which parts
> later decisions moved past, and any dangling references resolved>
```

- **disposition** — `completed pair` · `superseded` · `retired` ·
  `recovered historical brief` · `recovered historical design`
- **pair status** — the partner file, or `no report — <why this had no pair>`
- **Superseded by** — a real path or a DECISIONS entry number, carrying its repo
  where the ruling is another repo's (**0043**). If nothing supersedes it, say
  what replaced the *need* for it.
- The closing lines exist to stop a future cold read from trusting stale
  content. Be specific: cite the entries that moved past it.

**Prefer `git mv`** so the rename is recorded, not a delete-plus-add.

**Archiving is human-ratified and per-card** — never in bulk, never inferred from
a green gate, and it never runs `git commit` (**0028** clause 3). The operator
reviews `git diff --staged`.

### The uat stamp

A round's results log is the one document that asserts *"this was tested"*. So a
results log in core `docs/` carries, at the top:

```
<!-- uat: commit=<sha> dirty=<bool> host=<name> walked=<YYYY-MM-DD> gate=<Na/Mt> -->
```

`commit` and `walked` are required; `gate` is optional but is checked against
`verify.py` when present — **omit it rather than assert a count you did not
observe.** `auditor_uat_stamp` fails the gate if the stamp is missing, if a
required field is absent, if `commit` does not resolve to a real commit in this
repo, or if `gate` contradicts the registered counts.

**It does not check whether the walk passed.** That is the point: the gate
polices where an acceptance claim came from, never whether the acceptance was
earned. `verify.py` answers *"does it work"*; a human answers *"does it do what
was asked"*; this only makes the second answer traceable to a commit.

It exists because a results log once claimed a tester count matching no version
of this tree — a stale number recovered from a retired doc in `archive/` and
laundered into a live one. With no commit on the document, *"the walking machine
was on an old tree"* and *"the number was invented"* were indistinguishable.

### An interim results log, and the one exception to the freeze

§2 says a `_results` log is **frozen**. That is right for a closed round and
wrong for a trial, and the gap was found by walking into it: a round whose exit
test is *"two weeks of live use, then a verdict"* produces a results log while
the trial is still running, and freezing it means the closing verdict has nowhere
to go.

**So: a results log may declare itself `INTERIM` and be re-walked, once per
declaration, until it declares itself closed.** The conditions are all four,
because any three of them describe a log being quietly rewritten:

1. **It says so at the top, in its own title**, at the moment it is first
   written — never retrofitted when a revision turns out to be wanted.
2. **It names what it is waiting for**, concretely enough that a reader can tell
   whether it has happened. *"Until the trial reaches ten ruled cards"* qualifies;
   *"until the trial matures"* does not.
3. **Every re-walk re-cuts the uat stamp** to the commit it ran against, so each
   revision is traceable to a tree the way a first walk is.
4. **A superseded verdict is marked superseded and left standing**, never
   deleted. The log's product is what was believed when — the same reason
   `CONVENTION_decisions.md` §4 keeps wrong claims in place.

**Everything else stays frozen**, including every item the re-walk did not touch.
An interim log is not an editable document; it is a frozen document with a named
hole in it, and the hole closes once.

**Found 2026-08-28**, when `UAT_desk_stale_card_results.md` was re-walked to close
D7, D8 and D9. It had been stamped `INTERIM` by an explicit operator call on
2026-08-19 and its own closing line promised the re-walk, so revising it was what
the file asked for — but §2 said frozen and nothing said otherwise, so the walk
had to argue its own legitimacy in a paragraph instead of citing a rule. This
section is that rule.

### The gate-frozen marker

A live doc's *"N auditors + M testers"* claim is checked against `verify.py`'s
live counts by `auditor_doc_claims`. That claim goes stale the moment a later
round legitimately adds a tester — the doc is not wrong, it is *finished*. A doc
that has earned that status may say so explicitly, in its first ~15 lines:

```
<!-- gate-frozen: commit=<sha> -->
```

The marker exempts that file's compound-count claims from the live-count diff.
**It must earn the exemption:** `commit=` is required and must resolve to a real
commit in this repository; a missing or unresolvable sha is itself a violation,
not a silent pass — you cannot fake-freeze a doc.

The marker is for **finished docs only**. A handful of docs are maintained, not
finished, and may never carry it — root `README.md`, `docs/README.md`,
`docs/INTENT.md`, `docs/ARCHITECTURE.md`, `docs/DECISIONS.md`. A marker found in
any of those is a violation. That is the same list §1 treats as maintained and
`docs-archivist` refuses to archive — **keep the two in sync.**

### Why the auditor stops at the archive door

`auditor_doc_claims` scans root `README.md` and `docs/*.md` — **non-recursive**,
so `docs/archive/` and `docs/investigation/` are exempt by design. That exemption
is the point: a round-1 report recording the gate count of the day was *true when
written*. Forcing it to match today's counts would edit testimony to fit the
present — exactly the drift the auditor exists to catch, run backwards. Archived
docs are frozen; live docs are checked.

**A live doc whose numeric claims have gone stale should be fixed or archived,
never exempted in place.**

## 5. `docs/investigation/` — the decision

**It survives.** It is not retired, and no `context/` is created at the repo root.

The estate this convention was adopted from retired its own `investigation/` in
favour of a gitignored `context/`. That decision does not transfer, for four
reasons, stated so they can be argued with:

1. **Theirs was retired before it was ever populated.** Ours holds thirteen files
   spanning 2026-07-10 to 2026-08-19. Retiring an empty class costs nothing;
   retiring a populated one is a migration, and this round migrates nothing.
2. **The two classes hold different material.** Their `context/` is for material
   **the estate did not author** — vendor documents, transcripts, scraped
   sources. Their own convention says plainly that nothing the estate authored is
   ever filed there, and that an investigation *is* the estate's own work
   answerable to its own evidence rules. Our investigation files are exchanges
   this estate ran. By their convention they would not be eligible for `context/`
   anyway.
3. **`context/` is gitignored; these files are tracked, and they are cited.**
   DECISIONS entries name investigation files as the source of their reasoning.
   Moving cited evidence into an ignored directory would leave it on one machine
   and nowhere else — a consequence the source convention names and does not
   solve.
4. **The acknowledgement stamp has no equivalent on the other side.** The
   `<!-- actioned: … -->` line below records what an investigation *caused*.
   Retiring the folder retires a working mechanism to adopt one that was never
   used.

**What would show this wrong.** Count the files in `docs/investigation/` that are
**not** a prompt-and-response exchange this estate ran. If inbound third-party
material starts landing there, the class is doing a job it was not built for and
a `context/` becomes owed. **That count is two of sixteen** (2026-08-28):
`2026-08-19_downtier_recurrence_probe.py` is a script, not an exchange, and
`Work_Claude_UAT_chat_20260728.md` carries neither the date-first naming nor the
`1-prompt` / `2-response` suffix the naming rule below requires. Two is a
warning; four is the answer.

> **The denominator is the point, not the pair.** This read *"two of thirteen
> today"* when written on 2026-08-26 and was stale by 2026-08-27, when the
> coverage re-measure landed a prompt and a response. Nobody noticed, because
> nothing reads a convention's own arithmetic — `auditor_doc_claims` matches one
> claim shape and this is not it. **Corrected here as an instance rather than as
> housekeeping**: it is the same defect `CONVENTION_decisions.md` §2.1 recorded
> against itself the same week, and both belong on the list 0056's Consequences
> admit does not exist. **The numerator was not re-adjudicated** — three further
> files carry date-first names without the suffix and may well be exchanges named
> before the rule existed. Settling that is a pass of its own, not a line edit.

Nothing is moved by this section, including those two files.

### What the class holds

A thread's **starting prompt** and its **final response**, kept verbatim,
whatever the model. A Cowork round's output file is a response; the brief that
opened it is a prompt. The point is provenance: the trinity says what was decided
and why, and this folder holds the exchange the decision came out of, so a cold
read can check the reasoning against its source rather than taking the log on
trust.

- **Never maintained, never corrected, never graduates to core.** A captured
  exchange is evidence; editing it destroys the thing it is kept for. Wrong turns
  and abandoned reasoning stay in.
- **No archive stamp.** Investigations are not archived, because they were never
  live — they are born frozen. The one stamp they may carry is the
  acknowledgement stamp below.
- **Nothing here asserts current truth.** A core doc may cite an investigation as
  the *source* of a decision; it may not defer to it for what is true now.
- Outside `auditor_doc_claims`' scan, for the same reason `archive/` is (§4).

### Naming

```
YYYY-MM-DD_<topic>_<model>_1-prompt.md
YYYY-MM-DD_<topic>_<model>_2-response.md
YYYY-MM-DD_<topic>_<model>_3-thread.md     (optional: full export, when it lands)
```

Date first so the folder stacks chronologically; topic before model so both ends
of one exchange sit together; the numeric prefix guarantees prompt sorts above
response regardless of the words. Lowercase, hyphens inside a field, underscores
between fields.

### The acknowledgement stamp

An investigation records what was found. Nothing recorded whether anything *came
of it* — that answer lived only in the thread, which then evaporated. So a
response file may carry, as its **first line, above the `# Title`**:

```
<!-- actioned: YYYY-MM-DD · <finding-id> · <commit-sha|DECISIONS NNNN> · <one line: what was done> -->
```

This does not contradict *"never maintained."* It is the same move §4 makes for
archived docs — **the body is evidence; say what happened to it in the stamp
instead.** An acknowledgement is metadata *about* the document, not a correction
*of* it, and it lives above the title where the body is not. The archive stamp is
terminal and asserts a disposition; this one asserts nothing about status. **The
file never moves.**

1. **Append-only, one line per actioned finding.** Never edited, never removed. A
   reverted action is another line, not a deletion.
2. **Strictly backwards-looking.** It records what *was* done. A line saying what
   *should* be done is the stale forward-look that killed the handoffs (§6) and
   is a violation.
3. **The anchor must resolve** — a commit sha in this repo, or a DECISIONS entry
   number. Same bar as the uat stamp's `commit=` and the `gate-frozen` marker: an
   unresolvable anchor is a violation, not a silent pass.
4. **The body is never touched.** Not the numbers, not the reasoning, not a
   hypothesis the investigation itself disproved.
5. **No actioned lines is a normal state, not a failure.**
   `<!-- actioned: (none yet) -->` is complete and honest.

Not enforced by the gate (§7). Making it machine-checkable — resolving each
anchor the way `auditor_uat_stamp` resolves `commit=` — is a small auditor and a
separate decision; do not assume it by writing the stamp.

## 6. Do not recreate

*(Adopted, WizForgeAnalytics `CONVENTION_docs.md` §6, merged with this repo's
own §5-as-was, which reached the same rule from its own autopsies.)*

Two classes are permanently retired, both derivable and both demonstrably prone
to rot:

- **No status or next-session board.** `NEXT_SESSION_PLAN.md` contradicted itself
  on the tester count *lines apart*, in the document warning against exactly that
  rot. Status is derived: `verify.py`, `git log`, the card files, the decisions
  log.
- **No handoff or priming document.** `HANDOFF.md` held facts-with-numbers that
  drifted and cited a `CHANGELOG.md` that never existed. Priming a fresh thread
  is the trinity's job.

Forward-looking items — *"what we agreed but haven't built"* — are carried
manually into the next thread, not written down. **A written forward-look ages
into a false commitment**, and that is what killed the handoffs. Both retired
files are in `archive/` with their autopsies attached.

## 7. What is not enforced

Honest list, so nothing above reads as stronger than it is. **0048** clause 4:
a check that cannot fail trains the eye past it, so the gaps are named.

- **Nothing checks a document's class or prefix.** One file named without its
  prefix is invisible to every tool and every reader scanning by class. Folders
  would have made that impossible; §2 takes the risk knowingly, and
  `SOLO_PLAYBOOK.md` is the standing example of it.
- **Nothing checks that a UAT was walked** before a pair is archived, and nothing
  ever will — that judgement is human. `auditor_uat_stamp` narrows the gap by
  checking the *provenance* of the claim, never the claim.
- **`auditor_doc_claims` cannot distinguish a doc asserting a gate count from a
  doc quoting one.** The `archive/` and `investigation/` exemptions are the
  current answer, which means a live report quoting a count reds the gate until
  its pair closes.
- **Nothing checks that a generated file was regenerated in the commit that
  caused it.** §2's underscore rule is discipline; `auditor_architecture_current`
  checks one such file's currency and nothing checks the rest.
- **`docs/Consultants/` does not exist**, and the `consultant-docs` skill points
  at it. Until either the directory or a `CONVENTION_consultants.md` lands, that
  skill has no authority in this repo and stops (**0057** clause 5). The debt is
  named here rather than discharged by inventing a class with zero instances.
