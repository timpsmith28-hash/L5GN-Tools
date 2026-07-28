# Cowork brief — the local deck, slice 2: every finding becomes a line in a file

**Origin:** design thread, 2026-07-28. Second slice of the local-only Command Deck.
**Depends on:** DECISIONS **0027** (ratified) and **slice 1**
(`COWORK_BRIEF_local_deck_docs_and_time.md`) being landed — specifically its
path-safety machinery, which this slice reuses rather than reimplements.
**Deliverable:** a summary row in the report becomes "show me that line, in
context", read from disk at render time.

Today every finding is a count and a path. `todo_adr_scanner` records
`{path, line, tag, text}`, `blast_radius` records `{path, line, family, signal,
kind, guarded, tier}`, `env_scanner` records `{path, suspect_lines}`. All three
know exactly where the thing is and none of them can show it to you — by design,
because the report travels. 0027 removes that constraint for a local surface.

This is where render-time reading earns its keep: **`env_scanner` can show you
*where* a secret is without the report ever having held *what* it is.**

---

## Working rules

- Stdlib-only, read-only. **No write path in this slice.**
- Gate GREEN before commit; logic in testable functions, not route handlers.
- Nothing persisted — no cache of file content, nothing under `data/`.
- **Reuse slice 1's containment code. Do not write a second path resolver.** Two
  implementations of a security boundary is one more than can be kept correct.

---

## This slice widens the surface — say so, and re-prove it

Slice 1 reads **authored markdown inside the estate roots**. This slice reads
**source code, config files and anything else a scanner flagged**. That is a
materially wider blast radius for the same route family, and it is the reason
0027's condition (3) exists.

Requirements, all of them hard:

- The route takes an **opaque identifier** (project + finding index, or a hash of
  the finding), resolved against the in-memory finding list loaded from
  `estate.json`. **It never accepts a path, a line number, or an offset from the
  caller.** A finding that isn't in the loaded set cannot be rendered.
- The resolved path is verified to sit **inside the configured estate roots**
  before a byte is read — slice 1's check, called again here.
- **Re-run slice 1's containment testers against code paths**, not just markdown.
  Same two cases minimum: a resolved path outside the roots, and a traversal
  attempt through the identifier. If slice 1's tests only exercised `.md`, they
  do not cover this.
- **Only a window is rendered**, never a whole file. A cap (say 40 lines either
  side, state what you chose) with the target line marked. Whole-file reading
  belongs to slice 1's document viewer, which is restricted to authored docs for
  exactly this reason.
- **Refuse non-text and oversized files honestly.** A binary or a 50 MB file gets
  a stated refusal, not a hang and not a garbled render.

---

## The staleness problem — the design point of this slice

`estate.json` is a **snapshot**. The file on disk may have moved on since the
build: lines shift, code gets deleted, a marker gets fixed. A drill-down that
renders line 412 because a three-day-old scan said so will confidently show you
the wrong line, with no indication anything is off.

That is the "confident zero" failure this estate has now hit twice — MSIX
virtualisation, and MAX_PATH — in a third costume.

**Requirement: verify before rendering.** The finding carries what it expected to
see — a marker's `tag` and `text`, a blast-radius hit's `signal`, an
`env_scanner` suspect line. Before rendering, check the file's line still contains
it:

- **Match** → render the window normally.
- **Mismatch, but found nearby** (search a small window either side) → render the
  corrected location and **say the line moved since the build**.
- **Not found at all** → do not render a guessed window. State that the file has
  changed since `generated_at` and offer a rebuild. **An honest refusal beats a
  plausible wrong answer.**

Slice 1 shows the build's `generated_at`/`toolkit_commit` in the header; this
slice needs it per-finding, because here staleness is not cosmetic — it changes
whether what you're looking at is true.

---

## Task 1 ▸ the finding index

