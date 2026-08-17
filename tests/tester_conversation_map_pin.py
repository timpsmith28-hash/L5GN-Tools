"""tester_conversation_map_pin: the conversation-map pin auditor's clean/fail
classification, driven through its explicit-path `check()` -- the testable
core of `run()` (DECISIONS 0045 applied to 0040 clause 4's uncheckered
fingerprint).

Hermetic: builds its own artefact/pin pair under a temp dir and never reads
this repo's real `config/mcf_conversation_map.tsv`, which may or may not
exist on the machine running the suite (`config/README.md`: the map travels
by hand and a fresh checkout has none). That absence must never fail a
tester any more than it fails the gate.
"""
from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

from auditors import auditor_conversation_map_pin as acmp
from l5gntools import pin

_yes = lambda sha: True    # noqa: E731
_no = lambda sha: False    # noqa: E731


def run() -> list[str]:
    v: list[str] = []

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        artefact = root / "map.tsv"
        pin_file = root / "map.tsv.sha256"
        content = b"a\tb\tc\n"
        digest = hashlib.sha256(content).hexdigest()
        artefact.write_bytes(content)
        pin_file.write_text(f"{digest}  config/mcf_conversation_map.tsv\n",
                            encoding="utf-8")

        # 1. Matching pin -> clean.
        if acmp.check(artefact, pin_file, _yes):
            v.append("conversation_map_pin: matching pin wrongly flagged")

        # 2. Artefact absent (fresh checkout, map never copied here) -> clean,
        #    not a violation -- the documented normal state.
        missing = root / "absent.tsv"
        if acmp.check(missing, pin_file, _yes):
            v.append("conversation_map_pin: absent artefact wrongly flagged "
                     "(should be the normal fresh-checkout state)")

        # 3. Neither pin nor artefact -> clean.
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

        # 5. Artefact exists with no pin at all -> flagged (0040 clause 4 requires one).
        unpinned = acmp.check(artefact, no_pin, _yes)
        if not unpinned:
            v.append("conversation_map_pin: artefact with no pin should be flagged")

        # 6. Unresolvable anchor -> flagged, even though the hash matches.
        anchored = root / "anchored.sha256"
        anchored.write_text(
            f"{digest}  config/mcf_conversation_map.tsv\n"
            f"# pin: origin=local anchor=notreal date=2026-08-17 host=rig\n",
            encoding="utf-8")
        bad_anchor = acmp.check(artefact, anchored, _no)
        if not bad_anchor:
            v.append("conversation_map_pin: unresolvable anchor should be flagged")

        # 7. Same anchored pin, git unavailable (resolver None) -> clean, not a
        #    false failure -- mirrors auditor_uat_stamp outside a checkout.
        if acmp.check(artefact, anchored, None):
            v.append("conversation_map_pin: absent git wrongly produced a violation")

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
