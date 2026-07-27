# Cowork brief — estate-scoped visibility: let a solo box read its own estate

**Origin:** design thread, 2026-07-27, preparing the work-laptop walk.
**Blocks:** testing the Command Deck against the MCF dataset.
**Depends on:** `DECISIONS.md` **0025** being ratified first — do not start until it is.

The deck implements 0023 as a hardcoded `t.account LIKE '%-personal'` allowlist in
both read paths. On the work laptop every thread is a work account, so the deck
renders "Nothing pending" against the one dataset with the cleanest program and
project definitions in the estate. 0025 narrows the rule: gate by **surface**, not
by estate label. This brief implements that narrowing, and nothing else.

**Read first:** `DECISIONS.md` 0010, 0023, **0025**; `chronicler/review/core.py`
(the `_PERSONAL_ACCOUNT_CLAUSE` comment block states the current intent
explicitly — read it before changing it); `tests/tester_review.py`'s wall
assertions; `docs/SOLO_PLAYBOOK.md` §10 (the `[WORK]` profile).

---

## Working rules

- Stdlib-only, `review/` keeps its package boundary. Gate GREEN before commit.
- **The loopback condition is the load-bearing half of 0025.** The estate filter
  becomes config-derived; the bind restriction must not be. A work-estate surface
  asked to bind beyond loopback **refuses to start** — not a warning, not a flag.
- No change to deposits, namespaces, or 0010. This governs display only.
- The TOTP gate is still unbuilt and still out of scope.

---

## Task 1 ▸ the filter becomes estate-scoped

Replace the constant with a clause derived from the running machine's declared
estate (`config.machine()["estate"]`), resolved **once at app construction** and
passed in — not read per-request, and not read inside `core.py`'s query builders
(`review/` must stay independent of config resolution the same way it stays
independent of `pipeline.db`).

- `personal` → `t.account LIKE '%-personal'` (today's behaviour, unchanged).
- `work` → `t.account LIKE '%-work'`.
- `both`, missing, or unrecognised → **refuse to serve.** A machine that cannot
  say which single estate it is rendering is exactly the co-rendering case 0023
  gates, and there is no gate yet. Fail loudly with the reason.

Keep the deny-by-default shape: an allowlist derived from one declared estate,
never a blocklist of labels to exclude. The existing comment block explaining
*why* it is an allowlist must be updated, not deleted — it is the reasoning that
stops someone reintroducing a blocklist later.

## Task 2 ▸ loopback enforcement on a work-estate surface

In `run.py review`'s preflight, before anything binds:

- If the machine's estate is not `personal`, the bind host must be a loopback
  address (`127.0.0.1` / `::1` / `localhost`). Anything else → **exit non-zero**
  with a message naming 0025 and the correct invocation.
- The `[WORK]` profile's documented default becomes `--host 127.0.0.1`.
- The knight's `0.0.0.0` default is unchanged for a `personal` estate.

This is the part that must not be bypassable by config. Derive the estate from
config; derive the *rule* from the code.

## Task 3 ▸ testers

In `tests/tester_review.py`, extend the wall assertions rather than replacing
them — the personal case must keep passing exactly as it does now:

- estate `personal`: a `*-work` thread never appears in `pending_rulings` or
  `queue_by_project`, filtered or unfiltered (today's assertion, unchanged).
- estate `work`: a `*-work` thread **does** appear; a `*-personal` thread does
  **not**. The mirror image, proving the filter is scoped rather than disabled.
- estate `both` / absent / junk: refuses to construct, with a message naming the
  reason.
- loopback enforcement: work estate + a non-loopback host → non-zero exit;
  work + loopback → proceeds; personal + `0.0.0.0` → proceeds.

## Task 4 ▸ the MCF-scoped registry, documented not built

A work box should carry a registry containing **only its own estate's** projects.
Nothing about the personal estate needs to exist on that machine, and the
smallest correct registry is also the smallest disclosure.

Document in `SOLO_PLAYBOOK.md` §10 how to produce and ship one. Check first
whether `build_registry.py` can already emit a scope-filtered registry from the
work rig's own scan — if it can, this is a playbook paragraph and nothing more.
**If it cannot, say so and stop** — do not build a filter in this brief; it is a
separate change with its own blast radius.

---

## Out of scope

The TOTP gate (0023); any co-rendered view; the run ledger; transcript intake;
anything else on the deck roadmap.

---

## UAT — acceptance checks (Tim walks these)

- **Personal rig unchanged.** The deck on the dev vault behaves exactly as it did
  at `00d590d` — same projects, same counts, no work thread anywhere.
- **Work laptop shows MCF.** The deck renders the work estate's pending queue,
  grouped by project, on loopback.
- **The mirror holds.** No personal-account thread appears on the work box (there
  should be none present, but the filter must be the reason, not their absence).
- **Loopback is enforced structurally.** `run.py review --host 0.0.0.0` on the
  work laptop refuses to start and names 0025.
- **An undeclared estate refuses.** Blank the machine's `estate` and confirm the
  deck will not serve.
- **Registry scope.** The work box's registry contains MCF projects only.

Mark each **ready to walk**. Results log needs a uat stamp naming the commit; do
not write a `gate=` field (see `UAT_solo_playbook_results.md`'s stamp comment).

---

## Reporting

`docs/COWORK_REPORT_estate_scoped_visibility.md`, walk-sheet
`docs/UAT_estate_scoped_visibility.md`, stamped results after the walk. Record
what the estate filter resolves to on each machine, and the exact refusal
messages, verbatim.
