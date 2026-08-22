---
name: consultant-docs
description: Write and audit consultant documents — outside material condensed into the house format with a provenance header, plus a link-liveness check that reports status and never re-fetches. Use when adding an article, paper or vendor doc to docs/Consultants/, condensing an outside source, checking consultant headers, or asking whether a cited source is still reachable. Proposes only; never edits a body or silently refreshes a source.
---

# consultant-docs

Outside material is **informed opinion to weigh**, not instruction to follow.
This skill exists to keep that distinction legible after the context that made
it obvious has gone.

The failure mode it prevents is specific and slow: in six months a condensed
consultant document is indistinguishable from a house ruling — same folder,
same markdown, same confident prose — and a thread cites it as settled policy.
The header is what stops that, and an unheadered consultant doc is the defect.

## The standing rule

**A consultant document may be *cited* by a ruling. It may never *be* one.**
The ruling is always ours. A consultant doc that is allowed to stand as policy
is an argument from authority whose authority nobody checked.

## The header

Two parts, both required, both above the document's `# Title`. The comment
carries the machine-checkable fields; the blockquote carries the ones a human
reads. This is the same split the estate already uses for `uat:` stamps and
ARCHIVED stamps — deliberately, so a reader recognises the shape.

```
<!-- consultant: url=<absolute URL> retrieved=<YYYY-MM-DD> condensed=<true|false> checked=<YYYY-MM-DD> status=<HTTP status or unchecked> -->

> **CONSULTANT DOCUMENT** — outside opinion, not house policy. Cite it; never
> promote it to a ruling.
> **Source:** <publisher> — "<original title>" · <URL> · retrieved <YYYY-MM-DD>
> **Condensed:** <what was dropped, specifically — images, figures, a section
> summarised to prose. "Nothing" if verbatim.>
> **Kept because:** <one line: what this is *for* here. Not a summary of the
> article.>
```

Field notes, because each earns its place:

- **`condensed`** — condensing is fine and usually right, but a reader must be
  able to tell they are not looking at the source. Name what went, not that
  something went.
- **"Kept because"** is the field that decays first and matters most. A doc
  that does not say what it is *for* becomes an argument from authority the
  moment its context is gone. Write it as a reason this estate keeps the
  document, ideally naming the practice it converges with or challenges.
- **`checked` / `status`** are written by the liveness check below and by
  nothing else. `status=unchecked` is honest and acceptable; a fabricated
  status is not.

## Writing one — the condense pass

When adding a new source:

1. **Read the source.** Do not condense from a summary of it.
2. **Condense for what this estate would use**, not for general fidelity. A
   consultant doc is a working reference, not an archive of the article. The
   source URL is the archive.
3. **Never re-voice a conclusion as ours.** Keep attributive framing — "the
   author argues", "the piece claims" — wherever a claim is doing work. A
   condensed doc that reads as house prose is the failure this skill exists
   for, and it happens by accident during condensing more often than by
   intent.
4. **Preserve disagreements with house practice rather than smoothing them.**
   A consultant doc that only agrees with us is not worth keeping; the ones
   that argue against settled practice are the valuable ones, and condensing
   is where that friction quietly disappears.
5. **Write the header last**, from what you actually did — especially
   `condensed`, which is a record of the pass you just made.

## Auditing existing ones

Walk `docs/Consultants/*.md` and report, per file:

- header comment present, and every field parseable;
- blockquote present, above the `# Title`, with all four lines;
- `url` absolute and well-formed;
- `retrieved` a real date, not in the future;
- **"Kept because" is not a summary.** This is the one judgement call in the
  audit and it should be made and reported, not skipped: a line that
  paraphrases the article has not said what the document is for.
- body contains no first-person house voice ("we ruled", "our decision") —
  outside material must not read as ours.

**Report findings; fix nothing.** A missing header is proposed as a drafted
header for ratification, exactly as `docs-archivist` proposes a stamp. The
body is never edited: if a condensed doc reads as house prose, that is a
finding about the condense pass, and rewriting it silently destroys the
evidence.

## The liveness check

For each document, one **HEAD** request to its `url`, recording the status and
today's date into `checked` / `status`.

What this check does **not** mean, stated because the temptation is strong:

- **A 200 does not mean the claim still holds.** It means a page answered.
  Content behind a live URL changes; link-alive is not source-unchanged, and
  the check must never be reported as if it were.
- **A non-200 does not mean dead.** Many hosts refuse HEAD (405), block
  unknown agents (403), or rate-limit (429). Report the status; never report
  a verdict. If a status looks like a block rather than a removal, say which
  and why.
- **404 or a redirect to an unrelated page is a finding, not a repair job.**
  Record it in the header and raise it. Do not hunt for a replacement URL and
  quietly substitute it — a different URL is a different source, and swapping
  it in makes the provenance a lie.
- **Never re-fetch and update the body.** If the source moved on, the honest
  artefact is a *second* consultant doc with its own retrieved date, and a
  note on the first. The estate's posture on superseded testimony is that it
  is kept intact or removed, never corrected in place.

The check needs network, so it runs where network is: the machine holding the
repo, not a sandbox. If it cannot run, `status=unchecked` stands and the
report says the check did not run — never that the links were fine.

Batch politely: sequential, a short pause between hosts, and no retries beyond
one.

## Anti-patterns

- Editing a consultant body to fix its tone, its claims or its typos.
- Substituting a replacement URL for a dead one.
- Writing "Kept because" as a summary of the article.
- Reporting "links OK" when the check did not run, or could not run.
- Treating 403/405 as removal.
- Letting a consultant doc be cited as the *authority* for a decision rather
  than as input to one. If a ruling needs this doc to stand up, the ruling is
  not written yet.
- Adding a consultant doc with no "Kept because" on the grounds that it is
  obviously useful. That is exactly the doc that will be misread in six
  months.
