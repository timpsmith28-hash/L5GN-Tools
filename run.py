#!/usr/bin/env python3
"""L5GN-Tools dispatcher / batch runner.

Read-only. Every tool takes the project folder as a target and writes its
output only under L5GN-Tools/data. Nothing is ever written into a scanned folder.

Usage:
    python run.py list                       # list available tools
    python run.py build                      # run everything -> data/ + report.html
    python run.py <tool> [--target NAME]     # one tool on one project
    python run.py <tool> --all               # one tool across the whole estate
    python run.py census [--target PATH]     # this machine reports its own domain

Chronicler-runtime commands (knight; resolve paths from CHRONICLER_HOME):
    python run.py app    [--port N] [--host H]   # the deck: queue + estate + docs
                                                  # board + UAT + curator + Datasette
                                                  # at /db, one process (Task 4)
    python run.py window                         # 'app' + a desktop window
                                                  # (ephemeral port, pywebview; Task 5)
    python run.py serve  [--port N] [--host H]   # DEPRECATED alias for 'app'
    python run.py review [--port N] [--host H]   # DEPRECATED alias for 'app'
    python run.py backup [--keep N] [--no-push]  # off-box VACUUM INTO snapshot
    python run.py scrape [urls.txt] [--force]    # Gemini share-scrape -> intake
    python run.py ingest [--skip-backup] [--skip-intake]   # backup -> intake -> pipeline
    python run.py conductor --plan-id ID          # run an APPROVED Knowledge
                                                  # Curator plan end-to-end
                                                  # (COWORK_BRIEF_conductor_
                                                  # governor.md's execution loop)

Mesh commands (COWORK_BRIEF_unified_app.md Task 6 / DECISIONS 0036 -- the
cross-machine mesh is mothballed, not deleted; these keep existing and print
a stated refusal + remedy unless this machine's config sets "mesh": true):
    python run.py deposit [--push]               # (producer) package + ship estate snapshot
    python run.py consume                        # (knight) ingest deposits + interpret sweep
    python run.py intake [--dry-run]              # (knight) unpack export zips only
                                                  # ('ingest' still runs with intake skipped)
"""
from __future__ import annotations

import argparse
import sys

from l5gntools.common import DATA_DIR, resolve_targets, write_json
from l5gntools.registry import BY_NAME, SCANNERS
from l5gntools.report import build_all, scan_subset


_MESH_REMEDY = ('set "mesh": true for this machine in config/machines.json '
                '(or config/local.json)')


def _require_mesh(label: str) -> bool:
    """True iff mesh mode is enabled; prints the stated refusal otherwise.

    COWORK_BRIEF_unified_app.md Task 6 / DECISIONS 0036: the cross-machine
    mesh (deposit, consume, intake's drop zone, deploy/) is mothballed, not
    deleted. Every command gated by this stays present and callable -- it
    just refuses with a one-line remedy instead of a traceback or silence
    when mesh mode is off, which is the default now."""
    from l5gntools import config
    if config.mesh_enabled():
        return True
    print(f"{label}: mesh mode is not enabled -- {_MESH_REMEDY}.", file=sys.stderr)
    return False


def _cmd_deposit(args: argparse.Namespace) -> int:
    if not _require_mesh("deposit"):
        return 1
    from l5gntools import deposit as dep
    try:
        r = dep.deposit(push=args.push, force=args.force)
    except (ValueError, FileNotFoundError) as exc:
        print(f"deposit: {exc}", file=sys.stderr)
        return 2
    print(f"deposit: estate '{r['estate']}' (role {r['role']}) -> {r['outbox']}")
    print(f"  snapshot : {r['snapshot'] or '(none yet -- run build first for history)'}")
    if r["pushed"]:
        print(f"  pushed   : OK -> {r['push_target']}/{r['estate']}/")
    elif r.get("push_error") or r.get("push_stderr"):
        print(f"  push     : FAILED -- {r.get('push_error') or r.get('push_stderr')}")
    elif r.get("note"):
        print(f"  push     : {r['note']}")
    elif r["push_command"]:
        print(f"  push cmd : {r['push_command']}")
        print("             (staged only; re-run with --push to send)")
    else:
        print("  push     : no push_target configured (set it in config/local.json)")
    return 0


def _chronicler_env() -> dict:
    """Environment for the vendored ingest subsystem: point it at the DB where
    `consume` reads it, and (optionally) at this machine's runtime data root."""
    import os
    from l5gntools import config
    m = config.machine()
    env = dict(os.environ)
    if m.get("vault"):
        env.setdefault("CHRONICLER_DB_PATH", m["vault"])
    if m.get("chronicler_home"):
        env.setdefault("CHRONICLER_HOME", m["chronicler_home"])
    return env


