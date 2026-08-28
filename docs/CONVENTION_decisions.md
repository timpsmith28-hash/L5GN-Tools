# Convention — the decisions log

**Scope: this repo, `L5GN-Tools`.** It is the authority on the format of
`docs/DECISIONS.md`, and the authority the `decision-scribe` skill defers to
under **0052** clause 3 — that skill is the procedure, this file is the rule,
and where they disagree this file wins and the skill needs updating.

**Status: `proposed`.** It may be read and followed now; it is not authority to
cite until it is ratified by a re-read on a later day (§8).

**Adopted from:** repo `WizForgeAnalytics`, file `docs/CONVENTION_decisions.md`,
read from the `wizforge-mirror-2026-08-26` snapshot on **2026-08-27** under
**0051** clause 1(b). Its §§1, 2, 4, 5, 7, 8, 9 and 10 transfer close to whole.
Its **§3 is rewritten**, because its prefix rule does not describe this repo.
Its **§6 — "a living register is not a decisions log" — is dropped**: it rules
on `ValidationAutomation`, a repo that does not exist on this side of the wall,
and its own closing paragraph admits it binds a repo that did not ask. Nothing
of §6 is carried, not even as a caution.

## 0. What this discharges, and how it was found missing

Not the way theirs was. The work rig found its gap from the inside — a ruling
cited a convention file that had never been written. Ours was found from the
outside: the workflow map drawn on **2026-08-26** put every skill beside the
authority it claims, and `decision-scribe` was one of four skills whose
authority resolved to nothing here. It carries the entry format in its own
text, which **0052** clause 3 forbids, and it had been doing so for
fifty-seven entries.

That is the harder version of the same defect. A skill that names a missing
file fails visibly. A skill that carries the rule *instead* works perfectly
until a second skill carries a different version of it, and then there is no
way to say which one is wrong.

This file is what those fifty-seven entries were owed. **No entry is amended by
its arrival**, and nothing already in the log becomes non-conforming because
this document now exists — see §2's retrofit rule and §5's note on the status
line.

## 1. One log, one place

This repo carries exactly one decisions log, at `docs/DECISIONS.md`. Not two,
not one per subsystem, not a section inside a design document.

Other repos in the estate keep their own logs — `sf-data-service` does, and is
cited from here with its repo named at every mention (§3). A repo with no
rulings of its own has no
file. Absence is the correct state; an empty `DECISIONS.md` is worse than none,
because it reads as *"nothing has been decided here"* when the truth is usually
*"the decisions are somewhere else."*

## 2. The entry

A metadata line, then four sections. **The log's own last three or four entries
are the working spec** for tone and heading style; what follows is the required
shape, not a template to fill.

```
## NNNN — <the decision, stated>

**Date:** YYYY-MM-DD · **Status:** proposed · **Builds on:** NNNN (one-line
gloss), NNNN (gloss) · **Source:** what forced it · **Brief:** <file>
```

`**Date:**` and `**Status:**` are required. `**Builds on:**` and `**Source:**`
are used by almost every entry and their absence should be deliberate. The log
also carries `**Amends:**`, `**Supersedes:**`, `**Relates to:**`,
`**Convention:**` and others where they say something a `Builds on` would not;
that latitude is real and is not tidied away.

### 2.1 What `Date` means — and the fact that it currently means two things

**`Date` is the day the entry was drafted.** Not the day it was committed, not
the day it landed in the log, and never the day it was accepted — acceptance
carries its own date in `Status` (§5).

**This is stated now because the field is inconsistently populated and nothing
said which it was.** Recorded rather than quietly corrected, and each line
carries what it rests on:

- **0054–0057 carry the day they landed in the log** (2026-08-27), having been
  drafted across 25–26 August. *Source: the restamp's own reasoning, which
  existed only in an uncommitted commit-message draft until this paragraph.*
- **0017 disambiguates itself**, and its format is the precedent worth copying
  where the two dates differ and the difference matters:
  `**Date:** drafted 2026-07-21, ratified 2026-07-27`. *Source: the entry.*
- **What 0001–0053 mean is not known**, and is recorded as unknown rather than
  assumed to be the drafting date. Settling it means reading `git log` against
  each entry's landing commit; nobody has, and the answer is not needed to fix
  the rule going forward.

