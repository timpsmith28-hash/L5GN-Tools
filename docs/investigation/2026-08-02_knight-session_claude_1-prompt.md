# Prompt — the knight session, 2026-08-02

**Date:** 2026-08-02 · **Model:** Claude (Cowork, design thread) ·
**Machines:** `l5gn-castle-worker` (knight, ssh `l5gn-castle`) and `LucasGoonPC`.

Captured per `docs/README.md` §4.

---

## The ask

> after that walk me through the commands for us to check the knight and we'll
> get it closed out.

The knight had not pulled since the golden apply. The stated goal was a
maintenance session: orient, back up, pull, gate, migrate the vault to the deck
schema, and see whether the surface would run there.

## The plan as issued

Seven phases, ordered so nothing destructive preceded the thing that made it
recoverable:

0. orient, change nothing
1. back up first — no backup, no pull
2. record the vault's before-state
3. pull and gate
4. migrate, dry run first
5. verify nothing moved
6. serve the deck, expecting thread routes degraded and the docs board enabled

## What it turned into

Phase 0 surfaced a modified `schema_frozen.sql` and 232 MB of vault data inside
the code repo. Chasing the first was routine. Chasing the second led, through
the knight's `data/estate.json`, to a scanner defect that had been shipping in
every deposit since 2026-07-25 and that the gate is structurally unable to
detect.

The maintenance completed. The findings below are what the session was actually
for, and none of them were being looked for.