One in-memory list, built at startup from `estate.json`, of every drillable
finding across the three sources, each with: project, source scanner, path, line,
the expected-content token(s), and whatever the source carries for display
(`tag`/`text` for markers, `family`/`signal`/`kind`/`guarded`/`tier` for blast
radius, the suspect-line context for env).

One list means one identifier scheme, one containment check, and one staleness
check — rather than three drill-downs that drift apart. (The repo-tier producer
round is the precedent: four hand-rolled walks became one shared generator.)

## Task 2 ▸ markers in context

`todo_adr_scanner` markers, drillable. Filterable by tag (TODO / FIXME / HACK /
XXX) and by project.

Worth knowing before building: the **work estate has zero markers across all nine
projects** and the personal estate has 147, concentrated in `L5GN_Armory_v4`
(108). So this view is empty on the work rig by nature, not by fault — do not
treat an empty result as a bug, and make sure the UI says "none" rather than
looking broken.

## Task 3 ▸ blast-radius hits in context

The highest-value drill-down: the line that actually performs a prod write.

Tim's 2026-07-28 ratification of 3.C1/3.C3 recorded **one genuine prod-write hit
estate-wide** — a Salesforce write from the work laptop. That hit is the worked
example for this view: it should be reachable in two clicks and show the calling
line with enough context to judge it.

**`blast_radius`' guardrail is unchanged and must stay literally true**: the
scanner still stores no script body, alias or credential. The deck reads the line
live. Nothing captured changes.

## Task 4 ▸ suspected secrets — masked by default

`env_scanner`'s suspect lines. **This is the one that needs a deliberate ruling in
the code, not a default that happens to be convenient.**

- Render the line **masked by default** — enough to see the variable name, the
  file and the shape, not the value.
- **Revealing is a per-hit, explicit action**, like the deck's "Not this project"
  button: deliberate, one at a time, never a page-level toggle that unmasks
  everything at once.
- The revealed value is **never persisted, never logged, never placed in a URL**.
  Not in the route path, not in a query parameter — those end up in server logs.
- If the local surface ever renders on a shared screen, masking is the difference
  between a governance tool and an incident. Assume that will happen.

0027 permits reading it; it does not require showing it by default.

---

## Explicitly out of scope

- Cross-project document overlap (slice 3) and the thread join (slice 4).
- Any edit-in-place, "fix this marker", or write capability. Read-only, entirely.
- Any change to what the scanners capture. If a drill-down needs a field the
  scanner doesn't record, **report that rather than adding capture** — a scanner
  change alters the deposited artefact and is out of this slice's remit.
- LLM/inference (0018/0019).

---

## UAT — acceptance checks (Tim walks these)

- **The Salesforce prod-write hit is reachable in two clicks** and shows the real
  calling line with usable context.
- **A stale finding is caught.** Edit a file so a recorded marker moves, without
  rebuilding; confirm the deck either finds it nearby and says it moved, or
  refuses and says the file changed. **It must not silently render the wrong
  line** — this is the item I'd walk first.
- **Deleted target.** Delete a flagged file without rebuilding; confirm an honest
  refusal, not a stack trace.
- **Secrets are masked by default**, reveal is per-hit and deliberate, and the
  value never appears in a URL.
- **Containment holds for code paths**, not just markdown — a crafted identifier
  cannot escape the estate roots.
- **Binary and oversized files** are refused with a stated reason.
- **Empty is not broken.** On the work estate the markers view shows "none" and
  reads as a real answer.
- **Nothing persisted** after a browsing session.

Mark each **ready to walk**. Results log needs a uat stamp naming the commit; do
not write a `gate=` field.

---

## Reporting

`docs/COWORK_REPORT_local_deck_evidence.md`, walk-sheet
`docs/UAT_local_deck_evidence.md`, stamped results after the walk. Record the
staleness behaviour in all three cases (match / moved / gone) verbatim, the
containment tests against code paths, and the masking decision as implemented.
