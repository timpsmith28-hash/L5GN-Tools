"""deposit: bundle packaging, manifest integrity, and the namespace guard."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from l5gntools import deposit


def _seed(data_dir: Path) -> None:
    (data_dir / "history").mkdir(parents=True)
    (data_dir / "estate.json").write_text(
        json.dumps({"generated_at": "2026-07-17T09:00:00+01:00", "projects": []}),
        encoding="utf-8")
    (data_dir / "history" / "estate-2026-07-17.json").write_text(
        json.dumps({"generated_at": "2026-07-17T09:00:00+01:00"}), encoding="utf-8")


def run() -> list[str]:
    v: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        data_dir = Path(td)
        _seed(data_dir)

        # Happy path: a named estate bundles cleanly into its own namespace.
        b = deposit.build_bundle("personal", data_dir=data_dir)
        outbox = b["outbox"]
        if outbox.name != "personal" or outbox.parent.name != "outbox":
            v.append(f"deposit: outbox not namespaced by estate: {outbox}")
        if not (outbox / "estate.json").exists():
            v.append("deposit: estate.json not staged")
        if not (outbox / "history" / "estate-2026-07-17.json").exists():
            v.append("deposit: history snapshot not staged")

        man_path = outbox / "deposit_manifest.json"
        if not man_path.exists():
            return v + ["deposit: manifest not written"]
        man = json.loads(man_path.read_text(encoding="utf-8"))
        if man["estate"] != "personal":
            v.append(f"deposit: manifest estate wrong {man['estate']!r}")
        if "estate.json" not in man["files"] or len(man["files"]["estate.json"]) != 64:
            v.append("deposit: manifest missing a valid sha256 for estate.json")
        if man.get("estate_generated_at") != "2026-07-17T09:00:00+01:00":
            v.append("deposit: manifest did not carry estate generated_at")

        # Namespace guard: 'unknown' is refused without force, allowed with it.
        try:
            deposit.build_bundle("unknown", data_dir=data_dir)
            v.append("deposit: 'unknown' estate should have been refused")
        except ValueError:
            pass
        try:
            deposit.build_bundle(None, data_dir=data_dir, force=True)
        except ValueError:
            v.append("deposit: force=True should allow an 'unknown' estate")

        # rsync keeps the namespace on both ends.
        cmd = deposit.push_command(outbox, "l5gn-castle:/vault/estates", "personal", "rsync")
        if cmd[0] != "rsync" or cmd[-1] != "l5gn-castle:/vault/estates/personal/":
            v.append(f"deposit: rsync destination not namespaced: {cmd}")

        # scp copies the estate-named dir into the target (namespace via dir name).
        scmd = deposit.push_command(outbox, "l5gn-castle:/vault/estates", "personal", "scp")
        if scmd[0] != "scp" or scmd[-1] != "l5gn-castle:/vault/estates/" or str(outbox) not in scmd:
            v.append(f"deposit: scp command wrong: {scmd}")

        # Missing estate.json is a clear error, not a silent empty bundle.
        empty = Path(td) / "empty"
        empty.mkdir()
        try:
            deposit.build_bundle("personal", data_dir=empty)
            v.append("deposit: missing estate.json should raise")
        except FileNotFoundError:
            pass
    return v