**Why the inconsistency is load-bearing rather than cosmetic.** §8's
different-day rule — *ratification is a re-read by the operator on a different
day than the drafting* (**0033**) — is measured **from the drafting**. Where
`Date` means "landed", the interval the rule tests starts at the wrong end and
runs short: an entry drafted on the 25th and landed on the 27th reads as two
days younger than it is. **The error runs in the safe direction** — it can only
make a ratification look less ready than it is, never more — which is why this
is a correction to make rather than an incident to investigate.

**It bites where the log is right now.** Four of the seven entries currently
`proposed` are the four whose `Date` does not mean what the other entries' does,
and they are the next entries anyone will ratify.

**What to do about the four.** Nothing, for now, and deliberately: they are
`proposed`, and a proposed entry may be corrected in place because nobody is
permitted to rely on it yet (§4 — the freeze attaches at acceptance, not at
commit). Restamping them to their drafting dates is a legitimate correction and
is **not** made here, because it would move four dates in the same act that
defines what the field means, and the definition should be citable before it is
enforced. **Entries drafted from here carry the drafting date.**

**Git is the better authority for landing dates, for every entry**, and is why
this convention does not add a second field to record one.

**The heading states the decision, not the topic.** A reader scanning headings
should learn what was decided without opening anything. *"A ruling from another
repo is cited with its repo, at every mention"* is a heading; *"Citations"* is a
filing label. Long is fine — this log's headings run to two lines and that is
correct.

**Context** — what *forced* the decision. The specific thing that stopped
working, or the choice that could no longer be deferred. If nothing forced it,
ask whether it is a ruling or a preference.

**Decision** — numbered clauses, each a rule that can be checked. *"We should
prefer…"* is not a clause. Write what is permitted, what is refused, and by what
mechanism.

**Consequences** — **including the costs.** What becomes harder, slower or
invisible; what is being given up; whether the trade is being taken knowingly.
An entry whose consequences are all benefits has not been thought through.

**What would show this wrong** — **mandatory and concrete.** Countable beats
descriptive. *"Count the schema changes per source wired — one extension across
three vindicates this, three refutes it"* is a test. *"If it turns out not to
work"* is not.

**That last section is required of new entries only, and is not retrofitted.**
Ten of this log's fifty-seven entries carry it. The rest are frozen under §4 and
stay as they are. The consequence is a permanently non-uniform log whose older
entries cannot be falsified by their own terms — the cost of append-only, paid
rather than argued.

**`docs/DECISIONS.md`'s own header names three sections**, having been written
before the fourth became practice. That header describes the log's origin and is
not the format authority; this section is. The header is not edited to match —
it is prose about why the file exists, not a spec, and rewriting it to agree
would destroy the record of when the fourth section arrived.

## 3. Numbering and citation

Four digits, zero-padded, taken **from the file** by counting entries — never
from memory and never from a summary or a generated map. Two entries sharing a
number is unrecoverable in an append-only log, and nothing detects it (§9).

**Clause numbers are frozen once the entry is accepted.** Other documents,
briefs and commit trailers cite *"0044 clause 4"* by number. Add clauses at the
end; never insert, never resequence. If a clause must change, that is §6.

**A bare `NNNN` always means this repo's log**, and a ruling from another repo
carries that repo at **every mention** rather than only in a depends-on line.
**0043** is the rule and it carries the worked example; this section does not
reproduce it, because a rule copied into a second file is the copy a later
reader will believe (**0052** clause 2).

**This repo has no prefix of its own, and one may not be invented here.**
`CONVENTION_commits.md` §5 declares none, 0043 settles the ambiguity by making
the bare number this repo's, and a prefix is a thing a *citing* repo needs
rather than a cited one. If another repo ever needs to cite into this log, the
prefix it uses is declared in `CONVENTION_commits.md` §5 at that point, by the
round that needs it.

**A `proposed` entry may not be cited as authority.** It may be read, discussed
and pointed at as a draft. A brief that leans on one says so, and says which
tasks depend on it.

## 4. Append-only

**An accepted entry is never rewritten.** Not a number, not a claim, not a typo.
A later decision supersedes an earlier one by adding an entry that says so.

