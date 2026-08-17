"""DECISIONS 0044 clause 2's second, independent proof: data/knowledge_
curator/ must never reach a built deposit outbox. build_bundle's own
EXCLUDED_FROM_DEPOSIT check (l5gntools/deposit.py) states the rule; this
auditor proves it holds -- not just that today's fixed two-file whitelist
happens not to include it, but that a bundle built against a data_dir that
DOES carry data/knowledge_curator/ content still comes out clean.

Dynamic, not AST-walking like auditor_readonly/auditor_stdlib -- it
actually builds a bundle against a seeded temporary data_dir and inspects
the real outbox on disk, because the property being proved ("nothing under
data/knowledge_curator/ ever reaches the outbox") is a runtime property of
build_bundle's output, not a static shape of its source.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from l5gntools import deposit


def run() -> list[str]:
    v: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        data_dir = Path(tmp)

        # The two files build_bundle actually requires/uses.
        (data_dir / "estate.json").write_text(
            json.dumps({"generated_at": "2026-01-01T00:00:00Z"}), encoding="utf-8")
        history_dir = data_dir / "history"
        history_dir.mkdir(parents=True, exist_ok=True)
        (history_dir / "estate-2026-01-01.json").write_text("{}", encoding="utf-8")

        # The leak this auditor exists to catch: real Curator output,
        # seeded directly on disk exactly where a future build_bundle
        # might be tempted to walk from.
        leak_dir = data_dir / "knowledge_curator"
        leak_dir.mkdir(parents=True, exist_ok=True)
        (leak_dir / "report_2026-08-17.md").write_text(
            "quoted source span that must never travel", encoding="utf-8")

        try:
            bundle = deposit.build_bundle("personal", data_dir=data_dir, force=True)
        except RuntimeError as exc:
            v.append(f"auditor_deposit_exclusion: build_bundle refused a "
                     f"legitimate deposit (estate.json + history only were "
                     f"declared) -- {exc}")
            return v

        outbox = bundle["outbox"]
        if not outbox.is_dir():
            v.append("auditor_deposit_exclusion: build_bundle produced no outbox "
                     "to inspect")
            return v

        for path in outbox.rglob("*"):
            if path.is_file():
                rel = path.relative_to(outbox)
                if "knowledge_curator" in rel.parts:
                    v.append(f"auditor_deposit_exclusion: outbox carries "
                             f"{rel} -- data/knowledge_curator/ reached a "
                             f"deposit (DECISIONS 0044 clause 1 violated)")

        if not any(deposit.EXCLUDED_FROM_DEPOSIT):
            v.append("auditor_deposit_exclusion: EXCLUDED_FROM_DEPOSIT is "
                     "empty -- the rule this auditor proves has nothing "
                     "declared to prove")

    return v
