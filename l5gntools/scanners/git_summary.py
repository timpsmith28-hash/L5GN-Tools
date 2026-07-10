"""git_summary -- top-level commit summary for a project (the shallow scanner)."""
from __future__ import annotations

from ..contract import SAFE

from pathlib import Path

from ..common import is_git_repo, run_git

NAME = "git_summary"
DESCRIPTION = "Latest commit, branch, history depth and working-tree state."
ESTATE_LEVEL = False
SAFETY = SAFE


def scan(target: Path) -> dict:
    if not is_git_repo(target):
        return {"project": target.name, "is_git": False}

    latest = run_git(target, "log", "-1", "--format=%h%x1f%cI%x1f%an%x1f%s")
    h = date = author = subject = ""
    if latest and "\x1f" in latest:
        parts = latest.split("\x1f")
        h, date, author, subject = (parts + ["", "", "", ""])[:4]

    porcelain = run_git(target, "status", "--porcelain")
    dirty = len([ln for ln in porcelain.splitlines() if ln.strip()])
    count = run_git(target, "rev-list", "--count", "HEAD") or "0"
    first = run_git(target, "log", "--reverse", "--format=%cI", "--max-parents=0")
    first = first.splitlines()[0] if first else ""

    return {
        "project": target.name,
        "is_git": True,
        "branch": run_git(target, "branch", "--show-current"),
        "latest_hash": h,
        "latest_date": date,
        "latest_author": author,
        "latest_subject": subject,
        "commit_count": int(count) if count.isdigit() else 0,
        "dirty_files": dirty,
        "first_commit_date": first,
        "remote": run_git(target, "remote", "get-url", "origin"),
    }
