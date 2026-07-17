"""intake: classification of export zips and the process() drop-zone unpacker.

Hermetic & in-process: the chronicler pipeline is vendored under
``chronicler/pipeline`` and imports ``from db import CHRONICLER_ROOT`` at module
load, so we add that dir to sys.path, import ``intake`` directly, and redirect
its extraction targets into a temp dir. No env, no network, no real vault."""
from __future__ import annotations

import sys
import tempfile
import zipfile
from pathlib import Path

_PIPELINE = Path(__file__).resolve().parent.parent / "chronicler" / "pipeline"


def _zip(path: Path, entries: dict[str, str]) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for name, body in entries.items():
            zf.writestr(name, body)


def run() -> list[str]:
    v: list[str] = []
    if str(_PIPELINE) not in sys.path:
        sys.path.insert(0, str(_PIPELINE))
    import intake  # noqa: E402 -- deferred so sys.path is primed first

    # ---- classify() across every recognised shape and the unknown fallback ----
    if intake.classify(["Takeout/", "Takeout/My Activity/Gemini/MyActivity.json"]) != "gemini_takeout":
        v.append("intake: a Takeout/ tree should classify as gemini_takeout")
    if intake.classify(["conversations.json", "users.json"]) != "claude":
        v.append("intake: conversations.json should classify as claude")
    if intake.classify(["some/nested/users.json"]) != "claude":
        v.append("intake: a nested users.json should still classify as claude")
    if intake.classify(["projects/proj-a.json", "projects/proj-b.json"]) != "claude":
        v.append("intake: a projects-only export should classify as claude")
    if intake.classify(["README.txt", "notes/misc.csv"]) is not None:
        v.append("intake: an unrecognised zip should classify as None")
    # gemini_takeout takes precedence when both markers are present.
    if intake.classify(["Takeout/x", "conversations.json"]) != "gemini_takeout":
        v.append("intake: Takeout marker should win over a claude marker")

    orig_claude, orig_gemini = intake.RAW_CLAUDE, intake.RAW_GEMINI
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        intake.RAW_CLAUDE = base / "raw_claude_files"
        intake.RAW_GEMINI = base / "raw_gemini_files"
        try:
            dz = base / "dropzone"
            dz.mkdir()
            _zip(dz / "claude_export.zip", {"conversations.json": "[]", "users.json": "{}"})
            _zip(dz / "takeout.zip", {"Takeout/Gemini/MyActivity.json": "[]"})
            _zip(dz / "mystery.zip", {"random.txt": "nope"})
            # A file that is not a real zip -> BadZipFile path.
            (dz / "broken.zip").write_text("this is not a zip", encoding="utf-8")

            # ---- dry-run: classify only, extract & archive NOTHING ----
            dry = intake.process(dz, dry_run=True)
            kinds = {r["zip"]: r["kind"] for r in dry}
            if kinds.get("claude_export.zip") != "claude":
                v.append(f"intake: dry-run should classify claude, got {kinds.get('claude_export.zip')!r}")
            if kinds.get("takeout.zip") != "gemini_takeout":
                v.append("intake: dry-run should classify takeout")
            if kinds.get("mystery.zip") != "unknown":
                v.append("intake: dry-run should mark unrecognised zip unknown")
            if kinds.get("broken.zip") != "bad_zip":
                v.append("intake: a corrupt zip should be reported as bad_zip, not crash")
            if intake.RAW_CLAUDE.exists() or intake.RAW_GEMINI.exists():
                v.append("intake: --dry-run must not create extraction targets")
            if any(r.get("archived_to") for r in dry):
                v.append("intake: --dry-run must not archive anything")
            # every zip still sits at the top of the drop zone.
            if len(list(dz.glob("*.zip"))) != 4:
                v.append("intake: --dry-run must not move any zip out of the drop zone")

            # ---- real run: extract into targets, move recognised zips to archive ----
            res = intake.process(dz, dry_run=False)
            byzip = {r["zip"]: r for r in res}
            if not (intake.RAW_CLAUDE / "conversations.json").exists():
                v.append("intake: claude export contents should extract into RAW_CLAUDE")
            if not (intake.RAW_GEMINI / "Takeout" / "Gemini" / "MyActivity.json").exists():
                v.append("intake: takeout tree should extract into RAW_GEMINI")
            # recognised zips moved (not copied) under archive/<source>/.
            if (dz / "claude_export.zip").exists():
                v.append("intake: a processed claude zip should be MOVED out of the drop zone")
            archived = list((dz / "archive").rglob("*.zip"))
            arch_names = {p.parent.name for p in archived}
            if not any(p.name.endswith("claude_export.zip") for p in archived):
                v.append("intake: claude zip should land under archive/")
            if not {"claude", "gemini"} <= arch_names:
                v.append(f"intake: archive should be namespaced by source, got {arch_names}")
            if "archived_to" not in byzip.get("takeout.zip", {}):
                v.append("intake: a processed zip result should record archived_to")
            # unrecognised + corrupt zips are LEFT in place (never archived/extracted).
            if not (dz / "mystery.zip").exists() or not (dz / "broken.zip").exists():
                v.append("intake: unknown/corrupt zips should be left untouched in the drop zone")
            if byzip.get("mystery.zip", {}).get("kind") != "unknown":
                v.append("intake: unknown zip should be reported unknown on the real run too")

            # ---- non-existent drop zone -> empty result, no crash ----
            if intake.process(base / "no_such_dir") != []:
                v.append("intake: a missing drop zone should yield an empty result list")
        finally:
            intake.RAW_CLAUDE, intake.RAW_GEMINI = orig_claude, orig_gemini
    return v
