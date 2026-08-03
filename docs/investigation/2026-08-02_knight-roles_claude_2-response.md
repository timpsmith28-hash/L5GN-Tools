<!-- actioned: (none yet) -->

# Response — the knight's future roles: Historian, Chronicler, Shadow

**Date:** 2026-08-02 · **Model:** Claude (Cowork, design thread) ·
**Partner prompt:** `2026-08-02_knight-roles_claude_1-prompt.md`

Investigation, per `docs/README.md` §4. Born frozen. The `actioned:` block above
records consequences only; the convention is proposed in
`2026-08-02_architecture-drift_claude_2-response.md`.

**This is a design, not a ruling.** Nothing here is decided. The entries it
proposes are listed at the end and none of them exist yet.

---

## Headline

The inversion is mostly **ratification of something 0025 already forced**. Once
visibility is scoped by surface rather than by estate, a solo rig reading its own
estate on loopback is the complete story for that machine. The knight adds
nothing to it. What the knight is *for* therefore has to be restated, and the
three-service split is a good answer because each service has a different write
posture, a different latency tolerance and a different failure mode.

The largest consequence is one nobody has written down: **0023 stops being
load-bearing.** The 2026-07-28 handoff recorded the opposite — *"0023's TOTP gate
is now the blocker on deck-on-knight, not an optional hardening step"* — and that
was correct under the assumption the knight would co-render both estates. If the
knight never co-renders, the gate reverts to what it was before 0025: optional
hardening. The roadmap currently carries a specced-but-unbuilt gate as a
precondition for a thing this design may decide not to build.

The largest risk is also not the obvious one. It is not that the knight holds
work data — it is that **making the knight the backup target concentrates risk it
cannot itself survive**, because the knight has no off-box backup of its own and
has not had one since 0005/0006 flagged it two and a half weeks ago.

---

## 1. The three charters

The split is real because the three jobs have genuinely different properties, not
because three is a tidy number.

| | **Chronicler** | **Historian** | **Shadow** |
|---|---|---|---|
| Job | front-line linker, recorder, documentor | durability and the time axis | the slow half of the gate |
| Writes | the vault (`chronicler.db`) | its own stores only | nothing |
| Reads | raw exports, transcripts, the estate | deposits, snapshots, the history series | the repo, at a commit |
| Latency | interactive-adjacent — a ruling should land now | batch, overnight, hours are fine | batch, minutes are fine |
| Judgement | yes — linking is evidence plus a human ruling | none | none, by construction |
| Fails how | a bad link, visible and reversible | a stale trend, or a lost backup | a missed finding |
| Authority | writes the record | holds the record | **has none** |

**Chronicler is unchanged.** It stays what it is. The only thing this design does
to it is stop asking it to also be the trend engine, which it has been doing by
accident: `data/history/estate-*.json` accumulation, `estate_diff`, `drift` and
`project_trail` are all time-axis work sitting inside a linking subsystem.

**Historian owns the time axis and durability.** That means the backup
(`VACUUM INTO`, off-box — the standing fix since 0005/0006), the growing history
series, longitudinal diffs, and the trend queries the local deck renders. Slice
1's Task 4 "what changed since the last build" is, under this split, a Historian
query rendered by a local surface.

**Shadow runs what pre-commit cannot afford.** Detailed in §4.

### The boundary that makes Historian safe

**The Historian is a consumer that never writes back to a producer.** It reads
deposits, holds the long series, holds the backup — and nothing it computes
re-enters the deposit chain or any producer's `data/`.

This is worth stating as hard as 0010 states the wall, because the temptation is
obvious and immediate: the Historian will compute better numbers than the
producer has (it holds every prior build; the producer holds a handful), and the
reflex will be to push them back so the local deck can render them. That reflex
turns a one-way deposit chain into a loop, and a loop is how the 133-link
incident happened — a derived value flowing backwards into the thing it was
derived from and being mistaken for source.

