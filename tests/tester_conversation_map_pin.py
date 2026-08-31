"""tester_conversation_map_pin: the conversation-map pin auditor's clean/fail
classification, driven through its explicit-path `check()` and its pattern
discovery `subjects()` -- the testable core of `run()` (DECISIONS 0045 applied
to 0040 clause 4's unchecked fingerprint, then 0056 clauses 1-3).

Hermetic: builds its own artefact/pin pairs under a temp dir and never reads
this repo's real `config/*conversation_map.tsv`, which may or may not exist on
the machine running the suite (`config/README.md`: the map travels by hand and
a fresh checkout has none). That absence must never fail a tester any more than
it fails the gate.

**The pattern cases are the point of this file after 2026-08-31.** The defect
0056 clause 1 rules on was not a wrong answer -- it was a check that returned
the right answer about the one instance it had been told to look at, while a
second instance sat beside it unexamined. A tester that only ever hands
`check()` one pair reproduces exactly that blind spot, so `subjects()` is
tested against a directory holding two maps.
"""
from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

from auditors import auditor_conversation_map_pin as acmp
from l5gntools import pin

_yes = lambda sha: True    # noqa: E731
_no = lambda sha: False    # noqa: E731

_META = "# pin: origin=local anchor=abc123 date=2026-08-31 host=rig\n"


