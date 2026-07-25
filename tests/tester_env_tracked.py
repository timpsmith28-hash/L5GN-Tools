"""tester_env_tracked -- env_scanner joins secret-suspects against git and
suppresses example files (governance Task C / B2).

Fixture: a tracked `.env`, an untracked `.env`, a gitignored `.env` and an
`.env.example`, each carrying a password line. Assert the example is suppressed,
the other three carry the right label, and TRACKED sorts first.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from l5gntools.scanners import env_scanner


def _git(proj: Path, *args: str) -> None:
    env = {**os.environ,
           "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "-C", str(proj), *args], check=True, env=env,
                   capture_output=True)


def run() -> list[str]:
    v: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        proj = Path(td) / "Secrets"
        for sub in ("committed", "loose", "ignored"):
            (proj / sub).mkdir(parents=True)
            (proj / sub / ".env").write_text("password=hunter2\n", encoding="utf-8")
        (proj / "example").mkdir()
        (proj / "example" / ".env.example").write_text(
            "password=CHANGEME\n", encoding="utf-8")
        (proj / ".gitignore").write_text("ignored/\n", encoding="utf-8")

        _git(proj, "init", "-q")
        _git(proj, "add", "committed/.env", "example/.env.example", ".gitignore")
        _git(proj, "commit", "-qm", "init")   # 'loose' + 'ignored' left uncommitted

        out = env_scanner.scan(proj)
        suspects = {s["path"]: s["git"] for s in out["secret_suspects"]}

        if any("example" in p for p in suspects):
            v.append(f"env_scanner: .env.example must be suppressed -> {suspects}")
        if suspects.get("committed/.env") != "TRACKED":
            v.append(f"env_scanner: committed/.env should be TRACKED -> {suspects}")
        if suspects.get("loose/.env") != "untracked":
            v.append(f"env_scanner: loose/.env should be untracked -> {suspects}")
        if suspects.get("ignored/.env") != "ignored":
            v.append(f"env_scanner: ignored/.env should be ignored -> {suspects}")
        if out["secret_suspects"] and out["secret_suspects"][0]["git"] != "TRACKED":
            v.append("env_scanner: TRACKED suspect must sort first -> "
                     f"{[s['git'] for s in out['secret_suspects']]}")
        if out.get("tracked_suspect_count") != 1:
            v.append(f"env_scanner: tracked_suspect_count should be 1 -> "
                     f"{out.get('tracked_suspect_count')}")
    return v
