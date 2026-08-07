"""corpus_index.py -- K3, COWORK_BRIEF_knowledge_curator.md.

Chunks each mapped project's ``*KNOWLEDGE*.md`` files (K1's
``knowledge_index.json``) by markdown heading. A file with no headings at
all becomes ONE whole-file chunk, explicitly **flagged** -- per the spec,
that is the case K3's citability argument (a match cites a heading-scoped
chunk, not an undifferentiated file) breaks on, so it must be visible
downstream, not silently degrade to the same shape as a normal chunk.

Hashes per file (sha256 of its bytes) and caches on that hash, so a re-run
re-chunks only files that actually moved.

Usage:
    python3 corpus_index.py --index data/knowledge_curator/knowledge_index.json \\
        [--host HOST] [--cache PATH] [--out PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

_PIPE = Path(__file__).resolve().parent
if str(_PIPE) not in sys.path:
    sys.path.insert(0, str(_PIPE))
import knowledge_index as k1  # noqa: E402

DEFAULT_INDEX = k1.DEFAULT_OUT
DEFAULT_CACHE = Path("data/knowledge_curator/corpus_cache.json")
DEFAULT_OUT = Path("data/knowledge_curator/corpus_index.json")

_HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.*)$", re.MULTILINE)


@dataclass
class Chunk:
    file: str
    heading: str | None
    level: int | None
    text: str
    start_line: int
    flagged_whole_file: bool = False


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def chunk_text(text: str, relpath: str) -> list[Chunk]:
    """Split by heading. No heading anywhere in the file -> one whole-file
    chunk, flagged. An empty file also yields one (empty-text) flagged
    chunk, not zero chunks -- a file that produced nothing is a fact to
    report, not a silent absence."""
    matches = list(_HEADING_RE.finditer(text))
    if not matches:
        return [Chunk(file=relpath, heading=None, level=None, text=text,
                        start_line=1, flagged_whole_file=True)]
    chunks: list[Chunk] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunks.append(Chunk(
            file=relpath,
            heading=m.group(2).strip(),
            level=len(m.group(1)),
            text=text[start:end],
            start_line=text.count("\n", 0, start) + 1,
        ))
    return chunks


def chunk_file(path: Path, relpath: str) -> list[Chunk]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return chunk_text(text, relpath)


# ---------------------------------------------------------------------------
# Cache -- keyed on "<project_id>::<relpath>", invalidated on hash change.
# ---------------------------------------------------------------------------

def load_cache(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_cache(cache: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def build_corpus_index(knowledge_index: dict, root: Path | None, cache: dict) -> dict:
    projects_out: list[dict] = []
    rechunked = 0
    from_cache = 0
    unreadable: list[dict] = []

    for proj in knowledge_index.get("projects", []):
        project_dir = k1.project_dir_for(proj["local_folder"], root)
        files_out: list[dict] = []
        for relfile in proj.get("knowledge_files", []):
            if project_dir is None:
                unreadable.append({"project_id": proj["project_id"], "file": relfile,
                                     "reason": "project directory unresolved"})
                continue
            path = project_dir / relfile
            key = f"{proj['project_id']}::{relfile}"
            try:
                h = file_hash(path)
            except OSError as exc:
                unreadable.append({"project_id": proj["project_id"], "file": relfile,
                                     "reason": str(exc)})
                continue

            cached = cache.get(key)
            if cached is not None and cached.get("hash") == h:
                chunks = cached["chunks"]
                from_cache += 1
            else:
                chunks = [asdict(c) for c in chunk_file(path, relfile)]
                cache[key] = {"hash": h, "chunks": chunks}
                rechunked += 1

            files_out.append({
                "file": relfile,
                "hash": h,
                "chunk_count": len(chunks),
                "whole_file_flagged": any(c["flagged_whole_file"] for c in chunks),
                "chunks": chunks,
            })

        projects_out.append({
            "project_id": proj["project_id"],
            "local_folder": proj["local_folder"],
            "files": files_out,
        })

    return {
        "projects": projects_out,
        "files_rechunked": rechunked,
        "files_from_cache": from_cache,
        "unreadable": unreadable,
    }


def _print_report(index: dict) -> None:
    print(f"files rechunked:  {index['files_rechunked']}")
    print(f"files from cache: {index['files_from_cache']}")
    flagged = [
        (p["project_id"], f["file"])
        for p in index["projects"] for f in p["files"] if f["whole_file_flagged"]
    ]
    print(f"whole-file (no-heading) flagged: {len(flagged)}")
    for pid, f in flagged:
        print(f"    {pid}: {f}")
    if index["unreadable"]:
        print(f"unreadable: {len(index['unreadable'])}")
        for u in index["unreadable"]:
            print(f"    {u['project_id']}: {u['file']} -- {u['reason']}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--index", type=Path, default=DEFAULT_INDEX)
    ap.add_argument("--host", help="resolve project directories as if run on this hostname")
    ap.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    knowledge_idx = json.loads(args.index.read_text(encoding="utf-8"))
    root = k1.mcf_root(args.host)
    cache = load_cache(args.cache)

    index = build_corpus_index(knowledge_idx, root, cache)
    save_cache(cache, args.cache)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(index, indent=2), encoding="utf-8")

    _print_report(index)
    print(f"\ncorpus index written: {args.out}")


if __name__ == "__main__":
    main()
