"""env_scanner -- config / environment surface and secret-exposure flags.

Privacy note: this reports FILE NAMES and line numbers of suspicious matches
only. It never copies secret values into the output data.
"""
from __future__ import annotations

import re
from pathlib import Path

from ..common import iter_files, rel

NAME = "env_scanner"
DESCRIPTION = "Config/env file inventory and secret-exposure flags (names only)."
ESTATE_LEVEL = False

_CONFIG_SUFFIXES = (".env", ".ini", ".cfg", ".yml", ".yaml", ".toml", ".json")
_CONFIG_NAMES = ("dockerfile", "docker-compose", "requirements", ".env",
                 "makefile", "pyproject", "setup")
_SECRET_FILE_HINTS = (".pem", ".key", ".crt", ".p12", ".pfx")
_SECRET_LINE = re.compile(
    r"(?i)(password|passwd|secret|api[_-]?key|access[_-]?token|"
    r"private[_-]?key|aws_secret|bearer)\s*[:=]")


def _is_config(path: Path) -> bool:
    n = path.name.lower()
    if path.suffix.lower() in _CONFIG_SUFFIXES:
        return True
    return any(hint in n for hint in _CONFIG_NAMES)


def scan(target: Path) -> dict:
    config_files: list[str] = []
    secret_files: list[str] = []
    suspicious: list[dict] = []

    for path in iter_files(target):
        n = path.name.lower()
        if path.suffix.lower() in _SECRET_FILE_HINTS:
            secret_files.append(rel(path, target))
        if not _is_config(path):
            continue
        config_files.append(rel(path, target))
        # Only scan reasonably small text config files for exposed secrets.
        try:
            if path.stat().st_size > 512_000:
                continue
            hits = 0
            for i, line in enumerate(
                    path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                if _SECRET_LINE.search(line):
                    hits += 1
            if hits:
                suspicious.append({"path": rel(path, target), "suspect_lines": hits})
        except OSError:
            continue

    config_files.sort()
    secret_files.sort()
    return {
        "project": target.name,
        "config_files": config_files,
        "credential_files": secret_files,
        "secret_suspects": suspicious,
    }
