"""consume -- the knight's receiving end: ingest deposited estate bundles and run
the interpret sweep over them, per estate, walled.

A *writer* (like deposit), outside the read-only scanner contract. It:
  1. ingests each landed bundle (estates_dir/<estate>/estate.json), verifying the
     deposit manifest's sha256 and promoting the snapshot into that estate's own
     accumulating history/ -- so estate_diff has a growing trail to compare, even
     though a rig only ever sends its latest.
  2. runs the interpret layer once against the shared vault (vault_reader,
     project_trail) and once per estate for the build-vs-discuss reconciliation
     (estate_diff over that estate's history, then drift).

Presence for drift is judged from the UNION of every estate's deposited project
list -- so "discussed_not_present" means "discussed in chat but not built in ANY
estate the knight holds", the true estate-completeness gap.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from .common import now_iso
from .scanners import drift, estate_diff, project_trail, vault_reader


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _estate_dirs(estates_dir: Path) -> list[str]:
    if not estates_dir.exists():
        return []
    return sorted(d.name for d in estates_dir.iterdir()
                  if d.is_dir() and not d.name.startswith("_"))


def ingest_estate(estates_dir: Path, estate: str) -> dict:
    """Verify the landed bundle and archive its estate.json into the estate's
    accumulating history/. Idempotent per generated-date."""
    landing = estates_dir / estate
    estate_json = landing / "estate.json"
    if not estate_json.exists():
        return {"estate": estate, "status": "no_bundle",
                "note": f"no estate.json under {landing}"}

    manifest_verified = None
    machine = None
    manifest_path = landing / "deposit_manifest.json"
    if manifest_path.exists():
        try:
            man = json.loads(manifest_path.read_text(encoding="utf-8"))
            machine = man.get("machine")
            want = (man.get("files") or {}).get("estate.json")
            manifest_verified = (want == _sha256(estate_json)) if want else None
        except (ValueError, OSError):
            manifest_verified = False

    try:
        meta = json.loads(estate_json.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        return {"estate": estate, "status": "error", "error": str(exc)}

    day = (meta.get("generated_at") or now_iso())[:10]
    history = landing / "history"
    history.mkdir(parents=True, exist_ok=True)
    dest = history / f"estate-{day}.json"
    is_new = not dest.exists()
    shutil.copy2(estate_json, dest)

    return {"estate": estate, "status": "ingested", "machine": machine,
            "manifest_verified": manifest_verified, "snapshot": dest.name,
            "new_snapshot": is_new,
            "projects": len(meta.get("projects", []))}


def _present_names(estates_dir: Path, estates: list[str]) -> set:
    """Union of project names across every estate's deposited estate.json."""
    names: set = set()
    for estate in estates:
        est = estates_dir / estate / "estate.json"
        if est.exists():
            try:
                meta = json.loads(est.read_text(encoding="utf-8"))
                names |= {p.get("name") for p in meta.get("projects", []) if p.get("name")}
            except (ValueError, OSError):
                pass
    return names


def sweep(estates_dir: Path) -> dict:
    """Ingest all deposited estates, then run the interpret sweep, walled."""
    estates_dir = Path(estates_dir)
    estates = _estate_dirs(estates_dir)

    ingests = {e: ingest_estate(estates_dir, e) for e in estates}
    present = _present_names(estates_dir, estates)

    # Shared vault interpretation (one DB, account-walled internally).
    vr = vault_reader.scan_estate([])
    pt = project_trail.scan_estate([])
    _write(estates_dir / "_shared" / "vault_reader.json", vr)
    _write(estates_dir / "_shared" / "project_trail.json", pt)

    out: dict = {"estates_dir": str(estates_dir), "vault_status": vr.get("status"),
                 "estates": {}}
    for estate in estates:
        ed = estate_diff.diff_history(estates_dir / estate / "history")
        if pt.get("status") == "ok":
            dr = drift._compute(pt, ed if ed.get("status") == "ok" else None,
                                present_names=present)
        else:
            dr = {"status": "needs_inputs", "project_trail_status": pt.get("status")}
        reports = estates_dir / estate / "reports"
        _write(reports / "estate_diff.json", ed)
        _write(reports / "drift.json", dr)
        out["estates"][estate] = {
            "ingest": ingests[estate],
            "estate_diff": ed.get("status"),
            "drift": dr.get("summary") if dr.get("status") == "ok" else dr.get("status"),
        }
    return out