def run() -> list[str]:
    v: list[str] = []

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        artefact = root / "map.tsv"
        pin_file = root / "map.tsv.sha256"
        content = b"a\tb\tc\n"
        digest = hashlib.sha256(content).hexdigest()
        artefact.write_bytes(content)
        pin_file.write_text(
            f"{digest}  config/mcf_conversation_map.tsv\n{_META}",
            encoding="utf-8")

        # 1. Matching, metadata-complete pin -> clean.
        if acmp.check(artefact, pin_file, _yes):
            v.append(f"conversation_map_pin: matching complete pin wrongly "
                     f"flagged: {acmp.check(artefact, pin_file, _yes)}")

        # 2. Artefact absent (fresh checkout, map never copied here) -> clean,
        #    not a violation -- the documented normal state. The pin is still
        #    metadata-checked: 0056 clause 4's whole point is that a consumer
        #    WITHOUT the artefact reads the remedy off the pin.
        missing = root / "absent.tsv"
        if acmp.check(missing, pin_file, _yes):
            v.append("conversation_map_pin: absent artefact wrongly flagged "
                     "(should be the normal fresh-checkout state)")

        # 3. Neither pin nor artefact -> clean, and NOT dragged into a
        #    metadata finding by the clause-3 layer.
        no_pin = root / "no.sha256"
        if acmp.check(missing, no_pin, _yes):
            v.append("conversation_map_pin: neither pin nor artefact present "
                     "wrongly flagged")

        # 4. Artefact drifted from its pin -> exactly one finding naming both hashes.
        artefact.write_bytes(b"different bytes entirely")
        drifted = acmp.check(artefact, pin_file, _yes)
        if len(drifted) != 1 or digest not in drifted[0]:
            v.append(f"conversation_map_pin: drift not reported correctly: {drifted}")
        artefact.write_bytes(content)

        # 5. Artefact exists with no pin at all -> flagged (0040 clause 4
        #    requires one; 0056 clause 2 makes it a violation, not an absence).
        if not acmp.check(artefact, no_pin, _yes):
            v.append("conversation_map_pin: artefact with no pin should be flagged")

        # 6. Unresolvable anchor -> flagged, even though the hash matches.
        anchored = root / "anchored.sha256"
        anchored.write_text(
            f"{digest}  config/mcf_conversation_map.tsv\n"
            f"# pin: origin=local anchor=notreal date=2026-08-17 host=rig\n",
            encoding="utf-8")
        if not acmp.check(artefact, anchored, _no):
            v.append("conversation_map_pin: unresolvable anchor should be flagged")

        # 7. Same anchored pin, git unavailable (resolver None) -> clean, not a
        #    false failure -- mirrors auditor_uat_stamp outside a checkout.
        if acmp.check(artefact, anchored, None):
            v.append("conversation_map_pin: absent git wrongly produced a violation")

        # ---- 0056 clause 3: a hash-only pin is incomplete ------------------
        # This is the state config/mcf_conversation_map.tsv.sha256 was actually
        # in on 2026-08-31: a valid pin, a matching hash, and two thirds of
        # what clause 4 undertook to keep missing from it.
        bare = root / "bare.sha256"
        bare.write_text(f"{digest}  config/mcf_conversation_map.tsv\n",
                        encoding="utf-8")
        # The finding carries a missing-list AND an explanation naming every
        # field clause 3 wants. Only the first is an assertion about this pin,
        # so the tester reads the sentence before "DECISIONS" and nothing else
        # -- checking the whole string would pass on prose and prove nothing.
        def _missing(finding: str) -> str:
            return finding.split("DECISIONS")[0]

        bare_findings = acmp.check(artefact, bare, _yes)
        if len(bare_findings) != 1:
            v.append(f"conversation_map_pin: hash-only pin should produce one "
                     f"clause-3 finding, got {bare_findings}")
        elif not all(k in _missing(bare_findings[0])
                     for k in ("origin", "date", "host", "anchor")):
            v.append(f"conversation_map_pin: clause-3 finding should name every "
                     f"missing field, got {bare_findings[0]!r}")

        # A hash-only pin with git unavailable: still incomplete (origin, date,
        # host are unconditional), but `anchor` is NOT demanded -- the auditor
        # cannot distinguish an anchorless pin from an unanchorable one.
        bare_nogit = acmp.check(artefact, bare, None)
        if len(bare_nogit) != 1:
            v.append(f"conversation_map_pin: hash-only pin should still be "
                     f"incomplete without git, got {bare_nogit}")
        elif "anchor" in _missing(bare_nogit[0]):
            v.append(f"conversation_map_pin: anchor must not be demanded when no "
                     f"resolver is available -- clause 3 says 'where one "
                     f"exists': {_missing(bare_nogit[0])!r}")

        # A partially-complete pin names only what it is missing.
        partial = root / "partial.sha256"
        partial.write_text(
            f"{digest}  config/mcf_conversation_map.tsv\n"
            f"# pin: origin=local anchor=abc123 date=2026-08-31\n",
            encoding="utf-8")
        partial_findings = acmp.check(artefact, partial, _yes)
        if len(partial_findings) != 1 or "host" not in _missing(partial_findings[0]):
            v.append(f"conversation_map_pin: partial pin should name the missing "
                     f"field, got {partial_findings}")
        elif any(k in _missing(partial_findings[0])
                 for k in ("origin", "anchor", "date")):
            v.append(f"conversation_map_pin: a present field must not be reported "
                     f"missing: {_missing(partial_findings[0])!r}")

    # ---- 0056 clause 1: the subject is the pattern, not a path -------------
    # The regression this whole entry exists for: a second map appears and the
    # check must pick it up by existing, not by being edited.
    with tempfile.TemporaryDirectory() as td:
        cfg = Path(td)
        content = b"x\ty\n"
        digest = hashlib.sha256(content).hexdigest()

        (cfg / "mcf_conversation_map.tsv").write_bytes(content)
        (cfg / "mcf_conversation_map.tsv.sha256").write_text(
            f"{digest}  config/mcf_conversation_map.tsv\n{_META}", encoding="utf-8")
        # The second instance: present, unpinned -- the exact violation the
        # hardcoded auditor could not see.
        (cfg / "personal_conversation_map.tsv").write_bytes(content)
        # An unrelated config file must NOT be swept in.
        (cfg / "machines.json").write_text("{}", encoding="utf-8")
        # A pin whose artefact was never copied here still has a subject.
        (cfg / "orphan_conversation_map.tsv.sha256").write_text(
            f"{digest}  config/orphan_conversation_map.tsv\n{_META}",
            encoding="utf-8")

        found = {a.name for a, _ in acmp.subjects(cfg)}
        expected = {"mcf_conversation_map.tsv", "personal_conversation_map.tsv",
                    "orphan_conversation_map.tsv"}
        if found != expected:
            v.append(f"conversation_map_pin: subjects() should enumerate the "
                     f"pattern's matches and pins; expected {sorted(expected)}, "
                     f"got {sorted(found)}")

        # And the unpinned second map must actually be reported.
        all_findings: list[str] = []
        for a, p in acmp.subjects(cfg):
            all_findings.extend(acmp.check(a, p, _yes))
        if not any("personal_conversation_map.tsv" in f for f in all_findings):
            v.append(f"conversation_map_pin: an unpinned second map must be "
                     f"reported -- this is 0056's originating defect: "
                     f"{all_findings}")
        if any("machines.json" in f for f in all_findings):
            v.append("conversation_map_pin: the pattern must not sweep in "
                     "unrelated config files")

    # CLEAN_STATES sanity: every state pin.STATES declares is accounted for --
    # either explicitly clean or implicitly failing. Guards against a new
    # state being added to pin.py and silently falling through as clean.
    accounted = acmp.CLEAN_STATES | {
        "mismatch", "unpinned", "pin-malformed", "anchor-unresolvable"}
    missing_states = set(pin.STATES) - accounted
    if missing_states:
        v.append(f"conversation_map_pin: pin.STATES has states this tester "
                 f"doesn't classify: {missing_states}")

    return v
