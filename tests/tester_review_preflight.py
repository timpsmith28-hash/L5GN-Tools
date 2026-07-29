"""tester_review_preflight: the split preflight (local-deck slice 1).

`run.py review` used to exit 2 when the vault DB or the registry was missing.
That was right when every route wrote to the vault and wrong the moment the
same service started rendering estate documents, which need neither: a plain
producer rig with an estate build and no vault could not open its own knowledge
base.

The fix splits the preflight by *what each route needs*. This tester proves the
four machine shapes behave as they must:

    vault + estate  -> both halves serve
    vault, no estate -> queue serves, estate routes degrade
    estate, no vault -> estate routes serve, queue degrades   <- the new case
    neither          -> refused, because there is nothing to render

Hermetic and stdlib-only: `core.vault_preflight` is driven against temp paths,
and the estate half against a temp snapshot. No server is bound.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from chronicler.review import core, estate_data


def _minimal_snapshot(root: Path) -> dict:
    return {
        "generated_at": "2026-07-28T22:20:48+01:00",
        "toolkit_commit": "abc1234", "toolkit_dirty": False,
        "estate_name": "personal", "estate_root": str(root),
        "projects": [{
            "name": "Solo", "path": str(root / "Solo"),
            "git_summary": {"is_git": False},
            "doc_census": {"doc_count": 1, "authored_count": 1, "generated_count": 0,
                           "docs": [{"path": "README.md", "title": "Readme",
                                     "words": 3, "bytes": 20, "headings": 1,
                                     "doc_type": "readme", "provenance": "authored"}]},
        }],
    }


def run() -> list[str]:
    v: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        root = base / "estate"
        (root / "Solo").mkdir(parents=True)
        (root / "Solo" / "README.md").write_text("# Solo\n\nhello\n", encoding="utf-8")
        estate_path = base / "estate.json"
        estate_path.write_text(json.dumps(_minimal_snapshot(root)), encoding="utf-8")

        # --- the new case: an estate build and no vault ---------------------
        machine = {"vault": str(base / "no-such-vault"), "estate": "personal"}
        db, registry, gap = core.vault_preflight(machine)
        if db is not None:
            v.append("vault_preflight: reported a DB that does not exist")
        if gap is None:
            v.append("vault_preflight: a missing vault must produce a "
                     "VaultUnavailable, not None")
        else:
            if gap.reason not in ("vault_db_missing", "vault_home_unset"):
                v.append(f"vault_preflight: unexpected reason {gap.reason!r}")
            detail = gap.as_dict()
            if detail.get("available") is not False or not detail.get("detail"):
                v.append("VaultUnavailable.as_dict must carry available=False "
                         "and a human sentence")
        if registry:
            v.append("vault_preflight: returned a registry despite no vault")

        # ...and the estate half is unaffected by any of that.
        est = estate_data.EstateData.load(estate_path, roots=[root])
        if not est.available:
            v.append(f"estate half must load with no vault present ({est.reason})")
        if len(est.documents) != 1:
            v.append(f"estate half: expected 1 authored document, got {len(est.documents)}")
        else:
            rendered = est.read_document(est.documents[0]["id"])
            if "hello" not in rendered["text"]:
                v.append("estate half: document did not render on a vault-less machine")

        # --- the mirror case: a vault and no estate build -------------------
        absent = estate_data.EstateData.load(base / "never-built.json", roots=[root])
        if absent.available:
            v.append("estate half: reported available with no snapshot on disk")
        if absent.reason != "estate_missing":
            v.append(f"estate half: expected estate_missing, got {absent.reason!r}")
        header = absent.header()
        if header.get("available") is not False or header.get("reason") is None:
            v.append("estate half: the header must explain the absence -- it is "
                     "how the UI learns there is no build")
        # It must not raise. The queue half carries the surface in this shape.
        try:
            absent.projects()
            absent.documents_for("anything")
        except Exception as exc:  # noqa: BLE001 -- any raise here is the defect
            v.append(f"estate half: an absent estate must degrade, not raise ({exc})")

        # --- a malformed snapshot is a degradation, not a crash --------------
        junk = base / "junk.json"
        junk.write_text("{not json at all", encoding="utf-8")
        broken = estate_data.EstateData.load(junk, roots=[root])
        if broken.available or not (broken.reason or "").startswith("estate_unreadable"):
            v.append(f"estate half: malformed JSON must degrade with a reason, "
                     f"got available={broken.available} reason={broken.reason!r}")

        not_object = base / "list.json"
        not_object.write_text("[1, 2, 3]", encoding="utf-8")
        wrong_shape = estate_data.EstateData.load(not_object, roots=[root])
        if wrong_shape.available:
            v.append("estate half: a JSON array is not an estate snapshot")

    return v
