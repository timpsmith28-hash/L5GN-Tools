"""The CID-ready manifests are complete, unique, and consistent."""
from __future__ import annotations

from l5gntools.contract import ALLOWED_SAFETY
from l5gntools.registry import SCANNERS, manifest_all


def run() -> list[str]:
    v: list[str] = []
    mans = manifest_all()
    if len(mans) != len(SCANNERS):
        v.append(f"manifest_all() returned {len(mans)}, expected {len(SCANNERS)}")
    ids = [m["tool_id"] for m in mans]
    if len(set(ids)) != len(ids):
        v.append("duplicate tool_id across manifests")
    for m in mans:
        if m["safety"] not in ALLOWED_SAFETY:
            v.append(f"{m['tool_id']}: safety {m['safety']!r} not allowed")
        if m["scope"] not in ("estate", "project"):
            v.append(f"{m['tool_id']}: bad scope {m['scope']!r}")
        if not m["args"]:
            v.append(f"{m['tool_id']}: empty args description")
    return v
