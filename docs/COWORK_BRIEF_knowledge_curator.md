# Cowork brief — Knowledge Curator, K1–K5 (MCF, from the local transcripts)

**Origin:** `docs/SPEC_Knowledge_Curator.md` v1, retargeted in the design thread
2026-08-06 after review.
**Deliverable:** K1 → K5, the core loop, run once against the real MCF corpus on
the work rig. K6 stays parked.
**Builds on:** 0026 (knowledge documents are a first-class artefact), 0025
(a solo box reads its own estate), 0027 (a local surface may read source at
render time), 0030 (derived output is not a document), 0031 (a non-gating surface
reports findings, never verdicts).

---

## What changed from the spec, and why it gets simpler

**Source: the local Cowork transcript store, not `chronicler.db`.**
`chronicler/pipeline/local_transcripts.py` already discovers and parses both
local stores, read-only and stdlib-only, and captures each session's real
timestamps. Reuse it; do not write a second discoverer.

That retarget deletes four problems the vault route created:

- No snapshot-vs-live question (0013) — there is no DB.
- No `dbsafe` read-only handle to enforce (0019) — there is no DB.
- No "must run where the vault and the repos coexist" — the Cowork store and the
  MCF repos are both on the **work rig**, natively.
- No dependence on linking coverage. The vault route was bounded by 52 linked
  threads; the transcript store has **48 conversations across 8 MCF projects**,
  all of them, regardless of whether Chronicler ever linked them.

**Scope: MCF / work estate only.** Tim's framing, recorded because it is the
justification:

> *the knowledge I learn on my personal work isn't so precious — it's
> regurgitation/reuse of existing principles which for the vast majority you
> already have. the mcf knowledge is not that though — that's the domain specific
> stuff that is unique to the situation and can't be so easily reengineered
> (without the knowledge — basically an extension of your training data)*

That is a value argument, and it also dissolves the cross-estate disclosure risk
entirely: the tool never reads personal-estate content, so there is no mixed
artefact to police. **Personal-estate projects are out of scope, not deferred.**

---

## The spine: reverse chronological, latest wins

Process conversations **newest first, by real modified time**. This is not an
optimisation; it is the design.

- The **newest** claim on a topic establishes current truth.
- An **older** claim that agrees is corroboration — it says how long this has
  been settled.
- An older claim that **contradicts** one already established is **not a gap and
  not noise**. It is the supersession record: *this was believed on 16 Jul,
  it changed by 30 Jul, here is both and here is when.*

That last case is the insight worth building around, because it hands you K6's
parked contradiction problem almost free. The spec parked it because deciding
*which* of two conflicting statements is right is hard. **Ordering answers it
without deciding**: the later one is current, the earlier one is why.

So the report gains a **fourth section** the spec did not have:

> **Superseded** — claim, the newer statement that replaced it, both dates, both
> quoted. Evidence for why current knowledge says what it says.

This is `DECISIONS.md`'s own shape — append-only, superseded-by-a-later-entry —
applied to conversation instead of rulings. Say so in the report.

**Consequence for the run:** the ordering must be over a **real timestamp**, not
the Cowork UI's relative label. `"3 minutes ago"` / `"yesterday"` / `"Jul 30"` is
display text; the transcript files carry actual times.

Because ordering *is* the design, the timestamp's provenance matters and must be
recorded per conversation, best source first:

1. the **last message's own timestamp** inside the transcript — what actually
   happened, and immune to anything touching the directory;
2. the `.jsonl` **file mtime** — close, but moves on any rewrite;
3. the `local_*` **folder mtime** — weakest; a cache write or an app upgrade
   moves it.

Use the best available, **name which was used**, and where a conversation spans
several transcript files take the newest across them. A conversation whose time
cannot be resolved at all is **excluded and named**, never silently sorted to the
end — an unordered claim in an order-dependent design is worse than a missing one.

---

## The join — exact, via a curated session id

**`cwd` cannot join a Cowork session to a project.**
`ingest_local_transcripts.py` states it plainly: *"Cowork sessions never get a
direct link — their cwd encodes the session's own `local_<session-id>` path, not
the project folder."*

**But the `local_<session-id>` folder name is itself a stable, unique key**, and
curating it into the map makes the join exact rather than heuristic. That is the
design: no fuzzy matching, no alias derivation, no repeat of the contamination
0011 and 0017 spent two rounds cleaning up.

