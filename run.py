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
    python run.py serve  [--port N] [--host H]   # Datasette read surface (snapshot, --immutable)
    python run.py review [--port N] [--host H]   # narrow write endpoint (0007 stage 2)
    python run.py backup [--keep N] [--no-push]  # off-box VACUUM INTO snapshot
    python run.py scrape [urls.txt] [--force]    # Gemini share-scrape -> intake
    python run.py ingest [--skip-backup] [--skip-intake]   # backup -> intake -> pipeline
"""
from __future__ import annotations

import argparse
import sys

from l5gntools.common import DATA_DIR, resolve_targets, write_json
from l5gntools.registry import BY_NAME, SCANNERS
from l5gntools.report import build_all, scan_subset


def _cmd_deposit(args: argparse.Namespace) -> int:
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
        print("ingest: [2/3] intake drop zone")
        rc = _run_chronicler("intake.py", [], env)
        if rc != 0:
            return rc
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
    with the install hint (never silent-fails)."""
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


REVIEW_DEFAULT_PORT = 8002  # distinct from serve's 8001 so both can run at once


def _cmd_review(args: argparse.Namespace, argv: list[str]) -> int:
    """Launch the narrow project-link write endpoint (DECISIONS 0007 stage 2).

    Writes ONLY threads.project_link + project_confidence='manual' -- the pipeline
    owns every other column, so the two writers touch disjoint column sets and
    cannot collide (single-writer by column-scope, not by lock). Config-driven
    paths, bound 0.0.0.0 by default for tailnet + LAN on a `personal` estate.
    DECISIONS 0025: the deck renders only the running machine's declared
    estate, and a `work`-estate machine must bind loopback only -- enforced
    structurally below, not by the default. FastAPI/uvicorn are an OPTIONAL
    extra; if absent this skips cleanly and loudly with the install hint.

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

    if db is None and not estate.available:
        # Both data halves absent. This used to be the refusal case, and was,
        # while every route needed one of them. The docs board needs neither:
        # it derives from `docs/` in this checkout, which is present by
        # construction wherever this file is. So the preflight split runs to
        # its conclusion -- the surface serves the one route whose dependency
        # is satisfied and says plainly what it hasn't got.
        print("review: this machine has neither a vault nor an estate build.",
              file=sys.stderr)
        print(f"review:   vault  -- {vault_gap.detail}", file=sys.stderr)
        print(f"review:   estate -- {estate.reason} at {estate.source}",
              file=sys.stderr)
        print("review: serving the docs board only. Run `python run.py build` "
              "for the estate views, or point CHRONICLER_HOME at a vault for "
              "the review queue.", file=sys.stderr)

    if not app.available():
        print("review: FastAPI/uvicorn are not installed. They are an OPTIONAL "
              "extra, kept out of the stdlib-only core:\n"
              "         pip install -e .[review]", file=sys.stderr)
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
        print(f"review: {estate_clause_gap}", file=sys.stderr)
        print("review: and this machine has no estate build either, so there "
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
            f"review: refusing to bind {args.host!r} -- this machine's declared "
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
        print(f"review: vault DB={db}")
        print(f"review: registry={core.resolve_registry_path(m)} "
              f"({len(registry)} link-target ids)")
        print("review: queue routes ENABLED -- writes ONLY project_link + "
              "project_confidence='manual'")
    else:
        print(f"review: queue routes DEGRADED -- {vault_gap.detail}")
    if estate.available:
        head = estate.header()
        dirty = " (toolkit dirty)" if head.get("toolkit_dirty") else ""
        print(f"review: estate build={head.get('generated_at')} "
              f"commit={head.get('toolkit_commit')}{dirty}")
        print(f"review: estate routes ENABLED -- {head.get('project_count')} projects, "
              f"{head.get('authored_document_count')} authored documents, "
              f"search engine={index.status()['engine']}")
        if index is not None and index.notice:
            print(f"review: {index.notice}")
        for warning in head.get("warnings", []):
            print(f"review: estate warning -- {warning}")
    else:
        print(f"review: estate routes DEGRADED -- {estate.reason} at {estate.source}")
    if estate_clause_gap:
        print(f"review: estate={declared_estate!r} -- NO thread is rendered on "
              "this machine (DECISIONS 0025: a surface that cannot name one "
              "estate shows none). Document routes are unaffected -- docs/ and "
              "the estate build are not estate-labelled data.")
    else:
        print(f"review: estate={declared_estate!r} -- rendering only that estate's "
              "threads (DECISIONS 0025)")
    print(f"review: binding {args.host}:{port}")
    print(f"review: phone on the tailnet: http://<knight-100.x>:{port}/  |  "
          f"on the LAN: http://<knight-192.168.x>:{port}/")
    try:
        return app.run(db, registry, host=args.host, port=port,
                       account_clause=account_clause, estate=estate,
                       index=index, vault_unavailable=vault_gap)
    except KeyboardInterrupt:
        return 0


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
                        "'deposit' / 'consume' / 'ingest' / 'serve' / 'review' / "
                        "'backup' / 'scrape'")
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
                   help="serve: Datasette port (default 8001)")
    p.add_argument("--host", default="0.0.0.0",
                   help="serve: bind address (default 0.0.0.0 for Tailscale + LAN)")
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
