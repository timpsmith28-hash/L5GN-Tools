"""tester_remedy_round_trip -- 0060 clause 5, in its cheapest honest form:
where a gate check prints a remedy, something asserts that running that remedy
satisfies that check.

**Why this exists.** A checker demanding what no sanctioned writer produces is
strictly worse than an unenforced rule: it converts a green gate into a
permanently red one with a documented fix that does nothing. The estate has the
worked instance, at `154afbd` -- the pin auditor required 0056 clause 3's
metadata, `run.py pin bump` short-circuited on hash equality and refused to
write it, and the printed remedy ran, reported success and changed nothing.
0053 clause 5 did not catch it: that clause required a remedy to be *safe*
wherever the check can fire, and **a remedy can be perfectly safe and inert.**

## The survey this file rests on, and what it found

`COWORK_BRIEF_conformance_reader.md` Task 5 asked whether any check besides the
conversation-map pin prints a remedy at all, and said that if none did, the
finding was to be recorded and no code written. **One other does**, so the
no-code branch does not apply:

  * `auditor_conversation_map_pin` -> `python run.py pin bump ...`
    Round trip **already asserted**, by `tests/tester_pin.py` as of `154afbd`.
  * `auditor_architecture_current` -> `python run.py render-architecture`
    Round trip **unasserted until this file**. `tester_architecture_current`
    checks the commit-line mask and that the auditor is green *right now*; it
    never runs the remedy and re-checks.

The stage runners print "re-run with --apply", but a stage is not a gate check
and 0060 clause 5 binds checks.

**Amended 2026-09-04.** A third check now prints a remedy and its round trip is
asserted below:

  * `auditor_authors_declaration` -> move the `authors` list from
    `config/local.json` into `config/machines.json` under the same hostname.

The sentence this replaces read *"No other auditor prints a remedy."* It was
true when written and stopped being true the moment a check was added, with
nothing to notice -- which is the gap the paragraph below already named as
undetected. It is recorded here rather than quietly overwritten, because a
docstring that silently tracks the tree teaches a reader that it was never
wrong.

**Three round trips now, and the "only one" instruction is spent.** The brief
said *"assert one round trip, and only one"*, scoping a round that had one
unasserted check to assert. Each new remedy-printing check brings its own, and
nothing detects one that arrives without it -- still named in
`CONVENTION_conformance.md` §10 rather than implied to be covered.

## What this asserts, and what it cannot

It asserts the **writer/checker agreement** for the render remedy: the text
`write_architecture_shape` commits to disk, read back the way the auditor reads
it, is the text the auditor compares against. An inert remedy, a lossy write,
or a renderer the two paths did not share all fail here.

**It does not run `run.py render-architecture` against the real tree.** Doing so
inside the gate would have a check write a tracked file, which is the posture
0045 clause 2 refuses everywhere else. The remedy's write step is exercised
against a temporary destination instead, which is the part that can be
exercised without the gate mutating what it is checking.

**One round trip, deliberately** (the brief: "assert one round trip, and only
one"). If a third check ever prints a remedy, it wants adding here, and nothing
detects that it has not been -- named in `CONVENTION_conformance.md` §10 rather
than implied to be covered.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from auditors import auditor_architecture_current as aac
from auditors import auditor_authors_declaration as aad
from l5gntools.report import render_architecture_shape
from l5gntools.scanners.architecture_census import census


def _check_render_architecture_round_trip() -> list[str]:
    v: list[str] = []

    # The payload both paths derive from. The auditor calls exactly this
    # (its run(), line "fresh_text = render_architecture_shape(census(...))"),
    # and so does write_architecture_shape.
    data = census(aac.TOOLKIT_ROOT)
    rendered = render_architecture_shape(data)

    # The remedy's write step, against a temp destination rather than the
    # tracked file: the same call write_architecture_shape makes.
    with tempfile.TemporaryDirectory() as td:
        dest = Path(td) / "_architecture_shape.md"
        dest.write_text(rendered, encoding="utf-8")
        written_back = dest.read_text(encoding="utf-8")

    # The auditor's own decision procedure, reused rather than restated --
    # 0060 clause 6: a shared invariant expressed as a copy in a second place
    # is not a mechanism.
    if aac._mask_commit_line(written_back) != aac._mask_commit_line(rendered):
        v.append(
            "remedy round trip: `run.py render-architecture` writes a file "
            "that auditor_architecture_current would still reject. The "
            "printed remedy does not satisfy the check that prints it "
            "(0060 cl.5)."
        )

    # The remedy is not inert: it must actually produce content. An empty or
    # missing render that happened to compare equal to itself would pass the
    # check above while satisfying nothing.
    if not rendered.strip():
        v.append(
            "remedy round trip: render_architecture_shape produced empty "
            "output -- a remedy that writes nothing satisfies its checker "
            "only by accident (0060 cl.5)."
        )
    return v


def _check_authors_declaration_round_trip() -> list[str]:
    """`auditor_authors_declaration`'s remedy is an edit rather than a command,
    and 0060 clause 5 binds it the same way: performing the printed fix must
    satisfy the check that printed it.

    So the fix is performed here -- the `authors` key moved out of the overlay
    -- and the same decision procedure re-run. A remedy that named the wrong
    file, or a check keyed on something the remedy does not change, fails here.
    """
    v: list[str] = []
    before = json.dumps({
        "RIG": {"authors": ["config/map.tsv"], "vault": "v"},
        "OTHER": {"vault": "v2"},
    })

    flagged = aad.violations_in_overlay(before)
    if not flagged:
        v.append("remedy round trip: auditor_authors_declaration did not flag an "
                 "overlay declaring 'authors' -- the check the remedy answers "
                 "must be able to fire, or asserting its round trip proves "
                 "nothing (0048 cl.4)")
        return v

    # The remedy, as the message describes it: the 'authors' list leaves the
    # overlay for the tracked file. Only that key moves; the host section and
    # its machine-specific keys stay, which is what makes the fix survivable.
    data = json.loads(before)
    moved = data["RIG"].pop("authors")
    after = json.dumps(data)

    if aad.violations_in_overlay(after):
        v.append("remedy round trip: performing auditor_authors_declaration's "
                 "printed remedy leaves the check still failing. The printed "
                 "fix does not satisfy the check that prints it (0060 cl.5).")

    # Not inert: the remedy must move something real, and the host section must
    # survive it. A "fix" that emptied the overlay would pass the check above
    # while destroying the machine's configuration.
    if moved != ["config/map.tsv"]:
        v.append(f"remedy round trip: the remedy should relocate the declared "
                 f"list intact, got {moved!r}")
    if json.loads(after)["RIG"].get("vault") != "v":
        v.append("remedy round trip: the remedy must move only the 'authors' "
                 "key -- a fix that takes the host's machine-specific config "
                 "with it satisfies the checker by breaking the machine")

    # And the message must carry the remedy at all, or there is no round trip
    # to assert -- only a refusal.
    if "config/machines.json" not in flagged[0]:
        v.append("remedy round trip: auditor_authors_declaration's finding does "
                 "not name where the declaration should go, so the printed "
                 "remedy is not actionable from the failure alone")
    return v


def run() -> list[str]:
    return (_check_render_architecture_round_trip()
            + _check_authors_declaration_round_trip())
