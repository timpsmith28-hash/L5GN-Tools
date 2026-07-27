"""tester_doc_claims: the doc-claims auditor's matcher and violation logic.

Hermetic and order-independent: exercises the pure `find_claims` / `violations_in`
helpers on synthetic text rather than the live repo docs (whose real counts move
as auditors/testers are added). The load-bearing behaviours are:

  * a compound "N auditors + M testers" claim is detected and diffed
    (including the bold-wrapped-digit variant, "6 auditors + **37** testers"),
  * a *narrative* mention of a past count ("...once claimed 18 testers when
    verify.py had 14") is NOT matched -- the auditor must never flag history,
  * a gate-frozen marker exempts a stale claim, but only when it is
    well-formed, resolvable, and the doc is allowed to carry one at all.
"""
from __future__ import annotations

from auditors import auditor_doc_claims as adc

_yes = lambda sha: True    # noqa: E731 -- resolver stub: every sha resolves
_no = lambda sha: False    # noqa: E731 -- resolver stub: nothing resolves


def run() -> list[str]:
    v: list[str] = []

    # 1. Compound present-tense claim is detected, both variants.
    if adc.find_claims("gate is green (4 auditors + 18 hermetic testers).") != [(4, 18, 15)]:
        v.append("doc_claims: failed to detect 'N auditors + M hermetic testers'")
    plain = adc.find_claims("registers **4 auditors + 14 testers**, all hermetic")
    if [(a, t) for a, t, _ in plain] != [(4, 14)]:
        v.append("doc_claims: failed to detect plain 'N auditors + M testers'")

    # 1b. The bold-digit variant ("6 auditors + **37** testers") is caught too --
    # the accidental regex hole the round-vintage docs were escaping through.
    bold_digit = adc.find_claims("GREEN, 6 auditors + **37** testers at this build")
    if [(a, t) for a, t, _ in bold_digit] != [(6, 37)]:
        v.append(f"doc_claims: bold-wrapped digit claim not detected: {bold_digit}")

    # 2. The false-positive guard: a narrative past-count mention must NOT match.
    narrative = "HANDOFF once claimed 18 testers when verify.py had 14, caught cold."
    if adc.find_claims(narrative):
        v.append(f"doc_claims: narrative past-count wrongly matched: {narrative!r}")

    # A bare tester count with no adjacent auditor count must also not match.
    if adc.find_claims("the suite now has 14 testers"):
        v.append("doc_claims: bare standalone tester count wrongly matched")

    # 3. violations_in: matching counts -> clean; mismatched -> one violation.
    if adc.violations_in("4 auditors + 14 testers", 4, 14):
        v.append("doc_claims: matching claim wrongly flagged")
    mism = adc.violations_in("4 auditors + 18 testers", 5, 19, label="HANDOFF.md")
    if len(mism) != 1 or "HANDOFF.md:1" not in mism[0]:
        v.append(f"doc_claims: mismatch not reported correctly: {mism}")

    # 4. Line number is computed from the offset (2nd line -> line 2).
    two_line = "intro line\n5 auditors + 19 testers here"
    rep = adc.violations_in(two_line, 4, 14, label="d.md")
    if not rep or "d.md:2" not in rep[0]:
        v.append(f"doc_claims: wrong line number: {rep}")

    # 5. A stale claim WITH a valid frozen marker (resolvable sha, doc not in
    # NEVER_FREEZE) -> no violation. This is the whole point of the marker.
    frozen_ok = (
        "<!-- gate-frozen: commit=48ce16d -->\n"
        "# Report\n\n"
        "Gate at build time: 6 auditors + 40 testers.\n"
    )
    got = adc.violations_in(frozen_ok, 6, 42, label="COWORK_REPORT_x.md",
                            commit_exists=_yes)
    if got:
        v.append(f"doc_claims: valid frozen marker did not exempt stale claim: {got}")

    # 6. A stale claim WITHOUT a marker -> still one violation (today's
    # behaviour, unchanged by adding the marker feature).
    no_marker = "Gate at build time: 6 auditors + 40 testers.\n"
    unfrozen = adc.violations_in(no_marker, 6, 42, label="COWORK_REPORT_y.md",
                                 commit_exists=_yes)
    if len(unfrozen) != 1:
        v.append(f"doc_claims: unmarked stale claim not flagged: {unfrozen}")

    # 7. A marker with an unresolvable sha -> violation naming the file, and
    # the stale claim is NOT exempted (the marker didn't earn its keep).
    bad_sha = (
        "<!-- gate-frozen: commit=deadbee -->\n"
        "6 auditors + 40 testers.\n"
    )
    bad = adc.violations_in(bad_sha, 6, 42, label="COWORK_REPORT_z.md",
                            commit_exists=_no)
    if not any("COWORK_REPORT_z.md" in x and "not a commit" in x for x in bad):
        v.append(f"doc_claims: unresolvable frozen sha not caught: {bad}")
    if not any("COWORK_REPORT_z.md:2" in x for x in bad):
        v.append(f"doc_claims: unresolvable-sha doc's stale claim wrongly exempted: {bad}")

    # 7b. A marker missing 'commit=' entirely -> malformed, named as such.
    malformed = "<!-- gate-frozen: nonsense -->\n6 auditors + 40 testers.\n"
    mal = adc.violations_in(malformed, 6, 42, label="d.md", commit_exists=_yes)
    if not any("malformed" in x for x in mal):
        v.append(f"doc_claims: malformed marker not caught: {mal}")

    # 8. A marker in a never-freeze doc (e.g. docs/DECISIONS.md) -> violation,
    # and the doc's stale claim is still checked normally (not exempted).
    never = "<!-- gate-frozen: commit=48ce16d -->\n6 auditors + 40 testers.\n"
    nf = adc.violations_in(never, 6, 42, label="docs/DECISIONS.md",
                           commit_exists=_yes)
    if not any("not allowed" in x for x in nf):
        v.append(f"doc_claims: gate-frozen marker in a maintained doc not caught: {nf}")
    if not any("docs/DECISIONS.md:2" in x for x in nf):
        v.append(f"doc_claims: never-freeze doc's stale claim wrongly exempted: {nf}")

    # 9. git unavailable (resolver None): sha check skips, syntactically
    # present sha still earns the exemption -- mirrors auditor_uat_stamp.
    no_git = adc.violations_in(frozen_ok, 6, 42, label="COWORK_REPORT_w.md",
                               commit_exists=None)
    if no_git:
        v.append(f"doc_claims: absent git wrongly produced a violation: {no_git}")

    return v