def _run_chronicler(script: str, args: list[str], env: dict) -> int:
    """Run a chronicler/pipeline script in its own process, so the stdlib-only
    core never imports pyyaml/embeddings."""
    import subprocess
    from pathlib import Path
    path = Path(__file__).resolve().parent / "chronicler" / "pipeline" / script
    if not path.exists():
        print(f"{script}: not found (is chronicler/ vendored?)", file=sys.stderr)
        return 2
    return subprocess.run([sys.executable, str(path), *args], env=env).returncode


def _cmd_intake(rest: list[str]) -> int:
    if not _require_mesh("intake"):
        return 1
    return _run_chronicler("intake.py", rest, _chronicler_env())


def _preflight_backup() -> bool:
    """Snapshot the vault off-box BEFORE ingest mutates it (DECISIONS 0005/0006).

    Returns True to proceed with ingest. A missing DB (first ever ingest) is a
    clean skip -- there is nothing to back up yet. A real snapshot failure ABORTS
    ingest: if we cannot capture the pre-ingest state off-box, we do not mutate
    it (loud-failure principle). A *push* failure only warns -- the local snapshot
    was still taken, and an off-box network hiccup must not block ingest work."""
    from l5gntools import backup, config
    m = config.machine()
    try:
        src = backup.resolve_db_path(m)
    except FileNotFoundError:
        print("ingest: [1/3] backup skipped (vault path unresolved)")
        return True
    if not src.exists():
        print("ingest: [1/3] backup skipped (no vault yet -- first ingest)")
        return True
    print("ingest: [1/3] pre-flight off-box backup")
    try:
        r = backup.make_backup(machine=m)
    except Exception as exc:  # noqa: BLE001 -- any snapshot failure must abort
        print(f"ingest: pre-flight backup FAILED -- {exc}. Aborting before ingest.",
              file=sys.stderr)
        return False
    print(f"  snapshot -> {r['snapshot']}  (kept {len(r['kept'])})")
    if r["backup_target"] and r["pushed"]:
        print(f"  off-box  -> {r['backup_target']}: OK")
    elif r["backup_target"]:
        print(f"  WARNING: off-box push FAILED -- {r['push_error']} "
              "(local snapshot kept; continuing).", file=sys.stderr)
    else:
        print("  off-box  : no 'backup_target' configured -- snapshot is LOCAL ONLY.")
    return True


def _cmd_ingest(rest: list[str]) -> int:
    """Pre-flight backup, unpack the drop zone (intake), then run the pipeline.
    `--skip-intake` runs the pipeline only; `--skip-backup` skips the pre-flight
    snapshot; all other args pass through to run_pipeline.py."""
    env = _chronicler_env()
    do_backup = "--skip-backup" not in rest
    do_intake = "--skip-intake" not in rest
    rest = [a for a in rest if a not in ("--skip-intake", "--skip-backup")]
    print(f"ingest: DB={env.get('CHRONICLER_DB_PATH', '<default>')}")
    if do_backup and not _preflight_backup():
        return 3
    if do_intake:
        from l5gntools import config
        if config.mesh_enabled():
            print("ingest: [2/3] intake drop zone")
            rc = _run_chronicler("intake.py", [], env)
            if rc != 0:
                return rc
        else:
            print(f"ingest: [2/3] intake skipped -- mesh mode is not enabled "
                  f"-- {_MESH_REMEDY}. Continuing with whatever is already in "
                  "the pipeline's raw/ (same as --skip-intake).")
    print("ingest: [3/3] pipeline")
    return _run_chronicler("run_pipeline.py", rest, env)


def _cmd_scrape(rest: list[str]) -> int:
    """Scrape a batch of Gemini share URLs into the pipeline intake dir (Task E).

    `python run.py scrape [urls_file] [--force] [--timeout MS]`. Resolves the URL
    list and the scraped_gemini/ output from CHRONICLER_HOME. Gated on playwright:
    if it (or chromium) is absent the stage is un-runnable, so this reports that
    explicitly and skips loudly rather than silently doing nothing."""
    import subprocess
    from pathlib import Path
    from l5gntools import scrape, config
    m = config.machine()
    if not scrape.playwright_available():
        print("scrape: playwright is NOT installed -- this stage is un-runnable here.\n"
              "        It is an optional extra; the knight is where it must be present:\n"
              "          pip install -e .[scrape]\n"
              "          playwright install chromium\n"
              "          playwright install-deps      # Ubuntu: system libs for headless chromium\n"
              "        Whether chromium is installed on the knight is load-bearing -- "
              "see KNIGHT_PLAYBOOK.", file=sys.stderr)
        return 2

    force = "--force" in rest
    rest = [a for a in rest if a != "--force"]
    timeout = None
    urls_arg = None
    it = iter(rest)
    for a in it:
        if a == "--timeout":
            timeout = next(it, None)
        elif not a.startswith("-"):
            urls_arg = a

    try:
        urls_file = Path(urls_arg) if urls_arg else scrape.resolve_urls_file(m)
        out_dir = scrape.resolve_scraped_dir(m)
    except FileNotFoundError as exc:
        print(f"scrape: {exc}", file=sys.stderr)
        return 2
    if not urls_file.exists():
        print(f"scrape: no URL list at {urls_file}. Put one Gemini share URL per "
              "line there -- copying share links out of Gemini into urls.txt is Tim's "
              "manual step (see KNIGHT_PLAYBOOK).", file=sys.stderr)
        return 2

    out_dir.mkdir(parents=True, exist_ok=True)
    argv = scrape.scrape_argv(urls_file, out_dir, force=force,
                              timeout=(int(timeout) if timeout else None),
                              python=sys.executable)
    print(f"scrape: {' '.join(argv)}")
    print(f"scrape: output -> {out_dir}  (the pipeline's reconcile stage consumes this;"
          " run `run.py ingest` next)")
    return subprocess.run(argv).returncode


