"""Single source of truth for which scanners exist.

Auditors read this list; adding a scanner means importing it here (and nowhere
else needs to change). Order is the order tools run in a full sweep.
"""
from __future__ import annotations

from .contract import build_manifest
from .scanners import (
    bloat_audit,
    doc_census,
    drift,
    duplicate_finder,
    env_scanner,
    estate_diff,
    estate_status,
    file_census,
    git_deep_history,
    git_summary,
    import_scanner,
    project_trail,
    todo_adr_scanner,
    vault_reader,
    workspace_scanner,
)

SCANNERS = [
    workspace_scanner,
    file_census,
    git_summary,
    git_deep_history,
    doc_census,
    import_scanner,
    env_scanner,
    bloat_audit,
    todo_adr_scanner,
    estate_status,
    duplicate_finder,
    estate_diff,
    vault_reader,
    project_trail,
    drift,
]

BY_NAME = {m.NAME: m for m in SCANNERS}


def manifest_all() -> list[dict]:
    """Every scanner's CID-ready manifest -- the list a consumer (CID's BaseTool
    adapter) enumerates to discover the toolset. Grows automatically as scanners
    are added to SCANNERS."""
    return [build_manifest(m) for m in SCANNERS]
