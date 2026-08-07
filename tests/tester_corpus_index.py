"""corpus_index (K3): chunks each mapped project's KNOWLEDGE*.md by heading,
flags whole-file chunks (no headings at all), hashes per file, and re-chunks
only what moved.

Hermetic: synthetic project tree in a temp dir; no real MCF corpus touched.
"""
from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path


def run() -> list[str]:
    v: list[str] = []
    _PIPE = Path(__file__).resolve().parent.parent / "chronicler" / "pipeline"
    if str(_PIPE) not in sys.path:
        sys.path.insert(0, str(_PIPE))
    import corpus_index as k3

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        mcf_root = td / "MCF"

        proj_dir = mcf_root / "PricingModel"
        proj_dir.mkdir(parents=True)
        with_headings = proj_dir / "PRICINGMODEL_KNOWLEDGE.md"
        with_headings.write_text(
            "# Pricing knowledge\n\nintro text\n\n"
            "## Tier caps\n\nFree tier capped at 3 seats.\n\n"
            "## Renewal\n\nAnnual renewal reminds 30 days out.\n",
            encoding="utf-8",
        )
        no_headings = proj_dir / "OTHER_KNOWLEDGE.md"
        no_headings.write_text("just some prose with no markdown headings at all", encoding="utf-8")

        knowledge_idx = {
            "projects": [{
                "project_id": "mcf-pricing-model",
                "local_folder": "MCF/PricingModel",
                "knowledge_files": ["PRICINGMODEL_KNOWLEDGE.md", "OTHER_KNOWLEDGE.md"],
            }],
        }

        # --- chunk_text: heading split -----------------------------------------
        chunks = k3.chunk_text(with_headings.read_text(encoding="utf-8"), "PRICINGMODEL_KNOWLEDGE.md")
        headings = [c.heading for c in chunks]
        if headings != ["Pricing knowledge", "Tier caps", "Renewal"]:
            v.append(f"chunk_text heading split wrong: {headings}")
        if any(c.flagged_whole_file for c in chunks):
            v.append("a file WITH headings must not have any chunk flagged whole-file")
        tier_chunk = next(c for c in chunks if c.heading == "Tier caps")
        if "Free tier capped at 3 seats." not in tier_chunk.text:
            v.append(f"chunk text does not contain its own section's body: {tier_chunk.text!r}")

        # --- no-headings file: exactly one flagged whole-file chunk -------------
        chunks_no_h = k3.chunk_text(no_headings.read_text(encoding="utf-8"), "OTHER_KNOWLEDGE.md")
        if len(chunks_no_h) != 1 or not chunks_no_h[0].flagged_whole_file:
            v.append(f"no-heading file should yield exactly one flagged whole-file chunk: {chunks_no_h}")

        # --- build_corpus_index end to end ---------------------------------------
        cache: dict = {}
        index = k3.build_corpus_index(knowledge_idx, mcf_root, cache)
        proj = index["projects"][0]
        files_by_name = {f["file"]: f for f in proj["files"]}
        if files_by_name["PRICINGMODEL_KNOWLEDGE.md"]["chunk_count"] != 3:
            v.append(f"main file chunk count wrong: {files_by_name['PRICINGMODEL_KNOWLEDGE.md']}")
        if not files_by_name["OTHER_KNOWLEDGE.md"]["whole_file_flagged"]:
            v.append("OTHER_KNOWLEDGE.md should be reported whole_file_flagged=True")
        if index["files_rechunked"] != 2 or index["files_from_cache"] != 0:
            v.append(f"first build should rechunk both files, cache 0: {index}")

        # --- re-run with nothing changed: 0 rechunked, 2 from cache --------------
        index2 = k3.build_corpus_index(knowledge_idx, mcf_root, cache)
        if index2["files_rechunked"] != 0 or index2["files_from_cache"] != 2:
            v.append(f"unchanged re-run should rechunk 0: {index2}")
        if index2["projects"][0]["files"] != proj["files"]:
            v.append("cached re-run produced different chunk content than the live run")

        # --- changing ONE file re-chunks only that one -----------------------
        time.sleep(0.01)
        with_headings.write_text(
            with_headings.read_text(encoding="utf-8") + "\n## New section\n\nnew content\n",
            encoding="utf-8",
        )
        index3 = k3.build_corpus_index(knowledge_idx, mcf_root, cache)
        if index3["files_rechunked"] != 1 or index3["files_from_cache"] != 1:
            v.append(f"editing one file should rechunk exactly that one: {index3}")
        new_headings = [c["heading"] for c in
                        next(f for f in index3["projects"][0]["files"]
                             if f["file"] == "PRICINGMODEL_KNOWLEDGE.md")["chunks"]]
        if "New section" not in new_headings:
            v.append("the changed file's new heading did not show up after re-chunking")

        # --- unresolved project directory reported, not a crash -----------------
        bad_idx = {"projects": [{"project_id": "mcf-ghost", "local_folder": "MCF/Ghost",
                                   "knowledge_files": ["GHOST_KNOWLEDGE.md"]}]}
        index4 = k3.build_corpus_index(bad_idx, mcf_root, {})
        if not index4["unreadable"] or index4["unreadable"][0]["project_id"] != "mcf-ghost":
            v.append(f"a project whose folder doesn't exist should report unreadable, not crash: {index4}")

        # --- save/load cache round-trip, read-only on sources -----------------
        cache_path = td / "cache.json"
        before = no_headings.stat().st_mtime
        k3.save_cache(cache, cache_path)
        after = no_headings.stat().st_mtime
        if before != after:
            v.append("save_cache touched a source file's mtime")
        reloaded = k3.load_cache(cache_path)
        if reloaded.keys() != cache.keys():
            v.append("cache did not round-trip through save_cache/load_cache")

    return v
