# Cowork report — one application: the deck absorbs the report, the mesh stands down

**Brief:** `docs/COWORK_BRIEF_unified_app.md`
**Walk-sheet:** `docs/UAT_unified_app.md` · **Results:** `docs/UAT_unified_app_results.md`
**Built across:** `8ba9751`..`f1d7df3`, plus three live-walk fixes.
**Reported:** 2026-08-17, at `174e57e`.

---

## A provenance note this report has to carry

**This report was reconstructed from the tree, the commit series and the
module docstrings — it is not testimony from the build thread.** That thread
ended without writing one, which is the whole reason `unified_app` sat in the
board's *In flight* column with its code complete since `f1d7df3`.

`docs/README.md` §2 defines a report as *"testimony about a moment; its numbers
were true then and are not claims about now."* This one cannot honestly claim
that status. What it records is: what the code does at `174e57e`, what the
commits and docstrings say the build decided and why, and what the 2026-08-17
walk found. **Where the build thread's reasoning survives, it survives in the
module docstrings, and this report quotes them rather than paraphrasing** — an
account of a decision written by whoever made it beats a reconstruction of it.

It is also written **after** the walk rather than before, which inverts the
normal order. That gains one thing worth having: the report can state what the
acceptance walk actually found, instead of predicting it.

---

## 1. The 0034 ratification, and what ARCHITECTURE now says

**0034 is `accepted`**, ratified before the code, as the brief's precondition
required. Its four clauses landed:

1. `l5gntools/` — including every scanner — stays stdlib-only and read-only.
   `auditor_stdlib` and `auditor_readonly` keep their scope, unweakened.
2. The app tier declares its dependencies as required, not optional.
3. The dependency direction is one-way and **auditable**.
4. `available()` and `run.py review`'s loud skip retire for the app path.

Clause 3 got the enforcement the brief made a stop condition:
**`auditors/auditor_dependency_direction.py` exists and is green on every gate
run.** The brief was explicit that a round shipping the app split without it
would have *"weakened the stdlib contract in exchange for a promise"* — that
trade did not happen.

Clause 2 landed with a deliberate wrinkle worth recording, because it looks
like non-compliance and is not. `pyproject.toml` keeps FastAPI and uvicorn
under `[project.optional-dependencies].review` rather than moving them into
`[project.dependencies]`, and says why in a comment:

> `pip install -e .[review]` — the app tier (FastAPI/uvicorn) — **REQUIRED** to
> run `run.py app`/`window`, not a truly optional bolt-on; kept as an extra
> (not `[project.dependencies]`) so the stdlib-only `l5gntools` package itself
> stays unweakened — see DECISIONS 0034 clause 2.

The clause's *intent* — a missing web stack is an install error with a stated
remedy, not a legitimate configuration — is met in behaviour. The packaging
mechanism differs from the clause's literal wording, in service of clause 1.
Recorded plainly rather than smoothed over.

### ARCHITECTURE: §2 was rewritten, §3 was not

The brief stated that **ARCHITECTURE §3's boundary paragraph "becomes wrong the
moment this lands — rewriting it is part of the round, not a follow-up."**

**§2 was rewritten.** It now opens *"Shape: one application, with an optional
mesh mode"*, names `run.py app` / `run.py window` as the default, and cites
0035 and 0036. The README's loop diagram went with it, as Task 6 required.

**§3 was not.** It still describes exactly two subsystems — `l5gntools/` and
`chronicler/` — with no third tier, and **the string `0034` does not appear
anywhere in `docs/ARCHITECTURE.md`.** So the document that is meant to hold the
rationale for where the boundaries sit does not record the round in which one
of them moved: it does not say the app tier's dependencies are required, does
not name `auditor_dependency_direction` as what makes clause 1 survivable, and
does not describe the one-way import rule at all.

§3 is not *false* — nothing in it contradicts 0034 — but it is **silent about a
boundary that now exists**, which for a rationale document is the same failure
in a quieter costume. **This is an outstanding deliverable of this round, not a
follow-up**, and it is recorded here as unfinished rather than reported as done.

## 2. The module descriptor, as implemented

`chronicler/review/modules.py` — a flat list plus a by-id map, in code, with the
brief's `registry.py` instinct applied to the UI. `create_app` includes each
registered router; `/api/modules` renders the list; the browser builds its tab
strip from that response rather than from markup.

Nine modules are registered. The descriptor carries `id`, `label`, `order`,
`status`, `requires`, and — for migrated modules — `router` and `view`.

Two design choices in it are worth quoting because neither is obvious:

**`order` is spaced by ten.** *"so an eighth module can land between two
existing tabs without renumbering the file — a renumbering diff hides the actual
change inside noise."*

**`status=STATUS_LEGACY` is a real registration, not a placeholder.** A legacy
entry carries id, label, order and `requires` like any other and appears in the
tab strip; only its routes and pane remain inline in `app.py` / `index.html`.
Task 2 flips one by adding a router factory and a view file and changing one
word.

### The migrated tab, quoted in full

The brief asked for exactly one tab migrated alongside the registry. It was
`time`:

```python
    ModuleDescriptor(
        id="time", label="Time", order=40,
        status=STATUS_REGISTRY, requires=("estate",),
        router=estate_time.router, view="time.js"),
```

And the build's stated reason for choosing it:

> `time` is the migrated one. It was chosen for what it lacks: two read-only
> routes, both already living in `estate_time.py`, one `requires` (`estate`), no
> writes, no cross-pane calls, and a view whose helpers (`fmtDate` and four
> render functions) are used by nothing else in the file. **A tab that shared
> state with another pane would have proved the shell's boundary rather than
> the descriptor's.**

### The cost of migrating it, and the better proof

The brief's stop condition was *"Task 1 costs more than a day to migrate one
tab → the descriptor is wrong."* It did not trigger; the registry and the
migrated tab landed in one commit, as instructed.

**But the honest proof of the descriptor's claim is not `time` at all — it is
`report`.** Task 3's estate-report view was a genuinely new module, added
whole:

> `report` is the eighth module, added whole by Task 3 — **not a migration.** …
> Registering a genuinely new module here, rather than only flipping a `legacy`
> one, is the first real proof of the claim Task 1's UAT line makes — *"a new
> module is one registration plus one view file"* — ahead of that line's own
> throwaway-tab walk.

A ninth followed: `project_wizard`, registered by a later round (`e9ba614`)
without touching the registry's shape. **That is the strongest evidence
available that the descriptor holds** — an unrelated round adding a module by
one registration plus one view file, months of design pressure away from the
person who designed the seam.

## 3. Datasette: mounted, and what it was actually used for

**Verdict: mounted**, as an ASGI sub-app of the one server.

The brief made the decision turn on one honest question — *what did you actually
use it for since 0007?* — and the build answered it with evidence rather than
preference:

> `docs/archive/UAT_apply_alignment_results.md` ("Task 10 re-verification",
> walked 2026-07-27 — after the Command Deck already existed per DECISIONS 0018,
> dated 2026-07-25) re-ran **seven ad-hoc SQL checks** live against the vault via
> Datasette during the golden-apply verification: row counts, an orphan check, a
> distinct-value count, and a date-split diagnostic query that **found the actual
> root cause of a 251-vs-225 discrepancy.**

That is the load-bearing "arbitrary SQL over the corpus" case, used *after* the
deck existed — so it was not nostalgia for a superseded tool.

Datasette stays an **optional** extra (`.[viewer]`), unlike FastAPI/uvicorn.
The distinction is principled: every route above it works with no
vault-browsing sub-app at all, so the graceful-skip discipline 0034 clause 4
retired *for the app path* still legitimately applies here.

## 4. What became of 0013 and 0021

**0013 (serve a snapshot, never the live vault) — unchanged, and deliberately
so.** Moving from a second process to a sub-app does not touch its reasoning:

> a co-resident writer — this same process's own `/api/rule` routes — breaking
> Datasette's `--immutable` promise is the identical failure 0013 diagnosed,
> regardless of the process boundary.

The snapshot is still taken once at app-build time. The staleness note changed
from *"re-launch `run.py serve` to refresh"* to *"restart the app"* — **one
fewer process to remember, not a new promise about freshness.**

**0021 (the supervisor runs the read/review/deck trio) — moot, not wrong.**

> After this module, there are zero processes to supervise for this half…
> 0021 is not wrong, it is moot — superseded by there being nothing left to
> coordinate.

The build declined to edit 0021, correctly: the log is append-only. **It flagged
that a future entry should mark 0021 formally superseded once Task 4 landed the
single entry point. Task 4 landed. That entry has not been written** — recorded
here as outstanding.

## 5. The data root: resolution order, and why the move was deferred

**The physical relocation did not happen, by ruling.** 0035 clause 2 invoked the
brief's own stop condition (*"the data-root move puts the vault at any risk →
stop"*):

> Deferring is a **scheduling decision, not a technical one** — the mechanism is
> understood, the environment to execute it safely was not available here.

So Task 4 is **partial by ruling, not by omission**, and a cold reader should not
record it as unfinished work.

