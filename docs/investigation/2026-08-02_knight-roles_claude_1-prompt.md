# Prompt — the knight's future roles: Historian, Chronicler, Shadow

**Date:** 2026-08-02 · **Model:** Claude (Cowork, design thread) · **Machine:**
`LucasGoonPC`

Captured per `docs/README.md` §4. Tim's framing is reproduced verbatim below
because, on the record of this estate, his framings have repeatedly *been* the
design — "if it just filtered to one project — I check them off" produced the
deck's whole shape; "knowledge is a decision that was made" produced 0026;
"local only" produced 0025 and 0027.

---

## The framing, in Tim's words

First pass, 2026-07-31:

> a thought about what the future of the Knight could look like - if we move to a
> model where the work and personal rigs manage their own estate data (allowing
> for a vastly enriched data set and capabilites of what we do with it via the
> local only model) - it may be we don't move beyond the current report model we
> have for the work rig but if we reverse the roles to some degree for the gaming
> rig and knight we can at least backup the gaming rig > knight and offload the
> "boring" compute tasks

Second pass, 2026-08-01, after the local deck slice 1 landed:

> further thoughts on the future of the knight - where it can serve is extended
> memory / capacity for offloading simple tasks / backing up - So he becomes a
> History Knight (I think we might add a historian to match the chronicler - a
> service that can be used in conjunction with the toolkit - responsible for safe
> backups and trends over time | chronicler is the front line linker, recorder
> and documentor. we can also have a shadow on the knight - running the slow half
> of the commit gate (he gets the throrough auditing checks - some of what's
> current been pushing into UAT etc)

## The task as scoped

Work the three-service split into a written design: charters, the boundary that
keeps each safe, what actually moves to the knight, what the backup does to the
disclosure surface, what the Shadow can construct that the pre-commit gate
cannot, and which DECISIONS entries this needs before any code.

Constraints:

- **No code.** Output is a design and a list of entries to draft.
- **Lands in `investigation/`** — outside the maintained lifecycle, no UAT.
- **Name what this breaks**, not just what it enables. In particular, whether
  the inversion changes the status of any ratified decision.

## Why now

This design exists only in a chat thread. `docs/README.md` §5 rules that
forward-looking items are carried manually into the next thread rather than
written down — which works for one item and does not work for a three-service
architecture. If it is not written now it evaporates with the context, which is
the specific failure §5 was not designed to cover.
