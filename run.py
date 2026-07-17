#!/usr/bin/env python3
"""L5GN-Tools dispatcher / batch runner.

Read-only. Every tool takes the project folder as a target and writes its
output only under L5GN-Tools/data. Nothing is ever written into a scanned folder.

Usage:
    python run.py list                       # list available tools
    python run.py build                      # run everything -> data/ + report.html
    python run.py <tool> [--target NAME]     # one tool on one project
    python run.py <tool> --all               # one tool across the whole estate
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
    data_path, report_path = build_all(projects, resume=not args.fresh)
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
    p = argparse.ArgumentParser(prog="run.py", add_help=True,
                                description="L5GN-Tools estate scanners (read-only).")
    p.add_argument("command",
                   help="a tool name, or 'list' / 'build' / 'config' / 'deposit' / 'consume'")
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
    args = p.parse_args(argv)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if args.command == "config":
        return _cmd_config()
    if args.command == "deposit":
        return _cmd_deposit(args)
    if args.command == "consume":
        return _cmd_consume()
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