If the local deck wants Historian numbers, the honest shapes are: the deck
queries the Historian over the tailnet at render time and says plainly that it is
doing so, or the producer keeps its own shorter series and the two are allowed to
differ. Not: the Historian writes into the producer's `data/`.

---

## 2. What actually moves — and one thing that must not

Boring compute, in the sense that matters: batch, no judgement, latency-tolerant,
and ideally unpleasant to run on a machine someone is using.

**Moves cleanly.**

- **Embeddings / Layer C (0004, dormant).** `sentence-transformers` is the one
  heavyweight dependency the toolkit deliberately keeps outside the stdlib core,
  and 0018 already sited inference off the toolkit wall with *"knight =
  embeddings + retrieval"* as the honest default. Batch-embedding the corpus
  overnight is exactly Historian-shaped work, and it revives a decision that has
  been dormant since 2026-07-18 without putting a model runtime on the gaming
  rig.
- **Vocabulary S2 rebuild (0015).** Guards specified, dependency satisfied,
  sitting in the standing backlog. Corpus-wide term statistics with a
  cross-project commonality cutoff is a whole-corpus computation — pointless
  interactively, natural in batch.
- **Byte-level duplicate detection.** The open 1.A2 / Castle ruling rests on
  evidence already in hand (byte-identical duplicates, 165,246,539 bytes × 2).
  Hashing an estate is the archetypal job you do not want on a machine you are
  using — and the Historian can hash **the backup it already holds**, never
  touching the producer's disk at all. That is strictly better than doing it
  locally, not merely offloaded.
- **The longitudinal series itself.** `data/history/estate-*.json` only grows.
  The Historian holds the full series and computes trends; the producer keeps the
  last few builds and stops carrying an archive it never reads.
- **Transcript normalisation and ingest.** `normalize_*`, `parse_gemini_export`,
  the scrape pipeline. Batch, slow, idempotent, no judgement.
- **"Did the producer actually deposit today?"** The cheapest item on the list
  and possibly the most valuable. A machine cannot honestly report that it failed
  to run — that is failure shape #1 (*a check that cannot tell absent from
  couldn't-look*) at the level of the whole rig. Only a second machine noticing
  an absence can answer it.

**Does not move, and the reason is structural.**

- **A precomputed full-text index.** Tempting the moment the corpus outgrows
  in-memory FTS5. It carries document *text*, which makes it a deposit artefact,
  which puts it squarely inside 0010's wall and contradicts 0027's condition (1)
  — *persists nothing, no cache, nothing that could be deposited*. 0027's whole
  argument is that a **local** surface may read source at render time precisely
  because nothing leaves the process. An index on another machine is that
  constraint inverted. If local search outgrows memory the answer is a better
  local index, not a remote one.

---

## 3. The backup, and the risk that is not the obvious one

Tim's instinct — back the gaming rig up to the knight — is right and overdue. The
off-box backup has been the standing fix since 0005, was reframed but not
resolved by 0006, and is still listed in the standing backlog as *"the knight's
unconfigured off-box backup push."*

Three things follow that should be decided before the first push, not after.

**The disclosure surface changes shape.** Today the knight holds *summary*
artefacts: sizes, counts, titles, 120-character excerpts, and `blast_radius`
explicitly stores no script body, alias or credential. A backup holds everything.
0027's reasoning cuts the other way here — its exemption is for a **local**
surface, and a backup is the definition of an artefact that travels. So the
summary-only rule applies to the backup in full force, and "back up the rig" is
not one decision but two: *what* is copied, and whether the answer is "the vault
and the deposits" or "the repos as well."

**F-2 gets worse.** The self-scan found the work rig's hostname `10280L` reaching
the estate bundle through authored doc titles and a commit subject — recorded as
"own item, near-term mitigation: substitute rig aliases." That is a proportionate
disposition for a summary artefact. It is a less comfortable one for a full
backup, and the mitigation named (aliases in authored prose) explicitly cannot
reach commit subjects, which are immutable once written.

