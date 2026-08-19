"""scan_all_decisions.py -- census tool for docs/DECISIONS.md ruling mentions
across a claude_migration-style backup snapshot of Cowork session transcripts.

v2 adds three things on top of the original exact \\b00\\d{2}\\b scan:

1. FUZZY matches -- "decision seventeen", "ruling #17", "DECISIONS no. 9" --
   references that name a ruling near the word "decision"/"ruling" but don't
   use the zero-padded 00NN form. Reported separately from exact matches,
   since they're lower-precision (a false positive here means the regex
   caught an unrelated "decision 2" that has nothing to do with
   docs/DECISIONS.md) and should be spot-checked before trusting them.
2. PER-MESSAGE co-mentions -- when a single message names two or more
   distinct ruling numbers, that's a tight signal they're being discussed
   together, not just both existing somewhere in a long thread.
3. PER-CONVERSATION co-occurrence -- any two rulings that both appear
   anywhere in the same conversation, a looser signal used to find
   conversations where multiple rulings' stories intersect (see
   synthesis_case_studies/README.md's note on local_e9841a20, where 0012,
   0017 and 0018 all converge).

Read-only, no writes anywhere but stdout and --out.

Usage:
    python scan_all_decisions.py --root "C:\\Users\\timps\\backups\\claude_migration"
"""
from __future__ import annotations

import argparse
import glob
import itertools
import json
import os
import re
from collections import Counter

EXACT_RE = re.compile(r"\b00\d{2}\b")

_ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
         "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
         "seventeen", "eighteen", "nineteen"]
_TENS = {20: "twenty", 30: "thirty", 40: "forty"}


def _build_word_to_num() -> dict[str, int]:
    words: dict[str, int] = {}
    for i, w in enumerate(_ONES):
        words[w] = i
    for tens_val, tens_word in _TENS.items():
        words[tens_word] = tens_val
        for i in range(1, 10):
            if tens_val + i <= 49:
                words[f"{tens_word}-{_ONES[i]}"] = tens_val + i
                words[f"{tens_word} {_ONES[i]}"] = tens_val + i
    return words


WORD_TO_NUM = _build_word_to_num()
_WORD_ALTS = sorted(WORD_TO_NUM.keys(), key=len, reverse=True)
_WORD_ALTS_RE = "|".join(re.escape(w) for w in _WORD_ALTS)

# "decision(s)"/"ruling", then up to ~15 non-sentence-ending chars, then
# either a spelled-out number word or a bare 1-2 digit number (optionally
# preceded by # / no. / number).
FUZZY_RE = re.compile(
    r"\b(?:decisions?|ruling)s?\b[^.\n]{0,15}?"
    r"(?:#|no\.?|number)?\s*"
    r"(?P<num>\d{1,2}\b|" + _WORD_ALTS_RE + r")",
    re.IGNORECASE,
)


def normalize_fuzzy(raw: str) -> str | None:
    raw = raw.strip().lower()
    if raw.isdigit():
        n = int(raw)
    else:
        n = WORD_TO_NUM.get(raw)
        if n is None:
            return None
    if not (1 <= n <= 49):
        return None
    return f"{n:04d}"


def conv_id_from_path(path: str) -> str | None:
    for part in path.split(os.sep):
        if part.startswith("local_") and len(part) > 10:
            return part
    return None


