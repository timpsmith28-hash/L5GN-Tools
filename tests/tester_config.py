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

        # ---- 0054 clause 6: authorship is tracked-file-only ----------------
        # The one key that does NOT follow the precedence rules asserted above.
        # local.json may not supply authorship and may not override it: an
        # untracked declaration makes "no host declares this" and "the
        # declaration has not shipped here yet" the same input with two
        # meanings, and 0053 clause 5's pin-bump refusal rests on telling them
        # apart. Asserted as behaviour rather than left to tidiness, because
        # the violation this replaces survived by nobody reading either file.
        # Two levels, and they are asserted separately on purpose. Structure
        # (`_tracked_entry` drops the overlay from the layer stack) keeps a
        # smuggled declaration from being READ; the loud refusal added
        # 2026-09-04 keeps it from being WRITTEN and believed (clause 8).
        #
        # **This block was rewritten on 2026-09-04 and the reason is worth
        # keeping.** It used to assert the resolution behaviour by calling
        # `authored_artefacts` against a fixture whose overlay carried
        # `authors` -- the exact state `machine()` now raises on, so those
        # assertions could no longer reach their subject. The properties they
        # covered are all still covered below, one level lower.
        mfile4 = Path(td) / "machines4.json"
        lfile4 = Path(td) / "local4.json"
        mfile4.write_text(json.dumps({
            "default": {"role": "producer"},
            "TRACKED_RIG": {"authors": ["config/a.tsv"]},
            "BOTH_RIG": {"authors": ["config/tracked_wins.tsv"]},
        }), encoding="utf-8")
        smuggled = {
            "_comment": "a comment key is not a host section",
            "LOCAL_ONLY_RIG": {"authors": ["config/smuggled.tsv"]},
            "BOTH_RIG": {"authors": ["config/local_loses.tsv"]},
            "CLEAN_RIG": {"vault": "v"},
        }
        lfile4.write_text(json.dumps(smuggled), encoding="utf-8")
        config._MACHINES, config._LOCAL = mfile4, lfile4
        try:
            # ---- level 1: the overlay is unreadable, not merely outranked ----
            # Asserted against `_tracked_entry` directly, which is the layer the
            # property lives in. Going through `machine()` would hit the clause 8
            # refusal below and prove nothing about resolution.
            if config._authored_paths(config._tracked_entry("BOTH_RIG")) != \
                    ["config/tracked_wins.tsv"]:
                v.append("config: the tracked declaration must survive an overlay "
                         "carrying the same host (0054 cl.6)")
            if config._authored_paths(config._tracked_entry("LOCAL_ONLY_RIG")) != []:
                v.append("config: a host declared only in the overlay must author "
                         "nothing -- the overlay is not read (0054 cl.6)")

            # ---- level 2: and it refuses loudly rather than ignoring it ------
            offenders = config._overlay_authorship(smuggled)
            if offenders != ["BOTH_RIG", "LOCAL_ONLY_RIG"]:
                v.append("config: _overlay_authorship should name every host "
                         f"section carrying 'authors', sorted; got {offenders!r}")
            try:
                config.machine("TRACKED_RIG")
                v.append("config: an overlay declaring 'authors' must raise "
                         "OverlayAuthorshipError -- 0054 cl.8 says unrecognised "
                         "configuration fails loudly, and an inert key is exactly "
                         "the silent case cl.6 exists to remove")
            except config.OverlayAuthorshipError as exc:
                # The message must carry the remedy, or the refusal is a wall.
                text = str(exc)
                if "config/machines.json" not in text or "LOCAL_ONLY_RIG" not in text:
                    v.append("config: OverlayAuthorshipError must name the "
                             "offending host and the file to move it to, so the "
                             f"fix is legible from the failure alone; got {text!r}")
        finally:
            config._MACHINES, config._LOCAL = orig_machines, orig_local

        # ---- a clean overlay: everything else still behaves as it did -------
        mfile5 = Path(td) / "machines5.json"
        lfile5 = Path(td) / "local5.json"
        mfile5.write_text(json.dumps({
            "default": {"role": "producer"},
            "TRACKED_RIG": {"authors": ["config/a.tsv"]},
        }), encoding="utf-8")
        lfile5.write_text(json.dumps({"TRACKED_RIG": {"vault": "v"}}),
                          encoding="utf-8")
        config._MACHINES, config._LOCAL = mfile5, lfile5
        try:
            if config.authored_artefacts("TRACKED_RIG") != ["config/a.tsv"]:
                v.append("config: authorship declared in machines.json should "
                         f"resolve, got {config.authored_artefacts('TRACKED_RIG')!r}")
            if config.authoring_hosts("config/a.tsv") != ["TRACKED_RIG"]:
                v.append("config: authoring_hosts should name the tracked author, "
                         f"got {config.authoring_hosts('config/a.tsv')!r}")
            if config.authoring_hosts("config/never_declared.tsv") != []:
                v.append("config: authoring_hosts must name nobody for an "
                         "artefact no tracked host declares")

            # An entirely unconfigured host still raises loudly rather than
            # degrading to "authors nothing", which would read as a config gap.
            try:
                config.authored_artefacts("NO_SUCH_RIG")
                v.append("config: authored_artefacts on an unconfigured host must "
                         "raise UnknownHostError, not return an empty list -- an "
                         "empty list reads as 'declares nothing', which is a "
                         "different fact from 'is not a machine here'")
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