def _cmd_consume() -> int:
    if not _require_mesh("consume"):
        return 1
    from pathlib import Path
    from l5gntools import config, consume
    m = config.machine()
    estates_dir = m.get("estates_dir")
    if not estates_dir:
        print("consume: no 'estates_dir' configured for this machine "
              "(set it in config/machines.json for the knight).", file=sys.stderr)
        return 2
    res = consume.sweep(Path(estates_dir))
    print(f"consume: swept {res['estates_dir']}  (vault: {res['vault_status']})")
    if not res["estates"]:
        print("  (no estate bundles found yet -- push one from a rig first)")
    for estate, r in res["estates"].items():
        ing = r["ingest"]
        print(f"  [{estate}] ingest={ing['status']} verified={ing.get('manifest_verified')} "
              f"snap={ing.get('snapshot')} | estate_diff={r['estate_diff']} | drift={r['drift']}")
    return 0


def _cmd_window() -> int:
    """The window (COWORK_BRIEF_unified_app.md Task 5). Delegates entirely to
    `chronicler.review.launcher` -- see that module for the actual logic
    (ephemeral port, health wait, pywebview, single-instance refusal, the
    fallback when no window backend exists)."""
    from chronicler.review import launcher
    return launcher.run()


def _cmd_backup(args: argparse.Namespace) -> int:
    """Standalone off-box vault snapshot: `python run.py backup`. Same engine the
    ingest pre-flight uses. Auto-pushes off-box unless --no-push is given."""
    from l5gntools import backup, config
    m = config.machine()
    try:
        r = backup.make_backup(keep=args.keep, push=not args.no_push, machine=m)
    except (FileNotFoundError, FileExistsError, OSError) as exc:
        print(f"backup: FAILED -- {exc}", file=sys.stderr)
        return 2
    print(f"backup: snapshot -> {r['snapshot']}")
    print(f"  kept ({len(r['kept'])}): {', '.join(r['kept'])}")
    if r["pruned"]:
        print(f"  pruned : {', '.join(r['pruned'])}")
    if not r["backup_target"]:
        print("  off-box: no 'backup_target' configured (set it in config/local.json) "
              "-- snapshot is LOCAL ONLY.")
        return 0
    if r["pushed"]:
        print(f"  off-box: OK -> {r['backup_target']}")
        return 0
    if args.no_push:
        print(f"  off-box: staged only (--no-push); would run: {r['push_command']}")
        return 0
    print(f"  off-box: FAILED -- {r['push_error']}", file=sys.stderr)
    return 1


