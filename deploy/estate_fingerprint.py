#!/usr/bin/env python3
"""estate_fingerprint.py -- Task 0 of COWORK_BRIEF_estate_restructure.md.

Read-only. Captures the rename-proof identity of every repo under one or more
roots BEFORE anything moves -- the fingerprint that a later restructure would
destroy. It runs no move, creates nothing under a scanned repo, and writes its
output only to a path you name (default: stdout + a sibling markdown file in CWD).

Why it exists as a standalone script and not a scanner: it must be runnable
against `C:\\Users\\timps\\Documents\\GitHub\\` (and the work rig's `MCF\\` / `L5GN\\`)
in a session mounted on `Documents`, before the estate is restructured. It is
stdlib-only and read-only, same contract as the scanners, and every git call
carries --no-optional-locks so it never rewrites a scanned repo's index.

Usage:
    python deploy/estate_fingerprint.py <root> [<root> ...] [--json out.json]

The headline field is `root_commit_sha` -- the first-commit SHA, which survives
every rename, fork and folder move that has confused this estate. Identical
`root_commit_sha` under two names means one repo. That is the answer to the
smelt-gateway / L5GN-Castle question (COWORK_REPORT_projects_reconciliation.md
Finding 2).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

NO_LOCKS = "--no-optional-locks"


def _git(path: Path, *args: str) -> str:
    try:
        r = subprocess.run(["git", "-C", str(path), *args],
                           capture_output=True, text=True, timeout=60)
        return r.stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return ""


def _dir_stats(path: Path) -> tuple[int, int]:
    files = size = 0
    for p in path.rglob("*"):
        if ".git" in p.parts:
            continue
        try:
            if p.is_file():
                files += 1
                size += p.stat().st_size
        except OSError:
            continue
    return files, size


def fingerprint(d: Path) -> dict:
    is_git = (d / ".git").exists()
    entry: dict = {"name": d.name, "path": str(d), "is_git": is_git}
    files, size = _dir_stats(d)
    entry["file_count"] = files
    entry["size_mb"] = round(size / 1_048_576, 1)
    if not is_git:
        return entry
    root_sha = ""
    log = _git(d, NO_LOCKS, "log", "--format=%H", "--reverse")
    if log:
        root_sha = log.splitlines()[0]
    entry.update({
        "root_commit_sha": root_sha,
        "head_sha": _git(d, NO_LOCKS, "rev-parse", "HEAD"),
        "branch": _git(d, NO_LOCKS, "rev-parse", "--abbrev-ref", "HEAD"),
        "commit_count": _git(d, NO_LOCKS, "rev-list", "--count", "HEAD"),
        "first_commit_date": (_git(d, NO_LOCKS, "log", "--format=%aI", "--reverse")
                              or "\n").splitlines()[0] if log else "",
        "latest_date": _git(d, NO_LOCKS, "log", "-1", "--format=%aI"),
        "remotes": _git(d, NO_LOCKS, "remote", "-v"),
    })
    return entry


def _table(rows: list[dict]) -> str:
    hdr = ("| name | is_git | root_commit_sha | commit_count | first | latest "
           "| files | size_mb |\n|---|---|---|---|---|---|---|---|\n")
    out = [hdr]
    for r in rows:
        out.append("| {name} | {g} | {root} | {cc} | {f} | {l} | {fc} | {mb} |\n".format(
            name=r["name"], g="yes" if r.get("is_git") else "no",
            root=(r.get("root_commit_sha") or "")[:12],
            cc=r.get("commit_count", ""), f=(r.get("first_commit_date") or "")[:10],
            l=(r.get("latest_date") or "")[:10], fc=r.get("file_count", ""),
            mb=r.get("size_mb", "")))
    return "".join(out)


def main(argv: list[str]) -> int:
    roots = [a for a in argv if not a.startswith("--")]
    json_out = None
    if "--json" in argv:
        i = argv.index("--json")
        json_out = argv[i + 1] if i + 1 < len(argv) else "estate_fingerprint.json"
    if not roots:
        print(__doc__)
        return 2
    rows: list[dict] = []
    seen: set[str] = set()
    for root in roots:
        rp = Path(root)
        if not rp.exists():
            print(f"# WARNING: root does not exist: {rp}", file=sys.stderr)
            continue
        for child in sorted(rp.iterdir(), key=lambda p: p.name.lower()):
            if child.is_dir() and not child.name.startswith(".") \
                    and str(child.resolve()) not in seen:
                seen.add(str(child.resolve()))
                rows.append(fingerprint(child))
    print(_table(rows))
    # Duplicate-root detection: identical root_commit_sha under two names.
    by_root: dict[str, list[str]] = {}
    for r in rows:
        if r.get("root_commit_sha"):
            by_root.setdefault(r["root_commit_sha"], []).append(r["name"])
    dupes = {k: v for k, v in by_root.items() if len(v) > 1}
    if dupes:
        print("\n## Same root_commit_sha under multiple names (one repo, two names)\n")
        for sha, names in dupes.items():
            print(f"- `{sha[:12]}` -> {', '.join(names)}")
    if json_out:
        Path(json_out).write_text(json.dumps(rows, indent=2), encoding="utf-8")
        print(f"\n# raw JSON -> {json_out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
