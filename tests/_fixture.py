"""Build a throwaway fake project (optionally a git repo) in a temp dir."""
from __future__ import annotations

import subprocess
from pathlib import Path


def make_project(root: Path, git: bool = True) -> Path:
    proj = root / "FakeProj"
    (proj / "core").mkdir(parents=True)
    (proj / "core" / "engine.py").write_text(
        "import os\nfrom collections import Counter\n\n"
        "class Engine:\n    def run(self):\n        # TODO: wire this up\n        return 1\n",
        encoding="utf-8")
    (proj / "__init__.py").write_text("", encoding="utf-8")
    (proj / "README.md").write_text("# Fake\n\nA fixture project.\n", encoding="utf-8")
    (proj / "requirements.txt").write_text("requests\n", encoding="utf-8")
    (proj / "config.yaml").write_text("password: hunter2\n", encoding="utf-8")
    if git:
        env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        import os
        e = {**os.environ, **env}
        subprocess.run(["git", "-C", str(proj), "init", "-q"], check=True, env=e)
        subprocess.run(["git", "-C", str(proj), "add", "-A"], check=True, env=e)
        subprocess.run(["git", "-C", str(proj), "commit", "-qm", "init"], check=True, env=e)
    return proj
