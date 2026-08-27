# Conversation map convention

**Status:** authored, not enforced. The mechanism is by some distance the most
complete in this class -- a ratified append-only artefact, permanent per-row
provenance enforced at the writer, recency resolution with revocation, a
committed fingerprint and an auditor that checks it. This document is mostly a
statement of something that works. Two narrow gaps and one axis divergence are
named in §1.

**Scope:** this repo. One map per source (§2); the rules here govern every map,
present and future, which is the point of writing them once.

**Companion:** `CONVENTION_config.md` §7 argues the maps out of `config/` as
curated data rather than configuration.
`CONVENTION_project_registry.md` governs the artefact the maps' `project_id`
column points into.

**Cites:** 0012 (the registry's three tiers and id scheme, which `project_id`
resolves against), 0031 (a non-gating surface reports findings, never a
verdict), 0033 (the review mechanism a curated map costs, and its named
replacement), 0040 (the whole ruling; clauses 1, 2, 3, 4 and 7 are load-bearing
here), 0039 clauses 1-2 and 0044 clause 4 (the ratified map is named from the
machine's declared estate; `both` does not curate), 0045 (a pin is verified
read-only and reported, never repaired), 0046 (recency resolution, one shared
resolver, a superseding row says so), 0048 clause 4 (a check that is always red
trains the eye past it), 0050 (a source declares its own staleness; unreachable
reads as unknown), 0051 (containment by construction), 0052 (the convention
lives in the repo), 0053 clause 5 (authorship is declared per artefact, and the
gate splits on it).

---

## 1. What this fixes, measured

Read on 2026-08-25. **Row contents were deliberately not read** -- the columns
and counts below are all that is needed to state the convention, and the rows
carry employer project and thread names (§7).

| | |
|---|---|
| maps | **2** -- `mcf_conversation_map.tsv`, `personal_conversation_map.tsv` |
| rows, excluding headers | **37** and **4** |
| columns, ratified map | **5** -- `session_id`, `local_folder`, `project_id`, `conversation_name`, `notes` |
| columns, K0 candidate map | **9** -- the above four plus `match_pass`, `matched_length`, `candidate_count`, `status`, `note` |
| per-row provenance | **enforced at the writer**, as a `[provenance:...]` tag |
| maps carrying a committed fingerprint | **1 of 2** |
| maps covered by an auditor | **1 of 2** |
| pins carrying origin, anchor, date or host | **0 of 1** |

**0040 clause 2 is implemented, and not where a reader would look.** The clause
requires *"how each row was arrived at, machine-matched or human-mapped, never
overwritten by a re-run."* There is no provenance *column*; there is a
mandatory `[provenance:...]` tag at the head of `notes`, which
`curator_ratify` refuses to append a row without. 0046 chose the tag over a
column deliberately -- *"a status column would have needed a migration, a notes
tag does not"* -- and every consumer parses it through one shared parser rather
than inventing a second. §5 states the mechanism, because a rule enforced only
in a writer's validation is one refactor away from being lost.

**The axis divergence.** 0040 clause 2 says maps are **per source**, one file
each. The implementation is **per estate**: `MAP_FILENAMES` keys `work` to the
MCF map and `personal` to the personal map, resolved from the machine's
declared `estate` (0039 clause 1, 0044 clause 4), and an estate of `both` is
excluded from running the Curator at all (0039 clause 2). Both axes agree today
because each estate has exactly one source. They will disagree the first time an
estate has two, and this file says which wins: §2.

**The pin records less than clause 4 promised.** `config/mcf_conversation_map.tsv.sha256`
holds one line -- hash and path. `l5gntools/pin.py` supports a second,
metadata-carrying line:

```
# pin: origin=local anchor=<sha> date=YYYY-MM-DD host=<hostname>
```

It is unused here. Clause 4 said the repo would record *"that a map was
ratified, when, and against what content"*. The hash carries **against what
content**. Without the metadata line there is no **when**, no **on which
host**, and no anchor commit -- and `pin.verify_pin` already implements
`anchor-unresolvable` as a distinct violation state, so the checking half is
built and waiting on the writing half. §6.

**The second map inherited half the rule, against an accepted clause.** 0044
clause 4 already says *"each estate's map carries its own committed fingerprint
under 0040 clause 4 and 0045."* `personal_conversation_map.tsv` is covered by
`.gitignore`'s `/config/*conversation_map.tsv` -- the pattern 0040 clause 4
wrote *"so the next source's map inherits the rule rather than having to
remember it"* -- and is declared under `authors` in `local.json`. It has **no
`.sha256`**, and `auditor_conversation_map_pin` names the MCF map by a hardcoded
constant.