**Aligning those ids by hand proved fiddly, so K0 bootstraps them by matching
first prompts — once, under review.** See K0 below. The important property is
that the text matching produces a *candidate map for ratification*, not a runtime
join: after K0 the key is exact forever, and the fragile step never runs again.

**Two ids, and they are not interchangeable:**

| id | what it is |
|---|---|
| `local_<uuid>` (folder name) | the **conversation** — what appears in the Cowork UI, and the curated key |
| `<uuid>.jsonl` (file name) | an **agent session** inside it. There can be several — `subagents/agent-*.jsonl`, resumes |

So the map is **one conversation → N transcript files**. `local_transcripts.py`
currently keeps the inner session uuid as `thread_id` and does not surface the
outer `local_` folder id; **extend it to capture that segment** rather than
re-deriving it anywhere else.

**The curated map**, committed as `config/mcf_conversation_map.tsv`, keyed on the
session id:

```
session_id                                    local_folder            project_id        conversation_name
local_2d41a9a8-1f09-416a-b185-7d32f9969403    MCF/PricingModel        mcf-pricing-model PricingModel - Design Thread
```

The label inconsistencies visible in the source TSV get resolved **once, here,
explicitly, with a note on each** rather than being inferred every run:

- `MCF/PricingModel` **and** `MCF/PricingModelisation` → one Cowork project
  ("Pricing Model"). Two folders, one project — decide which holds the knowledge
  files.
- `MCF/ChurnLevelIndictor` (folder) vs `ChurnLevelIndicator` (label).
- `ActivitySatements - …` in four conversation titles.

Title-prefix derivation is **demoted to a sanity check on the label**, not the
join. Report disagreements; never resolve them automatically.

### The unmapped folders are a finding

The session store holds **~64 `local_*` folders** against **48 rows** in the
curated list. Tim's read is that some were deleted in the Cowork UI.

**If that is right, deleting a conversation in Cowork does not delete its
transcript on disk** — the local store is a more complete record than the
interface. That is worth establishing rather than assuming, and it is a
data-retention fact about the work estate with consequences beyond this tool.

So: **report every unmapped `local_*` folder**, with its date and message count,
under a *"present on disk, not in the map"* heading. Never skip silently — this
is the confident-zero shape, and a curator that quietly ignores a third of the
store is exactly the failure this estate keeps rediscovering.

Exclude non-session directories (`rpm`, `.project-cache`) by **matching
`local_<uuid>`**, never by a denylist — a denylist goes stale the first time the
app adds a directory.

---

## Grounding — what the first run will actually see

**48 conversations, 8 MCF projects**, roughly 1 July → 6 August. The work rig's
store measured 91 sessions / 1,982 messages on 2026-07-28, so a full pass is
low-thousands of messages through a local model. Tractable.

**Only 4 of 9 MCF projects have a `KNOWLEDGE*.md` file at all.** 0026 measured it:
6 knowledge docs across 4 projects, 36 of 77 documents classified.

That matters for K4's framing. For a project with **no** knowledge file, every
claim is technically a gap, and a report saying *"here are 200 gaps"* is useless.
Handle those projects differently:

> **No knowledge file yet** — this project has none. Here are the N claims that
> recurred across the most conversations, as a starting point for writing one.

Recurrence across separate conversations is the available signal for "this
mattered enough to keep saying", and it turns a useless list into a first draft.

Two smaller freebies in the data: conversations named `— CLOSED` mark a completed
line of work, so their claims are likelier settled; and per-project conversation
counts range from 1 (ValidationAutomation) to 14 (PricingModel), so expect wildly
uneven yield and report it per project rather than as one total.

---

## Precondition ▸ a DECISIONS entry

Smaller than the vault route needed, but two things are rulings.