def _cmd_conductor(args: argparse.Namespace) -> int:
    """`python run.py conductor --plan-id ID` -- runs an APPROVED Knowledge
    Curator plan end-to-end (COWORK_BRIEF_conductor_governor.md's execution
    loop, the brief's final built piece). Thin CLI shell over
    `chronicler.review.conductor_run.run_plan`, which does the real work
    (per-step re-validation, the governor + calibration ledger wired off the
    same timing stream, pacing between steps) -- everything here is argv
    parsing, loading the named plan, wiring Ctrl-C, and printing the result.

    A FIRST Ctrl-C requests a graceful stop: the step running right now is
    left to finish, and no further step is started. A SECOND Ctrl-C also
    cancels that in-flight step immediately (`curator_control.CancelToken`,
    Task 5's own primitive) -- see `conductor_run.RunControl`'s docstring
    for why one signal on its own can't tell these two intents apart."""
    import signal

    from chronicler.review import conductor_run as cr
    from chronicler.review import curator_control as ctl
    from chronicler.review import planner as pl

    if not args.plan_id:
        print("conductor: --plan-id is required.", file=sys.stderr)
        return 2

    registry = pl.PlanRegistry()
    registry.load_all()
    for err in registry.errors:
        print(f"conductor: WARNING -- malformed plan skipped: {err}", file=sys.stderr)
    spec = registry.get(args.plan_id)
    if spec is None:
        print(f"conductor: no plan '{args.plan_id}' found in {registry.root} "
              f"(known: {registry.list_ids()}).", file=sys.stderr)
        return 2

    control = cr.RunControl()

    def _on_sigint(signum, frame):
        if control.stop_after_step:
            print("\nconductor: second Ctrl-C -- stopping NOW (terminating the "
                  "in-flight step).", file=sys.stderr)
            control.request_stop_now()
        else:
            print("\nconductor: Ctrl-C -- finishing the current step, then "
                  "stopping. Ctrl-C again to stop immediately.", file=sys.stderr)
            control.request_stop_after_step()

    previous_handler = signal.signal(signal.SIGINT, _on_sigint)
    try:
        summary = cr.run_plan(spec, control=control)
    except (pl.PlanValidationError, ValueError) as exc:
        print(f"conductor: plan {args.plan_id!r} refused: {exc}", file=sys.stderr)
        return 2
    except ctl.ExecutionRefused as exc:
        print(f"conductor: {exc}", file=sys.stderr)
        return 2
    finally:
        signal.signal(signal.SIGINT, previous_handler)

    for r in summary["results"]:
        print(f"conductor: step {r.step_index} {r.project_id}/{r.stage} -> "
              f"{r.outcome.state} ({r.outcome.detail})")
        if r.paused_after:
            print(f"conductor:   governor paused {r.paused_after:.0f}s before the next step")
    if summary["stopped_early"]:
        print(f"conductor: stopped early -- {summary['stop_reason']}", file=sys.stderr)
        return 1
    print(f"conductor: plan {summary['plan_id']!r} complete -- "
          f"{len(summary['results'])} step(s) ran.")
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    """Launch Datasette read-only against a fresh SNAPSHOT (DECISIONS 0007 + 0013).

    Two guarantees, stacked. `--immutable` means the process cannot write, so
    single-writer is preserved structurally (0007). And what it is immutable
    *over* is a `VACUUM INTO` snapshot taken at launch, not the live vault (0013)
    -- because `--immutable` on a file another process is writing is what produced
    the false `database disk image is malformed` incident. Against a frozen copy
    the flag's promise is honestly true and a collision is impossible by
    construction.

    The cost is staleness, so this prints it plainly and puts it in the UI banner:
    a ruling made in `run.py review` after the snapshot is safe in the live vault,
    it simply is not in this copy until the next launch.

    Datasette is an optional extra; if it is absent this skips cleanly and loudly
    with the install hint (never silent-fails).

    **Deprecated (COWORK_BRIEF_unified_app.md Task 4).** `run.py app` mounts
    Datasette as a sub-app of the one process (Task 3) -- this second,
    standalone process is no longer necessary. Kept working, unchanged,
    for one round; it and `run.py app`'s `/db` can both run at once
    against the same vault without conflict (each takes its own
    independent snapshot -- see DECISIONS 0013), so there is no ordering
    requirement while both exist.
    """
    print("serve: this command is deprecated. Datasette is now mounted inside "
          "`run.py app` at /db -- this standalone process is no longer "
          "necessary. Still works, unchanged, for one round.", file=sys.stderr)
    import subprocess
    from l5gntools import viewer, config
    m = config.machine()
    try:
        db = viewer.resolve_db_path(m)
    except FileNotFoundError as exc:
        print(f"serve: {exc}", file=sys.stderr)
        return 2
    if not db.exists():
        print(f"serve: vault DB not found at {db} -- nothing to serve "
              "(is CHRONICLER_HOME / 'vault' set for this machine?).", file=sys.stderr)
        return 2
    if not viewer.datasette_available():
        print("serve: Datasette is not installed. It is an OPTIONAL extra, kept out "
              "of the stdlib-only core and the default install:\n"
              "         pip install -e .[viewer]", file=sys.stderr)
        return 2
    # Snapshot BEFORE launching: Datasette must never be pointed at the live file.
    try:
        snap = viewer.make_serve_snapshot(m)
    except Exception as exc:  # noqa: BLE001 -- any snapshot failure is fatal here
        # Loud failure, never a silent fallback to the live DB -- falling back is
        # exactly the behaviour 0013 forbids.
        print(f"serve: could not take the read snapshot ({type(exc).__name__}: {exc}). "
              "Refusing to serve the live vault instead -- that is the false-malformed "
              "path (DECISIONS 0013).", file=sys.stderr)
        return 2
    meta = viewer.write_metadata(snap["dir"], snap["taken_at"])
    argv = viewer.datasette_argv(snap["snapshot"], host=args.host, port=args.port,
                                 metadata=meta)
    print(f"serve: live vault   {snap['db']}")
    print(f"serve: snapshot     {snap['snapshot']}")
    print(f"serve: {viewer.staleness_note(snap['taken_at'])}")
    print(f"serve: {' '.join(argv)}")
    print(f"serve: read-only (--immutable, on a copy). From a phone on the tailnet: "
          f"http://<knight-100.x>:{args.port}/  |  on the LAN: "
          f"http://<knight-192.168.x>:{args.port}/")
    try:
        return subprocess.run(argv).returncode
    except KeyboardInterrupt:
        return 0


