"""The tool contract shared with CID.

Every scanner is authored to be consumable by BOTH L5GN-Tools' own runner and
CID's gated BaseTool adapter. To keep the dependency one-directional -- CID
depends on l5gntools, never the reverse -- this module stays CID-agnostic: it
defines its OWN safety vocabulary whose *string values* deliberately equal CID's
core.contracts.SafetyRating values, so CID's adapter maps them by value
(``SafetyRating(scanner.SAFETY)``) with no shared import.

A scanner's full contract is therefore:
    NAME, DESCRIPTION, ESTATE_LEVEL   (discovery + routing)
    SAFETY                            (CID approval gate; every scanner declares it)
    scan(target) | scan_estate(projects)   (the work)
and :func:`build_manifest` renders the JSON-friendly description CID consumes.
"""
from __future__ import annotations

# Safety vocabulary. Values MATCH CID's SafetyRating values on purpose (see the
# module docstring): "safe" runs immediately; "requires_approval" needs explicit
# human confirmation. Every scanner is read-only (auditor_readonly proves it), so
# every current scanner is SAFE.
SAFE = "safe"
REQUIRES_APPROVAL = "requires_approval"
ALLOWED_SAFETY = frozenset({SAFE, REQUIRES_APPROVAL})

#: Keys every manifest carries -- the shape CID's BaseTool adapter reads.
MANIFEST_KEYS = ("tool_id", "description", "category", "scope", "safety", "args")


def scope_of(scanner) -> str:
    return "estate" if getattr(scanner, "ESTATE_LEVEL", False) else "project"


def args_of(scanner) -> dict:
    """The single argument each scope expects, described for discovery."""
    if getattr(scanner, "ESTATE_LEVEL", False):
        return {"projects": "list[Path] -- sibling project folders to scan"}
    return {"target": "Path -- the project folder to scan"}


def build_manifest(scanner) -> dict:
    """The static, JSON-friendly description CID's BaseTool adapter needs."""
    scope = scope_of(scanner)
    return {
        "tool_id": scanner.NAME,
        "description": scanner.DESCRIPTION,
        "category": f"workspace-scanner.{scope}",
        "scope": scope,
        "safety": getattr(scanner, "SAFETY", SAFE),
        "args": args_of(scanner),
    }