> ## 00NN — The Knowledge Curator reads local transcripts, is MCF-scoped, and treats recency as truth order
>
> **Date:** 2026-08-06 · **Status:** proposed · **Builds on:** 0025 (a solo box
> reads its own estate), 0026 (knowledge documents), 0030 (derived output is not
> a document) · **Source:** `SPEC_Knowledge_Curator.md` review
>
> **Context.** The Curator was specced against `chronicler.db`. Retargeting it at
> the local Cowork transcript store removes its vault dependency, its linking-
> coverage ceiling, and its cross-estate exposure in one move — but introduces a
> question the estate has not ruled on: when two conversations disagree, which is
> true?
>
> **Decision.**
> 1. The Curator reads the **local transcript store on the machine that owns it**,
>    is **scoped to the work/MCF estate**, and never reads personal-estate
>    content. It is a solo-machine tool (0025) and produces no travelling artefact.
> 2. **Recency is the truth order.** Conversations are processed newest-first by
>    real modified time; the newest claim on a topic is current, an older
>    conflicting claim is **superseded and reported as such**, never discarded and
>    never treated as a gap.
> 3. Its output is **derived**, written under `data/`, and does not earn a place
>    in `docs/` (0030, `docs/README.md` §1).
>
> **Consequences.** The tool gains an honest answer to "why does the current
> knowledge say this" — the superseded trail — which the vault route could not
> have produced. The cost is that recency is a heuristic: a newer casual remark
> can supersede an older considered one. Accepted, because both are quoted and
> dated in the report, so a wrong ordering is visible rather than silent.

---

## Working rules

- **Reuse `local_transcripts.py`.** Do not write a second discoverer or parser.
  If it needs extending, extend it and say so.
- Stdlib only for transport — `urllib.request` against LM Studio's
  OpenAI-compatible endpoint. No `requests`, no `openai` client.
- Lives in `chronicler/` (writer subsystem, own deps permitted), **not**
  `l5gntools/`.
- Loud failure, no partial report, per the spec's standing rules.
- **Every artefact records model provenance** — model id, endpoint, temperature,
  run timestamp. A sampling model makes byte-identical re-runs impossible; the
  honest property is that unchanged conversations are never re-extracted, and a
  report whose model is unknown is unreproducible testimony.
- Gate GREEN. Each stage independently testable.
- UTF-8 explicit, UTC ISO-8601.

---

## Tasks

### K0 ▸ bootstrap the session ids from first prompts — once, then never again

**Input:** the curated sheet, now carrying a `1st User Message*` column — the
opening prompt of each of the 48 conversations, taken from the Cowork UI. A few
threads have broken history, so the captured text is a *later* message of Tim's,
not the first. The design accounts for that.

**Output:** a **candidate map** with evidence per row, for ratification. It is
not applied automatically. Once ratified it becomes
`config/mcf_conversation_map.tsv`, keyed on session id, and K0 is never run
again.

**Normalisation, both sides, before any comparison.** This text has been through
a Google Sheet, so substitution has certainly happened: NFKC, curly quotes →
straight, em/en dash → hyphen, non-breaking space → space, collapse all
whitespace runs to one, casefold. Do not skip this — a raw `startswith` will fail
on invisible differences and the failure will look like a missing conversation.

**Pass 1 — prefix match on the opener.** Compare the normalised sheet text
against the normalised **first user message** of each conversation.

- "First user message" means the first message with `role=user` **and text
  content** — skip system reminders, attachment preambles, and any wrapper the
  transcript adds. Getting this wrong is the most likely cause of a wholesale
  pass-1 failure.
- Where the conversation spans several transcript files, use the earliest.

**Measured on the real sheet, so build to these numbers, not to guesses:**

| N (normalised chars) | distinct | collisions |
|---|---|---|
| 32 | 48 / 49 | 1 |
| 200 | 48 / 49 | 1 |

**32 characters is sufficient**; the single collision does not resolve at any
length. Match on a generous prefix (200 is free) but know that the discriminating
power is already there at 32.

**Pass 2 — full-content search, for what pass 1 misses.** The broken-history
threads. Search the sheet's chunk as a normalised substring across *all* messages
of unmatched conversations.

- **Require a minimum normalised length — 60 characters.** Nine of the 48 sheet
  entries fall below that, the shortest being `/setup-cowork` at 13. Searching a
  13-character string across every message would match any thread that merely
  mentions it. Those nine are exactly the ones pass 1 should catch; if one
  reaches pass 2, report it unmatched rather than guessing.

**Ambiguity: refuse only when the candidates disagree.**

The sheet contains one exact duplicate — `WizForgeAnalytics - Salesforce MCP
server setup` (Jul 7) and `WizForgeAnalytics - Salesforce sheets audit` (Jul 8)
have **byte-identical 735-character openers**. The same prompt was fired into a
fresh thread the next day.

