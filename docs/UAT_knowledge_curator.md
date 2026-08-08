# UAT walk-sheet — Knowledge Curator, K0–K5

**Brief:** `docs/COWORK_BRIEF_knowledge_curator.md`
**Report:** `docs/COWORK_REPORT_knowledge_curator.md`

**Built:** 2026-08-07, on `LucasGoonPC` (no MCF corpus, no Cowork store
beyond this toolkit's own, no LM Studio reachable). **Gate at build time:**
`python verify.py` → **GREEN**, 6 auditors + 65 testers (4 added by the
COWORK_BRIEF_curator_tab.md round, unrelated to K0–K5's own logic), all K0–K5 logic
covered by hermetic tests against synthetic fixtures and a stub model
caller. **Nothing walked yet** — every item below needs the real run on
`10280L` first. This is a skeleton, not a completed walk; do not read the
`[G]` items as passed just because the underlying code is gate-GREEN — gate
green is `verify.py`'s claim about the code, not a human's claim about the
output (0031).

Mark each `[G]` / `[W]` / `[H]` per 0031 once the real run has happened.

- `[ ]` `[G]` No file is written under `docs/`; nothing is written to any
  transcript file or to `chronicler.db`.
- `[ ]` `[G]` Killing LM Studio mid-run produces **no report**, and says why.
- `[ ]` `[G]` A `quoted_source` that is not a literal substring is rejected;
  the rejection rate appears in the report header.
- `[ ]` `[G]` A conversation with an unresolvable timestamp is excluded and
  named.
- `[ ]` `[G]` Re-run with nothing changed re-extracts zero conversations.
- `[ ]` `[G]` K0 normalises both sides — a sheet entry differing only by a
  curly quote, an em dash or a doubled space still matches.
- `[ ]` `[G]` K0's two identical-opener rows are **accepted as a
  same-project pair and split by date**, and a synthetic different-project
  collision is **refused**.
- `[ ]` `[G]` A sheet entry shorter than 60 normalised characters never
  reaches pass 2.
- `[ ]` `[G]` All six K0 counts print, including the zeroes.
- `[ ]` `[H]` **Ratify K0's candidate map before anything is committed.**
  Read the evidence column, not just the answers.
- `[ ]` `[G]` A `local_*` folder present on disk but absent from the map is
  **reported**, not skipped. `rpm` and `.project-cache` are excluded by
  pattern, and adding a fake non-matching directory does not break the run.
- `[ ]` `[G]` Each conversation's timestamp source is recorded, and a
  conversation with no resolvable time is excluded and named.
- `[ ]` `[W]` K1 maps all 48 curated conversations by exact session id; the
  `PricingModel`/`PricingModelisation` and `ChurnLevelIndictor` cases are
  resolved explicitly and the resolution is visible.
- `[ ]` `[W]` A conversation spanning several transcript files (subagents or
  a resume) is treated as **one** conversation, ordered by the newest
  across them.
- `[ ]` `[W]` Title-prefix disagreements with the curated map are reported,
  not auto-resolved.
- `[ ]` `[H]` **The unmapped folders.** Look at what the run reports as
  present-but-unmapped. Are they conversations you deleted in the UI? If
  so, that answers a data-retention question about the work estate that is
  worth recording separately from this tool.
- `[ ]` `[W]` The projects with no knowledge file get the recurrence-ranked
  starter list, not a raw gap dump.
- `[ ]` `[H]` **Spot-check 10 gaps.** Do the quoted spans support "this is
  genuinely not written down in that project"?
- `[ ]` `[H]` **Spot-check the Superseded section.** Is the newer statement
  actually the current truth, or has recency picked a casual remark over a
  considered one?
- `[ ]` `[H]` **Spot-check 5 cross-project candidates.** Genuinely relevant,
  or generic phrasing over-triggering?
- `[ ]` `[H]` **Is the report readable top-to-bottom without opening the
  JSON?**
- `[ ]` `[H]` **Is the yield worth the pipeline?** Answered plainly,
  including if the answer is "not yet."

Results log needs a uat stamp naming the commit once walked; no `gate=`
field beyond what the stamp format requires.
