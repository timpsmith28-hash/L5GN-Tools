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
    "auditors.auditor_architecture_current",
    "auditors.auditor_cli_contract",
    "auditors.auditor_conversation_map_pin",
    "auditors.auditor_dependency_direction",
    "auditors.auditor_deposit_exclusion",
    "auditors.auditor_doc_claims",
    "auditors.auditor_module_contract",
    "auditors.auditor_readonly",
    "auditors.auditor_stdlib",
    "auditors.auditor_tool_contract",
    "auditors.auditor_uat_sheet_readable",
    "auditors.auditor_uat_stamp",
]
 
TESTERS: list[str] = [
    "tests.tester_common",
    "tests.tester_architecture_census",
    "tests.tester_architecture_current",
    "tests.tester_scanners",
    "tests.tester_scanner_scope",
    "tests.tester_report_selfcheck",
    "tests.tester_governance_scope",
    "tests.tester_decision_records",
    "tests.tester_env_tracked",
    "tests.tester_dupe_labels",
    "tests.tester_zero_commit_note",
    "tests.tester_blast_radius",
    "tests.tester_blast_uncommitted",
    "tests.tester_file_census",
    "tests.tester_doc_census",
    "tests.tester_census",
    "tests.tester_contract",
    "tests.tester_config",
    "tests.tester_project_root",
    "tests.tester_vault_reader",
    "tests.tester_project_trail",
    "tests.tester_estate_diff",
    "tests.tester_estate_data",
    "tests.tester_review_preflight",
    "tests.tester_drift",
    "tests.tester_authors",
    "tests.tester_deposit",
    "tests.tester_consume",
    "tests.tester_intake",
    "tests.tester_set_substantive",
    "tests.tester_md_transcript",
    "tests.tester_local_transcripts",
    "tests.tester_bootstrap_conversation_map",
    "tests.tester_knowledge_index",
    "tests.tester_extract_claims",
    "tests.tester_corpus_index",
    "tests.tester_match_claims",
    "tests.tester_compile_report",
    "tests.tester_ingest_local_transcripts",
    "tests.tester_coherence_check",
    "tests.tester_doc_claims",
    "tests.tester_uat_stamp",
    "tests.tester_dbsafe",
    "tests.tester_build_registry",
    "tests.tester_build_inventory",
    "tests.tester_build_activity",
    "tests.tester_xref_filenames",
    "tests.tester_extract_path_mentions",
    "tests.tester_registry_tiers",
    "tests.tester_backup",
    "tests.tester_serve",
    "tests.tester_relink_stage",
    "tests.tester_relink_scoring",
    "tests.tester_relink_apply",
    "tests.tester_backfill_candidate_project",
    "tests.tester_deck_migration",
    "tests.tester_registry_path",
    "tests.tester_finalize_db",
    "tests.tester_first_seen",
    "tests.tester_scrape_stage",
    "tests.tester_review",
    "tests.tester_docs_board",
    "tests.tester_module_registry",
    "tests.tester_uat_sidebar",
    "tests.tester_curator_data",
    "tests.tester_curator_ratify",
    "tests.tester_curator_control",
    "tests.tester_curator_findings",
    "tests.tester_governor",
    "tests.tester_planner",
    "tests.tester_ledger",
    "tests.tester_bench_ledger",
    "tests.tester_bench_failures",
    "tests.tester_bench_load_cost",
    "tests.tester_bench_report",
    "tests.tester_conductor_panel",
    "tests.tester_candidates",
    "tests.tester_conductor_run",
    "tests.tester_run_banner",
    "tests.tester_pin",
    "tests.tester_conversation_map_pin",
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