- Colliding candidates that resolve to the **same project** → accept, split by
  date, flag the pair in the report. The map's answer is the same either way.
- Colliding candidates that resolve to **different projects** → **refuse**, name
  both, leave unmatched. That is 0011's lesson: a generator writing an identity
  nobody ratified is how a second generation of junk grows back.

**Evidence per row**, in the existing vocabulary — which pass matched, the
normalised prefix length that matched, and the candidate count. A row with no
evidence is not a match; it is an unmatched row that happens to have a guess
beside it.

**Report, per the standing discipline:** matched-by-pass-1, matched-by-pass-2,
ambiguous-same-project, ambiguous-different-project, unmatched-sheet-rows, and
unmapped-`local_*`-folders-on-disk. Six counts. All six get printed even when
zero — a bootstrap that reports only its successes is unauditable.

### K1 ▸ the conversation map and the knowledge index

- **Extend `local_transcripts.py`** to surface the `local_<uuid>` conversation id
  alongside the existing per-file session uuid. One conversation, N files.
- Commit the curated conversation map keyed on that id, resolving the
  folder/label inconsistencies named above **once, explicitly**, with a note on
  each.
- **Reconcile the map against the store**, in both directions, and report both:
  *mapped but absent on disk* and *present on disk, not mapped* (~16 expected).
  The second is the deleted-in-UI question and is a finding in its own right.
- Cross-check labels against title-prefix derivation; report disagreements.
  This is a sanity check on naming, **not** the join — the join is exact.
- For each mapped repo folder, glob `*KNOWLEDGE*.md` per 0026's definition —
  filename contains `_KNOWLEDGE_`, case-insensitive, unanchored. Do **not**
  invent a second rule; `doc_census` already implements this one.
- Output `data/knowledge_curator/knowledge_index.json`, projects with **no**
  knowledge files included with an empty list.
- `unresolved` must distinguish **no mapping** / **mapped but folder absent on
  this machine** / **present but unreadable**. Three facts, three states.

### K2 ▸ claim extraction, newest first

- Order by real modified time, newest first. A conversation whose real time
  cannot be resolved is **excluded and named**.
- Per conversation, extract atomic claims as `{claim_text, quoted_source}` where
  `quoted_source` must be a **literal substring** of the transcript. Reject
  anything else — this rule is why the report is checkable in one glance.
- **Count and report rejections.** A model that frequently fails quote
  verification is a finding about the model; silent retry hides it.
- A conversation yielding zero claims is recorded as scanned-with-zero, never
  omitted.
- Cache on the transcript file's identity and mtime, so a re-run re-extracts only
  what changed.

### K3 ▸ knowledge corpus index

Per the spec: chunk by heading, one whole-file chunk if a file has no headings —
**flagged**, since that is the case K3's citability argument breaks on. Hash per
file, re-chunk only what moved.

### K4 ▸ the match pass, with ordering

Per the spec's two-stage design — shortlist by similarity, confirm by a second
model call with the matched span quoted back. **Record both** the shortlist score
and the confirm verdict; a confirm step whose verdicts never disagree with the
shortlist is doing nothing, and you can only see that if both are kept.

Four outcomes now, not three:

| outcome | condition |
|---|---|
| **captured** | confirmed match in the project's own corpus |
| **gap** | no confirmed match in its own corpus, and no earlier claim it supersedes |
| **superseded** | conflicts with a claim already established from a **newer** conversation |
| **cross-project** | confirmed in another MCF project's corpus, absent from its own |

Cross-project stays **within MCF**. There is no cross-estate case by construction.

### K5 ▸ the compiled report

`data/knowledge_curator/report_<date>.md` — **not** `docs/`. It is regenerable,
so §1's rule and 0030 both keep it out. Sections in order:

1. **Not yet formalized** (gaps), per project.
2. **No knowledge file yet** — the recurrence-ranked starter list, for the 5
   projects that have none.
3. **Cross-project relevance** — within MCF.
4. **Superseded** — the trail, both statements quoted and dated.
5. **Confirmed captured** — counts per project plus a small sample.

Header: run timestamp, **model id**, conversations scanned, claims extracted,
quote-rejection rate, projects covered, projects unresolved — so a thin run reads
as thin rather than as a clean bill of health.

---

