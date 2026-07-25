"""tester_scanner_scope -- the scope filter keeps content scanners out of
gitignored, vendored and data/chat paths (COWORK_BRIEF_scanner_bugfixes.md Task A).

The motivating bug: todo_adr_scanner mined hundreds of "TODO"-shaped strings out
of a gitignored chat-archive JSON. The fixture reproduces exactly that shape --
one real TODO in source, a pile of them inside a gitignored ``raw_claude_files/``
and a (tracked but data-named) ``chat_threads/`` -- and asserts the scanner
returns exactly the one real marker and records the rest as skipped.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from l5gntools.scanners import todo_adr_scanner
from l5gntools.scanners._scope import Scope, is_data_dir_name


def _git(proj: Path, *args: str) -> None:
    env = {**os.environ,
           "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "-C", str(proj), *args], check=True, env=env,
                   capture_output=True)


def _make(root: Path) -> Path:
    proj = root / "ScopeFix"
    (proj / "src").mkdir(parents=True)
    (proj / "src" / "a.py").write_text(
        "def f():\n    # TODO: the one real marker\n    return 1\n", encoding="utf-8")
    # gitignored chat archive, stuffed with TODO-shaped noise
    (proj / ".gitignore").write_text("raw_claude_files/\n", encoding="utf-8")
    (proj / "raw_claude_files").mkdir()
    (proj / "raw_claude_files" / "conversations.json").write_text(
        "\n".join(f'{{"msg": "TODO number {i}"}}' for i in range(200)),
        encoding="utf-8")
    # data-named directory that is NOT gitignored -- must still be skipped
    (proj / "chat_threads").mkdir()
    (proj / "chat_threads" / "notes.md").write_text(
        "# chat\nTODO: this is transcript content, out of scope\n", encoding="utf-8")
    _git(proj, "init", "-q")
    _git(proj, "add", "-A")
    _git(proj, "commit", "-qm", "init")
    return proj


def run() -> list[str]:
    v: list[str] = []

    if not is_data_dir_name("raw_gemini_files"):
        v.append("is_data_dir_name: raw_gemini_files should match the raw_* family")
    if not is_data_dir_name("chat_threads"):
        v.append("is_data_dir_name: chat_threads should be a data dir")
    if is_data_dir_name("src"):
        v.append("is_data_dir_name: 'src' must not be treated as a data dir")

    with tempfile.TemporaryDirectory() as td:
        proj = _make(Path(td))
        out = todo_adr_scanner.scan(proj)

        if out["marker_count"] != 1:
            v.append(f"todo_adr: expected exactly 1 marker (src/a.py), got "
                     f"{out['marker_count']}: {[m['path'] for m in out['markers']]}")
        paths = {m["path"] for m in out["markers"]}
        if any("raw_claude_files" in p or "chat_threads" in p for p in paths):
            v.append(f"todo_adr: read a walled data path: {sorted(paths)}")

        scope = out.get("scope", {})
        if not scope.get("skipped_paths"):
            v.append("todo_adr: scope report shows nothing skipped -- the data "
                     "dirs should have been recorded as skipped")
        reasons = scope.get("skipped_by_reason", {})
        if "data_dir" not in reasons:
            v.append(f"todo_adr: expected a data_dir skip; got reasons {reasons}")

        # Scope on a non-git project: no gitignore authority, but data dirs still go.
        plain = Scope(proj)
        if plain.skip(proj / "src" / "a.py"):
            v.append("Scope: source file src/a.py should be in scope")
        if not plain.skip(proj / "raw_claude_files" / "conversations.json"):
            v.append("Scope: raw_claude_files JSON should be skipped")
    return v