APP_DEFAULT_PORT = 8002  # distinct from serve's 8001 (deprecated but still
                        # runnable alongside 'app' for one round)
REVIEW_DEFAULT_PORT = APP_DEFAULT_PORT  # old name, kept as an alias


def _cmd_app(args: argparse.Namespace, argv: list[str], label: str = "app") -> int:
    """The single entry point (COWORK_BRIEF_unified_app.md Task 4; DECISIONS 0035).

    One process, one port: the queue/estate/docs-board/UAT/curator routes
    (DECISIONS 0007 stage 2's narrow write endpoint and everything the local
    deck grew around it) plus Datasette mounted as a sub-app at `/db`
    (Task 3) -- what used to be two separate commands (`run.py serve` +
    `run.py review`) on two separate ports. `run.py serve` and `run.py
    review` still work -- this function serves both, under a name that
    prints a deprecation notice first (see `_cmd_review`/`_cmd_serve`
    below) -- kept for one round per the brief, not deleted.

    Writes ONLY threads.project_link + project_confidence='manual' -- the pipeline
    owns every other column, so the two writers touch disjoint column sets and
    cannot collide (single-writer by column-scope, not by lock). Config-driven
    paths, bound 0.0.0.0 by default for tailnet + LAN on a `personal` estate.
    DECISIONS 0025: the deck renders only the running machine's declared
    estate, and a `work`-estate machine must bind loopback only -- enforced
    structurally below, not by the default. FastAPI/uvicorn are a REQUIRED
    dependency of this command as of DECISIONS 0034 clause 2 (no longer
    optional -- `available()` still reports absence and this still skips
    cleanly and loudly with the install hint, because a missing install is
    an install error, not a legitimate configuration to silently route
    around).

    The preflight is split by *what each route needs*, not one all-or-nothing
    check (local-deck slice 1). Vault-backed routes (the review queue) need the
    vault DB and the registry; estate-backed routes (documents, search, the
    timeline) need only `data/estate.json`. A machine with a vault and no
    estate build, and a machine with an estate build and no vault, must both
    serve -- so a missing half degrades that half and is reported, and only a
    machine missing *both* is refused, because then there is nothing to render.
    """
    from l5gntools import config
    from chronicler.review import app, core, doc_search, estate_data
    m = config.machine()

    # --- the vault half: may be absent on a plain producer rig ---
    db, registry, vault_gap = core.vault_preflight(m)

    # --- the estate half: may be absent on a machine that never runs build ---
    estate = estate_data.EstateData.load()

    # --- the curator half: a third route family (COWORK_BRIEF_curator_tab.md,
    # Task 1). Estate-labelled by construction (0032: MCF-scoped, work
    # estate only) -- `curator_estate_gap` disables every curator route with
    # the stated reason on any machine whose declared estate is not 'work',
    # so the tab renders a stated absence rather than curator data there
    # (stop condition). Loading data/knowledge_curator/ itself needs no
    # vault and no estate build -- it is independent of both other halves,
    # same preflight-split reasoning as the docs board.
    from chronicler.review import curator_data
    declared_estate_for_curator = m.get("estate")
    curator_estate_gap = None
    if declared_estate_for_curator != "work":
        curator_estate_gap = (
            f"this machine's declared estate is {declared_estate_for_curator!r}; "
            "the Knowledge Curator is scoped to the work/MCF estate only "
            "(DECISIONS 0032) and renders no data anywhere else.")
    curator = curator_data.Curator()

    if db is None and not estate.available:
        # Both data halves absent. This used to be the refusal case, and was,
        # while every route needed one of them. The docs board needs neither:
        # it derives from `docs/` in this checkout, which is present by
        # construction wherever this file is. So the preflight split runs to
        # its conclusion -- the surface serves the one route whose dependency
        # is satisfied and says plainly what it hasn't got.
        print(f"{label}: this machine has neither a vault nor an estate build.",
              file=sys.stderr)
        print(f"{label}:   vault  -- {vault_gap.detail}", file=sys.stderr)
        print(f"{label}:   estate -- {estate.reason} at {estate.source}",
              file=sys.stderr)
        print(f"{label}: serving the docs board only. Run `python run.py build` "
              "for the estate views, or point CHRONICLER_HOME at a vault for "
              "the review queue.", file=sys.stderr)

    if not app.available():
        # DECISIONS 0034 clause 2/4: FastAPI/uvicorn are REQUIRED for the app
        # tier -- this is an install error with a stated remedy, not a
        # graceful "optional feature" skip. They stay a pip extra (not
        # [project.dependencies]) only so `l5gntools/` itself stays
        # stdlib-only and independently installable -- that split is what
        # `auditor_stdlib`/`auditor_dependency_direction` still prove with
        # no web stack present, not a claim that the app runs without one.
        print(f"{label}: FastAPI/uvicorn are not installed -- required to run "
              f"{label}. Kept out of the stdlib-only l5gntools/ core "
              "(DECISIONS 0034), but not optional for this command:\n"
              "         pip install -e .[review]\n"
              "         (or .[desktop] if you're launching `run.py window`)",
              file=sys.stderr)
        return 2

    # DECISIONS 0025: the estate wall is config-derived, resolved ONCE here and
    # passed down -- app.py/core.py never read config themselves. An
    # unrecognised estate ('both', missing, junk) is exactly the co-rendering
    # case 0023 gates, and there is no gate yet, so this refuses loudly rather
    # than picking a default.
    # (`declared_estate` -- the config string -- is deliberately not named
    # `estate`, which now holds the loaded snapshot. Two different things.)
    # The clause scopes THREADS, and only threads: it is a `t.account LIKE ...`
    # predicate on the vault's queue tables. So an unresolvable estate must
    # disable the routes that read threads -- not the process. Estate documents
    # and the toolkit's own docs/ are not estate-labelled data, carry no
    # account column, and are governed by 0027's containment rule instead;
    # refusing to start over a clause they never use would take the docs board
    # off every machine whose declared estate is not exactly 'personal' or
    # 'work', for a wall it does not stand behind.
    #
    # The wall itself is untouched, and is if anything tightened: a machine
    # that cannot name one estate now serves NO thread, where before the same
    # condition was a startup argument that a later refactor could have
    # softened into a default. Deny-by-default, scoped to what the clause
    # actually governs.
    declared_estate = m.get("estate")
    estate_clause_gap = None
    try:
        account_clause = core.account_clause_for_estate(declared_estate)
    except ValueError as exc:
        estate_clause_gap = str(exc)
        account_clause = None
        db = None  # vault routes off: _need_vault() 503s them, uniformly
        # A gap the queue routes can state. `vault_preflight` may have found a
        # perfectly good vault -- the reason this machine serves no thread is
        # the unresolved estate, and the 503 must say so rather than claim a
        # missing DB that is sitting right there.
        vault_gap = core.VaultUnavailable(
            "estate_unresolved",
            f"Thread routes are disabled on this machine: {exc}")

    if db is None and estate_clause_gap and not estate.available:
        print(f"{label}: {estate_clause_gap}", file=sys.stderr)
        print(f"{label}: and this machine has no estate build either, so there "
              "is nothing left to render.", file=sys.stderr)
        return 2

    # DECISIONS 0025's load-bearing half: the loopback rule is NOT config-derived
    # and must not be bypassable by it. Any NON-PERSONAL estate asked to bind
    # beyond loopback refuses to start -- not a warning, not a flag. This also
    # supplies 0027's condition (2) for the document routes for free: the only
    # non-loopback surface permitted is a personal-estate one on its own machine.
    #
    # The message says "non-personal", not "work". The condition has always been
    # `!= "personal"`, but until the estate clause was scoped to the vault half
    # an unrecognised estate exited at the clause check and never reached this
    # line -- so in practice only `work` ever saw it, and the wording was true
    # by accident. It is now reachable with `both`, where "a work-estate
    # surface" contradicts the value printed in the same sentence.
    if declared_estate != "personal" and not core.is_loopback_host(args.host):
        print(
            f"{label}: refusing to bind {args.host!r} -- this machine's declared "
            f"estate is {declared_estate!r}, and DECISIONS 0025 requires any "
            "non-personal estate to bind loopback only "
            "(127.0.0.1 / ::1 / localhost). Run with --host 127.0.0.1.",
            file=sys.stderr)
        return 2

    # The search index is built here, in memory, once -- never written to disk
    # (DECISIONS 0027 condition 1). Skipped entirely when there is no estate.
    index = doc_search.DocumentIndex(estate) if estate.available else None

    port = args.port if "--port" in argv else REVIEW_DEFAULT_PORT
    if db is not None:
        print(f"{label}: vault DB={db}")
        print(f"{label}: registry={core.resolve_registry_path(m)} "
              f"({len(registry)} link-target ids)")
        print(f"{label}: queue routes ENABLED -- writes ONLY project_link + "
              "project_confidence='manual'")
    else:
        print(f"{label}: queue routes DEGRADED -- {vault_gap.detail}")
    if estate.available:
        head = estate.header()
        dirty = " (toolkit dirty)" if head.get("toolkit_dirty") else ""
        print(f"{label}: estate build={head.get('generated_at')} "
              f"commit={head.get('toolkit_commit')}{dirty}")
        print(f"{label}: estate routes ENABLED -- {head.get('project_count')} projects, "
              f"{head.get('authored_document_count')} authored documents, "
              f"search engine={index.status()['engine']}")
        if index is not None and index.notice:
            print(f"{label}: {index.notice}")
        for warning in head.get("warnings", []):
            print(f"{label}: estate warning -- {warning}")
    else:
        print(f"{label}: estate routes DEGRADED -- {estate.reason} at {estate.source}")
    if estate_clause_gap:
        print(f"{label}: estate={declared_estate!r} -- NO thread is rendered on "
              "this machine (DECISIONS 0025: a surface that cannot name one "
              "estate shows none). Document routes are unaffected -- docs/ and "
              "the estate build are not estate-labelled data.")
    else:
        print(f"{label}: estate={declared_estate!r} -- rendering only that estate's "
              "threads (DECISIONS 0025)")
    if curator_estate_gap:
        print(f"{label}: curator routes DEGRADED -- {curator_estate_gap}")
    else:
        print(f"{label}: curator routes ENABLED -- data_dir={curator.data_dir} "
              f"available={curator.available}")
    print(f"{label}: binding {args.host}:{port}")
    print(f"{label}: phone on the tailnet: http://<knight-100.x>:{port}/  |  "
          f"on the LAN: http://<knight-192.168.x>:{port}/")
    print(f"{label}: Datasette mounted at /db (sub-app, snapshot per request "
          f"DECISIONS 0013/0007; COWORK_BRIEF_unified_app.md Task 3) -- "
          f"see GET /api/health for whether it actually came up on this run.")
    try:
        return app.run(db, registry, host=args.host, port=port,
                       account_clause=account_clause, estate=estate,
                       index=index, vault_unavailable=vault_gap,
                       curator=curator, curator_estate_gap=curator_estate_gap,
                       machine=m)
    except KeyboardInterrupt:
        return 0


