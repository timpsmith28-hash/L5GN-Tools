"""tester_pin: `l5gntools.pin`'s reader and verifier (DECISIONS 0045).

Hermetic: every case builds its own pin file and artefact under a throwaway
temp dir, with the commit resolver injected exactly like
`auditor_uat_stamp`'s `commit_exists` -- nothing here touches this repo's
real `config/mcf_conversation_map.tsv` or its git state.

The load-bearing behaviours:

  * a matching hash with no anchor recorded -> `matches`, no findings,
  * a real mismatch -> `mismatch`, both hashes named, findings say "reported,
    not repaired" (0045 clause 2),
  * the artefact missing while the pin exists -> `artefact-absent`, clean --
    the normal state for a hand-carried artefact on a fresh checkout,
  * the artefact present with no pin at all -> `unpinned`, one finding,
  * neither exists -> `absent`, clean,
  * a pin file whose first line doesn't parse -> `pin-malformed`,
  * an anchor that doesn't resolve, with git available -> `anchor-unresolvable`,
    a violation, never a silent pass (0045 clause 3),
  * an anchor set but no resolver injected -> `git-unavailable`, clean, not
    a false failure (mirrors `auditor_uat_stamp`'s degrade-to-skip),
  * a legacy pin with no comment line at all still parses and verifies.
"""
from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

from l5gntools import pin

_yes = lambda sha: True    # noqa: E731 -- resolver stub: every sha resolves
_no = lambda sha: False    # noqa: E731 -- resolver stub: nothing resolves


def run() -> list[str]:
    v: list[str] = []

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        artefact = root / "map.tsv"
        pin_file = root / "map.tsv.sha256"

        content = b"row one\nrow two\n"
        digest = hashlib.sha256(content).hexdigest()
        artefact.write_bytes(content)

        # 1. Matching hash, no comment line at all (legacy shape) -> matches,
        #    clean, and parses with origin/anchor/date/host all None.
        pin_file.write_text(f"{digest}  config/map.tsv\n", encoding="utf-8")
        record = pin.parse_pin_file(pin_file)
        if record is None or record.sha256 != digest or record.anchor is not None:
            v.append(f"pin: legacy hash-only pin did not parse as expected: {record}")
        check = pin.verify_pin(pin_file, artefact, _yes)
        if check.state != "matches" or check.findings:
            v.append(f"pin: matching legacy pin should be clean 'matches', got {check}")

        # 2. A real mismatch -> both hashes named, findings say reported-not-repaired.
        artefact.write_bytes(b"drifted content")
        mismatch = pin.verify_pin(pin_file, artefact, _yes)
        if mismatch.state != "mismatch":
            v.append(f"pin: drifted artefact should be 'mismatch', got {mismatch.state!r}")
        if not mismatch.findings or digest not in mismatch.findings[0]:
            v.append(f"pin: mismatch finding doesn't name the recorded hash: {mismatch.findings}")
        if mismatch.actual_hash == digest:
            v.append("pin: mismatch actual_hash should differ from the recorded hash")
        if not any("not repaired" in f for f in mismatch.findings):
            v.append(f"pin: mismatch finding doesn't cite 'reported, not repaired': {mismatch.findings}")
        # Nothing touched: the drifted artefact is left exactly as written.
        if artefact.read_bytes() != b"drifted content":
            v.append("pin: verify_pin must never repair the artefact")
        artefact.write_bytes(content)  # restore for the rest of the cases

        # 3. Artefact absent, pin present -> artefact-absent, clean.
        missing_artefact = root / "does-not-exist.tsv"
        absent_check = pin.verify_pin(pin_file, missing_artefact, _yes)
        if absent_check.state != "artefact-absent" or absent_check.findings:
            v.append(f"pin: missing artefact with a pin should be clean "
                     f"'artefact-absent', got {absent_check}")

        # 4. Artefact present, no pin file at all -> unpinned, one finding.
        no_pin_file = root / "nopin.sha256"
        unpinned = pin.verify_pin(no_pin_file, artefact, _yes)
        if unpinned.state != "unpinned" or len(unpinned.findings) != 1:
            v.append(f"pin: artefact with no pin should be 'unpinned' with one "
                     f"finding, got {unpinned}")

        # 5. Neither exists -> absent, clean.
        neither = pin.verify_pin(no_pin_file, missing_artefact, _yes)
        if neither.state != "absent" or neither.findings:
            v.append(f"pin: neither pin nor artefact should be clean 'absent', got {neither}")

        # 6. Malformed pin (bad first line) -> pin-malformed.
        bad_pin = root / "bad.sha256"
        bad_pin.write_text("not a hash line at all\n", encoding="utf-8")
        malformed = pin.verify_pin(bad_pin, artefact, _yes)
        if malformed.state != "pin-malformed" or not malformed.findings:
            v.append(f"pin: malformed pin not caught: {malformed}")

        # 7. Anchor set, present, resolver says it doesn't resolve -> violation.
        anchored = root / "anchored.sha256"
        anchored.write_text(
            f"{digest}  config/map.tsv\n"
            f"# pin: origin=local anchor=deadbeef date=2026-08-17 host=testhost\n",
            encoding="utf-8")
        parsed = pin.parse_pin_file(anchored)
        if parsed is None or parsed.origin != "local" or parsed.anchor != "deadbeef" \
                or parsed.date != "2026-08-17" or parsed.host != "testhost":
            v.append(f"pin: anchored pin's comment line did not parse fully: {parsed}")
        unresolved = pin.verify_pin(anchored, artefact, _no)
        if unresolved.state != "anchor-unresolvable":
            v.append(f"pin: unresolvable anchor should fail, got {unresolved.state!r}")
        if not any("not a silent pass" in f for f in unresolved.findings):
            v.append(f"pin: unresolvable-anchor finding missing its citation: {unresolved.findings}")

        # 7b. Same anchored pin, resolver says it DOES resolve -> matches.
        resolved = pin.verify_pin(anchored, artefact, _yes)
        if resolved.state != "matches":
            v.append(f"pin: resolvable anchor should pass as 'matches', got {resolved.state!r}")

        # 8. Anchor set but no resolver injected (git unavailable) -> skip, not a
        #    failure -- mirrors auditor_uat_stamp's degrade-to-skip.
        no_git = pin.verify_pin(anchored, artefact, None)
        if no_git.state != "git-unavailable" or no_git.findings:
            v.append(f"pin: absent git should degrade to clean 'git-unavailable', got {no_git}")

        # 9. format_pin_line / format_pin_comment round-trip through parse_pin_file.
        line = pin.format_pin_line(digest, "config/map.tsv")
        comment = pin.format_pin_comment(origin="local", anchor="abc123",
                                          date="2026-08-17", host="rig")
        written = root / "formatted.sha256"
        written.write_text(line + "\n" + comment + "\n", encoding="utf-8")
        round_trip = pin.parse_pin_file(written)
        if (round_trip is None or round_trip.sha256 != digest
                or round_trip.origin != "local" or round_trip.anchor != "abc123"
                or round_trip.date != "2026-08-17" or round_trip.host != "rig"):
            v.append(f"pin: format_pin_line/format_pin_comment did not round-trip: {round_trip}")

        # 9b. format_pin_comment with anchor=None omits the field entirely.
        no_anchor_comment = pin.format_pin_comment(origin="local", anchor=None,
                                                     date="2026-08-17", host="rig")
        if "anchor=" in no_anchor_comment:
            v.append(f"pin: format_pin_comment should omit anchor= when None: {no_anchor_comment!r}")

    return v
