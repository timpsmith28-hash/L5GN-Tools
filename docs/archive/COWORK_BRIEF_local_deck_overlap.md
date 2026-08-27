> **ARCHIVED** 2026-08-24 · superseded · no report — slice 3 of three; never built, and the precondition it names never closed
> Superseded by DECISIONS **0048** (a surface earns its place by the decisions it moves, not the facts it displays) and by `docs/archive/COWORK_BRIEF_unified_app.md`. Original purpose: make "have I written this down twice?" and "is this folder a copy of that folder?" into answerable questions.
> **The duplication figure it opens with — 165,246,539 bytes across 110 files, byte-for-byte identical on the castle — was measured on 2026-07-28 and is not a claim about now.** Same two reasons as slice 2: it depends on slice 1's authored/generated provenance, whose round never closed, and 0048 reclassified this kind of surface as the reference room. Note what did *not* lapse: `l5gntools/scanners/duplicate_finder.py` exists and the question is still answerable. What was abandoned is the deck surface over it, not the capability underneath.

# Cowork brief — the local deck, slice 3: overlap, duplication, and the thing nobody saw

**Origin:** design thread, 2026-07-28. Third slice of the local-only Command Deck.
**Depends on:** DECISIONS **0027** (ratified), **0026** (knowledge documents), and
slice 1's authored/generated provenance being in place.
**Deliverable:** "have I written this down twice?" and "is this folder a copy of
that folder?" become answerable questions.

Castle carries **165,246,539 bytes across 110 files, byte-for-byte identical, in
two places** — `data/Chronicler_Backup/raw_gem_files` and
`data/chat_threads/raw_gem_files`, with matching pairs under `raw_gemini_files`
and `raw_claude_files`. It sat there through every build, surfacing only as a
capped `file_census` payload with no stated cause, and was found by hand on
2026-07-28. **A duplicate finder exists and did not find it.** Understanding why
is most of this brief.

---

## Why `duplicate_finder` missed it — three precise gaps

Read the module before changing it; it is short and its two-view design is sound.
The gaps are in what it looks at, not how it works.

1. **`_SUFFIXES = (".py", ".json", ".sh")`.** Markdown is not scanned at all, so
   document duplication — the "have I written this knowledge twice" case — is
   invisible by construction.
2. **Cross-project only.** It groups files appearing in **≥ 2 projects**. Castle's
   duplication is *within* one project, so it could never register.
3. **File-level only.** Even with the first two fixed, 110 individually-duplicated
   files is 110 findings, not one obvious "this directory is a copy of that
   directory". The signal drowns in its own volume.

---

## The architecture — 0027 decides where each half lives, and it's clean

**Exact duplication is cheap and content-free: it belongs in the scanner.** A
hash and a fingerprint are summaries. They travel safely, they go in
`estate.json`, nothing changes about the deposit rule.

**Near-duplication requires reading content: it belongs in the local deck.** You
cannot tell "these two documents say the same thing differently" from a hash, and
the comparison material can never enter a deposited artefact. So it is computed
**at render time, locally, persisted nowhere** — exactly 0027.

That split is not a convenience. It is the reason this slice divides the way it
does, and the report should say so.

---

## Working rules

- Stdlib-only. Hashing is `hashlib`; similarity must be something you can explain
  in one sentence, not a black box.
- Gate GREEN before commit. Scanner changes need testers; the deck half too.
- **Authored documents only** for the document half. The estate holds 734
  generated docs, 227 of them near-identical campaign modules by construction —
  including them would produce a wall of true-but-useless findings.
- Nothing persisted by the deck half.
- **Never assert "identical" from a fingerprint.** See Task 3.

---

## Task 1 ▸ close the scanner's gaps

In `duplicate_finder`:

- **Add `.md`** to the scanned suffixes, restricted to **authored** documents
  (the provenance field from `87253c8`). State in the report how many new groups
  this surfaces on each estate.
