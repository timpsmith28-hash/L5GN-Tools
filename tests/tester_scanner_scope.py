"""tester_scanner_scope -- the scope filter keeps content scanners out of
gitignored, vendored and data/chat paths (COWORK_BRIEF_scanner_bugfixes.md Task A),
and every registered scanner is on the hook for it, not just the one that
happened to be the motivating bug.

The registry-iterating check (COWORK_BRIEF_scanner_scope_bypass.md Task 2) is the
load-bearing part of this file. Before it existed, this tester imported exactly
one scanner (`todo_adr_scanner`) and proved the predicate was right and that one
caller honoured it -- green meant "todo_adr_scanner respects scope", not
"scanners respect scope". `file_census` and `workspace_scanner` bypassed the
guard for an unknown length of time and nothing here could have caught it,
because nothing here looked.

Now every scanner in `l5gntools.registry.SCANNERS` is run against a fixture
carrying a planted data directory whose name embeds a random sentinel, and the
assertion is unconditional: the sentinel must never appear anywhere in any
scanner's output. A scanner that never walks a file tree at all (git_summary,
bloat_audit, drift, ...) trivially passes, which is correct -- the assertion
generalises rather than special-casing which scanners are "content scanners".
A scanner that walks trees and forgets to consult `Scope` fails loudly, naming
itself, which is what makes the gate red for a caller that never calls.
"""
from __future__ import annotations

import json
import os
import secrets
import subprocess
import tempfile
from pathlib import Path

from l5gntools.registry import SCANNERS
from l5gntools.scanners._scope import Scope, is_data_dir_name

from ._fixture import make_project

#: Unique per test run so a match can only be the planted fixture -- never a
#: coincidence in this repo's own real `data/` directory, which some
#: estate-level scanners (drift, estate_diff, project_trail) read directly and
#: which genuinely does carry the literal string "raw_claude_files" today (the
#: whole reason this brief exists). A fixed marker could collide with real
#: content; a fresh random one cannot.
_SENTINEL = f"scopeleak{secrets.token_hex(6)}"
#: Matches every `is_data_dir_name` family at once (exact name, `raw_*`,
#: `*_files`) so the directory itself is unambiguously in scope for the guard,
#: while still carrying the sentinel in its own name -- any scanner that emits
#: so much as a directory path, not just a file path, is caught.
_DATA_DIR_NAME = f"raw_{_SENTINEL}_files"


def _git(proj: Path, *args: str) -> None:
    env = {**os.environ,
           "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "-C", str(proj), *args], check=True, env=env,
                   capture_output=True)


def _plant_data_dir(proj: Path, *, tracked: bool) -> None:
    """A data directory a content scanner has no business reading, stuffed with
    one file of every shape the six wired scanners look for: TODO/ADR markers,
    a markdown heading, a config-shaped secret line, an out-of-repo-mutation
    signal, and a distinctive import. If scope is honoured, none of it is ever
    read; if it is not, at least one scanner's output will say so.

    ``tracked`` commits the directory into git so the leak is proven to be the
    data_dir reason specifically, not an accidental gitignore -- the wall
    doctrine is explicit that a data dir is out of scope *even when a project
    forgot to gitignore it*.
    """
    d = proj / _DATA_DIR_NAME
    d.mkdir(parents=True, exist_ok=True)
    (d / "leak.py").write_text(
        f"import {_SENTINEL}_module\n"
        f"password = '{_SENTINEL}'\n\n"
        f"class {_SENTINEL}Engine:\n"
        f"    def run(self):\n"
        f"        # TODO: {_SENTINEL}\n"
        f"        os.system('rm -rf {_SENTINEL}')\n"
        f"        return 1\n",
        encoding="utf-8")
    (d / "leak.md").write_text(
        f"# {_SENTINEL}\nTODO: {_SENTINEL} transcript note\n", encoding="utf-8")
    (d / "leak.yaml").write_text(
        f"password: {_SENTINEL}\n", encoding="utf-8")
    (d / "conversations.json").write_text(
        json.dumps([{"msg": f"{_SENTINEL} message {i}"} for i in range(30)]),
        encoding="utf-8")
    if tracked:
        _git(proj, "add", "-A")
        _git(proj, "commit", "-qm", "plant data dir")


def _contains_sentinel(obj) -> bool:
    """Recursively true if `_SENTINEL` appears anywhere in a scanner's JSON-
    shaped return value -- a path, a filename, an import name, a hash location,
    anything serialisable. Deliberately structural: it does not know or care
    which field a given scanner uses to carry a path."""
    if isinstance(obj, str):
        return _SENTINEL in obj
    if isinstance(obj, dict):
        return any(_contains_sentinel(k) or _contains_sentinel(v)
                   for k, v in obj.items())
    if isinstance(obj, (list, tuple, set)):
        return any(_contains_sentinel(v) for v in obj)
    return False


def _check_registry(td: Path) -> list[str]:
    v: list[str] = []
    proj1 = make_project(td, git=True)
    _plant_data_dir(proj1, tracked=True)
    # A second project sharing the same planted filenames so estate-level
    # scanners that only report *cross*-project matches (duplicate_finder) get
    # a fair chance to leak too -- a single-project fixture can walk a data dir
    # internally and still emit nothing, because nothing crossed the >=2
    # threshold that gates its output.
    proj2 = td / "FakeProj2"
    (proj2 / "core").mkdir(parents=True)
    (proj2 / "core" / "engine.py").write_text("x = 1\n", encoding="utf-8")
    _plant_data_dir(proj2, tracked=False)
    projects = [proj1, proj2]

    for mod in SCANNERS:
        try:
            out = mod.scan_estate(projects) if mod.ESTATE_LEVEL else mod.scan(proj1)
        except Exception as exc:  # noqa: BLE001 -- a crash on a planted data dir
            v.append(f"{mod.NAME}: raised {type(exc).__name__} against a project "
                     f"carrying a data directory: {exc}")
            continue
        if _contains_sentinel(out):
            v.append(f"{mod.NAME}: leaked the planted data directory "
                     f"({_DATA_DIR_NAME!r}) into its output -- scope not honoured")
    return v


def run() -> list[str]:
    v: list[str] = []

    if not is_data_dir_name("raw_gemini_files"):
        v.append("is_data_dir_name: raw_gemini_files should match the raw_* family")
    if not is_data_dir_name("chat_threads"):
        v.append("is_data_dir_name: chat_threads should be a data dir")
    if is_data_dir_name("src"):
        v.append("is_data_dir_name: 'src' must not be treated as a data dir")

    with tempfile.TemporaryDirectory() as td:
        proj = make_project(Path(td), git=True)
        # Scope on a non-git project: no gitignore authority, but data dirs
        # still go -- data_dir wins even with nothing to consult git about.
        plain = Scope(proj)
        if plain.skip(proj / "core" / "engine.py"):
            v.append("Scope: source file core/engine.py should be in scope")
        if not plain.skip(proj / "raw_claude_files" / "conversations.json"):
            v.append("Scope: raw_claude_files JSON should be skipped")
        if not plain.skip_dir("chat_threads"):
            v.append("Scope.skip_dir: chat_threads should be a data dir")
        if plain.skip_dir("src"):
            v.append("Scope.skip_dir: 'src' must not be treated as a data dir")

    with tempfile.TemporaryDirectory() as td:
        v.extend(_check_registry(Path(td)))
    return v