So this is a conformance gap against a ratified ruling, not a missing rule, and
the reason it went unnoticed is the transferable part: **the containment half
was written as a pattern and generalised itself; the ratification half was
written as a path and did not.** A check that enumerates where its ruling names
a class stops covering its own subject the moment a second instance appears, and
reports nothing, because it has no opinion about instances it was not told
about.

---

## 2. What a map is

**Where a source carries a stable native conversation id, the curated map keyed
on that id is the join of record** (0040 clause 1). Fuzzy or derived linking is
not used for that source at all -- not as a fallback, not as a tiebreak. The
map is not a hint to a matcher; it replaces the matcher.

**Where a source offers more than one id space, the map keys on the resolved,
canonical id and never on a transient one.** The case that settled it: Gemini
issues `share.gemini.google/<token>` short links which resolve to
`gemini.google.com/share/<hex>`, and only the latter is the key. The rule in
one line, worth keeping because it generalises past that source:

> **A key that can be reissued is not a key.**

**One file per source** (0040 clause 2). A map never spans sources, and the
next source gets its own file rather than a column.

**Where the file is resolved per estate and the rule is per source, the rule
wins.** Today `ratified_map_path_for_estate` maps one estate to one filename
and refuses an estate it does not know, *"rather than silently falling back to
a default that would be wrong for that estate"* -- which is the right refusal
on the wrong axis, and harmless while each estate has one source. The moment an
estate acquires a second source, the fix is a second file resolved by (estate,
source), not a second column and not a shared map. Recording this now costs a
sentence; discovering it later costs a migration of ratified rows, which §4
makes deliberately expensive.

**Consumed at `project_confidence: 'manual'`** (clause 3), which the standing
override rule already protects from every automated pass. A map row outranks
anything a matcher produces, and nothing but a later ratification can displace
it (§5). That is the reason the ratification discipline in §4 has to be real:
the only control on a row's correctness is the review that admitted it.

**`project_id` resolves against the registry**, at any tier, by id --
never a canonical name, never a folder name (0012, and
`CONVENTION_project_registry.md` §2). A map row pointing at a name is broken
the first time something is renamed.

---

## 3. It is built from local knowledge, on the machine that holds it

A map cannot be authored anywhere except the machine whose transcript store
holds the conversations, because the `session_id` column *is* a local folder
id. This is the sharpest example in the estate of an artefact whose content is
local knowledge and whose rules are estate policy.

**K0 proposes; a human ratifies.** `bootstrap_conversation_map.py` matches a
curated sheet's captured opening prompts against the real local Cowork store
on that machine to fill in each row's `session_id`. Its own docstring states
the discipline:

> Produces a **candidate map for human ratification** -- it is never applied
> automatically.

It reads only: no transcript file, no database, and it writes only the
candidate TSV named by `--out`. Once ratified, *"the fragile step never runs
again"* -- the join is exact from then on and the matching step is retired
rather than kept warm.

**The input sheet is itself local knowledge.** Opening prompts, folder labels,
human titles, optional dates used only to break same-project duplicate-opener
collisions. None of it is derivable from the store alone; the store has ids and
text, and no opinion about which effort a conversation belonged to.

**A candidate is never the map.** The file K0 writes and the file consumers
read have different names for a reason. Ratification is the act of moving
content between them, and §4 is what that act must include.

---

## 4. Ratification, and the review it replaces

**A curated map is never committed** (0040 clause 4). It joins the class of
`project_registry.json` and `local.json`: authored here, shipped manually,
gitignored.

**That cost 0033's review mechanism, and the cost was named rather than
absorbed.** 0033's safety property is *"the human reads `git diff --staged` and
commits"*. An untracked file produces no diff. The stated replacement is
twofold, and both halves are required:

1. **The curator tab's staged-rows view is the primary review**, not a
   convenience. It is the only place the content of a change is seen before it
   is accepted.
2. **A `<map>.sha256` fingerprint is committed beside the map**, so the repo
   records that a map was ratified, when, and against what content, while
   carrying no titles.

0040 states the reduction plainly and accepts it: *"An audit trail that proves
a ratification happened is not the same as one that shows what was ratified."*
That sentence is the reason the fingerprint is not optional. It is the entire
remaining audit trail.

