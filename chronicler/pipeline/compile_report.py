"""compile_report.py -- K5, COWORK_BRIEF_knowledge_curator.md.

Assembles ``data/knowledge_curator/report_<date>.md`` from K1's
``knowledge_index.json``, K2's ``claims.json``, and K4's ``matches.json``.
**Not** written under ``docs/`` -- it is regenerable (DECISIONS 0030,
``docs/README.md`` §1). Sections, in order:

  1. Not yet formalized (gaps), per project.
  2. No knowledge file yet -- recurrence-ranked starter list.
  3. Cross-project relevance -- within MCF.
  4. Superseded -- the trail, both statements quoted and dated.
  5. Confirmed captured -- counts per project plus a small sample.

The header carries run timestamp, model id, conversations scanned, claims
extracted, quote-rejection rate, projects covered, and projects unresolved,
so a thin run reads as thin rather than as a clean bill of health.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent

RECURRENCE_TOPIC_FLOOR = 0.55
RECURRENCE_TOP_N = 10
CAPTURED_SAMPLE_N = 5


# ---------------------------------------------------------------------------
# Recurrence clustering for "no knowledge file yet" -- greedy, similarity
# based, stdlib only (reuses match_claims.similarity, no new metric).
# ---------------------------------------------------------------------------

def cluster_claims(claims: list[dict], floor: float = RECURRENCE_TOPIC_FLOOR) -> list[dict]:
    import sys
    pipe = str(_HERE)
    if pipe not in sys.path:
        sys.path.insert(0, pipe)
    from match_claims import similarity  # noqa: E402

    clusters: list[dict] = []
    for c in claims:
        placed = False
        for cluster in clusters:
            if similarity(c["claim_text"], cluster["members"][0]["claim_text"]) >= floor:
                cluster["members"].append(c)
                placed = True
                break
        if not placed:
            clusters.append({"members": [c]})

    out = []
    for cluster in clusters:
        conv_ids = {m["conversation_id"] for m in cluster["members"]}
        out.append({
            "example_claim_text": cluster["members"][0]["claim_text"],
            "conversation_count": len(conv_ids),
            "conversations": sorted(conv_ids),
            "quotes": [{"claim_text": m["claim_text"], "quoted_source": m["quoted_source"],
                          "conversation_id": m["conversation_id"], "real_time": m.get("real_time")}
                        for m in cluster["members"]],
        })
    out.sort(key=lambda c: c["conversation_count"], reverse=True)
    return out


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def _fmt_quote(claim_text: str, quoted_source: str, conv_id: str, real_time: str | None) -> str:
    date = (real_time or "unknown date")[:10]
    return f"  - **{claim_text}** ({date}, `{conv_id}`)\n    > {quoted_source}"


def section_not_yet_formalized(claims_by_outcome: dict, knowledge_index: dict) -> str:
    has_kf = {p["project_id"] for p in knowledge_index.get("projects", []) if p.get("knowledge_files")}
    lines = ["## 1. Not yet formalized (gaps)\n"]
    gaps = [c for c in claims_by_outcome.get("gap", []) if c["project_id"] in has_kf]
    if not gaps:
        lines.append("_No gaps recorded for a project that already has a knowledge file._\n")
        return "\n".join(lines)
    by_project: dict[str, list] = {}
    for c in gaps:
        by_project.setdefault(c["project_id"], []).append(c)
    for pid in sorted(by_project):
        lines.append(f"\n### {pid} ({len(by_project[pid])} gap(s))\n")
        for c in by_project[pid]:
            lines.append(_fmt_quote(c["claim_text"], c["quoted_source"], c["conversation_id"], c["real_time"]))
    return "\n".join(lines)


def section_no_knowledge_file(claims_by_outcome: dict, knowledge_index: dict) -> str:
    no_kf_projects = [p["project_id"] for p in knowledge_index.get("projects", [])
                        if not p.get("knowledge_files")]
    lines = ["\n## 2. No knowledge file yet -- starter list\n"]
    if not no_kf_projects:
        lines.append("_Every mapped project already has at least one KNOWLEDGE*.md._\n")
        return "\n".join(lines)
    all_claims = [c for claims in claims_by_outcome.values() for c in claims]
    for pid in sorted(no_kf_projects):
        proj_claims = [c for c in all_claims if c["project_id"] == pid]
        lines.append(f"\n### {pid}\n")
        if not proj_claims:
            lines.append("_No claims extracted for this project yet._\n")
            continue
        clusters = cluster_claims(proj_claims)[:RECURRENCE_TOP_N]
        for cl in clusters:
            lines.append(f"  - **{cl['example_claim_text']}** "
                          f"(recurred across {cl['conversation_count']} conversation(s))")
    return "\n".join(lines)


def section_cross_project(claims_by_outcome: dict) -> str:
    lines = ["\n## 3. Cross-project relevance (within MCF)\n"]
    cross = claims_by_outcome.get("cross-project", [])
    if not cross:
        lines.append("_None found this run._\n")
        return "\n".join(lines)
    for c in cross:
        found_in = (c.get("supersedes") or {}).get("found_in_project", "?")
        lines.append(f"  - **{c['claim_text']}** -- own project `{c['project_id']}`, "
                      f"confirmed in `{found_in}` ({(c['real_time'] or '')[:10]}, `{c['conversation_id']}`)")
        lines.append(f"    > {c['quoted_source']}")
    return "\n".join(lines)


def section_superseded(claims_by_outcome: dict) -> str:
    lines = ["\n## 4. Superseded\n"]
    superseded = claims_by_outcome.get("superseded", [])
    if not superseded:
        lines.append("_The superseded path did not fire this run -- either no conflicting "
                      "claims exist yet, or the ordering design has not been exercised. "
                      "Worth noting plainly rather than silently._\n")
        return "\n".join(lines)
    for c in superseded:
        newer = c.get("supersedes") or {}
        lines.append(f"\n  - **{c['project_id']}**")
        lines.append(f"    - was: **{c['claim_text']}** ({(c['real_time'] or '')[:10]}, `{c['conversation_id']}`)")
        lines.append(f"      > {c['quoted_source']}")
        lines.append(f"    - now: **{newer.get('newer_claim_text', '?')}** "
                      f"({(newer.get('newer_real_time') or '')[:10]}, `{newer.get('newer_conversation_id', '?')}`)")
        lines.append(f"      > {newer.get('newer_quoted_source', '')}")
    return "\n".join(lines)


def section_confirmed_captured(claims_by_outcome: dict) -> str:
    lines = ["\n## 5. Confirmed captured\n"]
    captured = claims_by_outcome.get("captured", [])
    if not captured:
        lines.append("_None this run._\n")
        return "\n".join(lines)
    by_project: dict[str, list] = {}
    for c in captured:
        by_project.setdefault(c["project_id"], []).append(c)
    for pid in sorted(by_project):
        items = by_project[pid]
        lines.append(f"\n### {pid} -- {len(items)} claim(s) captured\n")
        for c in items[:CAPTURED_SAMPLE_N]:
            lines.append(f"  - {c['claim_text']}")
        if len(items) > CAPTURED_SAMPLE_N:
            lines.append(f"  - _...and {len(items) - CAPTURED_SAMPLE_N} more._")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Header + assembly
# ---------------------------------------------------------------------------

def build_header(claims_report: dict, matches_report: dict, knowledge_index: dict) -> str:
    projects = knowledge_index.get("projects", [])
    unresolved = knowledge_index.get("unresolved", [])
    covered = sorted({p["project_id"] for p in projects})
    unresolved_ids = sorted({u["project_id"] for u in unresolved})

    return "\n".join([
        "# Knowledge Curator report",
        "",
        f"- run timestamp: {matches_report.get('run_timestamp', claims_report.get('run_timestamp', '?'))}",
        f"- model id: {matches_report.get('model_id', claims_report.get('model_id', '?'))}",
        f"- endpoint: {matches_report.get('endpoint', claims_report.get('endpoint', '?'))}",
        f"- conversations scanned: {claims_report.get('conversations_scanned', 0)}",
        f"- conversations excluded (no resolvable timestamp): "
        f"{len(claims_report.get('conversations_excluded_no_timestamp', []))}",
        f"- claims extracted: {claims_report.get('claims_extracted', 0)}",
        f"- claims rejected (not a literal quote): {claims_report.get('claims_rejected', 0)} "
        f"(rate {claims_report.get('quote_rejection_rate', 0.0):.1%})",
        f"- projects covered: {len(covered)} ({', '.join(covered) if covered else 'none'})",
        f"- projects unresolved: {len(unresolved_ids)} "
        f"({', '.join(unresolved_ids) if unresolved_ids else 'none'})",
        "",
    ])


def compile_report(claims_report: dict, matches_report: dict, knowledge_index: dict) -> str:
    claims_by_outcome: dict[str, list] = {}
    for c in matches_report.get("claims", []):
        claims_by_outcome.setdefault(c["outcome"], []).append(c)

    parts = [
        build_header(claims_report, matches_report, knowledge_index),
        section_not_yet_formalized(claims_by_outcome, knowledge_index),
        section_no_knowledge_file(claims_by_outcome, knowledge_index),
        section_cross_project(claims_by_outcome),
        section_superseded(claims_by_outcome),
        section_confirmed_captured(claims_by_outcome),
    ]
    return "\n".join(parts) + "\n"


def out_path_for(run_timestamp: str | None) -> Path:
    if run_timestamp:
        date = run_timestamp[:10]
    else:
        date = datetime.now(timezone.utc).date().isoformat()
    return Path("data/knowledge_curator") / f"report_{date}.md"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--claims", type=Path, default=Path("data/knowledge_curator/claims.json"))
    ap.add_argument("--matches", type=Path, default=Path("data/knowledge_curator/matches.json"))
    ap.add_argument("--index", type=Path, default=Path("data/knowledge_curator/knowledge_index.json"))
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    claims_report = json.loads(args.claims.read_text(encoding="utf-8"))
    matches_report = json.loads(args.matches.read_text(encoding="utf-8"))
    knowledge_index = json.loads(args.index.read_text(encoding="utf-8"))

    report_md = compile_report(claims_report, matches_report, knowledge_index)
    out_path = args.out or out_path_for(matches_report.get("run_timestamp"))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report_md, encoding="utf-8")
    print(f"report written: {out_path}")


if __name__ == "__main__":
    main()
