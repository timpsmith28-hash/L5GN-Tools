# Cowork brief — one application: the deck absorbs the report, the mesh stands down

**Origin:** design thread, 2026-08-08 (UI/UX thread, first round).
**Depends on:** DECISIONS **0007** (the read/write split and its column boundary),
**0013** (serve a snapshot, never the live vault), **0021** (the supervisor runs the
read/review/deck trio), **0025** (a solo box reads its own estate on loopback),
**0027** (a local surface reads the source at render time), and INTENT **§3**
("could I debug this at 2am") / **§5** (structural guarantees, one writer).
**Deliverable:** a **single application, started from a shortcut**, that holds the
scanners, Chronicler and the Knowledge Curator behind one shell — on one machine,
on loopback, with no network dependency.

---

## Why this round, stated honestly

The temptation is to describe this as "unifying three modules." That would be
flattering and false. **Chronicler and the Knowledge Curator are already one
application** — same process, same bind, same `create_app`, tabs six and seven of
seven. The review app has also quietly absorbed the estate reads (`/api/estate/*`),
the docs board, search and time. The consolidation this brief is named after is
largely a thing that already happened, one round at a time, without anyone
declaring it.

What is actually left is four smaller and less romantic problems:

1. **A second process serves a snapshot of a database the first process reads
   live.** `run.py serve` (Datasette, :8001) and `run.py review` (:8002) are two
   surfaces over one vault, with two staleness stories, needing 0021's supervisor
   to keep them alive together.
2. **`report.html` is frozen at build time.** 884 KB with the data baked in. It is
   the only estate surface that cannot answer "what is true now," and it is the
   first thing anyone opens.
3. **The tab strip cannot take an eighth module.** Seven tabs are hardcoded in
   markup; 1,620 lines of `index.html` carry them as global functions and `onclick`
   attributes behind a `showPane()` switch. More modules are coming. This is the
   part that breaks first, and it breaks quietly — by getting harder to change, not
   by failing.
4. **None of it is loadable.** Two terminals, two ports, a URL to remember, and a
   `pip install -e .[review]` that the code itself treats as optional.

Only (4) is what was asked for. (1)–(3) are what makes (4) worth doing rather than
a shortcut wrapped around a mess.

**The cross-machine mesh stands down in this round.** Not because it failed — it
works, and `deposit`/`consume` are among the cleaner things in the estate — but
because a single-machine application and a two-role mesh want different answers to
the same questions (where data lives, who binds what, what a "role" is), and
carrying both doubles every one of those answers. It is **mothballed, not deleted.**

---

## Rulings already taken (do not re-litigate)

| Question | Ruling |
|---|---|
| Shell | **A packaged local web app.** FastAPI on loopback + a window shell around it. **Not** Electron, **not** Tauri, **not** a native GUI rewrite. The UI is already HTML; replacing it buys appearance and costs the 2am test. |
| Where it lives | **Extend `chronicler/review`.** No new service, no new port, no second bind. Same argument as the curator round: two implementations of a boundary is one more than can be kept correct. |
| Datasette | **Mounted into the app or dropped.** Never a second process. Arbitrary SQL over the corpus is real value; a supervisor keeping two daemons alive on one box is not. |
| `report.html` | **Demoted from surface to export.** A view reads `data/estate.json` at render time (0027 authorises this). `run.py build` keeps producing the standalone file, because a file you can email is a different artefact from a screen. |
| The module list | **A code-declared descriptor registry**, mirroring `registry.py`. Not markup, not config. |
| Stdlib-only | **`l5gntools/` stays stdlib-only. The application layer does not.** The contract becomes a package boundary rather than a repo boundary — see 0034. |
| The mesh | **Mothballed behind a `mesh` extra; playbooks archived with stamps.** Code stays in the tree. |
| Visual design | **Out of scope this round.** This round builds the skeleton that a design round can then work on. Restyling now means restyling twice. |

---

## Precondition ▸ DECISIONS 0034 must be ratified before any code

`auditor_stdlib` and `app.available()` between them encode a claim: *this toolkit
runs on a bare Python and the web stack is a bolt-on you can decline.* `run.py
review` "skips loudly" for exactly that reason. If the application **is** the
product, that claim is no longer true, and shipping code that quietly contradicts
it is the sort of drift this estate keeps a decision log to prevent.

Draft the entry below, ratify it, commit it, and only then build. If it is ruled
against, the round still proceeds — but the window shell must handle a missing web
stack as a first-class state, and Task 5 grows a case it currently does not have.

