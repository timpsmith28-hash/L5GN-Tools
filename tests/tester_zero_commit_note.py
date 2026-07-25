"""tester_zero_commit_note -- file_census names the 0-commit blind spot
(governance Task E).

An initialised repo with nothing committed protects nothing, yet the old
`at_risk_note` only populated for non-git projects, so a 0-commit repo read as if
it might be safe. Assert the note fires on a git repo with zero commits and is
absent once something is committed.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from l5gntools.scanners import file_census


def _git(proj: Path, *args: str) -> None:
    env = {**os.environ,
           "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "-C", str(proj), *args], check=True, env=env,
                   capture_output=True)


def run() -> list[str]:
    v: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        # git repo, initialised, NOTHING committed
        zero = Path(td) / "ZeroCommit"
        zero.mkdir()
        (zero / "data.csv").write_text("a,b\n1,2\n", encoding="utf-8")
        _git(zero, "init", "-q")
        out = file_census.scan(zero)
        if not out["is_git"]:
            v.append("file_census: an initialised repo should be is_git=true")
        if not out["at_risk_note"] or "no commits" not in out["at_risk_note"]:
            v.append(f"file_census: 0-commit repo should carry the no-commits note "
                     f"-> {out['at_risk_note']!r}")

        # same repo, now with a commit -> note clears
        _git(zero, "add", "-A")
        _git(zero, "commit", "-qm", "init")
        out2 = file_census.scan(zero)
        if out2["at_risk_note"] is not None:
            v.append(f"file_census: a committed repo should have no note -> "
                     f"{out2['at_risk_note']!r}")
    return v