def _cmd_review(args: argparse.Namespace, argv: list[str]) -> int:
    """Deprecated name for `_cmd_app` (COWORK_BRIEF_unified_app.md Task 4).

    Kept working for one round, per the brief -- printing where it went is
    the whole job of this wrapper, not a warning nobody reads and an early
    return. `argv` is still needed (not `args`) because `_cmd_app` checks
    `"--port" in argv` to tell "the user passed --port" from "argparse's
    default happened to equal it" -- see `REVIEW_DEFAULT_PORT` below.
    """
    print("review: this command moved. `run.py review` and `run.py serve` are "
          "now one process: `run.py app`. Both old names still work this round "
          "and print this notice; there is no functional difference below.",
          file=sys.stderr)
    return _cmd_app(args, argv, label="review")


def _cmd_census(args: argparse.Namespace) -> int:
    """Role-aware machine census (Task C).

    A consumer never runs `build`, so `file_census` alone leaves the knight
    invisible. This asks whichever machine it runs on to describe its own ground:
    a producer's configured roots, or the knight's code root plus vault root.
    Paths come from config; nothing is hardcoded.
    """
    from pathlib import Path
    from l5gntools import census as cen
    from l5gntools import config
    m = config.machine()
    try:
        report = cen.run_census(machine=m,
                                target=Path(args.target) if args.target else None)
    except FileNotFoundError as exc:
        print(f"census: {exc}", file=sys.stderr)
        return 2
    for line in cen.format_summary(report):
        print(line)
    return 0


