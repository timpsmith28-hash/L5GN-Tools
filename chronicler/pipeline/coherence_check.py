"""coherence_check.py -- Phase 3 of docs/COWORK_BRIEF_local_transcript_intake.md:
the reason personal goes first. Measures `source='claude-local'` threads
(Phase 2's ingest) against `source='claude'` (the personal Claude export,
already in the same dev vault via normalize_claude.py) and reports real
numbers -- it does not assert overlap or its absence, it measures it.

**Read-only.** SELECT only, no writes, no `--apply` -- there is nothing to
apply. The brief's own acceptance for this phase is "a written comparison
with real numbers," not a code change; a dedupe rule is *stated* here as a
recommendation from the measurement, never implemented -- that's explicitly
left for whoever acts on this report.

What this measures, per the brief:
  1. Threads present in the local store but not in the export, and vice
     versa.
  2. For threads in both: does the reconstruction match -- same message
     count, same ordering, same content modulo formatting? Sampled and
     diffed, not asserted.
  3. What the local store loses relative to the export, and what it gains.
  4. A dedupe rule that falls out of (1)-(3), stated explicitly as a
     recommendation.

Matching threads across sources is a real problem, not a lookup: the two
stores use entirely different id spaces (a Claude Code/Cowork session uuid
has no relationship to a claude.ai conversation uuid), so there is no join
key. Two signals, in order of strength:
  - **Exact normalized title match** (case/whitespace-insensitive) -- the
    strong signal; a false positive here would need two independently
    generated titles to collide, unlikely enough to trust as a match.
  - **Near-title match** (Jaccard similarity of title words above a
    threshold) -- surfaced separately as "close, not counted," for a human
    to look at, never auto-counted as a match (the brief's "sample and diff,
    don't assert" instruction, taken literally: a fuzzy signal does not get
    to assert a match on its own).
No timestamp-proximity matching is attempted: two independent products used
around the same moment does not imply the same conversation, and using it
as a matching signal would manufacture false positives rather than measure
anything real.

Usage:
    python3 pipeline/coherence_check.py [--account claude-personal] [--sample N]
"""
from __future__ import annotations

import argparse
import difflib
import re

from db import get_connection

_WS_RE = re.compile(r"\s+")
_WORD_RE = re.compile(r"[a-z0-9]+")


def normalize_title(title: str | None) -> str:
    if not title:
        return ""
    return _WS_RE.sub(" ", title.strip().lower())


def normalize_text(text: str | None) -> str:
    """Content-modulo-formatting: collapse all whitespace runs, lower-case.
    Deliberately blunt -- this is for a similarity ratio, not a byte-exact
    check (the brief's own phrasing: 'same content modulo formatting')."""
    if not text:
        return ""
    return _WS_RE.sub(" ", text.strip().lower())


def title_words(title: str) -> set:
    return set(_WORD_RE.findall(title.lower()))


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

def load_threads(conn, source: str, account: str | None) -> list[dict]:
    q = "SELECT thread_id, title, created_at, updated_at FROM threads WHERE source=?"
    params: list = [source]
    if account:
        q += " AND account=?"
        params.append(account)
    rows = conn.execute(q, params).fetchall()
    out = []
    for r in rows:
        msg_count = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE thread_id=?", (r["thread_id"],)
        ).fetchone()[0]
        out.append({
            "thread_id": r["thread_id"], "title": r["title"],
            "created_at": r["created_at"], "updated_at": r["updated_at"],
            "message_count": msg_count,
        })
    return out


