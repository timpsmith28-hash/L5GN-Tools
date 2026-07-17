"""author-identity folding: two git aliases collapse to one canonical in the
git_deep_history census, while per-commit authors stay raw."""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from l5gntools import config
from l5gntools.scanners import git_deep_history


def _commit(repo: Path, author: str, msg: str) -> None:
    env = {**os.environ,
           "GIT_AUTHOR_NAME": author, "GIT_AUTHOR_EMAIL": "x@x",
           "GIT_COMMITTER_NAME": author, "GIT_COMMITTER_EMAIL": "x@x"}
    (repo / f"{msg}.txt").write_text(msg, encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, env=env)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", msg], check=True, env=env)


def run() -> list[str]:
    v: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td) / "Repo"
        repo.mkdir()
        subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
        _commit(repo, "alias-a", "c1")
        _commit(repo, "Canon", "c2")
        _commit(repo, "alias-a", "c3")

        # Inject a known alias map without depending on the committed authors.json.
        orig = config.author_aliases
        config.author_aliases = lambda: {"alias-a": "Canon", "canon": "Canon"}
        try:
            out = git_deep_history.scan(repo)
        finally:
            config.author_aliases = orig

        cba = out["commits_by_author"]
        if cba.get("Canon") != 3:
            v.append(f"authors: expected Canon folded to 3, got {cba}")
        if "alias-a" in cba:
            v.append(f"authors: raw alias should not survive in census: {cba}")
        if out.get("author_aliasing") != {"alias-a": "Canon"}:
            v.append(f"authors: aliasing map wrong: {out.get('author_aliasing')}")
        # Per-commit authors remain raw (source-faithful).
        raw_authors = {c["author"] for c in out["commits"]}
        if "alias-a" not in raw_authors:
            v.append("authors: per-commit author should stay raw")

        # The committed authors.json at least loads to a dict.
        if not isinstance(config.author_aliases(), dict):
            v.append("authors: config.author_aliases() should return a dict")
    return v
