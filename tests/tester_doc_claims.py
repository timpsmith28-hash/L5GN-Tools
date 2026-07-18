"""tester_doc_claims: the doc-claims auditor's matcher and violation logic.

Hermetic and order-independent: exercises the pure `find_claims` / `violations_in`
helpers on synthetic text rather than the live repo docs (whose real counts move
as auditors/testers are added). The two load-bearing behaviours are:

  * a compound "N auditors + M testers" claim is detected and diffed, and
  * a *narrative* mention of a past count ("...once claimed 18 testers when
    verify.py had 14") is NOT matched -- the auditor must never flag history.
"""
from __future__ import annotations

from auditors import auditor_doc_claims as adc


def run() -> list[str]:
    v: list[str] = []

    # 1. Compound present-tense claim is detected, both variants.
    if adc.find_claims("gate is green (4 auditors + 18 hermetic testers).") != [(4, 18, 15)]:
        v.append("doc_claims: failed to detect 'N auditors + M hermetic testers'")
    plain = adc.find_claims("registers **4 auditors + 14 testers**, all hermetic")
    if [(a, t) for a, t, _ in plain] != [(4, 14)]:
        v.append("doc_claims: failed to detect plain 'N auditors + M testers'")

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

    return v
