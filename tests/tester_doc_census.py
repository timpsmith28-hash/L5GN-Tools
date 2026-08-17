"""tester_doc_census -- document type (Task A) and provenance (Task B)
classification, the coverage inputs (Task C), and the out-of-band flag
(Task D). `COWORK_BRIEF_doc_provenance_coverage.md`, DECISIONS 0026.

Hermetic: builds a synthetic project tree in a temp dir carrying one file of
every type and provenance the scanner must tell apart, then asserts the
per-doc classification and the project-level tallies. No real estate data is
read here -- that verification (the 824-document personal estate) was done by
hand against `data/estate.json` while the rule was being chosen, and is
recorded in the brief's report, not re-run on every commit.

The load-bearing assertions are the same shape as `file_census`'s: exact
membership for the classifications that matter, not "contains the right
answer among wrong ones".
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from l5gntools.scanners import doc_census


def _write(root: Path, relpath: str, text: str = "# doc\nbody\n") -> None:
    p = root / relpath
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def _check_doc_type() -> list[str]:
    v: list[str] = []
    cases = {
        "docs/adr/0001-thing.md": "adr",
        "SolConfig_Knowledge.md": "knowledge",
        "LEGACY_BUNDLE_KNOWLEDGE.md": "knowledge",
        "CLAUDE.md": "claude_md",
        "README.md": "readme",
        "readme_old.md": "readme",
        "GLOSSARY.md": "glossary",
        "docs/DECISIONS.md": "decisions",
        "docs/INTENT.md": "intent",
        "docs/ARCHITECTURE.md": "architecture",
        "docs/RUNBOOK_deploy.md": "runbook",
        "docs/KNIGHT_PLAYBOOK.md": "runbook",
        "docs/UAT_thing.md": "uat",
        "docs/RELEASE_CHECKLIST.md": "uat",
        "docs/Q3_PLAN.md": "plan",
        "docs/BUILD_STATUS.md": "plan",
        "docs/COWORK_BRIEF_x.md": "brief",
        "docs/COWORK_REPORT_x.md": "report",
        "docs/NOTES.md": "unclassified",
        "docs/journal/random_thoughts.md": "unclassified",
    }
    for path, expected in cases.items():
        got = doc_census.classify_doc_type(path)
        if got != expected:
            v.append(f"doc_census: {path!r} classified as {got!r}, expected {expected!r}")
    return v


def _check_provenance() -> list[str]:
    v: list[str] = []
    generated = [
        ".vault/gap/x.md", "_citadel_intel_docs/campaign_modules/y.md",
        "output/report.md", "logs/run.md", "AutoFiles/v1.1/z.md",
        "a/_archive/pipeline_data/w.md",
        # A leading underscore/dot on the FILENAME itself, directory
        # otherwise ordinary -- architecture_census's own render
        # (`docs/_architecture_shape.md`, DECISIONS 0030) is exactly this
        # shape, and must count as generated even though `docs/` does not.
        "docs/_architecture_shape.md", "docs/.hidden_note.md",
    ]
    authored = [
        "docs/README.md", "briefs/COWORK_BRIEF_x.md", "PoC/notes.md",
        "L5GN_Journal/newsletter_ideas.md",
    ]
    for path in generated:
        if doc_census.classify_provenance(path) != "generated":
            v.append(f"doc_census: {path!r} not classified generated")
    for path in authored:
        if doc_census.classify_provenance(path) != "authored":
            v.append(f"doc_census: {path!r} wrongly classified generated "
                     f"-- false positive")
    return v


def _make_project(root: Path) -> Path:
    proj = root / "MixedProj"
    _write(proj, "README.md", "# Mixed project\n")
    _write(proj, "docs/DECISIONS.md", "# Decisions\n## 0001\n")
    _write(proj, "SolConfig_Knowledge.md", "# Knowledge\nstuff\n")
    _write(proj, "docs/journal/random.md", "just prose\n")
    # Generated: must not count toward authored/classified metrics.
    _write(proj, ".vault/gap/dump.md", "# Generated dump\n")
    _write(proj, ".vault/gap/dump2.md", "# Generated dump 2\n")
    _write(proj, "output/build_notes.md", "auto-written\n")
    return proj


def _check_scan() -> list[str]:
    v: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        proj = _make_project(Path(td))
        out = doc_census.scan(proj)

        if out["doc_count"] != 7:
            v.append(f"doc_census: doc_count is {out['doc_count']}, expected 7")
        if out["generated_count"] != 3:
            v.append(f"doc_census: generated_count is {out['generated_count']}, expected 3")
        if out["authored_count"] != 4:
            v.append(f"doc_census: authored_count is {out['authored_count']}, expected 4")
        # classified: README, DECISIONS, Knowledge -- journal/random.md stays
        # unclassified. Generated docs never enter this count.
        if out["classified_count"] != 3:
            v.append(f"doc_census: classified_count is {out['classified_count']}, expected 3")
        if abs(out["classified_pct"] - 75.0) > 0.01:
            v.append(f"doc_census: classified_pct is {out['classified_pct']}, expected 75.0 "
                     f"(3 of 4 authored)")

        tally = out["type_tally"]
        for expected_type in ("readme", "decisions", "knowledge", "unclassified"):
            if not tally.get(expected_type):
                v.append(f"doc_census: type_tally missing {expected_type!r}: {tally}")
        if "readme" not in tally or tally["readme"] != 1:
            v.append(f"doc_census: readme tally is {tally.get('readme')}, expected 1")

        # Kept-for-compatibility booleans must reflect AUTHORED classification
        # only -- a generated tree must not be able to satisfy has_readme.
        if not out["has_readme"]:
            v.append("doc_census: has_readme false despite an authored README.md")
        if out["has_claude_md"]:
            v.append("doc_census: has_claude_md true with no CLAUDE.md in the fixture")

        # Each per-doc entry carries both new fields.
        by_path = {d["path"]: d for d in out["docs"]}
        if by_path.get(".vault/gap/dump.md", {}).get("provenance") != "generated":
            v.append("doc_census: per-doc provenance missing/wrong for a generated doc")
        if by_path.get("README.md", {}).get("doc_type") != "readme":
            v.append("doc_census: per-doc doc_type missing/wrong for README.md")
    return v


def _check_out_of_band() -> list[str]:
    v: list[str] = []
    # Fewer than OUT_OF_BAND_MIN_PROJECTS: never flags, however skewed.
    tiny = [{"name": "A", "doc_census": {"doc_count": 5}},
            {"name": "B", "doc_census": {"doc_count": 500}}]
    if doc_census.out_of_band(tiny):
        v.append("doc_census: out_of_band flagged with fewer than the minimum project count")

    # A clear outlier against a stable estate median must be named, and the
    # small, ordinary projects must not be.
    projects = [
        {"name": "Small1", "doc_census": {"doc_count": 20}},
        {"name": "Small2", "doc_census": {"doc_count": 25}},
        {"name": "Small3", "doc_census": {"doc_count": 30}},
        {"name": "Runaway", "doc_census": {"doc_count": 400}},
    ]
    flagged = {e["project"] for e in doc_census.out_of_band(projects)}
    if flagged != {"Runaway"}:
        v.append(f"doc_census: out_of_band flagged {flagged}, expected exactly {{'Runaway'}}")

    # A project with no doc_census entry at all (zero docs) must not crash the
    # median computation or be flagged.
    with_empty = projects + [{"name": "Empty", "doc_census": {}}]
    try:
        doc_census.out_of_band(with_empty)
    except Exception as exc:  # noqa: BLE001 -- a crash here is still a crash
        v.append(f"doc_census: out_of_band raised on a project with doc_count 0: {exc}")
    return v


def run() -> list[str]:
    v: list[str] = []
    v.extend(_check_doc_type())
    v.extend(_check_provenance())
    v.extend(_check_scan())
    v.extend(_check_out_of_band())
    return v
