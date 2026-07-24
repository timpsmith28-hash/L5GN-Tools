# Crystal Spire delve index — harvest and producer scoring

**Task F of** `docs/COWORK_BRIEF_intent_evidence.md`
**Date:** 2026-07-21 · **Read-only.** No floor content copied here; `modules_v3/`
was listed but never read into this document.

---

## Headline

The delve index harvests cleanly: **1,601 floors across 111 delves in 10 eras**,
and **all 111 delves map to a vault thread** by title, which is the labelled
dataset this estate has never had.

Then the scoring returned **precision 0.000 and recall 0.000** — zero overlap in
either direction.

**That is not a producer failure.** It is a measurement that the two sets
describe different things, and the *perfect* disjointness is what makes the
conclusion strong rather than weak. Detail in
[What the zero actually means](#what-the-zero-actually-means).

---

## 1. Structure — complete

`world_graph.json` holds 1,602 zones: 1,601 keyed `delve_<era>_<NNNN>_f<N>`
(e.g. `delve_foundingtheempire_0001_f1`) plus one `citadel_gate` entry room.

| Era | Floors | Delves |
|---|---:|---:|
| smeltingthelore | 201 | 9 |
| thechancellortrials | 194 | 7 |
| themanifestoreborn | 191 | 22 |
| foundingtheempire | 174 | 19 |
| chaoticchronotheory | 165 | 6 |
| modulizingthemass | 161 | 16 |
| chroniclesanddragons | 158 | 13 |
| obsidianempiremastery | 152 | 6 |
| thesovereignhandshake | 104 | 10 |
| industrialwizardry | 101 | 3 |
| **Total** | **1,601** | **111** |

Ten eras, matching the ten `ERA_DIGEST_*.md` files in the repo.

> **Which side of the mount boundary these numbers came from:** the **sandbox
> mount**, and that is now safe. `DRIVE_ID_SCAN.md` records the mount silently
> truncating `world_graph.json` and `world2.json` at ~12–13 MB. It no longer
> does. Measured today: `world_graph.json` reads 13,428,214 bytes and parses to
> 1,602 zones; `world2.json` reads 12,536,206 bytes and holds 1,601 `"floor"`
> records. Both match the host-side figures in that scan exactly, and a
> truncated JSON could not parse at all. Every count in this document is
> therefore whole-corpus.

## 2. Volume and Drive-ID lineage — thin, and only in one place

The brief expected a delve → era → volume → Drive ID chain. **The volume half
barely exists.**

- **13 volume names** are mentioned anywhere in the corpus.
- **Exactly one delve — 92 — carries manifests that bind a volume to a Drive
  ID.** Every other delve names volumes at most in passing.
- 11 distinct Drive IDs appear in those manifests.

This matches `DRIVE_ID_SCAN.md` independently: it found delve 92 to be the
hotspot, holding 18 of the 33 genuine IDs, and describes it as "a 136-floor
registry/manifest conversation." It is a conversation *about the manifest*,
which is why the lineage is concentrated there and absent elsewhere.

**Drive IDs are deliberately not reproduced in this document.** They are live,
and Task 0 has just finished removing that class of content from a git repo;
copying them into `L5GN-Tools/docs/` would recreate the exposure in a second
repo. `DRIVE_ID_SCAN.md` in Crystal Spire remains the authoritative list.

### Volume-name drift — a caveat for any future use

The same volume appears under several spellings:

| Cluster | Spellings observed |
|---|---|
| Manifesto Reborn Vol 1 | `TheManifestoRebornVol01`, `ManifestoRebornVol01` |
| Manifesto Reborn Vol 2 | `TheManifestoRebornVol02`, `ManifestoRebornVol02`, `ManifestationRebornVol02` |
| Manifesto Reborn Vol 3 | `TheManifestoRebornVol03`, `ManifestoRebornVol03` |

Any join on volume name needs normalising first. `ManifestationRebornVol02` in
particular is a corruption, not a distinct volume.

**Conclusion for the volume chain: it cannot support scoring.** A lineage
present for 1 of 111 delves is an anecdote.

## 3. Delve → vault thread — this is the part that works

The `modules_v3/` **filenames** carry the delve's source title:
`module_<Era>_<NNNN>_<TitleSlug>[_floorN].md`. De-camel-casing the slug and
fuzzy-matching against `threads.title`:

**111 of 111 delves match a vault thread at ratio ≥ 0.75**, most far higher:

| Delve | Slug | Matched thread title | Ratio |
|---|---|---|---|
| 0002 | EtlPipelineReviewAndOptimisation | etl pipeline review and optimisation | **1.00** |
| 0003 | GovernanceGapsInUniversalSystems | governance gaps in universal systems | **1.00** |
| 0007 | GoogleDriveFileNotFound | google drive file not found | **1.00** |
| 0005 | GifAnalysisWebWorkflowAndMetadata | gif analysis: web workflow and metadata | 0.99 |
| 0006 | V6MigrationControlTowerAnalysis | v6 migration control tower analysis | 0.99 |
| 0008 | V73UnifiedCommandBuildProgress | v7.3 unified command build progress | 0.97 |
| 0004 | ActivityStatementMigrationBenchmarkingAu | activity statement migration & benchmarking auditor | 0.93 |
| 0001 | ConsolidatingSpreadsheetsMethods | consolidating spreadsheets: methods and options | 0.84 |

**This settles the brief's first caveat.** It asked whether a delve maps to a
vault thread at all, given the world was forged from Drive-hosted stitched saga
volumes while the vault holds chat threads. **It does — comprehensively.** The
stitched volumes and the vault are drawn from the same conversations, and the
titles survived the round trip.

Only 110 distinct threads result from 111 delves — two delves match the same
thread, most likely a long conversation split across two delves.

## 4. Scoring

Ground truth: the 110 vault threads the delve index identifies.
Prediction: threads S4+S5 link to `L5GN-Crystal-Spire` at combined score ≥ 0.90.

| Metric | Value |
|---|---|
| Ground truth | 110 |
| Predicted | 14 |
| True positives | **0** |
| False positives | 14 |
| False negatives | 110 |
| **Precision** | **0.000** |
| **Recall** | **0.000** |

### What the zero actually means

Read the two sets before reading the metric.

**"False positives" — threads S4/S5 linked, absent from the delve index:**

> building a mobile delve menu browser · help me apply the fix discussed below
> to the attached `tui.py` · building a terminal-based d&d world for discord ·
> refactoring citadel's event-driven architecture · l5gn crystal spire

**"False negatives" — delve threads S4/S5 did not link:**

> google sheets audit tool development · kingdom building: picking up momentum ·
> sovereign os handshake & mission brief · activity statement logic context ·
> project file review request

The first list is threads **about building Crystal Spire**. The second is
threads **whose content was harvested into Crystal Spire's world**. A thread
about a Google Sheets audit tool became a delve because the forge turned it into
a dungeon floor — not because it was ever about the game.

**These are disjoint by construction, and the metric is measuring the gap
between two different questions:**

- S4/S5 answer *"which conversation built this project?"*
- The delve index answers *"which conversation became this project's content?"*

The producers scored 0.000 because they are **not wrong** — they are answering
the question they were designed for. Judged as project-linkage, the 14 "false
positives" look substantially correct on inspection: `tui.py`, delve menu,
terminal D&D world and "l5gn crystal spire" are all genuinely about the game.

**The delve index is therefore not a ground truth for producer scoring.** It is
something else, and arguably more interesting: a **provenance index** — a record
of which conversations were consumed as raw material. That is a different
relation from `project_link` and the schema has nowhere to put it.

### The honest limitation

This means the brief's ambition — "precision and recall, on real data, for the
first time in this estate's life" — is **not delivered**, and cannot be from
this dataset. The estate still has no labelled dataset for project linkage.
What it has now is a labelled dataset for *content provenance*, which is worth
having but answers a different question.

Building a real linkage ground truth still requires human labelling. The 14
threads above are a reasonable place to start: small, and the ones a person can
adjudicate quickly.

## 5. A finding that landed sideways — generic basenames

Crystal Spire's S4 hits are driven by these basenames:

| Hits | Basename | Owners in the estate |
|---:|---|---|
| 9 | `engine.py` | **1 (Crystal Spire only)** |
| 2 | `tui.py` | 1 |
| 2 | `similarity_report.md` | 1 |
| 1 | `world.json` | 1 |

`engine.py`, `tui.py` and `repl.py` are among the most generic filenames in
software, yet each is **unique within this 11-project estate** and therefore
scores **weight 1.0**, which alone exceeds `AUTO_LINK_THRESHOLD` (0.90) and
auto-links.

That is how "when I run `docker compose exec gateway mount | grep /data`" became
Crystal Spire's earliest evidenced thread in Task E — an `engine.py` attachment
on a thread with nothing to do with the game.

**Uniqueness within a small estate is not distinctiveness.** The stoplist tests
a hardcoded name list; the real signal is that a basename is *common in the
world* regardless of how many local projects happen to hold it. This is the
single highest-value fix to S4's precision and it is cheap: extend the stoplist
with the generic-but-locally-unique names, or weight by name commonality rather
than by local owner count alone.

## 6. Boundaries observed

- **Read-only throughout.** Nothing in Crystal Spire was modified by this task.
- **No floor content in this document.** Delve ids, era names, volume names,
  counts and thread titles only. Thread titles are Tim's own words from his own
  vault, not corpus content.
- **`modules_v3/` was never read.** Only its filenames were listed, which is
  where the title slugs live.
- **No Drive IDs reproduced.** Counted, never quoted.
- **No real names reproduced.** The gazetteer was not consulted or copied.
