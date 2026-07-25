"""tester_blast_uncommitted -- the UNCOMMITTED-CRITICAL alarm
(COWORK_BRIEF_blast_radius.md Task B).

write-capability ∩ untracked. A tracked, committed guarded-write is not critical;
an untracked raw-write is. Assert only the second raises the alarm and it sorts
first.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from l5gntools.scanners import blast_radius as br


def _git(proj: Path, *args: str) -> None:
    env = {**os.environ,
           "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "-C", str(proj), *args], check=True, env=env,
                   capture_output=True)


def run() -> list[str]:
    v: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        proj = Path(td) / "MixedWrites"
        proj.mkdir()
        # committed, gated -> guarded-write, NOT critical
        (proj / "gated.py").write_text(
            "# typed_phrase gate  four-eyes\nrun('sf data import --target-org prod')\n",
            encoding="utf-8")
        _git(proj, "init", "-q")
        _git(proj, "add", "gated.py")
        _git(proj, "commit", "-qm", "init")
        # untracked, ungated prod write -> raw-write-prod, CRITICAL
        (proj / "rogue.py").write_text(
            "run('sf data import --target-org prod')\n", encoding="utf-8")

        out = br.scan(proj)
        crit = out["uncommitted_critical"]
        if len(crit) != 1:
            v.append(f"expected exactly 1 uncommitted-critical, got "
                     f"{[c['path'] for c in crit]}")
        elif crit[0]["path"] != "rogue.py":
            v.append(f"the untracked raw-write should be the alarm -> {crit[0]}")
        elif crit[0]["tier"] != "raw-write-prod" or crit[0]["git_state"] != "untracked":
            v.append(f"alarm mislabelled -> {crit[0]}")
        if not out["has_uncommitted_critical"]:
            v.append("has_uncommitted_critical should be true")
        # the committed gated write must not appear as critical
        if any(c["path"] == "gated.py" for c in crit):
            v.append("a committed guarded-write must not be UNCOMMITTED-CRITICAL")
    return v