def load_messages(conn, thread_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT seq, role, content, created_at FROM messages WHERE thread_id=? ORDER BY seq",
        (thread_id,),
    ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Match
# ---------------------------------------------------------------------------

NEAR_MATCH_THRESHOLD = 0.5  # Jaccard on title words; surfaced, never counted as a match.


def match_threads(local: list[dict], export: list[dict]):
    """Returns (exact_pairs, near_pairs, local_only, export_only).
    exact_pairs: [(local_thread, export_thread)] on exact normalized title.
    near_pairs: [(local_thread, export_thread, jaccard)] close but not exact,
    for human review only -- excluded from local_only/export_only either way
    (they're candidates, not confirmed non-matches).
    """
    export_by_title: dict = {}
    for e in export:
        export_by_title.setdefault(normalize_title(e["title"]), []).append(e)

    exact_pairs = []
    near_pairs = []
    matched_local_ids = set()
    matched_export_ids = set()

    for l in local:
        lt = normalize_title(l["title"])
        if lt and lt in export_by_title:
            for e in export_by_title[lt]:
                exact_pairs.append((l, e))
                matched_local_ids.add(l["thread_id"])
                matched_export_ids.add(e["thread_id"])

    unmatched_local = [l for l in local if l["thread_id"] not in matched_local_ids]
    unmatched_export = [e for e in export if e["thread_id"] not in matched_export_ids]

    lw = {l["thread_id"]: title_words(l["title"] or "") for l in unmatched_local}
    ew = {e["thread_id"]: title_words(e["title"] or "") for e in unmatched_export}
    near_local_ids = set()
    near_export_ids = set()
    for l in unmatched_local:
        best = None
        for e in unmatched_export:
            score = jaccard(lw[l["thread_id"]], ew[e["thread_id"]])
            if score >= NEAR_MATCH_THRESHOLD and (best is None or score > best[2]):
                best = (l, e, score)
        if best:
            near_pairs.append(best)
            near_local_ids.add(best[0]["thread_id"])
            near_export_ids.add(best[1]["thread_id"])

    local_only = [l for l in unmatched_local if l["thread_id"] not in near_local_ids]
    export_only = [e for e in unmatched_export if e["thread_id"] not in near_export_ids]

    return exact_pairs, near_pairs, local_only, export_only


# ---------------------------------------------------------------------------
# Diff a matched pair
# ---------------------------------------------------------------------------

def compare_pair(conn, local_t: dict, export_t: dict) -> dict:
    lmsgs = load_messages(conn, local_t["thread_id"])
    emsgs = load_messages(conn, export_t["thread_id"])

    l_text = [normalize_text(m["content"]) for m in lmsgs]
    e_text = [normalize_text(m["content"]) for m in emsgs]
    l_roles = [m["role"] for m in lmsgs]
    e_roles = [m["role"] for m in emsgs]

    ratio = difflib.SequenceMatcher(a="\n".join(l_text), b="\n".join(e_text)).ratio()

    return {
        "title": local_t["title"],
        "local_thread_id": local_t["thread_id"], "export_thread_id": export_t["thread_id"],
        "local_message_count": len(lmsgs), "export_message_count": len(emsgs),
        "same_message_count": len(lmsgs) == len(emsgs),
        "same_role_sequence": l_roles == e_roles,
        "content_similarity_ratio": round(ratio, 3),
    }


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

def run(export_account: str = "claude-personal", local_account: str | None = None,
        sample: int = 10) -> dict:
    conn = get_connection()
    try:
        local = load_threads(conn, "claude-local", local_account)
        export = load_threads(conn, "claude", export_account)
        exact_pairs, near_pairs, local_only, export_only = match_threads(local, export)

        diffs = [compare_pair(conn, l, e) for l, e in exact_pairs[:sample]]
    finally:
        conn.close()

    local_only_messages = sum(t["message_count"] for t in local_only)
    export_only_messages = sum(t["message_count"] for t in export_only)

    return {
        "local_account": local_account, "export_account": export_account,
        "local_total": len(local), "export_total": len(export),
        "exact_matches": len(exact_pairs), "near_matches": len(near_pairs),
        "local_only": len(local_only), "local_only_messages": local_only_messages,
        "export_only": len(export_only), "export_only_messages": export_only_messages,
        "diffs_sampled": diffs,
        "near_pairs_sample": [
            {"local_title": l["title"], "export_title": e["title"], "jaccard": round(s, 2)}
            for l, e, s in near_pairs[:sample]
        ],
    }


def report(r: dict) -> None:
    print(f"coherence_check -- local account {r['local_account']!r} vs "
          f"export account {r['export_account']!r}")
    print(f"  local threads:   {r['local_total']}")
    print(f"  export threads:  {r['export_total']}")
    print(f"  exact title matches: {r['exact_matches']}")
    print(f"  near title matches (NOT counted, for review): {r['near_matches']}")
    print(f"  local-only:  {r['local_only']} thread(s), {r['local_only_messages']} message(s)"
          f"  -- the local store's GAIN over the export")
    print(f"  export-only: {r['export_only']} thread(s), {r['export_only_messages']} message(s)"
          f"  -- present in the export, absent from the local store")
    if r["diffs_sampled"]:
        print(f"\n  sampled diffs of {len(r['diffs_sampled'])} exact-title match(es):")
        for d in r["diffs_sampled"]:
            flag = "" if d["same_message_count"] and d["same_role_sequence"] else "  ** DIFFERS **"
            print(f"    {d['title']!r}: local={d['local_message_count']}msg "
                  f"export={d['export_message_count']}msg "
                  f"role_seq_match={d['same_role_sequence']} "
                  f"content_ratio={d['content_similarity_ratio']}{flag}")
    if r["near_pairs_sample"]:
        print(f"\n  near-title matches for human review (not counted as matches):")
        for p in r["near_pairs_sample"]:
            print(f"    local={p['local_title']!r}  export={p['export_title']!r}  "
                  f"jaccard={p['jaccard']}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Phase 3: coherence check, local store vs personal export.")
    ap.add_argument("--export-account", default="claude-personal")
    ap.add_argument("--local-account", default=None,
                    help="defaults to every claude-local-* account found")
    ap.add_argument("--sample", type=int, default=10)
    args = ap.parse_args()
    r = run(args.export_account, args.local_account, args.sample)
    report(r)


if __name__ == "__main__":
    main()