> ## 0034 — The stdlib-only contract is a package boundary, not a repo boundary; the app tier is a declared dependency
>
> **Date:** 2026-08-08 · **Status:** proposed · **Amends:** the stdlib-only
> contract as recorded in ARCHITECTURE §3 and §6 · **Builds on:** 0007, 0025 ·
> **Source:** design thread
>
> **Context.** The read-only/stdlib contract exists to protect the *scanners*:
> they run against folders they must never write to, on machines whose Python
> environment is not guaranteed, and `auditor_stdlib` + `auditor_readonly` police
> that. That reasoning is entirely about `l5gntools/scanners/` and the package
> that carries them.
>
> It was then generalised into a property of the repository, and the review app
> was built as an *optional extra* to preserve it. That was right while the app
> was a bolt-on for applying ~19 rulings. It stops being right when the app is the
> way the system is used at all: `available()` returning False then describes a
> broken install, not a legitimate configuration, and reporting it as a graceful
> skip makes a defect look like a choice.
>
> **Decision.** The contract is scoped to what it was always protecting:
>
> 1. **`l5gntools/` — including every scanner — remains stdlib-only and
>    read-only, unchanged and unweakened.** `auditor_stdlib` and
>    `auditor_readonly` keep their present scope. Nothing in this entry permits
>    a scanner to grow a dependency.
> 2. **The application tier (`chronicler/review/`, the launcher) declares its
>    dependencies as required, not optional.** FastAPI and uvicorn move out of
>    `[project.optional-dependencies].review` and into the app's declared tier.
> 3. **The dependency direction is one-way and auditable: the app imports
>    `l5gntools`; `l5gntools` never imports the app.** This is the property that
>    makes (1) survivable, so it is enforced by an auditor, not remembered.
> 4. `available()` and `run.py review`'s loud skip are retired *for the app path*.
>    A missing web stack is an install error with a stated remedy, not a skip.
>
> **Consequences.** The repo can no longer claim "runs on a bare Python" without
> qualification, and ARCHITECTURE §3's boundary paragraph becomes wrong the moment
> this lands — rewriting it is part of the round, not a follow-up. The scanners
> remain independently installable and independently testable, which is the
> property that actually mattered; `verify.py` must keep proving it with no web
> stack present, or (1) is decorative.

---

## Working rules

- **No new port, no new bind, no new service.** Loopback only, per 0025 clause 3.
  0025's structural requirement stands: a work-estate surface asked to bind beyond
  loopback **refuses to start**. Do not weaken that while moving the bind code.
- **CORS comes out.** `allow_origins=['*']` is documented in `app.py` as acceptable
  *only* because of the tailnet bind. Loopback and same-origin remove the need
  entirely. Delete the middleware; do not leave it in as harmless. A justification
  whose stated reason has expired is a trap for the next reader.
- **Zero edits under `l5gntools/scanners/`.** If this round needs a scanner
  changed, the round is wrong. Stop and say so.
- **No framework, no bundler, no npm.** The UI shell is native ES modules and a
  hash router. Adding React to a repo whose whole argument is 2am-debuggability is
  a larger decision than this round and must be argued on its own.
- **Do not touch the vault schema.** Not one column, not one index.
- **Back up before the data-root move.** `run.py backup` exists. The vault is
  irreplaceable (INTENT §5); everything else in this round is a cache.
- Gate GREEN before every commit. `git commit -F <file>`, never `-m` with embedded
  newlines.

---

## Grounding — what exists today

| Surface | How it runs | State |
|---|---|---|
| `run.py <tool>` / `build` | CLI, stdlib-only | Fine. Not changed by this round. |
| `report.html` | file, 884 KB, data baked in | Stale by construction |
| `run.py serve` :8001 | Datasette over a snapshot | Second process, second staleness story |
| `run.py review` :8002 | FastAPI + uvicorn + StaticFiles | The real deck. 7 tabs, ~40 routes, ~6,500 lines |

Inside the deck: `index.html` is 1,620 lines with the tab strip hardcoded at
lines 260–267 and every pane's logic as top-level functions. `app.py`'s
`create_app` declares each route explicitly. Neither is broken; both are at their
ceiling, and the failure mode of a ceiling is that changes get expensive rather
than that anything goes red.

---

## Task 1 ▸ The module descriptor — give the UI what `registry.py` gives the scanners

A module declares itself; the app discovers it. One descriptor per module, in
code:

- `id`, `label`, `order`
- the router factory that contributes its routes
- the view module it loads in the browser
- **`requires`** — what it needs to function (vault, estate build, transcript
  store, LM Studio), so that **degradation is declared rather than coded per-route**.
  The deck already degrades per-route by hand in several places; this is that
  behaviour hoisted into data.

`create_app` iterates the registry. The tab strip is rendered from `/api/modules`,
not from markup. A new module is **one registration plus one view file**.

An auditor — `auditor_module_contract.py`, modelled on `auditor_tool_contract` —
proves it: every registered module carries every declared field, every view file
has a registration, no orphans in either direction.

