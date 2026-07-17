"""intake.py -- drop-zone unpacker for chat-log export zips.

Drop Claude / Google-Takeout export zips into the drop zone and this classifies
each, extracts it into the raw_* input dir the normalizers expect, then archives
the zip (moved, not copied, so the drop zone always shows "not yet processed").
Stdlib-only. Runs standalone or as the first step of ``run.py ingest``.

Layout (all under CHRONICLER_ROOT/chat_threads, honouring CHRONICLER_HOME):
    zip_downloads/            <- drop zips here
    zip_downloads/archive/<source>/<ts>__<name>.zip   <- processed zips
    raw_claude_files/         <- Claude export extracted here
    raw_gemini_files/         <- Takeout tree extracted here

Usage:
    python3 pipeline/intake.py                 # process the default drop zone
    python3 pipeline/intake.py --dropzone DIR  # a different drop zone
    python3 pipeline/intake.py --dry-run       # classify only, extract nothing
"""
from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from db import CHRONICLER_ROOT

CHAT = CHRONICLER_ROOT / "chat_threads"
DEFAULT_DROPZONE = CHAT / "zip_downloads"
RAW_CLAUDE = CHAT / "raw_claude_files"
RAW_GEMINI = CHAT / "raw_gemini_files"


def classify(names: list[str]) -> str | None:
    """Identify an export zip from its entry names. Returns 'claude',
    'gemini_takeout', or None (unknown -> left untouched)."""
    lower = [n.lower() for n in names]
    if any(n.startswith("takeout/") for n in lower):
        return "gemini_takeout"
    if any(Path(n).name in ("conversations.json", "users.json") for n in lower):
        return "claude"
    if any(n.startswith("projects/") and n.endswith(".json") for n in lower):
        return "claude"
    return None


def _archive(zip_path: Path, dropzone: Path, source: str) -> Path:
    dest_dir = dropzone / "archive" / source
    dest_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")
    dest = dest_dir / f"{ts}__{zip_path.name}"
    shutil.move(str(zip_path), str(dest))
    return dest


def process(dropzone: Path = DEFAULT_DROPZONE, dry_run: bool = False) -> list[dict]:
    results: list[dict] = []
    if not dropzone.exists():
        return results
    # Only top-level zips; never re-touch anything already under archive/.
    for zip_path in sorted(dropzone.glob("*.zip")):
        try:
            with zipfile.ZipFile(zip_path) as zf:
                names = zf.namelist()
                kind = classify(names)
                if kind is None:
                    results.append({"zip": zip_path.name, "kind": "unknown",
                                    "action": "skipped (unrecognised)"})
                    continue
                target = RAW_CLAUDE if kind == "claude" else RAW_GEMINI
                if not dry_run:
                    target.mkdir(parents=True, exist_ok=True)
                    zf.extractall(target)
        except zipfile.BadZipFile:
            results.append({"zip": zip_path.name, "kind": "bad_zip", "action": "skipped"})
            continue

        rec = {"zip": zip_path.name, "kind": kind,
               "extracted_to": target.name, "entries": len(names)}
        if not dry_run:
            source = "claude" if kind == "claude" else "gemini"
            rec["archived_to"] = str(_archive(zip_path, dropzone, source)
                                     .relative_to(dropzone))
        results.append(rec)
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dropzone", type=Path, default=DEFAULT_DROPZONE,
                    help=f"drop-zone dir (default: {DEFAULT_DROPZONE})")
    ap.add_argument("--dry-run", action="store_true",
                    help="classify only; extract and archive nothing")
    args = ap.parse_args()

    results = process(args.dropzone, dry_run=args.dry_run)
    if not results:
        print(f"intake: no zips found in {args.dropzone}")
        return 0
    mode = " (dry-run)" if args.dry_run else ""
    print(f"intake: {len(results)} zip(s) in {args.dropzone}{mode}")
    for r in results:
        extra = r.get("archived_to") or r.get("extracted_to") or ""
        print(f"  {r['zip']:<50} {r['kind']:<15} {r['action'] if 'action' in r else '-> ' + extra}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
