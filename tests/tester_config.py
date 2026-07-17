"""Verify machine-config selection, default fallback, and root resolution.

Hermetic: points the loader at a throwaway machines.json so it never depends on
the real committed config (whose machine keys users are meant to rename)."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from l5gntools import config


def run() -> list[str]:
    v: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        mfile = Path(td) / "machines.json"
        mfile.write_text(json.dumps({
            "default": {"role": "producer", "estate": "unknown"},
            "TEST-HOST": {"role": "producer", "estate": "personal",
                          "roots": ["/tmp/estate_a", "/tmp/estate_b"]},
        }), encoding="utf-8")

        orig_machines, orig_local = config._MACHINES, config._LOCAL
        config._MACHINES = mfile
        config._LOCAL = Path(td) / "local.json"      # intentionally absent
        try:
            # Unknown host -> falls back to the 'default' entry, never crashes.
            unknown = config.machine("no-such-host-xyz-123")
            if unknown.get("_matched") is not False:
                v.append("config: unknown host should report _matched == False")
            if unknown.get("role") != "producer":
                v.append(f"config: unknown host should inherit default role, got {unknown.get('role')!r}")
            if unknown.get("estate") != "unknown":
                v.append(f"config: unknown host should inherit default estate, got {unknown.get('estate')!r}")

            # Default entry declares no roots -> estate_roots is None (legacy).
            if config.estate_roots("no-such-host-xyz-123") is not None:
                v.append("config: default (no roots) should yield estate_roots() == None")

            # A host that declares roots resolves to a list of Paths.
            roots = config.estate_roots("TEST-HOST")
            if not roots or not all(isinstance(r, Path) for r in roots):
                v.append("config: a machine entry with 'roots' should yield a list[Path]")
            elif [str(r) for r in roots] != [str(Path("/tmp/estate_a")), str(Path("/tmp/estate_b"))]:
                v.append(f"config: roots not resolved as declared: {roots}")

            # The live host always resolves to a dict carrying its hostname marker.
            here = config.machine()
            if here.get("_hostname") != config.hostname():
                v.append("config: machine() should tag the resolved entry with _hostname")
        finally:
            config._MACHINES, config._LOCAL = orig_machines, orig_local
    return v
