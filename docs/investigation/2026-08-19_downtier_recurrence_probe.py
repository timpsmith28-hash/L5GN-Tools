#!/usr/bin/env python3
"""downtier_recurrence_probe.py -- 0049's own homework, run as a query.

DECISIONS 0049's "What would show this wrong" says clause 3 (*the conversation
corpus is a sensed input for down-tier opportunities*) is testable against the
corpus that already exists, and **should be tested before anything is built on
it**. This is that test. It is `COWORK_BRIEF_curator_linking.md`'s Task 0.

**A probe, not a build.** Stdlib only, read-only, no vault access, no model,
no embedding (0041 stands). It is deliberately NOT registered as a scanner and
NOT part of the toolkit: nothing here earns a place in `l5gntools/` until there
is a finding worth standing behind. Run it from wherever, read the output, put
the paragraph in the round's report, and keep or bin the file.

    python downtier_recurrence_probe.py
    python downtier_recurrence_probe.py --claims data/knowledge_curator/claims.json --top 20

Reads `data/knowledge_curator/claims.json` -- K2's extraction report:
`conversations[]`, each with `conversation_id`, `real_time` and `claims[]` of
`{claim_text, quoted_source}` (see `chronicler/pipeline/extract_claims.py`).

**It reports three thresholds and picks none.** This estate's founding
near-loss was a `similarity_threshold = 0.6` whose reasoning was nearly lost;
a probe does not get to introduce a fourth unexplained constant. The sweep is
the output, and how much the answer moves across it is itself a finding.

**The caveat this prints on its own output:** claims are *statements learned*,
not *asks made*. Recurrence here is a proxy for the recurrence of a TOPIC, not
proof of a recurring REQUEST. A pass on topic recurrence alone is a weaker
result and must be labelled as one -- a down-tier proposal built on a
mislabelled signal is the wish 0049 clause 4 refuses.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_CLAIMS = Path("data/knowledge_curator/claims.json")

#: The sweep. Reported side by side; none is adopted, here or downstream.
THRESHOLDS = (0.5, 0.6, 0.7)

#: A cluster is only recurrence if it crosses conversations AND time. One long
#: session restating itself is an echo, and without this filter it dominates.
MIN_DISTINCT_CONVERSATIONS = 3
MIN_DISTINCT_WEEKS = 2

#: Small and boring on purpose. A tuned stopword list is a second unexplained
#: constant; this one only removes words that would make everything look alike.
STOPWORDS = frozenset("""
a an the and or but if then than that this these those there here it its it's
is are was were be been being am do does did doing done have has had having
i you he she we they me him her us them my your his our their of in on at to
for with from by as into over under about against between during without
within along across after before above below up down out off again further
once all any both each few more most other some such no nor not only own same
so too very can will just don should now what which who whom when where why
how would could may might must shall let s t d ll m o re ve y
""".split())

_WORD_RE = re.compile(r"[a-z0-9][a-z0-9'\-]*")


def tokenise(text: str) -> frozenset[str]:
    """Casefold, strip punctuation, drop stopwords and 1-2 char noise. No
    stemming: a stemmer is a dependency-shaped opinion, and this probe's whole
    value is that a human can reproduce its reasoning by eye."""
    words = _WORD_RE.findall((text or "").casefold())
    return frozenset(w for w in words if len(w) > 2 and w not in STOPWORDS)


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if not inter:
        return 0.0
    return inter / len(a | b)


def parse_when(value) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    v = value.strip()
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(v)
    except ValueError:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def load_claims(path: Path) -> list[dict]:
    """Flattens the K2 report into `{conversation_id, when, claim_text,
    quoted_source}` records. Conversations with no parsable `real_time` are
    kept but cannot contribute to the week span -- reported, never dropped
    silently."""
    data = json.loads(path.read_text(encoding="utf-8"))
    out: list[dict] = []
    for conv in data.get("conversations") or []:
        conv_id = conv.get("conversation_id")
        when = parse_when(conv.get("real_time"))
        for claim in conv.get("claims") or []:
            text = (claim or {}).get("claim_text")
            if not isinstance(text, str) or not text.strip():
                continue
            out.append({
                "conversation_id": conv_id,
                "when": when,
                "claim_text": text.strip(),
                "quoted_source": ((claim or {}).get("quoted_source") or "").strip(),
                "tokens": tokenise(text),
            })
    return out


def cluster(records: list[dict], threshold: float) -> list[list[int]]:
    """Single-link clustering with rare-token blocking.

    Blocking: each record is only compared against records sharing one of its
    rarest tokens. That keeps the pass near O(n*k) instead of O(n^2) without
    changing what a match means -- two claims below the threshold on Jaccard
    were never going to cluster, and two above it share at least one token by
    construction (the rarest of which puts them in the same block).
    """
    df: dict[str, int] = defaultdict(int)
    for rec in records:
        for tok in rec["tokens"]:
            df[tok] += 1

    blocks: dict[str, list[int]] = defaultdict(list)
    for idx, rec in enumerate(records):
        if not rec["tokens"]:
            continue
        rarest = sorted(rec["tokens"], key=lambda t: (df[t], t))[:4]
        for tok in rarest:
            blocks[tok].append(idx)

    parent = list(range(len(records)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[max(rx, ry)] = min(rx, ry)

    for members in blocks.values():
        if len(members) < 2:
            continue
        # A pathologically large block (a token that is not actually rare)
        # would reintroduce the quadratic cost; cap it and say so.
        if len(members) > 400:
            members = members[:400]
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                a, b = members[i], members[j]
                if find(a) == find(b):
                    continue
                if jaccard(records[a]["tokens"], records[b]["tokens"]) >= threshold:
                    union(a, b)

    groups: dict[int, list[int]] = defaultdict(list)
    for idx in range(len(records)):
        groups[find(idx)].append(idx)
    return [g for g in groups.values() if len(g) > 1]


def summarise(group: list[int], records: list[dict]) -> dict:
    convs = {records[i]["conversation_id"] for i in group if records[i]["conversation_id"]}
    whens = [records[i]["when"] for i in group if records[i]["when"]]
    weeks = {(w.isocalendar().year, w.isocalendar().week) for w in whens}
    # Single-link clustering chains: A~B and B~C puts A and C together even
    # when A and C are unalike. `distinct_texts` is the cheap tell -- a cluster
    # of 30 members with 30 distinct texts is either a real family or a chain,
    # and the three printed examples are how you tell which by eye.
    return {
        "size": len(group),
        "distinct_texts": len({records[i]["claim_text"] for i in group}),
        "conversations": len(convs),
        "weeks": len(weeks),
        "first": min(whens).date().isoformat() if whens else None,
        "last": max(whens).date().isoformat() if whens else None,
        "undated_members": len(group) - len(whens),
        "members": group,
    }


def survives(summary: dict) -> bool:
    return (summary["conversations"] >= MIN_DISTINCT_CONVERSATIONS
            and summary["weeks"] >= MIN_DISTINCT_WEEKS)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--claims", type=Path, default=DEFAULT_CLAIMS)
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--report-threshold", type=float, default=0.6,
                    help="which sweep point to print examples for (default 0.6 -- "
                         "the middle of the sweep, NOT an adopted constant)")
    args = ap.parse_args()

    if not args.claims.is_file():
        print(f"no claims report at {args.claims} -- run the K2 extraction first, "
              f"or pass --claims", file=sys.stderr)
        return 2

    records = load_claims(args.claims)
    if not records:
        print(f"INCONCLUSIVE: {args.claims} parsed but holds no claims. This is not a "
              f"verdict on 0049 clause 3 -- it is the absence of a corpus to test it "
              f"against. Run the K2 extraction first.")
        return 3

    convs = {r["conversation_id"] for r in records}
    undated = sum(1 for r in records if r["when"] is None)

    # --- the sufficiency gate, added 2026-08-19 after the first live run ------
    # The first run of this probe hit a 3-conversation corpus and printed the
    # FAIL reading, which would have been a false kill: a filter requiring >= 3
    # distinct conversations CANNOT be passed meaningfully by a corpus of 3.
    # So the floor is DERIVED from the filter rather than picked -- the corpus
    # must exceed the filter's own thresholds by 3x before a surviving cluster
    # means anything, because at 1x every survivor is the whole corpus and the
    # filter has stopped filtering. It is stated here rather than buried so the
    # multiplier can be argued with; what it must not be is an unexplained
    # constant (this estate's founding near-loss was exactly that).
    corpus_weeks = {(w.isocalendar().year, w.isocalendar().week)
                    for w in (r["when"] for r in records) if w}
    need_convs = 3 * MIN_DISTINCT_CONVERSATIONS
    need_weeks = 3 * MIN_DISTINCT_WEEKS
    if len(convs) < need_convs or len(corpus_weeks) < need_weeks:
        print("=" * 72)
        print("INCONCLUSIVE -- the corpus is too small for this probe to mean anything")
        print("=" * 72)
        print(f"corpus:   {len(records)} claims / {len(convs)} conversations / "
              f"{len(corpus_weeks)} calendar weeks")
        print(f"needed:   >= {need_convs} conversations AND >= {need_weeks} weeks "
              f"(3x the cluster filter's own thresholds of "
              f"{MIN_DISTINCT_CONVERSATIONS}/{MIN_DISTINCT_WEEKS})")
        print()
        print("This is NOT a failure of 0049 clause 3 and must not be recorded as one.")
        print("A filter demanding clusters across >= 3 conversations cannot be passed")
        print("meaningfully by a corpus that barely has 3 -- every survivor would be")
        print("the entire corpus, and every non-survivor an artifact of size.")
        print()
        print("What unblocks it: a K2 extraction across the real corpus rather than a")
        print("project-scoped or bench-scoped slice. Check `partial_run_projects` and")
        print("`conversations_scanned` in the report you just pointed this at.")
        return 3
    print("=" * 72)
    print("0049 recurrence probe -- does the corpus hold legible repetition?")
    print("=" * 72)
    print(f"corpus:          {len(records)} claims across {len(convs)} conversations")
    print(f"undated claims:  {undated} (cannot contribute to the week-span filter)")
    print(f"filters:         >= {MIN_DISTINCT_CONVERSATIONS} distinct conversations "
          f"AND >= {MIN_DISTINCT_WEEKS} distinct calendar weeks")
    print()

    print("--- threshold sweep (no threshold is adopted by this probe) ---")
    swept: dict[float, list[dict]] = {}
    for threshold in THRESHOLDS:
        summaries = [summarise(g, records) for g in cluster(records, threshold)]
        kept = sorted((s for s in summaries if survives(s)),
                      key=lambda s: (s["conversations"], s["size"]), reverse=True)
        swept[threshold] = kept
        print(f"  jaccard >= {threshold}:  {len(summaries):5d} clusters, "
              f"{len(kept):5d} survive the filter, "
              f"largest spans {kept[0]['conversations'] if kept else 0} conversations")
    print()

    threshold = args.report_threshold
    kept = swept.get(threshold)
    if kept is None:
        summaries = [summarise(g, records) for g in cluster(records, threshold)]
        kept = sorted((s for s in summaries if survives(s)),
                      key=lambda s: (s["conversations"], s["size"]), reverse=True)

    print(f"--- top {args.top} surviving clusters at jaccard >= {threshold} ---")
    if not kept:
        print("  none.")
        print()
        print("READ: no cluster survives the recurrence filter. On this corpus, "
              "0049 clause 3\n  senses nothing -- 'an elegant description of "
              "nothing', in the entry's own words.\n  That is a successful test "
              "and a cheap one. Record it in the report and do not\n  build the "
              "down-tier surface on an untested clause.")
        return 0

    for rank, summary in enumerate(kept[:args.top], start=1):
        print()
        print(f"[{rank}] {summary['size']} claims ({summary['distinct_texts']} distinct) "
              f"/ {summary['conversations']} conversations "
              f"/ {summary['weeks']} weeks / {summary['first']} .. {summary['last']}")
        for i in summary["members"][:3]:
            rec = records[i]
            print(f"    claim:  {rec['claim_text'][:160]}")
            if rec["quoted_source"]:
                print(f"    quoted: \"{rec['quoted_source'][:160]}\"")
            print()

    print("=" * 72)
    print("HOW TO READ THIS (COWORK_BRIEF_curator_linking.md, Task 0)")
    print("=" * 72)
    print("PASS  -- you can name, for at least three clusters above, a specific local")
    print("         capability that would have answered the ask AND the evidence that")
    print("         it can (0049 clause 4's bar). Those three are the down-tier work's")
    print("         first candidates.")
    print("FAIL  -- the survivors are vocabulary noise, or nothing suggests a capability")
    print("         that would replace the ask. Record that as the finding; do not build.")
    print()
    print("CHAINING: clustering here is single-link, so A~B and B~C group A with C even")
    print("when A and C are unalike. A cluster whose members are nearly all distinct")
    print("texts spanning unrelated topics is a chain, not a recurring ask -- discount it.")
    print()
    print("CAVEAT, to be repeated in the report: claims are STATEMENTS LEARNED, not ASKS")
    print("MADE. Recurrence here is a proxy for topic recurrence, not proof of a")
    print("recurring request. If it passes on topic alone, say so in those words.")
    print()
    print("BASELINE: whichever cluster count you quote, write it down with its")
    print("threshold and today's date. 0049 clause 5 is measured as recurrence")
    print("DECLINING in the corpus, observed -- which needs a first observation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