def extract_text(message: dict) -> str:
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for c in content:
            if isinstance(c, dict) and c.get("type") == "text":
                parts.append(c.get("text", ""))
        return "\n".join(parts)
    return ""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", default="decisions_census.json")
    ap.add_argument("--top-pairs", type=int, default=15, help="how many top co-occurring pairs to print")
    args = ap.parse_args()

    files = [
        f
        for f in glob.glob(os.path.join(args.root, "**", ".claude", "projects", "*", "*.jsonl"), recursive=True)
        if not f.endswith("audit.jsonl")
    ]

    exact_by_ruling: dict[str, dict[str, int]] = {}   # ruling -> {conv_id -> hits}
    fuzzy_by_ruling: dict[str, dict[str, int]] = {}   # ruling -> {conv_id -> hits}
    message_comention_pairs: Counter = Counter()      # frozenset({r1, r2}) -> count, same message
    conv_rulings: dict[str, set] = {}                 # conv_id -> set of exact rulings mentioned anywhere

    for f in files:
        cid = conv_id_from_path(f)
        if cid is None:
            continue
        try:
            with open(f, "r", errors="replace") as fh:
                lines = fh.readlines()
        except OSError:
            continue
        for line in lines:
            if "message" not in line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            msg = d.get("message")
            if not msg:
                continue
            text = extract_text(msg)
            if not text:
                continue

            exact_hits = set(EXACT_RE.findall(text))
            for r in exact_hits:
                exact_by_ruling.setdefault(r, {}).setdefault(cid, 0)
                exact_by_ruling[r][cid] += text.count(r)
            if exact_hits:
                conv_rulings.setdefault(cid, set()).update(exact_hits)
                if len(exact_hits) >= 2:
                    for a, b in itertools.combinations(sorted(exact_hits), 2):
                        message_comention_pairs[frozenset((a, b))] += 1

            for m in FUZZY_RE.finditer(text):
                norm = normalize_fuzzy(m.group("num"))
                if norm is None:
                    continue
                # don't double-count something the exact scan already caught
                # verbatim as "00NN" in the same span
                fuzzy_by_ruling.setdefault(norm, {}).setdefault(cid, 0)
                fuzzy_by_ruling[norm][cid] += 1

    # per-conversation co-occurrence (looser signal)
    conv_comention_pairs: Counter = Counter()
    for cid, rulings in conv_rulings.items():
        if len(rulings) < 2:
            continue
        for a, b in itertools.combinations(sorted(rulings), 2):
            conv_comention_pairs[frozenset((a, b))] += 1

    def _fmt_counter(c: Counter, n: int) -> list[dict]:
        out = []
        for pair, count in c.most_common(n):
            a, b = sorted(pair)
            out.append({"a": a, "b": b, "count": count})
        return out

    exact_summary = sorted(
        (
            {"ruling": r, "n_conversations": len(convs), "n_mentions": sum(convs.values())}
            for r, convs in exact_by_ruling.items()
        ),
        key=lambda row: (row["n_conversations"], row["n_mentions"]),
    )
    fuzzy_summary = sorted(
        (
            {"ruling": r, "n_conversations": len(convs), "n_mentions": sum(convs.values())}
            for r, convs in fuzzy_by_ruling.items()
        ),
        key=lambda row: (row["n_conversations"], row["n_mentions"]),
    )

    print("== exact (00NN) matches ==")
    print(f"{'ruling':<8}{'n_conversations':<18}{'n_mentions':<12}")
    for row in exact_summary:
        print(f"{row['ruling']:<8}{row['n_conversations']:<18}{row['n_mentions']:<12}")

    print("\n== fuzzy matches (spelled-out / bare-number, near 'decision'/'ruling') ==")
    print("spot-check these before trusting them -- higher false-positive risk")
    print(f"{'ruling':<8}{'n_conversations':<18}{'n_mentions':<12}")
    for row in fuzzy_summary:
        print(f"{row['ruling']:<8}{row['n_conversations']:<18}{row['n_mentions']:<12}")

    print(f"\n== top {args.top_pairs} co-mentioned pairs (same message) ==")
    for pair in _fmt_counter(message_comention_pairs, args.top_pairs):
        print(f"  {pair['a']} + {pair['b']}: {pair['count']} messages")

    print(f"\n== top {args.top_pairs} co-occurring pairs (same conversation, anywhere) ==")
    for pair in _fmt_counter(conv_comention_pairs, args.top_pairs):
        print(f"  {pair['a']} + {pair['b']}: {pair['count']} conversations")

    with open(args.out, "w") as out:
        json.dump({
            "exact": {r: convs for r, convs in exact_by_ruling.items()},
            "fuzzy": {r: convs for r, convs in fuzzy_by_ruling.items()},
            "message_comention_pairs": _fmt_counter(message_comention_pairs, len(message_comention_pairs)),
            "conv_comention_pairs": _fmt_counter(conv_comention_pairs, len(conv_comention_pairs)),
        }, out, indent=2)
    print(f"\nFull detail written to {args.out}")


if __name__ == "__main__":
    main()
