"""Mounts Datasette as an ASGI sub-app under the one server, replacing the
second `run.py serve` process (COWORK_BRIEF_unified_app.md Task 3).

**Verdict: mount it.** The brief's own test is "what did you actually use
it for since 0007? If the answer is arbitrary SQL over the corpus, mount
it." `docs/archive/UAT_apply_alignment_results.md` ("Task 10
re-verification", walked 2026-07-27 -- after the Command Deck already
existed per DECISIONS 0018, dated 2026-07-25) re-ran seven ad-hoc SQL
checks live against the vault via Datasette during the golden-apply
verification: row counts, an orphan check, a distinct-value count, and a
date-split diagnostic query that found the actual root cause of a 251-vs-225
discrepancy. That is exactly the load-bearing "arbitrary SQL" case the
brief distinguishes from "nothing since the deck landed" -- so this is not
the drop-it branch.

**Still serves a snapshot, never the live vault (DECISIONS 0013).** Moving
from a second process to a sub-app of the first does not touch that
reasoning at all: a co-resident writer -- this same process's own
`/api/rule` routes -- breaking Datasette's `--immutable` promise is the
identical failure 0013 diagnosed, regardless of the process boundary. The
snapshot is taken once, at app-build time, mirroring `run.py serve`'s old
contract exactly: the staleness note that used to say "re-launch `run.py
serve` to refresh" now says "restart the app" -- one fewer process to
remember to restart, not a new promise about freshness.

**What becomes of DECISIONS 0021 (the supervisor trio).** 0021 ruled that
one supervisor should bring up serve + review + deck together because the
knight was starting to run three long-lived processes. After this module,
there are zero processes to supervise for this half: Datasette is a
sub-app of the one process Task 4 makes the whole deck. 0021 is not wrong,
it is moot -- superseded by there being nothing left to coordinate. Record
it here rather than editing 0021 (the log is append-only); a future
DECISIONS entry can mark 0021 formally superseded when Task 4 lands the
single entry point.

Datasette stays an OPTIONAL extra (`pip install -e .[viewer]`), never
required like FastAPI/uvicorn became under 0034 clause 2 -- unlike the web
stack, the review app is fully useful without it (every route above this
module works with no vault-browsing sub-app at all), so the same
`available()` / graceful-skip discipline `app.py` already applies to
FastAPI applies here to Datasette.

**Two mounting gotchas, both found by actually testing this against a real
snapshot rather than trusting the API to behave as documented -- neither
is mentioned in Datasette's own docstrings, and both reproduce against
plain Starlette with no FastAPI or this codebase involved:**

1. **Lifespan is not forwarded.** `Datasette.app()` returns a
   spec-compliant ASGI app, but a `Starlette` `Mount()` (what
   `FastAPI.mount()` uses) does not forward the outer app's ASGI
   *lifespan* protocol down into a mounted sub-app. Datasette relies on
   that lifespan `startup` event to call its own `invoke_startup()`,
   which is what actually registers the database; without it every route
   404s with `"Database not found"` even though the file loaded without
   error. `app.py` calls `ds.invoke_startup()` explicitly from its own
   `@app.on_event("startup")` handler rather than trusting the mount to
   do it -- which is also why this function returns the `Datasette`
   instance itself, not just its `.app()`.
2. **`Mount()` does not strip the prefix for Datasette's own router.**
   Datasette does its own path handling via a `base_url` *setting*
   (default `"/"`), not by trusting whatever the ASGI `root_path`/`path`
   split looks like when it is mounted under a sub-path -- so even with
   (1) fixed, every route still 404'd. Passing
   `settings={"base_url": "/db/"}` -- matching the exact prefix `app.py`
   mounts this sub-app at -- fixed it. The two prefixes must stay in sync
   by hand; there is no way to derive one from the other across this
   module boundary, so if `app.py`'s mount path ever changes, this
   setting has to change with it.
"""
from __future__ import annotations

#: The single source of truth for the mount prefix. `app.py`'s
#: `app.mount(MOUNT_PATH, ...)` and this module's `Datasette(settings=
#: {"base_url": ...})` both read from here so the two cannot drift apart
#: (see the module docstring's gotcha (2)).
MOUNT_PATH = "/db"


def available() -> bool:
    """True iff the optional `datasette` package is importable."""
    try:
        import datasette  # noqa: F401
        return True
    except ImportError:
        return False


def build_datasette(machine: dict | None = None):
    """Take a fresh read snapshot and build the `Datasette` instance over it.

    Returns `(ds, note)` on success -- `ds` is the `Datasette` object itself,
    not `ds.app()`, because the caller needs both: the ASGI callable to
    mount, and `ds` to explicitly await `ds.invoke_startup()` (see the
    module docstring's note on why -- a `Mount()`'d sub-app's own lifespan
    is not invoked by the outer app's, so nothing calls it unless the
    caller does). `note` is the same staleness sentence `run.py serve` used
    to print, now meant for a log line or a startup banner. Returns
    `(None, reason)` when Datasette is not installed or there is no vault
    to snapshot yet -- both legal, reported rather than raised, so a
    machine with neither still boots the rest of the deck (the same shape
    as every other optional half in this app).
    """
    if not available():
        return None, ("datasette is not installed (optional extra: "
                      "pip install -e '.[viewer]')")

    from l5gntools import viewer

    try:
        snap = viewer.make_serve_snapshot(machine)
    except FileNotFoundError as exc:
        return None, str(exc)
    except Exception as exc:  # noqa: BLE001 -- any snapshot failure is fatal
        # here, never a silent fallback to the live DB -- falling back is
        # exactly the behaviour 0013 forbids.
        return None, (f"could not take the read snapshot "
                      f"({type(exc).__name__}: {exc})")

    meta_path = viewer.write_metadata(snap["dir"], snap["taken_at"],
                                      refresh_hint="restart the app")

    from datasette.app import Datasette
    # `immutables`, not `files` -- the file is opened read-only and Datasette
    # skips its own locking for it, same guarantee `--immutable` gives the
    # CLI invocation `run.py serve` used (`viewer.datasette_argv`). It must
    # NOT also appear in `files`, or Datasette opens it a second time without
    # that flag.
    #
    # `base_url` MUST match `MOUNT_PATH` below, and both must match the
    # prefix `app.py` actually calls `app.mount(...)` with -- see gotcha (2)
    # in the module docstring. Kept as one constant so the two call sites
    # cannot drift silently.
    ds = Datasette(immutables=[snap["snapshot"]], metadata=str(meta_path),
                   settings={"base_url": MOUNT_PATH + "/"})
    note = viewer.staleness_note(snap["taken_at"], refresh_hint="restart the app")
    return ds, note