- **Detect within-project duplication**, not only cross-project. Keep the existing
  cross-project view — it answers a different question ("is this a shared toolkit
  or copy-paste drift?") and both matter. Label which is which; do not merge them
  into one undifferentiated list.
- Keep the single-hash-feeds-both-views property. Do not add a second pass.

**Watch the cost.** Hashing every authored `.md` is trivial; hashing 165 MB of
`raw_gem_files` twice is not. The existing `Scope` skip and the data-directory
wall (`raw_*` / `*_files`) already exclude the latter from most scanners —
confirm what `duplicate_finder` actually walks before widening it, and report the
runtime change.

## Task 2 ▸ directory-level duplication — the Castle case

A new, deliberately cheap check: fingerprint each directory as
**(file count, total bytes, hash of the sorted basename list)**. Two directories
sharing a fingerprint are duplication *candidates*.

Castle would have surfaced instantly: 110 files, 165,246,539 bytes, identical
name sets, twice.

This is cheap because it needs no file content — it is arithmetic over data
`file_census` already collects. It is also **the check that would have caught the
thing nobody saw**, which is the argument for it.

Report candidates ranked by wasted bytes. A candidate pair covering 165 MB is
worth surfacing above one covering 4 KB.

## Task 3 ▸ candidate, not verdict — the honesty requirement

**A fingerprint match is a candidate. It is not proof.** Two directories can share
a file count, a byte total and a name set and still differ in content. Asserting
"identical" from a fingerprint is precisely the class of confident-wrong answer
this estate has been bitten by three times now.

So:

- The **scanner** reports `duplicate_candidate`, with the fingerprint evidence
  that made it a candidate. Never "identical".
- The **deck** offers "verify this pair" — hash the members at render time,
  locally, on demand, and report *confirmed identical* or *differs, here is where*.
  Verification is exactly the expensive content-reading operation 0027 puts on the
  local surface and keeps out of the artefact.

Confirmed status is a render-time result. It is **not** written back into
`estate.json`.

## Task 4 ▸ document overlap in the deck — the "written it twice" case

Near-duplicate detection across authored documents, computed locally.

- **Similarity must be explainable.** A token-set overlap over distinctive terms
  — stated as *"these two documents share N% of their distinctive tokens"* — is
  defensible to a cold reader. A tuned score nobody can account for is not.
  Slice 1's FTS index is available in memory and may serve as the primitive.
- **Present pairs with evidence**, never a verdict: the two documents, the
  overlap measure, and the shared passages that produced it, side by side.
- **Expect legitimate repetition and do not call it a defect.** READMEs share
  boilerplate; a brief copied as a starting template is good practice; the trinity
  files repeat by design. The useful finding is *two knowledge documents in
  different projects describing the same thing*, which is exactly what 0026 makes
  identifiable.
- Rank `knowledge`-typed pairs first (0026): those are the artefacts of record,
  and a knowledge base saying the same thing twice in two places is the failure
  mode worth catching.

---

## Report back, do not rule

- **Whether Task 2's directory fingerprints flag Castle's four duplicate pairs.**
  They should; if they do not, that is a finding about the check, not about
  Castle. Either way this is **evidence for the open 1.A2 ruling** — how a non-git
  folder's data directories get classified out with no `.gitignore` to do it.
  Gather it; the ruling stays Tim's.
- **The estate-wide wasted-bytes total** from confirmed-identical pairs. Castle
  alone is ~165 MB duplicated; the honest number for the whole estate is worth
  knowing before anyone decides what to delete.
- **Any deletion recommendation is out of scope.** Surface the duplication; do not
  propose or perform removals. That is a separate decision with a backup
  precondition (0005/0006).

---

## Explicitly out of scope

- The thread join (slice 4).
- Deleting, moving or deduplicating anything. Read-only throughout.
- LLM/inference-based similarity (0018/0019) — the whole point is a measure you
  can explain without one.
- Any change to what is *deposited* beyond Task 1's new hash groups and Task 2's
  fingerprints, both of which are summaries.

---

## UAT — acceptance checks (Tim walks these)

- **Castle's duplicate pairs appear** as directory candidates, ranked by wasted
  bytes, and verifying one confirms byte-identical.
- **A candidate that isn't identical reads as a candidate** — construct a pair
  with matching count/bytes/names but differing content, and confirm the deck says
  *differs* rather than asserting identity.
- **Document overlap finds a real pair** across the estate, with the shared
  passages shown. If it finds nothing, that is a legitimate result — say so.
- **Boilerplate is not reported as a defect.** READMEs and copied brief templates
  appear as expected repetition, not as findings demanding action.
- **Generated documents are excluded** — the 227 campaign modules do not appear.
- **Nothing was deleted, moved, or written back.** `estate.json` carries no
  confirmed-identical flag.
- Scanner runtime has not blown up; the report states the before/after.

Mark each **ready to walk**. Results log needs a uat stamp naming the commit; do
not write a `gate=` field.

---

## Reporting

`docs/COWORK_REPORT_local_deck_overlap.md`, walk-sheet
`docs/UAT_local_deck_overlap.md`, stamped results after the walk. Record the new
group counts per estate, the directory-candidate list with wasted bytes, the
Castle result in full, and the similarity measure as implemented — in the one
sentence it has to be explainable in.
