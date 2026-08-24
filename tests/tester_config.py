"""Verify machine-config selection, unmatched-host refusal, per-artefact
authorship, and root resolution.

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
            # The live hostname is declared in the fixture on purpose: since
            # an unmatched host now raises, a bare `config.machine()` against
            # a throwaway config would refuse on every machine and the
            # _hostname assertion below could never run.
            config.hostname(): {"role": "producer", "estate": "unknown"},
        }), encoding="utf-8")

        orig_machines, orig_local = config._MACHINES, config._LOCAL
        config._MACHINES = mfile
        config._LOCAL = Path(td) / "local.json"      # intentionally absent
        try:
            # Unknown host -> RAISES. It must not inherit 'default': a rootless
            # default answering for an unknown host is how a sandbox run
            # produces a confident snapshot of an empty estate
            # (TOOLKIT_notes_2026-08-23 §4).
            try:
                config.machine("no-such-host-xyz-123")
                v.append("config: an unmatched host must raise UnknownHostError, "
                         "not fall back to 'default' -- a rootless default is a "
                         "confident answer about nothing")
            except config.UnknownHostError as exc:
                # The message has to carry the fix, or the raise is just a
                # crash with better manners.
                if "TEST-HOST" not in str(exc):
                    v.append(f"config: UnknownHostError should name the hosts that "
                             f"ARE configured so the fix is legible from the "
                             f"failure alone, got: {exc}")
                if "no-such-host-xyz-123" not in str(exc):
                    v.append(f"config: UnknownHostError should name the host it "
                             f"refused, got: {exc}")

            # Everything resolved through machine() inherits the refusal --
            # there is no back door that still answers for an unknown host.
            for label, call in (("estate_roots", lambda: config.estate_roots("no-such-host-xyz-123")),
                                 ("mesh_enabled", lambda: config.mesh_enabled("no-such-host-xyz-123")),
                                 ("authored_artefacts", lambda: config.authored_artefacts("no-such-host-xyz-123"))):
                try:
                    call()
                    v.append(f"config: {label}() answered for an unmatched host; "
                             f"every accessor resolving through machine() must "
                             f"inherit its refusal")
                except config.UnknownHostError:
                    pass

            # configured_hosts lists real hosts only -- not 'default', not
            # the _comment keys.
            hosts = config.configured_hosts()
            if "TEST-HOST" not in hosts or "default" in hosts:
                v.append(f"config: configured_hosts() should list declared hosts "
                         f"only, excluding 'default' and _comment keys: {hosts}")

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

            # A host absent from BOTH files raises, even though both files
            # carry a 'default' section that would otherwise have answered.
            # This is the case that used to silently succeed.
            try:
                config.machine("OTHER")
                v.append("config: a host absent from both files must raise even "
                         "when both files declare a 'default' -- default is a "
                         "base layer under a matched host, not a stand-in")
            except config.UnknownHostError:
                pass
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

    v.extend(_check_artefact_authorship())
    v.extend(_check_scoped_roots())
    return v


def _check_artefact_authorship() -> list[str]:
    """`authors` declares which artefacts a host authors (DECISIONS 0053
    clause 5, as applied by `run.py pin bump`).

    The property that matters is that authorship is **per artefact and not
    per role**: the fixture below is deliberately two hosts with the *same*
    role and different `authors` lists, because that is the real estate --
    LucasGoonPC and 10280L are both `producer` and only one of them authors
    the conversation map. A mechanism keyed on `role` would pass a weaker
    fixture and fail this one.
    """
    v: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        mfile = Path(td) / "machines.json"
        mfile.write_text(json.dumps({
            "default": {"role": "producer"},
            "AUTHOR-RIG": {"role": "producer",
                            "authors": ["config/map.tsv", "docs/thing.md"]},
            "CONSUMER-RIG": {"role": "producer"},
        }), encoding="utf-8")
        orig_machines, orig_local = config._MACHINES, config._LOCAL
        config._MACHINES, config._LOCAL = mfile, Path(td) / "absent.json"
        try:
            if not config.authors_artefact("config/map.tsv", "AUTHOR-RIG"):
                v.append("config: a declared artefact should read as authored on "
                         "the host that declares it")
            if config.authors_artefact("config/map.tsv", "CONSUMER-RIG"):
                v.append("config: a host that declares no 'authors' must author "
                         "nothing -- same role as the authoring rig is exactly "
                         "the case this must not be fooled by")
            if config.authors_artefact("config/never_declared.tsv", "AUTHOR-RIG"):
                v.append("config: an artefact no host declares must not read as "
                         "authored anywhere -- an undeclared artefact is a config "
                         "gap, never permission")

            # Separator style must not decide the answer: the caller may hold
            # a Windows path and the config a posix one, and a pin refusal
            # that hinged on a backslash would be the 8.3 class of bug again.
            if not config.authors_artefact("config\\map.tsv", "AUTHOR-RIG"):
                v.append("config: authorship must compare posix-normalised, so a "
                         "backslash path from a Windows caller still matches")
            if not config.authors_artefact(Path("config/map.tsv"), "AUTHOR-RIG"):
                v.append("config: authors_artefact should accept a Path as well "
                         "as a string")

            hosts = config.authoring_hosts("config/map.tsv")
            if hosts != ["AUTHOR-RIG"]:
                v.append(f"config: authoring_hosts should name where an artefact "
                         f"IS authored, so a refusal can say so: {hosts}")
            if config.authoring_hosts("config/never_declared.tsv") != []:
                v.append("config: an undeclared artefact should have no authoring "
                         "hosts, reported as empty rather than as everyone")

            declared = config.authored_artefacts("AUTHOR-RIG")
            if declared != ["config/map.tsv", "docs/thing.md"]:
                v.append(f"config: authored_artefacts should return the declared "
                         f"list, normalised: {declared}")
            if config.authored_artefacts("CONSUMER-RIG") != []:
                v.append("config: a host with no 'authors' key should report an "
                         "empty list, not None and not a crash")
        finally:
            config._MACHINES, config._LOCAL = orig_machines, orig_local
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
