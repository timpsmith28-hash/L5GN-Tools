# Prompt — re-measure the INTENT §2 coverage figure

**Handed to:** Claude (Cowork), 2026-08-27, on `LucasGoonPC`.
**Captured verbatim** under `CONVENTION_docs.md` §5: a Cowork round's output file
is a response; the brief that opened it is a prompt.

---

You're working in `C:\Users\timps\Documents\GitHub\L5GN-Tools` on host `LucasGoonPC`.

Read `CLAUDE.md` first -- it is the map and it carries the environment hazards.
Then `docs/INTENT.md` §2 and §6, which are the subject of this round.

The job: settle whether the estate's headline figure is still true, and report
the answer whichever way it goes.

`INTENT.md` §2 records the thesis -- that chat history linked to the code it
produced is a recoverable record of reasoning -- as 8.1% proven: 27 of 332
substantive threads (>=4 messages) carry a `link_evidence` link, against a
flattering headline of 150 links across 1,171 threads (12.8%). It calls 8.1%
"the single most important figure in this estate."

The hypothesis to test, and it is the operator's: that figure was measured
before conversations were properly grouped, so it may be an artefact of grouping
rather than of linking.

## What to do

1. **Establish the definition before the number.** State, in the report, exactly
   what you counted as a substantive thread, what counts as carrying an evidence
   link, and over what population. If your definition does not match INTENT's,
   the comparison proves nothing and the round has failed at its one job.
2. **Re-measure, scoped to the personal estate.** `DECISIONS` 0039 scopes this
   class of run to the estate declared for the machine, never more than one
   estate in a single run or output. A personal-only figure is the sanctioned
   shape, not a shortcut.
3. **Read-only against the vault.** INTENT §5: the scanners cannot write;
   detection and action are different programs.
4. **Report all three numbers:** the old figure, the new figure, and the delta
   attributable to grouping rather than to linking. If you cannot separate those
   two causes, say so -- that is a finding, not a gap to paper over.

## The measure that matters more than coverage

INTENT §2 states the real falsification test: ask the system a question only it
can answer -- "why was vocabulary killed as a linking signal?", "what was the
reasoning behind `similarity_threshold = 0.6`?" -- and see if it answers. As of
when INTENT was written it could not answer either.

Run that test too. A coverage figure that improves while those questions still go
unanswered would be the most important finding available today, and it would mean
coverage is the wrong proxy.

## Stop conditions

* The vault is unreachable, or the schema does not carry what INTENT's definition
  needs -> stop and say so. Do not substitute a nearby number.
* Your definition cannot be made to match INTENT's -> stop. Report the mismatch;
  a different number measured differently is not a correction.
* The new figure is worse -> report it plainly. INTENT §6 lists five failure
  modes and closes: "Any of these is a reason to stop or cut scope. None of them
  is a reason to add features." A worse number is a result, not a problem with
  the measurement.
* You find yourself choosing a definition because it produces a better figure ->
  stop. That is the failure this round is most exposed to.

## Containment

The vault holds work-estate conversations under `0051`. Counts cross; content
does not. Quoted spans are content (`0027`). Nothing from an MCF thread appears
in the output -- not a title, not a fragment, not an example.

## What lands

A dated measurement document. Place it per `docs/CONVENTION_docs.md`; if that
convention has no class for a measurement, say so rather than inventing a prefix
-- a new prefix is an amendment to that file, not a call made while naming one.

## What may not happen

Do not edit `INTENT.md`. If the figure has changed, propose the edit with its
exact wording and stop. INTENT is maintained in place, and changing the estate's
headline claim is the operator's act.

Do not run `git commit`. Draft any commit message to `data/git_warden/` and hand
back the command.