def _cmd_config() -> int:
    from l5gntools import config
    m = config.machine()
    print(f"hostname : {m['_hostname']}"
          f"{'' if m['_matched'] else '   (no matching entry -> using default)'}")
    print(f"role     : {m.get('role', '(unset)')}")
    print(f"estate   : {m.get('estate', '(unset)')}")
    roots = config.estate_roots()
    if roots:
        print("roots    :")
        for r in roots:
            print(f"  - {r}{'' if r.exists() else '   (MISSING)'}")
    else:
        print("roots    : (none configured -> legacy sibling discovery)")
    for key in ("vault", "estates_dir", "push_target"):
        if m.get(key):
            print(f"{key:<9}: {m[key]}")
    return 0


def _cmd_list() -> int:
    print("Available tools:\n")
    for m in SCANNERS:
        scope = "estate" if m.ESTATE_LEVEL else "project"
        print(f"  {m.NAME:<20} [{scope:^7}]  {m.DESCRIPTION}")
    print("\n  build                [ all   ]  run every tool -> data/ + report.html")
    print("  census               [machine]  this machine reports its own domain "
          "(producer roots, or the knight's code + vault roots)")
    return 0


def _cmd_build(args: argparse.Namespace) -> int:
    projects = resolve_targets(None, True, args.include_third_party)
    mode = "fresh" if args.fresh else "resume"
    if args.only:
        wanted = {n.strip() for n in args.only.split(",") if n.strip()}
        subset = [p for p in projects if p.name in wanted]
        names = ", ".join(p.name for p in subset)
        print(f"Warming cache for {len(subset)} project(s) [{mode}]: {names}")
        scan_subset(subset, resume=not args.fresh)
        print("  (subset cached; run 'build' with no --only to assemble)")
        return 0
    print(f"Building estate report over {len(projects)} project(s) [{mode}]...")
    try:
        data_path, report_path = build_all(projects, resume=not args.fresh)
    except RuntimeError as exc:
        # The report self-check failed: what was written is not a parseable
        # governance artifact. Fail loud rather than leave a broken report that
        # reads as complete (COWORK_BRIEF_scanner_bugfixes.md Task B.2).
        print(f"build: {exc}", file=sys.stderr)
        return 1
    print(f"  data feed : {data_path}")
    print(f"  viewer    : {report_path}")
    return 0


