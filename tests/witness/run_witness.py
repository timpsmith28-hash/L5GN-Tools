"""CLI entry point: run one witness suite and write its `data/witness/<sheet>.json`
artefact. Not part of `verify.py` -- run by hand or by whatever schedules the
witness (COWORK_BRIEF_ui_witness.md Task 5: "the Shadow schedules the
witness, the witness runs where a surface can run").

Usage:
    python -m tests.witness.run_witness uat_sidebar
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

SUITES = {
    "uat_sidebar": "tests.witness.witness_uat_sidebar",
}


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in SUITES:
        names = ", ".join(sorted(SUITES))
        print(f"usage: python -m tests.witness.run_witness <suite>\n"
              f"  available suites: {names}", file=sys.stderr)
        return 2
    import importlib
    mod = importlib.import_module(SUITES[argv[1]])
    result = mod.run()
    out = result.write(REPO_ROOT)
    print(f"wrote {out.relative_to(REPO_ROOT)}")
    for obs in result.items:
        print(f"  [{obs.outcome:>8}] {obs.id}: {obs.detail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
