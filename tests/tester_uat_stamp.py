"""tester_uat_stamp: the uat-stamp auditor's parser and check logic.

Hermetic and order-independent: drives the pure `parse_stamp` / `check` helpers
on synthetic text, with the SHA resolver injected, so nothing here touches the
repository's real docs or its git state.

The load-bearing behaviours:

  * a missing stamp fails (the whole point -- an acceptance claim with no
    provenance is what let a stale tester count back into a live doc),
  * a stamp naming a commit that does not exist fails,
  * a `gate=` claim that contradicts verify.py fails,
  * git being unavailable degrades to a skip of the SHA check, never a false
    failure.
"""
from __future__ import annotations

from auditors import auditor_uat_stamp as aus

_GOOD = "<!-- uat: commit=48ce16d dirty=false host=knight walked=2026-07-21 gate=5a/23t -->"

_yes = lambda sha: True    # noqa: E731 -- resolver stub: every sha resolves
_no = lambda sha: False    # noqa: E731 -- resolver stub: nothing resolves


def run() -> list[str]:
    v: list[str] = []

    # 1. Parsing: fields come back lowercased and complete.
    got = aus.parse_stamp(f"# Log\n{_GOOD}\n\nbody")
    if not got or got.get("commit") != "48ce16d" or got.get("walked") != "2026-07-21":
        v.append(f"uat_stamp: stamp did not parse as expected: {got}")
    if aus.parse_stamp("no stamp here at all") is not None:
        v.append("uat_stamp: absent stamp did not return None")

    # 2. A good stamp against a matching gate is clean.
    if aus.check(_GOOD, "d.md", 5, 23, _yes):
        v.append("uat_stamp: valid stamp wrongly flagged")

    # 3. No stamp -> exactly one violation, and it says what to add.
    missing = aus.check("# Log\n\nwalked it, all passed", "d.md", 5, 23, _yes)
    if len(missing) != 1 or "no uat stamp" not in missing[0]:
        v.append(f"uat_stamp: missing stamp not reported correctly: {missing}")

    # 4. A commit that does not resolve is caught.
    unresolved = aus.check(_GOOD, "d.md", 5, 23, _no)
    if not any("not a commit in this repository" in x for x in unresolved):
        v.append(f"uat_stamp: unresolvable commit not caught: {unresolved}")

    # 5. git unavailable (resolver None) skips the SHA check, keeps the rest.
    if aus.check(_GOOD, "d.md", 5, 23, None):
        v.append("uat_stamp: absent git produced a violation instead of a skip")

    # 6. A gate claim contradicting verify.py is caught -- the motivating case.
    stale = "<!-- uat: commit=48ce16d walked=2026-07-21 gate=5a/18t -->"
    wrong = aus.check(stale, "d.md", 5, 23, _yes)
    if not any("5 auditors + 18 testers" in x for x in wrong):
        v.append(f"uat_stamp: stale gate count not caught: {wrong}")

    # 7. A malformed gate value is caught rather than silently ignored.
    bad = aus.check("<!-- uat: commit=abc walked=2026-07-21 gate=lots -->",
                    "d.md", 5, 23, _yes)
    if not any("malformed" in x for x in bad):
        v.append(f"uat_stamp: malformed gate not caught: {bad}")

    # 8. A required field missing is named explicitly.
    nowalk = aus.check("<!-- uat: commit=48ce16d -->", "d.md", 5, 23, _yes)
    if not any("missing 'walked='" in x for x in nowalk):
        v.append(f"uat_stamp: missing required field not reported: {nowalk}")

    # 9. gate= is optional -- its absence is not a violation.
    if aus.check("<!-- uat: commit=48ce16d walked=2026-07-21 -->", "d.md", 5, 23, _yes):
        v.append("uat_stamp: absent optional gate= wrongly flagged")

    return v
