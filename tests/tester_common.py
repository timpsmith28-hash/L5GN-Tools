"""Sanity-check the shared helpers on a temp git repo."""
from __future__ import annotations

import tempfile
from pathlib import Path

from l5gntools import common
from ._fixture import make_project


def run() -> list[str]:
    v: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        proj = make_project(Path(td), git=True)

        if not common.is_git_repo(proj):
            v.append("is_git_repo: expected True on a git fixture")
        if not common.run_git(proj, "rev-parse", "HEAD"):
            v.append("run_git: expected a HEAD sha")

        pys = [p for p in common.iter_files(proj, suffixes=(".py",))]
        if not any(p.name == "engine.py" for p in pys):
            v.append("iter_files: engine.py not found")

    # write_json must refuse to escape the data dir.
    try:
        common.write_json("../escape.json", {})
        v.append("write_json: allowed a path outside the data dir")
    except ValueError:
        pass
    return v
