"""A root tagged ``is_project`` is the project, not a folder of projects.

The self-scan brief needed L5GN-Tools scanned as a normal project. Neither
existing config shape could express that: naming the parent ``GitHub`` root
drags in unrelated siblings (and `discover_projects` skips TOOLKIT_ROOT on a
container walk anyway), and naming the toolkit as a plain root turns its own
subfolders -- ``docs``, ``config``, ``l5gntools`` -- into projects. This locks
the third shape, including the deliberate TOOLKIT_ROOT bypass: explicit
declaration in a producer's config is the only route in.

Hermetic: temp machines.json, temp folder tree, TOOLKIT_ROOT patched to a path
inside that tree so the self-skip is exercised for real.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from l5gntools import common, config


def run() -> list[str]:
    v: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "GitHub"
        (root / "L5GN" / "Alpha").mkdir(parents=True)
        (root / "L5GN" / "Beta").mkdir(parents=True)
        (root / "Unrelated-Sibling").mkdir(parents=True)
        toolkit = root / "L5GN-Tools"
        (toolkit / "docs").mkdir(parents=True)
        (toolkit / "l5gntools").mkdir(parents=True)

        mfile = Path(td) / "machines.json"
        orig_machines, orig_local = config._MACHINES, config._LOCAL
        orig_toolkit = common.TOOLKIT_ROOT
        config._MACHINES = mfile
        config._LOCAL = Path(td) / "absent.json"
        common.TOOLKIT_ROOT = toolkit

        def declare(roots: list) -> list[str]:
            mfile.write_text(json.dumps({config.hostname(): {"roots": roots}}),
                             encoding="utf-8")
            return sorted(p.name for p in common.discover_projects())

        try:
            # A container root yields its children and never the toolkit itself.
            got = declare([{"path": str(root), "scope": "l5gn"}])
            if "L5GN-Tools" in got:
                v.append("discover_projects: a container root must skip TOOLKIT_ROOT")
            if got != ["L5GN", "Unrelated-Sibling"]:
                v.append(f"discover_projects: container root gave {got}")

            # The is_project root contributes itself -- not docs/, not l5gntools/.
            got = declare([
                {"path": str(root / "L5GN"), "scope": "l5gn"},
                {"path": str(toolkit), "scope": "l5gn", "is_project": True},
            ])
            if got != ["Alpha", "Beta", "L5GN-Tools"]:
                v.append(f"discover_projects: is_project root gave {got}")

            # ...and it carries its declared scope, resolved off the root itself.
            if config.scope_for_path(toolkit) != "l5gn":
                v.append("scope_for_path: an is_project root should scope its own path")

            # A bare --target name resolves to an is_project root by folder name.
            hit = common.resolve_targets("L5GN-Tools", do_all=False)
            if [p.resolve() for p in hit] != [toolkit.resolve()]:
                v.append(f"resolve_targets: bare name did not hit the is_project root: {hit}")

            # A declared-but-missing root is dropped, not reported as a project.
            got = declare([{"path": str(root / "gone"), "scope": "l5gn",
                            "is_project": True}])
            if got:
                v.append(f"discover_projects: missing is_project root should vanish, got {got}")
        finally:
            config._MACHINES, config._LOCAL = orig_machines, orig_local
            common.TOOLKIT_ROOT = orig_toolkit
    return v