**A second, distinct auditor is a required deliverable of this task, not a UAT
afterthought:** `auditor_dependency_direction.py` proves 0034 clause 3 — it walks
`l5gntools/`'s imports and fails on any import of `chronicler.review` or any other
app-tier module. It is not a variant of `auditor_module_contract`; that one proves
the descriptor is complete, this one proves the direction that makes 0034 clause 1
(scanners stay stdlib-only) survivable at all. Build it in the same commit that
first makes both tiers importable side by side — the UAT check on line "an auditor
fails a deliberate import of the app tier" is this auditor's proof, not a separate
thing to build later.

**Migrate exactly one tab in the same commit as the registry, and leave the other
six on the old path.** If both shapes cannot coexist, the descriptor is wrong and
the round has found that out cheaply.

## Task 2 ▸ Split `index.html`

A shell — nav, hash router, and the shared helpers that are currently loose
globals (`esc`, `jget`, `degraded`, `ago`, `fmtDate`) — plus one ES module per
view. Native `<script type="module">` imports; no build step.

The hash router is not cosmetic. Today a reload drops you back on the review
queue, and both the UAT sidebar and the curator lose their place — which is
precisely where losing your place is most expensive, because both are mid-walk
surfaces holding unsubmitted human judgement. **A view must be linkable and a
reload must land where you were.**

Carry over, unchanged, the escaping discipline already in the file: `snippetHtml`'s
comment is load-bearing and its rule — the highlight is applied **after** escaping,
so a document containing `<script>` cannot smuggle markup through a snippet — must
survive the split intact.

## Task 3 ▸ The estate report becomes a view; Datasette stands down or moves in

**The report view** reads `data/estate.json` at render time. 0027 already
authorises a local surface to read the source rather than a captured summary, and
this is exactly its case.

**Keep `l5gntools/report.py` and the standalone `report.html` build.** It is a
deposit artefact and a thing you can hand to someone with no application
installed. It stops being *the surface* and becomes *an export*, and the report
must say which of the two it is on its own face — a file that looks like the app
but holds a week-old snapshot is the "plausible wrong answer" INTENT §5 names as
the worst thing this system can produce.

**Datasette:** mount it as an ASGI sub-app under the one server, or drop it. Decide
by answering one question in the report: *what did you actually use it for since
0007?* If the answer is arbitrary SQL over the corpus, mount it. If the answer is
"nothing since the deck landed," drop it and say so.

Either way, record what becomes of **0013** (snapshot vs live) and **0021** (the
supervisor trio) — both dissolve or change shape here, and neither should dissolve
silently.

## Task 4 ▸ One entry point, one data root

`run.py app` replaces `serve` and `review`. Both old commands stay for one round
and print where they went.

**The data root moves out of the install tree.** `data/`, `chronicler.db` and
`config/local.json` currently live inside the repo, which a packaged application
must not write into. Resolution order stays config-derived — never hardcoded, per
0007's consequence (a) — and an existing repo-resident install must either keep
working or be moved by a **stated, single, reversible step**. Never silently.
Draft the ruling (0035) with this task; the migration behaviour is the substance
of it.

The machine role collapses from producer/consumer to a single `standalone`. Keep
the config indirection — it is what makes the data-root split possible at all.

## Task 5 ▸ The window

A launcher: start uvicorn on an **ephemeral loopback port**, wait on `/api/health`,
open a `pywebview` window, and shut the server down when the window closes.

- **Ephemeral, not 8002.** A fixed port is a collision waiting for the day two
  things want it.
- **A second instance must refuse or focus the first.** Two servers on one vault
  is a direct hit on the one-writer doctrine, and a launcher is exactly the place
  that mistake gets made.
- **A shortcut / `.bat`, not a frozen binary.** PyInstaller is its own round and
  its own class of pain.
- If the window fails to open, the fallback is a printed loopback URL and a working
  server — never a silent exit.

## Task 6 ▸ The mesh stands down

`deposit`, `consume`, `intake`'s drop zone and `deploy/` move behind a `mesh`
extra. **The commands keep existing** and report "mesh mode is not enabled" with
the one-line remedy. No code is deleted.

`KNIGHT_PLAYBOOK.md` and `PRODUCER_PLAYBOOK.md` archive via docs/README §3 route 2
(superseded), stamped, naming the ruling (0036) and stating plainly that they
describe a configuration that still works and is not currently in use.

**ARCHITECTURE §2 and §4 are wrong the moment this lands.** Rewriting them is part
of this task. The README's loop diagram goes with them.

---

## Explicitly out of scope

- **Any visual design.** Colours, type, spacing, layout language. This round makes
  design *possible* by giving the UI a shell and a module boundary; doing both at
  once means doing the visual work twice.
- Tauri, Electron, a frozen binary, an installer, auto-start, auto-update.
- **Auth / the TOTP gate.** 0023 remains unbuilt and 0025 clause 3 means this
  round does not need it. Do not build a stub.