**The knight cannot survive being the backup target.** This is the one that
matters. The knight holds the only live vault; its sole off-box copy is the stale
`L5GN-Castle\...\Chronicler_Backup`, refreshed by hand, drifted since the knight
became primary (0006). Making it *also* the gaming rig's backup target does not
spread risk — it **concentrates** it, on the single machine in the estate with no
recovery path. A disk failure would then lose the vault, the history series and
the rig's backup together.

So the ordering is: **the knight's own off-box backup is a precondition for the
knight becoming a backup target**, not a follow-up. That inverts the usual
instinct and it is the single most actionable line in this document.

---

## 4. The Shadow — what it can construct that pre-commit cannot

The Shadow is the strongest of the three ideas, because it attacks a failure
shape the estate has already proven is *structural* rather than incidental.

From the closing remarks of the 2026-07-28 handoff, pattern 3: *"Every tester
built its DB fresh from `schema.sql`, so the `CREATE TABLE` always fired under
test and never in reality. Every tester ran on Linux in the sandbox, where an
open file can be unlinked, so a leaked sqlite handle was invisible until Windows
refused to delete the temp dir."* `tester_deck_migration` is still the **first**
tester in the suite that constructs a pre-existing state.

That is not laziness. It is the pre-commit budget: the hook must return in
seconds, so the suite is hermetic and fast, and hermetic-and-fast is exactly what
makes it blind to state it did not build. **The Shadow has no such budget.** It
can:

- **Construct pre-existing state** — an old vault, an unmigrated schema, a
  half-written deposit, a `render_log` that predates a rebuild. The whole class
  `tester_deck_migration` had to fight to reach.
