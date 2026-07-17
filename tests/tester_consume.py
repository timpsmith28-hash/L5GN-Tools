"""consume: bundle ingest (manifest verify + history accumulation) and the
per-estate sweep wiring, with the vault scanners stubbed out."""
from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from l5gntools import consume
from l5gntools.scanners import project_trail, vault_reader


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _snapshot(name_hash: str, day: str) -> dict:
    return {"generated_at": f"{day}T09:00:00Z", "projects": [
        {"name": "AppA", "git_summary": {"is_git": True, "latest_hash": name_hash},
         "git_deep_history": {"commits": [{"hash": name_hash, "date": day, "subject": "x"}]},
         "doc_census": {"docs": []}},
        {"name": "AppB", "git_summary": {"is_git": False}, "doc_census": {"docs": []}},
    ]}


def _seed_landing(estates_dir: Path) -> None:
    personal = estates_dir / "personal"
    (personal / "history").mkdir(parents=True)
    # prior snapshot already accumulated on the knight
    (personal / "history" / "estate-2026-07-15.json").write_text(
        json.dumps(_snapshot("aaa111", "2026-07-15")), encoding="utf-8")
    # the freshly-landed bundle (newest)
    est = personal / "estate.json"
    est.write_text(json.dumps(_snapshot("bbb222", "2026-07-16")), encoding="utf-8")
    (personal / "deposit_manifest.json").write_text(
        json.dumps({"machine": "TestRig", "estate": "personal",
                    "files": {"estate.json": _sha256(est)}}), encoding="utf-8")


def run() -> list[str]:
    v: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        estates_dir = Path(td)
        _seed_landing(estates_dir)

        # ---- ingest_estate: verify + accumulate ----
        ing = consume.ingest_estate(estates_dir, "personal")
        if ing["status"] != "ingested":
            return v + [f"consume: ingest status {ing['status']!r}"]
        if ing["manifest_verified"] is not True:
            v.append(f"consume: manifest should verify, got {ing['manifest_verified']!r}")
        if ing["snapshot"] != "estate-2026-07-16.json":
            v.append(f"consume: wrong archived snapshot {ing['snapshot']!r}")
        hist = list((estates_dir / "personal" / "history").glob("estate-*.json"))
        if len(hist) != 2:
            v.append(f"consume: expected 2 accumulated snapshots, got {len(hist)}")

        # idempotency: re-ingesting the same generated-date adds no new snapshot.
        again = consume.ingest_estate(estates_dir, "personal")
        if again["new_snapshot"] is not False:
            v.append("consume: re-ingesting the same day should report new_snapshot False")
        if len(list((estates_dir / "personal" / "history").glob("estate-*.json"))) != 2:
            v.append("consume: idempotent re-ingest should not accumulate a duplicate snapshot")

        # tampered manifest -> verified False
        (estates_dir / "personal" / "deposit_manifest.json").write_text(
            json.dumps({"machine": "TestRig", "files": {"estate.json": "deadbeef"}}),
            encoding="utf-8")
        if consume.ingest_estate(estates_dir, "personal")["manifest_verified"] is not False:
            v.append("consume: tampered manifest should fail verification")

        # ---- manifest_verified None: no manifest, or manifest without the file hash ----
        with tempfile.TemporaryDirectory() as td2:
            ed2 = Path(td2)
            # (a) landed bundle with NO manifest at all -> verified None (unknown, not False).
            noman = ed2 / "personal"
            noman.mkdir(parents=True)
            (noman / "estate.json").write_text(
                json.dumps({"generated_at": "2026-07-16T09:00:00Z", "projects": []}),
                encoding="utf-8")
            r = consume.ingest_estate(ed2, "personal")
            if r["status"] != "ingested" or r["manifest_verified"] is not None:
                v.append(f"consume: missing manifest should give verified None, got {r.get('manifest_verified')!r}")
            if r["machine"] is not None:
                v.append("consume: machine should be None when no manifest is present")

            # (b) manifest present but carrying no estate.json hash -> verified None.
            (noman / "deposit_manifest.json").write_text(
                json.dumps({"machine": "Rig", "files": {}}), encoding="utf-8")
            r2 = consume.ingest_estate(ed2, "personal")
            if r2["manifest_verified"] is not None:
                v.append("consume: a manifest lacking the estate.json hash should verify None")
            if r2["machine"] != "Rig":
                v.append("consume: machine name should be read from the manifest even when hash absent")

            # no_bundle: an estate dir with no estate.json is reported, not crashed.
            (ed2 / "work").mkdir()
            nb = consume.ingest_estate(ed2, "work")
            if nb["status"] != "no_bundle":
                v.append(f"consume: empty estate dir should report no_bundle, got {nb['status']!r}")

            # _present_names unions project names across every estate.
            (ed2 / "work" / "estate.json").write_text(
                json.dumps({"projects": [{"name": "WorkOnly"}, {"name": "Shared"}]}),
                encoding="utf-8")
            (noman / "estate.json").write_text(
                json.dumps({"projects": [{"name": "PersonalOnly"}, {"name": "Shared"},
                                         {"name": None}]}),
                encoding="utf-8")
            names = consume._present_names(ed2, ["personal", "work"])
            if names != {"WorkOnly", "Shared", "PersonalOnly"}:
                v.append(f"consume: _present_names should union non-null names across estates, got {names}")

        # ---- sweep: stub the vault scanners, assert per-estate reports ----
        orig_vr, orig_pt = vault_reader.scan_estate, project_trail.scan_estate
        vault_reader.scan_estate = lambda projects: {"status": "ok", "totals": {}}
        project_trail.scan_estate = lambda projects: {"status": "ok", "projects": [
            {"estate_project": "AppA", "estate": "L5GN", "thread_count": 2,
             "substantive_count": 1, "latest_activity": "2026-07-16", "present_in_estate": None},
            {"estate_project": "Ghost", "estate": "L5GN", "thread_count": 3,
             "substantive_count": 2, "latest_activity": "2026-07-16", "present_in_estate": None},
        ]}
        try:
            res = consume.sweep(estates_dir)
        finally:
            vault_reader.scan_estate, project_trail.scan_estate = orig_vr, orig_pt

        if res["vault_status"] != "ok":
            v.append(f"consume: sweep vault_status {res['vault_status']!r}")
        if "personal" not in res["estates"]:
            return v + ["consume: sweep produced no personal estate result"]
        pe = res["estates"]["personal"]
        if pe["estate_diff"] != "ok":
            v.append(f"consume: estate_diff should be ok over 2 snapshots, got {pe['estate_diff']!r}")
        for rpt in ("estate_diff.json", "drift.json"):
            if not (estates_dir / "personal" / "reports" / rpt).exists():
                v.append(f"consume: missing per-estate report {rpt}")
        if not (estates_dir / "_shared" / "project_trail.json").exists():
            v.append("consume: missing shared project_trail.json")
        # 'Ghost' is discussed but present in no estate -> completeness gap fires.
        dr = json.loads((estates_dir / "personal" / "reports" / "drift.json").read_text())
        if "Ghost" not in {x["project"] for x in dr["alerts"]["discussed_not_present"]}:
            v.append("consume: Ghost should surface as discussed_not_present")
    return v