**Staged, never committed by a tool.** `stage_ratified_map` runs exactly
`git add -- <this machine's ratified map path>` and nothing else -- matching
0033's code-declared path allowlist. No code in the ratification module calls
`git commit`. The commit stays a human act, which is the property 0033 was
protecting when the untracked map cost it the diff.

**K0's own refusals are honoured, not re-litigated.** A different-project
collision is offered no ratify action at all. A tool that re-decides upstream's
refusal has made itself the authority upstream declined to be.

**Re-hash in the same commit as the ratification.** A pin bumped in a later
tidy-up commit records the wrong moment, and a pin bumped without a
ratification records a lie. The `.sha256` is not swallowed by
`/config/*conversation_map.tsv` -- the pattern ends at `.tsv` -- so the
fingerprint stays tracked with no negation rule.

**Only the authoring host may bump a pin** (0053 clause 5). On a host holding a
hand-copied map, bumping fingerprints the stale local copy and commits it over
the authoritative pin -- turning a false alarm into real corruption, and
turning the gate green. Authorship is declared per artefact under `authors`,
and `run.py pin bump` is the only sanctioned writer.

**History is not rewritten.** A correction is a new ratification, and the
notes column says what it corrects.

---

## 5. Provenance, append-only, and recency

**The map is append-only. Nothing in it is ever edited or removed.**
`curator_ratify._append_row_bytes` is a pure byte-append -- opened `"a"`, never
`"r+"` and never a rewrite -- and it is the only code in that module that
writes a byte. `append_ratified_row` requires a **new** `session_id`;
`append_correction_row` requires an **existing** one. Correcting a ratification
means appending a new row for the same key, never touching the old one.

**Resolution is by recency: the last row for a key wins** (0046). File order is
recency -- an append-only file needs no timestamp column -- and every consumer
calls one shared resolver rather than re-implementing the join. A `revoked` row
removes the key from the resolved view entirely; a `corrected` row replaces the
prior row's fields exactly as an ordinary later ratification would.

Two things follow that are easy to get wrong. **Row count is not conversation
count** -- §1's 37 and 4 are rows, and the resolved view is smaller wherever a
key was corrected or revoked. And **a superseded row is still testimony**: it
stays in the file, and reading the file without the resolver gives a wrong
answer confidently.

**Provenance is permanent, and enforced at the writer.** Every appended row's
`notes` begins with a machine-parseable `[provenance:...]` tag recording how
the row was arrived at:

| tag | meaning |
|---|---|
| `pass1` / `pass2` | machine-matched by K0, by which pass |
| `human-picked` | a person chose between candidates in a refused collision |
| `hand-mapped` | a person supplied it with no candidate at all |

A correcting row additionally carries `[status:corrected]` or
`[status:revoked]` (0046 clause 3) **and a free-text reason in words**.
`curator_ratify` refuses to append a row whose notes do not start with a
provenance tag -- so this is not a convention anyone can forget, it is a
precondition of writing.

**Why the tag rather than a column** (0046): a status column would have needed
a migration of every existing row; a notes tag needs none, and rows written
before the mechanism existed read as an ordinary uncorrected ratification with
zero migration. One parser is reused everywhere rather than a second being
invented per consumer.

**The distinction is load-bearing rather than decorative.** A K0 opener match
and a human recollection fail differently: the first is wrong when two
conversations opened alike, the second is wrong when memory is. When a link
later looks wrong, the first question is which kind of row it was, and the
artefact can answer.

**Per-row actions only.** There is no list parameter anywhere in the
ratification module that could become a bulk-accept, *"because there is nowhere
to put one"*. That is a structural refusal rather than a rule someone keeps,
and it is the reason review in §4 cannot be skipped at scale.

**Gaps are named, with their reason, and sized where they can be** (0040
clause 7). A conversation the map cannot key is a row that says so, not a row
omitted. An omitted row is indistinguishable from a conversation that does not
exist.

---

## 6. Currency, and the consumer's normal state

**The map travels by hand; the pin travels by `git pull`.** That asymmetry is
the whole difficulty, and it is not a defect in either half.

`auditor_conversation_map_pin` implements 0045 on this artefact: one pin,
verified read-only, **reported never repaired**. Its clean states are
`matches`, `artefact-absent`, `absent` and `git-unavailable` -- a fresh
checkout or a machine never handed a copy passes clean, which is the documented
normal state rather than a defect, mirroring 0045 clause 5's *"working ahead of
a pin is a normal state, not an error"*.

