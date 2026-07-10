"""estate_status -- one git dashboard row per project across the whole estate."""
from __future__ import annotations

from pathlib import Path

from . import git_summary

NAME = "estate_status"
DESCRIPTION = "Git dashboard: latest commit / branch / depth / dirty for every project."
ESTATE_LEVEL = True


def scan_estate(projects: list[Path]) -> dict:
    rows = [git_summary.scan(p) for p in projects]
    git_rows = [r for r in rows if r.get("is_git")]
    return {
        "project_count": len(rows),
        "git_repos": len(git_rows),
        "total_dirty": sum(r.get("dirty_files", 0) for r in git_rows),
        "rows": rows,
    }
