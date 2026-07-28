<!-- gate-frozen: commit=e565c98 -->

> **ARCHIVED** 2026-07-28 · completed pair · no separate results log — walked as Parts 2/3 of
> `UAT_work_rig_solo.md`, evidenced in `UAT_work_rig_solo_results.md`
> Superseded by: nothing — DECISIONS 0025 is the standing rule; this pair is how it was built.
> Accurate history: Task 4's finding (`build_registry.py --estate work` already scoped the
> registry, so nothing needed building) held in practice — 18 link-target ids on 10280L. The
> loopback refusal fired verbatim as designed.
> Stop trusting: UAT item 2.3 (undeclared-estate refusal) reads as ready to walk and was NOT
> walked; it is covered hermetically only. Read the walk evidence in the work-rig results log.

# UAT walk-sheet — estate-scoped visibility

Pair: `docs/COWORK_BRIEF_estate_scoped_visibility.md` → `docs/COWORK_REPORT_estate_scoped_visibility.md`.
Gate: `python verify.py` **GREEN**, 6 auditors + **46** testers (frozen). **Nothing
committed.** Status: **built, not walked** — no work laptop / MCF dataset in this
session. Mark each **ready to walk**, never "passed".

## Personal rig (`LucasGoonPC` / whichever gaming rig)

- [ ] **P1.** `run.py review` behaves exactly as it did at `00d590d` — same
  projects, same counts, no work thread anywhere in `pending_rulings` or
  `queue_by_project`, filtered or unfiltered. (`config[host]["estate"] ==
  "personal"` on this machine already — confirm with `run.py config`.)
- [ ] **P2.** `run.py review --host 0.0.0.0` (or the bare default) still binds
  and serves — the knight/personal default is unchanged by this brief.

## Work laptop (`10280L`)

- [ ] **W1.** `run.py config` on `10280L` reports `estate: work`.
- [ ] **W2.** `run.py review` (bare, no `--host`) on `10280L` **refuses to
  start** — exits non-zero, message names 0025 and `--host 127.0.0.1`. This is
  the load-bearing check: the shared `--host` default is `0.0.0.0`, so this
  must fail loudly, not silently bind.
- [ ] **W3.** `run.py review --host 0.0.0.0` on `10280L` **refuses to start**
  — exits non-zero, names 0025 and the correct invocation.
- [ ] **W4.** `run.py review --host 127.0.0.1` on `10280L` **starts** and
  renders the MCF pending queue, grouped by project.
- [ ] **W5.** The mirror holds: no `*-personal` thread appears on the work
  box's `review` — expected to be none present regardless, but confirm the
  *filter* is why (spot-check by temporarily seeding one `*-personal` row in a
  throwaway copy of the vault if none exists naturally, and confirm it does
  not surface, then discard the copy).
- [ ] **W6.** Blank `10280L`'s declared `estate` (comment it out or set to an
  unrecognised value) in `config/local.json` and confirm `run.py review`
  refuses to serve, naming 0025 — then restore it.
- [ ] **W7.** `chronicler/pipeline/build_registry.py --estate work` on
  `10280L`, pointed at `CHRONICLER_REGISTRY_PATH` for that machine, produces a
  registry containing MCF projects only (`--report-aliases` output shows only
  `estate=work` in ESTATE SOURCES).

---

## Recording the walk

Results log: `docs/UAT_estate_scoped_visibility_results.md` (new file), stamped
`<!-- uat: commit=<sha-walked-at> dirty=<bool> host=10280L walked=<date> -->` —
no `gate=` field (see `UAT_solo_playbook_results.md`'s stamp comment for why).
Record verbatim: what `run.py config` printed for `estate` on each machine, and
the exact refusal text from W2/W3/W6.