## Explicitly out of scope

- **Personal-estate content.** Not deferred — out.
- **K6 entirely** (cadence, dedupe, contradiction detection beyond ordering).
- Any write into a `KNOWLEDGE*.md` file, ever. The tool proposes; Tim edits.
- Any write to `chronicler.db` or the transcript store. Both are read-only inputs.
- A UI, scheduling, or coupling into the ingest pipeline.

## Stop conditions

- **Personal-estate transcripts are read** → stop. The scoping is the safety
  argument.
- **A report is written under `docs/`** → stop (0030, §1).
- **Ordering falls back to the relative label** (`"yesterday"`) or to file order
  when a real timestamp is missing → stop. Exclude and name instead.
- **The conversation map is derived rather than curated** → stop; that is 0011's
  alias contamination reinvented.
- **`quoted_source` verification is downgraded to a similarity score** → stop.
- **A partial report is emitted** after a stage failed → stop.
- **An artefact is produced without model provenance** → stop.

---

## UAT — acceptance checks (Tim walks these)

Mark each `[G]` / `[W]` / `[H]` per 0031.

- `[G]` No file is written under `docs/`; nothing is written to any transcript
  file or to `chronicler.db`.
- `[G]` Killing LM Studio mid-run produces **no report**, and says why.
- `[G]` A `quoted_source` that is not a literal substring is rejected; the
  rejection rate appears in the report header.
- `[G]` A conversation with an unresolvable timestamp is excluded and named.
- `[G]` Re-run with nothing changed re-extracts zero conversations.
- `[G]` K0 normalises both sides — a sheet entry differing only by a curly quote,
  an em dash or a doubled space still matches.
- `[G]` K0's two identical-opener rows are **accepted as a same-project pair and
  split by date**, and a synthetic different-project collision is **refused**.
- `[G]` A sheet entry shorter than 60 normalised characters never reaches pass 2.
- `[G]` All six K0 counts print, including the zeroes.
- `[H]` **Ratify K0's candidate map before anything is committed.** Read the
  evidence column, not just the answers. This is the one step where a wrong row
  becomes permanent.
- `[G]` A `local_*` folder present on disk but absent from the map is
  **reported**, not skipped. `rpm` and `.project-cache` are excluded by pattern,
  and adding a fake non-matching directory does not break the run.
- `[G]` Each conversation's timestamp source is recorded, and a conversation with
  no resolvable time is excluded and named.
- `[W]` K1 maps all 48 curated conversations by exact session id; the
  `PricingModel`/`PricingModelisation` and `ChurnLevelIndictor` cases are
  resolved explicitly and the resolution is visible.
- `[W]` A conversation spanning several transcript files (subagents or a resume)
  is treated as **one** conversation, ordered by the newest across them.
- `[W]` Title-prefix disagreements with the curated map are reported, not
  auto-resolved.
- `[H]` **The unmapped folders.** Look at what the run reports as present-but-
  unmapped. Are they conversations you deleted in the UI? If so, that answers a
  data-retention question about the work estate that is worth recording
  separately from this tool.
- `[W]` The five projects with no knowledge file get the recurrence-ranked
  starter list, not a 200-row gap dump.
- `[H]` **Spot-check 10 gaps.** Do the quoted spans support "this is genuinely
  not written down in that project"?
- `[H]` **Spot-check the Superseded section.** Is the newer statement actually
  the current truth, or has recency picked a casual remark over a considered one?
  This is the heuristic's honest weak point and the reason both are quoted.
- `[H]` **Spot-check 5 cross-project candidates.** Genuinely relevant, or generic
  phrasing over-triggering?
- `[H]` **Is the report readable top-to-bottom without opening the JSON?**
- `[H]` **Is the yield worth the pipeline?** Answered plainly, including if the
  answer is "not yet."

Results log needs a uat stamp naming the commit; no `gate=` field.

---

## Reporting

`docs/COWORK_REPORT_knowledge_curator.md`, walk-sheet
`docs/UAT_knowledge_curator.md`, stamped results after the walk.

Record the ratification, the curated map with every inconsistency resolution
named, the quote-rejection rate (a real measurement of the model's honesty on
this task), per-project yield rather than one total, and how often the
**Superseded** path fired — that section is the round's novel claim and if it
never fires, the ordering design bought nothing and should be said so.
