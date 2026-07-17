"""project_trail: assert per-project trail shape, ordering, and confidence rank
against a temp frozen-shaped vault (reusing tester_vault_reader's builder).

Hermetic: patches the shared vault-path resolver so it never reads this
machine's configured vault."""
from __future__ import annotations

import tempfile
from pathlib import Path

from l5gntools.scanners import project_trail, vault_reader
from .tester_vault_reader import _make_vault


def run() -> list[str]:
    v: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "chronicler.db"
        _make_vault(db, user_version=1)

        orig = vault_reader._resolve_vault_path
        vault_reader._resolve_vault_path = lambda: db
        try:
            out = project_trail.scan_estate([])
        finally:
            vault_reader._resolve_vault_path = orig

        if out.get("status") != "ok":
            return [f"project_trail: expected ok, got {out.get('status')!r}"]
        repo = {p["estate_project"]: p for p in out["projects"]}
        if "smelt-gateway" not in repo:
            return ["project_trail: smelt-gateway not surfaced"]
        sg = repo["smelt-gateway"]
        if sg["thread_count"] != 2 or sg["substantive_count"] != 2:
            v.append(f"project_trail: bad counts {sg['thread_count']}/{sg['substantive_count']}")
        if sg["estate"] != "L5GN":
            v.append(f"project_trail: estate wrong {sg['estate']!r}")
        # Both substantive -> newest-first: t2 (2026-07-11) ahead of t1 (2026-07-10).
        order = [t["thread_id"] for t in sg["trail"]]
        if order != ["t2", "t1"]:
            v.append(f"project_trail: trail order wrong {order}")
        # Confidence rank carried: t2 manual(4) > t1 evidence(2).
        ranks = {t["thread_id"]: t["confidence_rank"] for t in sg["trail"]}
        if ranks.get("t2") != 4 or ranks.get("t1") != 2:
            v.append(f"project_trail: confidence ranks wrong {ranks}")
        if sg["dominant_signal"] != "path_mention":
            v.append(f"project_trail: dominant_signal wrong {sg['dominant_signal']!r}")
        # Account wall carried at thread level.
        accts = {t["account"] for t in sg["trail"]}
        if accts != {"gemini-personal", "gemini-work"}:
            v.append(f"project_trail: account wall not carried {accts}")
    return v