**The state it gets wrong is the one consumers live in.** A host whose copy is
older than the current pin is not drifting -- it has simply not been re-handed.
`CLEAN_STATES` covers *no copy* and *current copy* and fails the state in
between, which is where a consumer machine spends most of its life. That was
found on a work rig rather than here, and splitting it by host is 0053's work,
not this file's.

**A pin should say when and where it was taken** (§1). With the metadata line
written, an out-of-date consumer copy becomes *legible* rather than merely
red: the pin names the host that authored it and the date, so the remedy --
be re-handed a copy from that host -- is readable from the failure alone. That
is 0050's posture applied to a hand-carried artefact: a source declares its own
staleness, and one that cannot be reached reads as unknown, never as fresh.

---

## 7. Containment

**The rows carry conversation titles**, which for the MCF map means employer
project and thread names. That is why the maps are gitignored, why they are
hand-carried, and why the fingerprint mechanism exists at all -- a hash proves
ratification while carrying none of the titles.

**This document was written without reading a data row**, and that is the
standard rather than a flourish. Everything a convention needs -- the columns,
the counts, the mechanism -- is available from the header and the shape.
Anything that requires reading the rows is a curation task, done on the machine
that owns them.

**What may cross a boundary**: row counts, column names, the mechanism, the
fact that a gap exists and its size. **What may not**: titles, folder labels,
notes, and any excerpt carrying them.

**A shared link is a transient means, revoked once captured** (0040 clause 6
and its clause 7 corollary). A capture route that stays open is a standing
surface, and this estate's position on standing surfaces is 0036's.

---

## 8. The procedure, for the skill that will script it

A skill scripts the procedure and cites this file (0052). What a map skill
would script:

1. **Establish the source has a stable native id.** If it does not, a map is
   the wrong instrument -- §2.
2. **Confirm the id space is the resolved, canonical one**, not a reissuable
   token.
3. **Run K0 against the local store**, on the machine that holds it, producing
   a candidate to `--out`. Never over the ratified map.
4. **Review the candidate in the curator tab's staged-rows view**, one row at
   a time -- the primary review, and the only place content is seen (§4).
5. **Ratify by appending**, with the `[provenance:...]` tag the writer requires;
   correct or revoke by appending a further row carrying `[status:...]` and a
   reason in words. Never edit or remove a row (§5).
6. **Name the gaps**, with reasons and sizes, as rows (0040 clause 7).
7. **Stage, then let a human commit** -- `git add` on this machine's map path
   only; no tool commits (§4).
8. **Re-hash in the same commit**, on the authoring host only, via
   `run.py pin bump` (§4).
9. **Ship the map by hand** to the hosts that consume it, and expect the pin to
   arrive there separately by `git pull` (§6).

**A skill may propose every step. It ratifies none of them, and it never
bumps a pin.**

---

## 9. What is already gated, and what should not be

**Gated today, correctly:** fingerprint drift on the MCF map, via
`auditor_conversation_map_pin`, through `verify.py` and `.githooks/pre-commit`.

**Required by 0044 clause 4 and not implemented:** the same auditor driven by
the gitignore pattern rather than a hardcoded constant, so every map is covered
the way every map is already contained. That is the §1 conformance gap, and
closing it is mostly deleting a path.

**Should never gate:** a consumer's copy being older than the pin. It can go
red with no defect present, which is the class 0053 moved outside the gate, and
a check that is red on every consumer run trains the eye past it (0048 clause
4).

**Cannot be gated at all:** whether a row is *right*. A map row outranks every
automated pass permanently (§2), which means the only control on its
correctness is the review in §4. That is why the review is the primary one and
not a convenience.

---

## 10. The check, before you ratify a map change

1. Does the source have a **stable, canonical, non-reissuable id**?
2. Does every `project_id` resolve to a **registry id**, at some tier?
3. Is the change an **append**? A correction is a new row carrying
   `[status:...]` and a reason -- never an edit (§5).
4. Are **gaps present as rows**, with reasons, rather than absent?
5. Was the change **seen** in the staged-rows view, one row at a time, not just
   diffed against a candidate file?
6. Are you on the **authoring host** for this artefact (`authors`, 0053
   clause 5)?
7. Is the **`.sha256` re-hashed in the same commit** as the ratification?
8. Does anything leaving this machine carry **titles** rather than counts (§7)?
