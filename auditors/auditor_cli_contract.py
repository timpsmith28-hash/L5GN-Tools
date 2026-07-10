"""Every registered scanner must honour the shared contract."""
from __future__ import annotations

from l5gntools.registry import BY_NAME, SCANNERS


def run() -> list[str]:
    v: list[str] = []
    seen: set[str] = set()
    for mod in SCANNERS:
        label = getattr(mod, "__name__", str(mod))
        for attr in ("NAME", "DESCRIPTION", "ESTATE_LEVEL"):
            if not hasattr(mod, attr):
                v.append(f"{label}: missing required attribute {attr}")
        name = getattr(mod, "NAME", None)
        if name in seen:
            v.append(f"{label}: duplicate NAME {name!r}")
        if name:
            seen.add(name)
        if getattr(mod, "ESTATE_LEVEL", False):
            if not callable(getattr(mod, "scan_estate", None)):
                v.append(f"{label}: estate-level scanner missing scan_estate()")
        else:
            if not callable(getattr(mod, "scan", None)):
                v.append(f"{label}: project scanner missing scan()")
    for name, mod in BY_NAME.items():
        if getattr(mod, "NAME", None) != name:
            v.append(f"registry key {name!r} does not match module NAME")
    return v