def _cmd_tool(name: str, args: argparse.Namespace) -> int:
    mod = BY_NAME[name]
    targets = resolve_targets(args.target, args.all, args.include_third_party)
    if mod.ESTATE_LEVEL:
        out = mod.scan_estate(targets)
        path = write_json(f"{mod.NAME}.json", out)
        print(f"{mod.NAME}: wrote {path}")
    else:
        for t in targets:
            out = mod.scan(t)
            path = write_json(f"{mod.NAME}/{t.name}.json", out)
            print(f"{mod.NAME}: {t.name} -> {path}")
    return 0


def main(argv: list[str]) -> int:
    # 'ingest' forwards remaining args to the vendored pipeline; handle it before
    # argparse so pipeline flags (--render-only, --skip-*) don't clash with ours.
    if argv and argv[0] == "ingest":
        return _cmd_ingest(argv[1:])
    if argv and argv[0] == "intake":
        return _cmd_intake(argv[1:])
    if argv and argv[0] == "scrape":
        return _cmd_scrape(argv[1:])
    p = argparse.ArgumentParser(prog="run.py", add_help=True,
                                description="L5GN-Tools estate scanners (read-only).")
    p.add_argument("command",
                   help="a tool name, or 'list' / 'build' / 'census' / 'config' / "
                        "'deposit' / 'consume' / 'ingest' / 'app' / 'window' / "
                        "'serve' / 'review' / 'backup' / 'scrape' / 'conductor' "
                        "('serve' and 'review' are deprecated aliases for 'app', "
                        "kept for one round)")
    p.add_argument("--target", help="sibling folder name or path")
    p.add_argument("--all", action="store_true", help="run across every project")
    p.add_argument("--include-third-party", action="store_true",
                   help="include cloned/vendored sibling repos")
    p.add_argument("--fresh", action="store_true",
                   help="ignore cached data and re-scan everything")
    p.add_argument("--only", help="build: comma-separated project names to warm-cache")
    p.add_argument("--push", action="store_true",
                   help="deposit: actually push to the knight (else stage + print the command)")
    p.add_argument("--force", action="store_true",
                   help="deposit: allow depositing an 'unknown' estate namespace")
    p.add_argument("--keep", type=int, default=7,
                   help="backup: snapshot generations to retain (keep-last-N)")
    p.add_argument("--no-push", action="store_true",
                   help="backup: take + prune the snapshot but stage the off-box "
                        "push instead of running it")
    p.add_argument("--port", type=int, default=8001,
                   help="app/review: port (default 8002 unless given here); "
                        "serve: Datasette port (default 8001)")
    p.add_argument("--host", default="0.0.0.0",
                   help="app/serve/review: bind address (default 0.0.0.0 for "
                        "Tailscale + LAN)")
    p.add_argument("--plan-id", dest="plan_id",
                   help="conductor: the approved plan id to run (see "
                        "data/knowledge_curator/plans/)")
    args = p.parse_args(argv)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if args.command == "config":
        return _cmd_config()
    if args.command == "deposit":
        return _cmd_deposit(args)
    if args.command == "consume":
        return _cmd_consume()
    if args.command == "census":
        return _cmd_census(args)
    if args.command == "backup":
        return _cmd_backup(args)
    if args.command == "conductor":
        return _cmd_conductor(args)
    if args.command == "app":
        return _cmd_app(args, argv)
    if args.command == "window":
        return _cmd_window()
    if args.command == "serve":
        return _cmd_serve(args)
    if args.command == "review":
        return _cmd_review(args, argv)
    if args.command == "list":
        return _cmd_list()
    if args.command == "build":
        return _cmd_build(args)
    if args.command in BY_NAME:
        return _cmd_tool(args.command, args)
    print(f"unknown command/tool: {args.command!r}. Try 'python run.py list'.",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
