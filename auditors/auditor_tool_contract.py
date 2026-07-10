"""Every registered scanner must honour the CID-ready tool contract:
a declared SAFETY in the allowed vocabulary, and a well-formed manifest.
This is the boundary CID's gated adapter relies on."""
from __future__ import annotations

from l5gntools.contract import ALLOWED_SAFETY, MANIFEST_KEYS, build_manifest
from l5gntools.registry import SCANNERS


def run() -> list[str]:
    v: list[str] = []
    for mod in SCANNERS:
        label = getattr(mod, "NAME", getattr(mod, "__name__", str(mod)))
        safety = getattr(mod, "SAFETY", None)
        if safety is None:
            v.append(f"{label}: missing SAFETY declaration")
        elif safety not in ALLOWED_SAFETY:
            v.append(f"{label}: SAFETY {safety!r} not in {sorted(ALLOWED_SAFETY)}")
        try:
            man = build_manifest(mod)
        except Exception as exc:  # a manifest that won't build is a broken contract
            v.append(f"{label}: manifest build failed: {exc}")
            continue
        for key in MANIFEST_KEYS:
            if key not in man:
                v.append(f"{label}: manifest missing key {key!r}")
    return v
