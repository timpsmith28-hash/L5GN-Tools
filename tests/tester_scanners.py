"""Run every scanner against the fixture and assert output shape."""
from __future__ import annotations

import tempfile
from pathlib import Path

from l5gntools.registry import SCANNERS
from ._fixture import make_project


def run() -> list[str]:
    v: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        proj = make_project(Path(td), git=True)
        projects = [proj]
        for mod in SCANNERS:
            try:
                out = mod.scan_estate(projects) if mod.ESTATE_LEVEL else mod.scan(proj)
            except Exception as exc:  # noqa: BLE001 -- a crash is the failure
                v.append(f"{mod.NAME}: raised {type(exc).__name__}: {exc}")
                continue
            if not isinstance(out, dict):
                v.append(f"{mod.NAME}: scan did not return a dict")

        ws = next(m for m in SCANNERS if m.NAME == "workspace_scanner").scan(proj)
        if ws["py_files"] < 1 or "Engine" not in ws["top_classes"]:
            v.append("workspace_scanner: did not detect the fixture's Engine class")

        gs = next(m for m in SCANNERS if m.NAME == "git_summary").scan(proj)
        if not gs.get("is_git") or not gs.get("latest_hash"):
            v.append("git_summary: missing git detail on a git fixture")

        env = next(m for m in SCANNERS if m.NAME == "env_scanner").scan(proj)
        if not env["secret_suspects"]:
            v.append("env_scanner: did not flag the fixture's exposed password")
    return v