**The freeze attaches at acceptance, not at commit.** An entry carrying
`**Status:** proposed` may be edited in place — body, clauses and clause
numbering — because nobody is permitted to rely on it (§3) and git history holds
what it said. That edit is declared in the commit body, naming the entry, the
clause and what changed, and does not ride with unrelated work
(`CONVENTION_commits.md` §6). Correcting a proposed entry forward, by a further
entry, is not the route.

At acceptance everything freezes except the **status line**, which is stamped at
ratification and again at supersession. Nothing else in a landed entry changes,
ever.

This is expensive on purpose. It means the log contains claims now known to be
wrong, sitting in place with their corrections attached elsewhere — harder to
read than a tidy current-state document, and that is the entire point. The log's
product is *what was believed when, and why it changed*. A log you can edit
answers no question a fresh reading of the tree would not answer better.

## 5. Status

Five values:

- **`proposed`** — drafted, not yet ratified. Not authority (§3). Three entries
  stand at `proposed` today: 0055 through 0057.
- **`accepted <date>`** — ratified. Binding, body frozen.
- **`superseded by NNNN`** — replaced, wholly or in part. Body untouched.
- **`withdrawn`** — drafted, never accepted, and no longer sought. Only a
  `proposed` entry may be withdrawn; the number stays spent and the body is
  emptied to a one-line reason naming where the substance went. Distinct from
  superseded: nothing replaced it, and it must not read as though something did.
- **`recovered`** — reconstructed from evidence rather than recorded at the
  time. See §7.

**The date is required on new acceptances and is not retrofitted.** Forty-six
entries carry a bare `accepted` with no date; three carry `accepted <date>`.
The bare ones are frozen under §4 and stay bare. Their acceptance date is
recoverable from git and from nowhere else, which is a cost of the years before
this rule rather than a reason to edit them.

**0036 carries no `**Status:**` field at all.** It is accepted practice and
load-bearing, and it is frozen. It is named here so a reader who notices knows
it was seen, and so a tool counting status lines knows to expect fifty-six
across fifty-seven entries.

## 6. Superseding

A superseding entry cites the one it replaces, states in Context what changed,
and says **explicitly which clauses of the old entry survive**. Partial
supersession is normal and should be exact.

**This log records the supersession on the superseding entry**, in a
`**Supersedes:**` or `**Amends:**` field. That is the practice in place and it
is what this convention adopts. The work rig's opposite rule — stamping the
entry that *loses* the clause — is not carried, because adopting it would
require editing frozen bodies to backfill the fragments, which §4 forbids
outright.

The cost is real and is taken knowingly: **a reader of a superseded entry sees
nothing to warn them**, and must reach the superseding entry by search. Nothing
detects this (§9). If it bites, the fix is a generated map that resolves
citations, not a rule that edits the log.

## 7. Starting a log where none exists

Number from **0001**, in the order the decisions were actually made, not the
order they were found. Each recovered entry **says it is recovered**, names
where the reasoning was found, and labels a reconstructed Context as inference
rather than testimony. Recovered entries stay `proposed` until the operator
confirms each one actually was the decision taken.

**Do not recover what cannot be sourced.** A ruling you are confident about but
cannot point to is a candidate for a new entry drafted today, not a backdated
one.

## 8. Propose and ratify

An entry is drafted `proposed`. **Ratification is a re-read by the operator on a
different day than the drafting** (**0033**). Same-sitting ratification of your
own reasoning is the rubber stamp the split exists to prevent, and a thread that
marks its own draft accepted has defeated the mechanism rather than completed
it.

**A thread never ratifies.** Not its own entries, not anyone's.

## 9. What is not enforced

Nothing in this file is checked by anything, and **0048** clause 4 says a check
that cannot fail trains the eye past it — so these are stated rather than
pretended:

- **No gate reads this file.** An entry with no *"What would show this wrong"*,
  a renumbered clause, an edited body — all commit cleanly.
- **Nothing detects a duplicate number.** Two threads told to write "the next
  entry" will both write it, and §3 says why that is unrecoverable.
- **Nothing distinguishes a real falsifier from a platitude.** *"If it turns out
  not to work"* satisfies §2 mechanically.
- **The different-day rule is unobservable.** A status line stamped `accepted`
  carries no evidence of when it was read, and nothing would notice a
  same-sitting ratification.
- **Nothing warns a reader of a superseded entry**, per §6.