The resolution order that remains, and which 0035 names as the correct
foundation for the move when it happens, is config-driven throughout —
`l5gntools.config`'s `machines.json["default"] < machines.json[host] <
local.json["default"] < local.json[host]`, plus `viewer.resolve_db_path`'s env →
machine → default chain. Never hardcoded, per 0007 consequence (a).

**The migration step an existing install takes is therefore: none.** A
repo-resident install keeps working, unchanged, which satisfies the brief's
"must either keep working or be moved by a stated, single, reversible step" by
taking the first branch.

0035 clause 3 also declined a drive-by change the brief's framing invited: the
`producer`/`consumer` role vocabulary was **not** collapsed to `standalone`,
because `census.py`'s domain reporting stays meaningful regardless of mesh mode,
and *"changing a contract with its own test fixtures is exactly the kind of
drive-by widening this estate's own governance treats as a defect."*

## 6. The launcher, and how the second instance is refused

`run.py app` is the entry point; `run.py window` adds the desktop shell.
`serve` and `review` survive as deprecated aliases that print where they went —
not silently retired, per the brief.

**A second instance refuses.** The mechanism, and why it is a health check
rather than a pid check:

> a lock file (`data/app.lock`) names the port and pid of a running instance. A
> second launch checks whether that port still answers `/api/health` — **not just
> whether the pid is alive, which is a weaker and less portable check
> (`os.kill(pid, 0)` does not mean the same thing on Windows as POSIX)** — and if
> it does, refuses to start a second server against the same vault (INTENT §5:
> one writer) rather than attempting to focus another process's OS window, which
> has no simple cross-platform answer. **A stale lock … is harmless: the health
> check fails, and this launcher proceeds and overwrites it.**

Refuse rather than focus is the right call for the reason given — focusing is
not portably solvable — and the stale-lock case being *harmless by construction*
rather than *handled* is the stronger form.

**The window-fails-to-open path was exercised, not assumed:**

> `import webview; webview.create_window(...); webview.start()` was run by hand
> here and raised `WebViewException` with "You must have either QT or GTK with
> Python extensions installed". The fallback — print the loopback URL, leave the
> server running, wait on it — was exercised by hand too. **Never a silent exit.**

**One walk finding sits against this file.** H2 found that the app *sometimes
fails its first load on the work rig*, with a retry succeeding. `launcher.py`
sets `HEALTH_TIMEOUT_S = 20` with a 0.25s poll. Twenty seconds is not obviously
short, which makes the timeout the *suspicion* rather than the diagnosis — it
may equally be the window opening against a server that answers health before
it is ready to render. **Not diagnosed. Reproducible only on `10280L`, and the
results log records that timings must come before any change.**

## 7. Behind the `mesh` extra

Standing down, per 0036 — **mothballed, not deleted.** No code was removed.

| Now gated | Gate |
|---|---|
| `run.py deposit` | `_require_mesh("deposit")` |
| `run.py consume` | `_require_mesh("consume")` |
| `run.py intake`'s drop zone | `_require_mesh("intake")` |
| `deploy/` (push-exports, systemd units) | documented as mesh-mode in `deploy/README.md` |

All three commands still exist and report a stated refusal with a one-line
remedy — walked directly during the build, exit 1, correct text each time.

**The gate is config, not pip.** `pyproject.toml`'s `mesh = []` extra installs
nothing, and says so:

> `mesh` is deliberately empty: deposit/consume/intake's drop zone are
> stdlib-only, so there is no package to install. The gate is a machine config
> flag (`"mesh": true` in `config/machines.json` or `config/local.json`) …
> The extra exists so `pip install -e .[mesh]` reads correctly as documentation
> of the boundary.

**Cost of re-enabling: one config key.** `"mesh": true` on the machine, at the
same precedence as every other machine setting. No reinstall, no code, no
migration. The archived playbooks (`KNIGHT_PLAYBOOK.md`,
`PRODUCER_PLAYBOOK.md`) carry stamps naming 0036 and stating plainly that they
describe a configuration that still works and is not currently in use.

That is the cheapest possible mothball, and it is the reason 0036 could be taken
without an exit plan: there is nothing to undo.

---

## 8. Is the deck in a shape a design round can work on?

**Yes — and the walker's own answer is better evidence than this report's.**

Asked whether the eighth module is genuinely easy now, Tim answered that the
deck does not feel crowded, that he is happy with it as the current iteration,
and:

> *"for future passes on the UI front we'll now be able to start from a proper
> list of modules which we can then organise properly before we build
> everything."*

That is precisely the property this round existed to create, described by
someone who did not build it and was not looking for it. **The thing that did
not exist before was a list.** Seven tabs were hardcoded in markup across 1,620
lines with every pane's logic as top-level functions; there was nothing to
organise, only something to edit. There is now a list, in code, that an auditor
checks and that an unrelated round has already extended without touching its
shape.

Three things are still in the way of a design round, and none of them is the
architecture:

1. **ARCHITECTURE §3 is silent about the app tier** (§1 above). A design round
   that reads the trinity for the boundary will not find the one that governs
   the surface it is redesigning.
2. **The layer marker is parsed and never rendered** — carried from the
   `ui_witness` walk, and the clearest example of the UI having information the
   surface does not show.
3. **Six of nine modules are still `legacy`** — registered and in the tab strip,
   but with routes inline in `app.py` and panes in `index.html`. The descriptor
   is proven; the migration is a third done. A design round can work against the
   registry, but it will meet `index.html` sooner than it expects.

None blocks the design round. All three would make it cheaper, and the first is
this round's own unfinished deliverable.

---

## Outstanding from this round

1. **ARCHITECTURE §3** — rewrite for the app tier and 0034. Named by the brief
   as part of the round.
2. **A DECISIONS entry marking 0021 superseded** — flagged by the build,
   unblocked since Task 4 landed.
3. **Six `legacy` modules** to migrate, one at a time, per Task 2's own shape.
4. **H2's intermittent first load on `10280L`** — timings before changes.
