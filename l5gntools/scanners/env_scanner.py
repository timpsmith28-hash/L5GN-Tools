"""env_scanner -- config / environment surface and secret-exposure flags.

Privacy note: this reports FILE NAMES, line counts and git tracked-status only.
It never copies secret values into the output data (Tim's ruling; consistent with
the long-standing "names only" contract).

The hard half (governance Task B2): a secret-suspect file only matters if it is
**committed**. The scanner now joins every suspect against git and labels it
`TRACKED` / `untracked` / `ignored`, sorts `TRACKED` first, and suppresses
`*.env.example` (and `.sample` / `.template`) -- an example file is *supposed* to
hold placeholders, so flagging it just trains the reader to ignore the scanner.
"""
from __future__ import annotations

from ..contract import SAFE

import re
from pathlib import Path

from ..common import iter_files, rel
from ._scope import Scope
from .file_census import status_of

NAME = "env_scanner"
DESCRIPTION = "Config/env inventory + tracked-status of secret suspects (names only)."
ESTATE_LEVEL = False
SAFETY = SAFE

_CONFIG_SUFFIXES = (".env", ".ini", ".cfg", ".yml", ".yaml", ".toml", ".json")
_CONFIG_NAMES = ("dockerfile", "docker-compose", "requirements", ".env",
                 "makefile", "pyproject", "setup")
_SECRET_FILE_HINTS = (".pem", ".key", ".crt", ".p12", ".pfx")
_SECRET_LINE = re.compile(
    r"(?i)(password|passwd|secret|api[_-]?key|access[_-]?token|"
    r"private[_-]?key|aws_secret|bearer)\s*[:=]")

#: An example/sample/template config is meant to hold placeholders -- suppressed
#: from the secret-suspect list so the alarm stays meaningful.
_EXAMPLE_MARKERS = (".example", ".sample", ".template")

#: TRACKED first: the report should answer "is any secret committed?" without
#: reading a list. `None` is a non-git project (no authority to judge).
_STATUS_ORDER = {"tracked": 0, None: 1, "untracked": 2, "ignored": 3}


def _is_config(path: Path) -> bool:
    n = path.name.lower()
    if path.suffix.lower() in _CONFIG_SUFFIXES:
        return True
    return any(hint in n for hint in _CONFIG_NAMES)


def is_example_config(name: str) -> bool:
    """True for `*.env.example`, `secrets.yml.sample`, `config.template`, etc.
    Any of the example markers appearing as a suffix segment counts."""
    low = name.lower()
    return any(m in low for m in _EXAMPLE_MARKERS)


def _label(status: str | None, is_git: bool) -> str:
    """Human tracked-status label for a suspect."""
    if status == "tracked":
        return "TRACKED"
    if not is_git:
        return "untracked (no git)"
    return status or "untracked"


def scan(target: Path) -> dict:
    scope = Scope(target)
    is_git = scope.git is not None
    config_files: list[str] = []
    secret_files: list[str] = []
    suspicious: list[dict] = []

    for path in iter_files(target):
        # Honour data/vendored skips, but NOT gitignored: a gitignored .env must
        # still be seen so it can be labelled `ignored` (Task C). That label is
        # the finding, not something to hide.
        if scope.skip(path, honor=("data_dir", "vendored")):
            continue
        relpath = rel(path, target)
        if path.suffix.lower() in _SECRET_FILE_HINTS:
            secret_files.append(relpath)
        if not _is_config(path):
            continue
        config_files.append(relpath)
        # An example/sample/template file is listed as config but never flagged
        # as a secret suspect -- it is supposed to carry placeholders.
        if is_example_config(path.name):
            continue
        try:
            if path.stat().st_size > 512_000:
                continue
            hits = sum(
                1 for line in
                path.read_text(encoding="utf-8", errors="ignore").splitlines()
                if _SECRET_LINE.search(line))
            if hits:
                status = status_of(relpath, scope.git)
                suspicious.append({
                    "path": relpath, "suspect_lines": hits,
                    "git": _label(status, is_git),
                    # raw status drives the sort; the label is for the reader
                    "_status": status,
                })
        except OSError:
            continue

    config_files.sort()
    secret_files.sort()
    # TRACKED suspects first -- a committed secret is the alarm.
    suspicious.sort(key=lambda s: (_STATUS_ORDER.get(s.pop("_status"), 9), s["path"]))
    tracked_suspects = sum(1 for s in suspicious if s["git"] == "TRACKED")
    return {
        "project": target.name,
        "config_files": config_files,
        "credential_files": secret_files,
        "secret_suspects": suspicious,
        "tracked_suspect_count": tracked_suspects,
        "scope": scope.report(),
    }
