"""tester_dupe_labels -- shared-filename groups labelled identical vs divergent
by content hash (governance Task D).
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from l5gntools.scanners.duplicate_finder import label_shared, scan_estate


def run() -> list[str]:
    v: list[str] = []

    if label_shared(["a", "a"]) != "identical":
        v.append("label_shared: matching digests should be identical")
    if label_shared(["a", "b"]) != "divergent":
        v.append("label_shared: differing digests should be divergent")
    if label_shared(["a", None]) != "divergent":
        v.append("label_shared: an unreadable file cannot be proven identical")

    with tempfile.TemporaryDirectory() as td:
        p1 = Path(td) / "ProjOne"
        p2 = Path(td) / "ProjTwo"
        for p in (p1, p2):
            p.mkdir()
            # same name, same content -> identical
            (p / "reconcile.py").write_text("print('shared tool')\n", encoding="utf-8")
        # same name, different content -> divergent
        (p1 / "helper.py").write_text("A = 1\n", encoding="utf-8")
        (p2 / "helper.py").write_text("A = 2  # forked\n", encoding="utf-8")

        out = scan_estate([p1, p2])
        by_name = {s["filename"]: s["content"] for s in out["shared_filenames"]}
        if by_name.get("reconcile.py") != "identical":
            v.append(f"scan_estate: reconcile.py should be identical -> {by_name}")
        if by_name.get("helper.py") != "divergent":
            v.append(f"scan_estate: helper.py should be divergent -> {by_name}")
        if out.get("shared_filename_divergent") != 1:
            v.append(f"scan_estate: divergent count should be 1 -> "
                     f"{out.get('shared_filename_divergent')}")
    return v
