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

        # ---- Precedence: default < host < local default < local host ----
        mfile2 = Path(td) / "machines2.json"
        lfile2 = Path(td) / "local2.json"
        mfile2.write_text(json.dumps({
            "default": {"role": "producer", "estate": "unknown", "vault": "m-default"},
            "RIG": {"estate": "personal", "vault": "m-host", "push_target": "keep"},
        }), encoding="utf-8")
        lfile2.write_text(json.dumps({
            "default": {"vault": "l-default", "secret": "s"},
            "RIG": {"vault": "l-host"},
        }), encoding="utf-8")
        config._MACHINES, config._LOCAL = mfile2, lfile2
        try:
            r = config.machine("RIG")
            # local host wins over every lower layer for an overlapping key.
            if r.get("vault") != "l-host":
                v.append(f"config: local[host] should win precedence, got vault={r.get('vault')!r}")
            # host layer supplies keys absent from local; default supplies role.
            if r.get("estate") != "personal":
                v.append(f"config: machine[host] estate should survive, got {r.get('estate')!r}")
            if r.get("role") != "producer":
                v.append(f"config: machine[default] role should survive, got {r.get('role')!r}")
            if r.get("push_target") != "keep":
                v.append("config: machine[host]-only key should survive the overlay")
            if r.get("secret") != "s":
                v.append("config: local[default] key should overlay onto a matched host")
            if r.get("_matched") is not True:
                v.append("config: a host present in local.json should report _matched True")

            # local default with no host section still overlays a host miss.
            r2 = config.machine("OTHER")
            if r2.get("vault") != "l-default" or r2.get("estate") != "unknown":
                v.append(f"config: unmatched host should take local[default] overlay, got {r2}")
            if r2.get("_matched") is not False:
                v.append("config: host absent from both files should report _matched False")
        finally:
            config._MACHINES, config._LOCAL = orig_machines, orig_local

        # ---- estate_roots: empty list is falsy -> None (legacy discovery) ----
        mfile3 = Path(td) / "machines3.json"
        mfile3.write_text(json.dumps({"HAS_EMPTY": {"roots": []}}), encoding="utf-8")
        config._MACHINES, config._LOCAL = mfile3, Path(td) / "absent.json"
        try:
            if config.estate_roots("HAS_EMPTY") is not None:
                v.append("config: an empty 'roots' list should yield estate_roots() None")
        finally:
            config._MACHINES, config._LOCAL = orig_machines, orig_local

        # ---- Malformed / empty config files never raise, just yield {} ----
        bad = Path(td) / "bad.json"
        bad.write_text("{not valid json", encoding="utf-8")
        empty = Path(td) / "empty.json"
        empty.write_text("", encoding="utf-8")
        arr = Path(td) / "arr.json"
        arr.write_text("[1, 2, 3]", encoding="utf-8")  # valid JSON, wrong shape
        if config._load(bad) != {}:
            v.append("config: malformed JSON should load as {}")
        if config._load(empty) != {}:
            v.append("config: empty file should load as {}")
        if config._load(Path(td) / "missing.json") != {}:
            v.append("config: missing file should load as {}")
        if config._load(arr) != {}:
            v.append("config: a non-object JSON body should load as {}")

        # ---- author_aliases: canonical->self, aliases lowercased, _keys skipped ----
        afile = Path(td) / "authors.json"
        afile.write_text(json.dumps({
            "Tim Smith": ["timps", "T. Smith", "tsmith@example.com"],
            "Solo": [],
            "_comment": ["ignored"],
        }), encoding="utf-8")
        orig_authors = config._AUTHORS
        config._AUTHORS = afile
        try:
            aliases = config.author_aliases()
            if aliases.get("tim smith") != "Tim Smith":
                v.append("config: canonical author should map to itself (lowercased key)")
            if aliases.get("timps") != "Tim Smith" or aliases.get("t. smith") != "Tim Smith":
                v.append("config: aliases should fold to their canonical name")
            if aliases.get("tsmith@example.com") != "Tim Smith":
                v.append("config: email-shaped alias should still fold")
            if "T. Smith" in aliases:
                v.append("config: alias keys should be lowercased, not raw")
            if aliases.get("solo") != "Solo":
                v.append("config: a canonical with no aliases should still self-map")
            if any(k.startswith("_") for k in aliases):
                v.append("config: underscore meta keys should be skipped")
        finally:
            config._AUTHORS = orig_authors

        # Absent authors file -> empty mapping, never a crash.
        config._AUTHORS = Path(td) / "no_authors.json"
        try:
            if config.author_aliases() != {}:
                v.append("config: absent authors.json should yield an empty alias map")
        finally:
            config._AUTHORS = orig_authors

    v.extend(_check_scoped_roots())
    return v


def _check_scoped_roots() -> list[str]:
    """Roots may be tagged with a scope (DECISIONS 0012 / round-3 Task C.3).

    Both shapes must work: a bare path string (legacy, scope unknown) and
    {"path":..., "scope":...}. The tagged form is what lets a flat estate be
    classified without moving any folders, so the fallback path -- untagged
    yields None rather than a guess -- matters as much as the happy path.
    """
    v: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        (base / "GitHub").mkdir()
        (base / "GitHub" / "Spire").mkdir()
        (base / "Work").mkdir()
        (base / "Work" / "MCF").mkdir()
        (base / "Work" / "MCF" / "ActivityStatements").mkdir()
        (base / "Loose").mkdir()
        (base / "Loose" / "Orphan").mkdir()

        mfile = base / "machines.json"
        mfile.write_text(json.dumps({
            "testhost": {"roots": [
                {"path": str(base / "GitHub"), "scope": "l5gn"},
                {"path": str(base / "Work"), "scope": "l5gn"},
                {"path": str(base / "Work" / "MCF"), "scope": "mcf"},
                str(base / "Loose"),
            ]}
        }), encoding="utf-8")
        orig_m, orig_l = config._MACHINES, config._LOCAL
        config._MACHINES = mfile
        config._LOCAL = base / "no_local.json"
        try:
            # bare strings and tagged dicts both resolve as roots
            roots = config.estate_roots("testhost") or []
            if len(roots) != 4:
                v.append(f"config: estate_roots returned {len(roots)} roots, "
                         "expected all four (mixed bare + tagged shapes)")
            if not all(isinstance(r, Path) for r in roots):
                v.append("config: estate_roots must still return Paths for legacy "
                         "callers")

            tagged = config.estate_roots_tagged("testhost")
            if [t.get("scope") for t in tagged] != ["l5gn", "l5gn", "mcf", None]:
                v.append(f"config: root scope tags read as "
                         f"{[t.get('scope') for t in tagged]}")

            if config.scope_for_path(base / "GitHub" / "Spire", "testhost") != "l5gn":
                v.append("config: a project under a tagged root did not inherit its "
                         "scope -- this is the whole config-tag mechanism")

            # nested tagged root wins over its tagged parent (longest match)
            got = config.scope_for_path(base / "Work" / "MCF" / "ActivityStatements",
                                        "testhost")
            if got != "mcf":
                v.append(f"config: nested root scope resolved to {got!r}, expected "
                         "'mcf' -- the more specific root must win")

            # untagged root -> None, never a guess
            if config.scope_for_path(base / "Loose" / "Orphan", "testhost") is not None:
                v.append("config: an untagged root must yield None, not an inferred "
                         "scope (a wrong scope silently mis-files a project)")
            if config.scope_for_path(base / "Elsewhere", "testhost") is not None:
                v.append("config: a path under no configured root must yield None")
        finally:
            config._MACHINES, config._LOCAL = orig_m, orig_l
    return v
