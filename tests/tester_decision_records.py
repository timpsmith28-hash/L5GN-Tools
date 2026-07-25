"""tester_decision_records -- the scanner sees DECISIONS.md and Open-questions
sections (governance Task B + scanner_bugfixes Task C).

* `DECISIONS.md` is counted by *entry* and *tier*, in both status vocabularies
  (CONFIRMED/ASSUMED/PENDING and the trinity's accepted/superseded).
* `adr/NNNN-*.md` still counts as before.
* A project with neither reports zero without error.
* An `## Open questions` section anywhere contributes to the PENDING tier.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from l5gntools.scanners.todo_adr_scanner import (parse_decisions,
                                                 parse_open_questions, scan)

_DECISIONS = """# DECISIONS

## 0001 - alpha
**Date:** 2026-01-01 · **Status:** accepted · **Source:** x
body

## 0002 - beta
**Status:** superseded by 0003
body

## 0003 - gamma
**Status:** CONFIRMED
body

## 0004 - delta
Status: PENDING
body
"""


def run() -> list[str]:
    v: list[str] = []

    count, tiers = parse_decisions(_DECISIONS)
    if count != 4:
        v.append(f"parse_decisions: expected 4 entries, got {count}")
    for tier in ("accepted", "superseded", "CONFIRMED", "PENDING"):
        if tiers.get(tier) != 1:
            v.append(f"parse_decisions: tier {tier} should be 1 -> {tiers}")

    s, items = parse_open_questions(
        "## Open questions\n- four-eyes vs typed phrase\n- persist the gate?\n"
        "## Next section\n- unrelated\n")
    if s != 1 or items != 2:
        v.append(f"parse_open_questions: expected (1,2), got {(s, items)}")

    with tempfile.TemporaryDirectory() as td:
        # project WITH a DECISIONS.md, an adr/ file, and an Open-questions doc
        proj = Path(td) / "HasRecords"
        (proj / "docs" / "adr").mkdir(parents=True)
        (proj / "docs" / "DECISIONS.md").write_text(_DECISIONS, encoding="utf-8")
        (proj / "docs" / "adr" / "0001-init.md").write_text(
            "# init\n**Status:** accepted\n", encoding="utf-8")
        (proj / "docs" / "design.md").write_text(
            "# design\n## Open questions\n- rollback story\n", encoding="utf-8")
        out = scan(proj)
        if out["decisions_count"] != 4:
            v.append(f"scan: decisions_count should be 4 -> {out['decisions_count']}")
        if out["adr_count"] != 1:
            v.append(f"scan: adr_count should be 1 (unchanged convention) -> {out['adr_count']}")
        # 1 PENDING from DECISIONS + 1 open-question item = 2
        if out["decision_tiers"].get("PENDING") != 2:
            v.append(f"scan: PENDING should include the open-question item -> "
                     f"{out['decision_tiers']}")
        if out["open_questions"]["items"] != 1:
            v.append(f"scan: open_questions items -> {out['open_questions']}")

        # project with NEITHER -> zeros, no error
        bare = Path(td) / "Bare"
        (bare / "src").mkdir(parents=True)
        (bare / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")
        b = scan(bare)
        if b["decisions_count"] != 0 or b["adr_count"] != 0 or b["decision_tiers"]:
            v.append(f"scan: bare project should report zero decisions -> "
                     f"{b['decisions_count']}/{b['adr_count']}/{b['decision_tiers']}")
    return v
