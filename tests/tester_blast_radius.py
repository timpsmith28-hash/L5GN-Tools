"""tester_blast_radius -- the blast-radius scanner tiers by consequence and stays
out of walled data (COWORK_BRIEF_blast_radius.md Task A).

Fixture families:
  (a) raw `sf data import --target-org prod`   -> raw-write-prod
  (b) the same behind a typed-gate module      -> guarded-write
  (c) read-only `sf data query`                -> read-only
  (d) `requests.get`                           -> read-only
Plus: an unknown target-org ranks prod (fail-safe), and a `sf data import` string
inside a gitignored chat JSON is NOT flagged.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from l5gntools.scanners import blast_radius as br


def _git(proj: Path, *args: str) -> None:
    env = {**os.environ,
           "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "-C", str(proj), *args], check=True, env=env,
                   capture_output=True)


def _proj(root: Path, name: str, files: dict) -> Path:
    p = root / name
    p.mkdir(parents=True)
    for rel, content in files.items():
        fp = p / rel
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content, encoding="utf-8")
    return p


def run() -> list[str]:
    v: list[str] = []

    # --- pure classifiers ----------------------------------------------------
    if br.classify_env("sf data import --target-org acmeMain") != "prod":
        v.append("classify_env: 'acmeMain' should read prod")
    if br.classify_env("sf data import --target-org devSandbox1") != "sandbox":
        v.append("classify_env: a sandbox alias should read sandbox")
    if br.classify_env("sf data import --target-org acme7") != "unknown":
        v.append("classify_env: an unrecognised alias should read unknown")
    if br.hit_tier("write", False, "unknown") != "raw-write-prod":
        v.append("hit_tier: unknown env must rank as prod (fail-safe)")
    if br.hit_tier("write", True, "prod") != "guarded-write":
        v.append("hit_tier: a guarded write must not exceed guarded-write")
    if br.hit_tier("write", False, "sandbox") != "raw-write":
        v.append("hit_tier: a raw sandbox write is raw-write")

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        raw = _proj(root, "RawProd", {
            "upload.py": "import subprocess\n"
                         "subprocess.run('sf data import --target-org prod'.split())\n",
            ".gitignore": "raw_gemini_files/\n",
            "raw_gemini_files/chat.json": '{"m":"sf data import --target-org prod"}\n'})
        _git(raw, "init", "-q"); _git(raw, "add", "upload.py", ".gitignore")
        _git(raw, "commit", "-qm", "init")

        guarded = _proj(root, "Guarded", {
            "safe_write.py": "# typed_phrase gate; def gate(): pass  # four-eyes\n"
                             "run('sf data import --target-org prod')\n"})
        readq = _proj(root, "ReadOnly", {
            "q.py": "run('sf data query --target-org prod')\n"})
        http = _proj(root, "HttpGet", {
            "c.py": "import requests\nrequests.get('https://x')\n"})
        unknown = _proj(root, "UnknownOrg", {
            "u.py": "run('sf data upsert --target-org acme7')\n"})

        cases = {"RawProd": (raw, "raw-write-prod"),
                 "Guarded": (guarded, "guarded-write"),
                 "ReadOnly": (readq, "read-only"),
                 "HttpGet": (http, "read-only"),
                 "UnknownOrg": (unknown, "raw-write-prod")}
        for label, (p, want) in cases.items():
            out = br.scan(p)
            if out["tier"] != want:
                v.append(f"blast_radius[{label}]: tier {out['tier']!r}, want {want!r}")

        # scope: the gitignored chat JSON must not contribute a hit
        rawout = br.scan(raw)
        if any("raw_gemini_files" in h["path"] for h in rawout["hits"]):
            v.append("blast_radius: flagged a hit inside a gitignored chat archive")
        if rawout["hit_count"] < 1:
            v.append("blast_radius: the real prod-write in upload.py should be flagged")
        # guardrail: no raw source line stored, only the canonical signal name
        for h in rawout["hits"]:
            if "target-org" in h.get("signal", "") or "prod" in h.get("signal", ""):
                v.append(f"blast_radius: a hit signal leaked raw content -> {h['signal']!r}")
    return v
