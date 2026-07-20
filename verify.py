"""verify.py -- the gate. Runs every auditor then every tester and returns a
single exit code (0 == green). The pre-commit hook runs this and refuses red
commits, so the disciplined path is the only path into the trunk.

Borrowed from Citadel v5 (CID). Register each new auditor/tester below.

Usage:
    python verify.py
"""
from __future__ import annotations

import importlib
import sys

AUDITORS: list[str] = [
    "auditors.auditor_cli_contract",
    "auditors.auditor_doc_claims",
    "auditors.auditor_readonly",
    "auditors.auditor_stdlib",
    "auditors.auditor_tool_contract",
]

TESTERS: list[str] = [
    "tests.tester_common",
    "tests.tester_scanners",
    "tests.tester_contract",
    "tests.tester_config",
    "tests.tester_vault_reader",
    "tests.tester_project_trail",
    "tests.tester_estate_diff",
    "tests.tester_drift",
    "tests.tester_authors",
    "tests.tester_deposit",
    "tests.tester_consume",
    "tests.tester_intake",
    "tests.tester_set_substantive",
    "tests.tester_md_transcript",
    "tests.tester_doc_claims",
    "tests.tester_dbsafe",
    "tests.tester_build_registry",
    "tests.tester_registry_tiers",
    "tests.tester_backup",
    "tests.tester_serve",
    "tests.tester_relink_stage",
    "tests.tester_scrape_stage",
    "tests.tester_review",
]


def _run_group(module_names: list[str]) -> int:
    found = 0
    for name in module_names:
        module = importlib.import_module(name)
        short = name.rsplit(".", 1)[-1]
        try:
            violations = module.run()
        except Exception as exc:  # noqa: BLE001 -- a crashing gate is a red gate
            found += 1
            print(f"[FAIL] {short}: gate raised {type(exc).__name__}: {exc}")
            continue
        if violations:
            found += len(violations)
            print(f"[FAIL] {short}: {len(violations)} issue(s)")
            for item in violations:
                print(f"         - {item}")
        else:
            print(f"[ OK ] {short}")
    return found


def main() -> int:
    print("== auditors ==")
    total = _run_group(AUDITORS)
    print("== testers ==")
    total += _run_group(TESTERS)
    print()
    if total:
        print(f"verify: RED ({total} issue(s)) -- commit refused.")
        return 1
    print("verify: GREEN -- all gates passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