- Any change to the scanners, the vault schema, the Chronicler pipeline, or the
  Curator's stages.
- Cross-machine anything: sync-back, deposits over the wire, the second rig.
- Performance work. Nothing here is slow yet.

---

## Stop conditions

- **Task 1 costs more than a day to migrate one tab.** The descriptor is wrong.
  Stop, report the shape that resisted, re-argue before continuing.
- **0034 is ruled against.** Task 5 grows a missing-web-stack case; do not proceed
  as if it landed.
- **`auditor_dependency_direction.py` (0034 clause 3) does not land.** Clause 3 is
  what keeps clause 1 from rotting — it is the whole reason a stdlib-only scanner
  package can sit beside a dependency-heavy app tier without the boundary being
  "please don't import that." A round that ships the app split without this
  auditor has weakened the stdlib contract in exchange for a promise, which is the
  trade INTENT §5 ("guarantees are structural, not behavioural") rules out. Stop
  and build it before merging, even if that costs Task 1's day-budget.
- **Datasette will not mount cleanly.** Drop it and record that — do not restore
  the second process to save the feature.
- **The data-root move puts the vault at any risk.** Stop. The vault is the one
  irreplaceable thing here; a working app with the DB where it is today is a
  complete success and Task 4 can be its own round.
- **The window shell fights the platform.** Ship the loopback URL fallback and
  report it. The round still delivers.

---

## UAT — acceptance checks (Tim walks these)

`[G]` = the gate or an auditor can prove it · `[H]` = only a human walking it can

- `[G]` `verify.py` is GREEN **in an environment with no web stack installed** —
  otherwise 0034 clause (1) is decorative.
- `[G]` An auditor fails a deliberate import of the app tier from inside
  `l5gntools/` (0034 clause 3 is enforced, not remembered).
- `[G]` Adding a module is one registration plus one view file. Prove it by adding
  a throwaway module in the walk and removing it after.
- `[G]` `auditor_module_contract` fails on a registration missing a field, and on
  a view file with no registration.
- `[G]` A module whose `requires` are absent renders as **declared-degraded with a
  named cause**, not as empty, not as broken, and not as an error page.
- `[G]` Reload on any view lands on that view. Deep-link to a view directly and it
  opens.
- `[H]` **Reload mid-UAT-walk and mid-curator-ratification.** Unsubmitted judgement
  is the thing most expensive to lose; find out what actually happens to it.
- `[G]` One process, one port, one bind, and that bind is loopback. `netstat` shows
  nothing else listening.
- `[G]` A work-estate machine asked to bind beyond loopback **refuses to start**
  (0025's structural requirement survived the move).
- `[G]` No CORS middleware remains anywhere in the tree.
- `[G]` The report view changes when `data/estate.json` changes, with no rebuild.
  The exported `report.html` does not, **and says so on its own face.**
- `[G]` Starting a second instance refuses or focuses the first. It never opens a
  second server on the same vault.
- `[G]` Killing the window stops the server. No orphan uvicorn.
- `[G]` The window fails to open (simulate it) → a loopback URL is printed and the
  server works. No silent exit.
- `[G]` `deposit` / `consume` / `intake` without the `mesh` extra report a stated
  refusal with a remedy — not a traceback, not silence.
- `[G]` The archived playbooks carry stamps naming the ruling, and nothing in core
  `docs/` still asserts a two-role mesh.
- `[H]` **Start it from the shortcut as if you had not built it.** Does it feel
  like an application, or like a terminal with a costume on?
- `[H]` **Is anything harder to find than it was across two ports?** Consolidation
  that buries a surface is a finding against this round.
- `[H]` **Could you debug it at 2am?** One process, one entry point — is the path
  from "the window is blank" to "here is the failing route" shorter or longer than
  it was with two daemons and a supervisor?
- `[H]` **Is the eighth module actually easy now?** Not "did the throwaway module
  work" — would you *reach for* adding one.

Results log needs a uat stamp naming the commit; do not write a `gate=` field.

---

## Reporting

`docs/COWORK_REPORT_unified_app.md`, walk-sheet `docs/UAT_unified_app.md`, stamped
results after the walk.

Record: the 0034 ratification and what ARCHITECTURE §3 now says; the module
descriptor as implemented, with the one migrated tab quoted in full and the cost
of migrating it; the Datasette verdict **and the honest answer to what it was used
for**; what became of 0013 and 0021; the data-root resolution order and the exact
migration step an existing install takes; the launcher's second-instance behaviour
and how it is enforced; and the list of everything now behind the `mesh` extra,
with a note on what re-enabling it would cost.

State plainly, at the end, whether the deck is now in a shape a **design** round
can work on — and if it is not, what is still in the way. That is the whole reason
this round runs before the one that was actually asked for.