- **Run against real data** — the actual vault, the actual estate build, the
  actual deposits. Every "this has never met a real note" item (deck UAT 1.2, the
  backfill's note-parsing, still gating ~500 live rows) is a Shadow check.
- **Run the full estate scan** and diff it against the last one, which is minutes
  of work and cannot live in a hook.
- **Run on a second OS with a different filesystem posture.** The Linux/Windows
  split has already produced one invisible defect; making the difference a
  deliberate check rather than an accident is free once the machine exists.
- **Take the checks currently being pushed into UAT because they are too slow or
  too stateful to automate** — which is Tim's own framing and the reason this
  service reduces the UAT stack rather than adding to it.

### The rule that keeps it honest

**The Shadow never says "green."**

The pre-commit hook on Windows stays the gate. The Shadow emits a **findings
ledger** — it does not block, does not gate a push, and does not issue a verdict.
Two authorities that can disagree about green is worse than one authority with
known blind spots, and it would muddy the corollary the estate has now proven
twice: *a Cowork thread's GREEN is provisional until it runs on the machine that
owns the files.*

Auditor of last resort. Output is findings, and findings are read by a human.

### Where the findings go

The Shadow makes an existing unsolved problem acute rather than creating a new
one. There are already ~20 open findings with no home — F-1…F-9 from the
self-scan, six scanner defects, five proposed follow-up briefs, E7 from the board
walk, and six open items on the work-rig sheet — and `docs/README.md` §5 retires
status boards by class. A service *generating* findings nightly needs that
answered first.

The interesting question, and it is genuinely open: **are findings derivable the
way the board's columns are derivable?** The board proved that a lifecycle nobody
was recording could be computed from filenames alone. Findings are currently
prose in results logs. If they can be parsed, they are a board card type and the
§5 objection dissolves, because nothing is being *maintained*. If they cannot,
the Shadow needs its own append-only store — which is 0022's run ledger with a
different payload, and should probably be the same table.

---

## 5. What this does to the existing decisions

**0023 — status changes, and this is the headline.** Under a co-rendering knight
the TOTP gate is a hard precondition. Under this design the knight never
co-renders: the work rig keeps its own estate locally (per Tim's framing, it may
never move beyond the current report model), the gaming rig reads its own on
loopback, and the knight holds backups and computes trends without a display
surface. 0023 reverts to optional hardening. **This must be written down**, or
the roadmap keeps carrying a blocker for a surface nobody is building.

**0025 — unaffected, and vindicated.** The whole design is downstream of it.

**0010 — unaffected, and load-bearing here.** The never-writes-back-to-a-producer
rule is 0010's shape applied to a new axis.

**0021 — extended.** The supervisor was specced for the read/review/deck trio.
Historian and Shadow are two more long-lived units under the same systemd target,
which is the right home and needs no new mechanism.

**0022 — probably absorbs the Shadow's output.** "This ran" and "this was
checked" are the same provenance instinct. One append-only ledger, two payloads,
is better than two ledgers.

**0018 — the knight's role narrows and sharpens.** Its honest default was already
*"knight = embeddings + retrieval; generation is a swappable backend."* Under
this design that becomes the Historian's job, which is a more precise siting than
0018 could give it at the time.

---

## Findings

Appended per the ruling on this investigation.

| id | finding | severity |
|---|---|---|
| **K1** | 0023's status changes from precondition to optional hardening if the knight never co-renders. Currently recorded the opposite way in the 2026-07-28 handoff, and the roadmap still carries it as a blocker. | **decision status drift, unrecorded** |
| **K2** | The knight has no off-box backup (0005/0006, still open). Making it the gaming rig's backup target concentrates risk on the one machine with no recovery path. Its own backup is a **precondition**, not a follow-up. | **highest actionable** |
| **K3** | A backup is an artefact that travels, so summary-only (0027's unchanged half) applies to it in full. "What is copied" is a separate decision from "back up the rig". | needs a ruling before first push |
| **K4** | F-2 (work-rig hostname in authored prose and commit subjects) is proportionate for a summary artefact and less so for a full backup. The named mitigation cannot reach commit subjects. | escalates an accepted finding |
| **K5** | A precomputed FTS index cannot move to the knight — it carries document text, so 0010 and 0027(1) both bite. Named because it is the obvious next request. | design boundary |
| **K6** | The Shadow makes the homeless-findings problem acute. ~20 open findings already have no home and §5 forbids a status board. Whether findings are *derivable* is the open question; 0022's ledger is the fallback. | blocks the Shadow, not the Historian |
| **K7** | Chronicler is currently doing time-axis work by accident (`estate_diff`, `drift`, `project_trail`, the history series). The split has to say where those move, or it is naming only. | scoping |
| **K8** | The Historian will compute better numbers than any producer holds, creating immediate pressure to write them back. That loop is the 133-link shape. Needs stating as hard as 0010. | design boundary |

### Entries this needs before any code

None of these exist. Listed in dependency order.

1. **The role split** — Historian / Chronicler / Shadow charters, and the
   never-writes-back-to-a-producer rule (K7, K8).
2. **The backup as a travelling artefact** — what is copied, and the knight's own
   off-box backup as a precondition (K2, K3, K4).
3. **The Shadow's authority** — findings, never a verdict; pre-commit remains the
   gate. Could fold into (1), but it is the rule most likely to be eroded by
   convenience later, which argues for its own entry.
4. **An amendment to 0023** recording the status change (K1). Per the log's own
   convention this is a new entry that says so, never an edit.

### What this investigation deliberately did not do

- **No entries drafted.** Listing what is needed is not the same as writing it,
  and each of the four wants Tim's ruling on the substance first.
- **No code, no config, no deploy units.**
- **No estimate of what the knight can actually run.** Resource headroom on that
  box is unmeasured, and 0018 already notes *"the knight is not resource-rich."*
  Embeddings on it is an assumption inherited from 0018, not a measurement.
- **The work rig was left alone.** Tim's framing is that it may never move beyond
  the current report model. Nothing here proposes changing that, and the design
  is better for not needing to.
