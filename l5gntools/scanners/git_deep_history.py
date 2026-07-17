"""git_deep_history -- full development ledger for a project (the deep scanner)."""
from __future__ import annotations

from ..contract import SAFE

from collections import Counter
from pathlib import Path

from .. import config
from ..common import is_git_repo, run_git

NAME = "git_deep_history"
DESCRIPTION = "Full commit ledger plus per-author and per-day activity stats."
ESTATE_LEVEL = False
SAFETY = SAFE

_MAX_COMMITS = 1000


def scan(target: Path) -> dict:
    if not is_git_repo(target):
        return {"project": target.name, "is_git": False}

    aliases = config.author_aliases()

    raw = run_git(target, "log", f"-n{_MAX_COMMITS}",
                  "--format=%h%x1f%cI%x1f%an%x1f%s")
    commits: list[dict] = []
    by_author: Counter[str] = Counter()
    by_day: Counter[str] = Counter()
    aliasing: dict[str, str] = {}
    for line in raw.splitlines():
        if "\x1f" not in line:
            continue
        h, date, author, subject = (line.split("\x1f") + ["", "", "", ""])[:4]
        canonical = aliases.get(author.lower(), author)
        if canonical != author:
            aliasing[author] = canonical
        # per-commit author stays raw (source-faithful); only the census folds
        commits.append({"hash": h, "date": date, "author": author, "subject": subject})
        by_author[canonical] += 1
        by_day[date[:10]] += 1

    return {
        "project": target.name,
        "is_git": True,
        "total_commits": len(commits),
        "truncated": len(commits) >= _MAX_COMMITS,
        "commits_by_author": dict(by_author.most_common()),
        "author_aliasing": aliasing,
        "commits_by_day": dict(sorted(by_day.items())),
        "commits": commits,
    }
