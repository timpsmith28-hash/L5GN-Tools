"""
Gemini reconciliation join — build spec item 5 (design doc section 11).

Joins share-scrape skeletons (scraped_gemini/<share_id>.json — correct turn
order/boundaries, no native ID, often no usable timestamp) against
unresolved Takeout messages (thread_id IS NULL — real UTC timestamps and
content, no thread boundary) written by normalize_gemini_personal.py.
Assigns a synthetic thread_id + seq to every Takeout row it can confidently
match, inheriting the skeleton's order as ground truth.

See chronicler_system_design.md section 11 for the full algorithm this
implements (matching order, thresholds, review_queue rules).

Usage:
    python3 pipeline/reconcile_gemini.py [--scraped-dir PATH] [--force]
                                          [--fuzzy-threshold 0.90]
"""
import argparse
import difflib
import hashlib
import json
import re
from pathlib import Path

from db import get_connection, init_db, CHRONICLER_ROOT

PARSER_VERSION = "reconcile_v1"
ACCOUNT_LABEL = "gemini-personal"
DEFAULT_SCRAPED_DIR = CHRONICLER_ROOT / "scraped_gemini"

# Confirmed live bug in scrape_gemini_share.py's extract_title() — all 4
# current samples fall back to the raw browser tab title. Worked around
# here per 11.4 rather than re-deriving extract_title() (separate item).
FALLBACK_TITLE = "\u200eGemini - direct access to Google AI"

FUZZY_THRESHOLD_DEFAULT = 0.90   # section 7 item 4 — real tunable, not a solved constant
EXACT_RATIO_THRESHOLD = 0.97     # below this, a claimed match is logged as "fuzzy" for review

ROLE_MAP = {"model": "assistant", "user": "user"}


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def synth_id(*parts) -> str:
    return hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()[:32]


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def share_id_from_url(url: str) -> str:
    return url.rstrip("/").rsplit("/", 1)[-1]


def load_skeleton(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_unclaimed(cur):
    """Every Takeout row still awaiting reconciliation, keyed for matching.
    Content is pre-normalized once here (row["_norm"]) rather than inside
    the matching hot loop, which otherwise re-normalizes the same rows on
    every skeleton-message comparison."""
    rows = cur.execute(
        """SELECT message_id, role, content, created_at, source_turn_hash
           FROM messages
           WHERE thread_id IS NULL AND role IN ('user','assistant')"""
    ).fetchall()
    out = [dict(r) for r in rows]
    for row in out:
        row["_norm"] = normalize(row["content"])
    return out


def build_exact_index(pool, claimed_ids):
    index = {}
    for row in pool:
        if row["message_id"] in claimed_ids:
            continue
        key = (row["role"], row["_norm"])
        index.setdefault(key, []).append(row)
    return index


def best_fuzzy_match(norm_content, role, pool, claimed_ids, fuzzy_threshold, window=None):
    """window, if given, is a (start_iso, end_iso) string range to restrict
    candidates to (11.3 step 2 — hash-anchor bracketing). None = full pool
    (11.3 step 6 — no anchors available, current reality until item 4 lands
    attachment/hash data into skeleton JSON).

    Full SequenceMatcher.ratio() over a multi-thousand-row pool of
    sometimes multi-KB messages is too slow to run pairwise unfiltered
    (each call is roughly O(len_a * len_b)). Filters, cheapest first: a
    length-ratio gate, then SequenceMatcher's own real_quick_ratio() and
    quick_ratio() upper bounds before ever paying for a full ratio().

    Critically, the floor for those upper-bound checks is fuzzy_threshold,
    not 0.0 — any match below fuzzy_threshold gets discarded by the caller
    anyway, so there's no reason to let a weak candidate raise the running
    best_ratio and no reason to pay for ratio() on a candidate whose cheap
    upper bound already can't clear the threshold. Seeding best_ratio at
    0.0 (an earlier version of this function) made the upper-bound filters
    nearly useless in practice: the first few hundred candidates would
    always pass since anything beats 0.0, so most of the pool still hit the
    expensive full ratio() call. Seeding at the threshold turns these into
    genuinely effective, cheap pre-filters.

    Pool rows carry pre-normalized content (row["_norm"]) so normalize()
    never re-runs per comparison.
    """
    best = None
    best_ratio = fuzzy_threshold  # floor — sub-threshold candidates are useless to us
    found = False
    len_a = len(norm_content)
    matcher = difflib.SequenceMatcher()
    matcher.set_seq2(norm_content)

    for row in pool:
        if row["message_id"] in claimed_ids or row["role"] != role:
            continue
        if window and row["created_at"] is not None:
            if not (window[0] <= row["created_at"] <= window[1]):
                continue

        candidate = row["_norm"]
        len_b = len(candidate)
        if len_a and len_b:
            shorter, longer = (len_a, len_b) if len_a < len_b else (len_b, len_a)
            if shorter / longer < 0.5:  # cheap length gate — can't hit 0.90 ratio if this far apart
                continue
        elif len_a != len_b:
            continue

        matcher.set_seq1(candidate)
        if matcher.real_quick_ratio() <= best_ratio:
            continue  # cheap O(1) length-based upper bound already at/below floor — skip
        if matcher.quick_ratio() <= best_ratio:
            continue  # cheap O(n) char-histogram upper bound already at/below floor — skip

        ratio = matcher.ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best = row
            found = True

    return (best, best_ratio) if found else (None, 0.0)


def find_hash_anchors(messages):
    """Section 11.3 step 1/2 — forward-compatible with item 4's attachment
    extension. Current scraped_gemini/*.json has no per-message attachment
    data yet, so this returns an empty dict today; once the scraper is
    extended, messages carrying a `turn_hash` will anchor the bracket
    windows below automatically, no changes needed here."""
    anchors = {}
    for i, msg in enumerate(messages):
        for att in msg.get("attachments") or []:
            if att.get("turn_hash"):
                anchors[i] = att["turn_hash"]
                break
    return anchors


def match_skeleton(messages, pool, claimed_ids, fuzzy_threshold):
    """Returns a list of dicts, one per skeleton message, per section 11.3-11.4."""
    hash_anchors = find_hash_anchors(messages)
    has_any_anchor = bool(hash_anchors)

    # Pre-resolve anchor timestamps against the pool, for windowing (11.3 step 2).
    anchor_positions = {}
    if has_any_anchor:
        by_hash = {}
        for row in pool:
            if row["source_turn_hash"]:
                by_hash.setdefault(row["source_turn_hash"], []).append(row)
        for idx, h in hash_anchors.items():
            candidates = [r for r in by_hash.get(h, []) if r["message_id"] not in claimed_ids]
            if candidates:
                anchor_positions[idx] = candidates[0]

    results = []
    exact_index = build_exact_index(pool, claimed_ids)

    def window_for(i):
        if not anchor_positions:
            return None
        before = [pos for idx, pos in anchor_positions.items() if idx <= i]
        after = [pos for idx, pos in anchor_positions.items() if idx >= i]
        if not before or not after:
            return None
        start = min(r["created_at"] for r in before if r["created_at"])
        end = max(r["created_at"] for r in after if r["created_at"])
        if not start or not end:
            return None
        return (start, end)

    for i, msg in enumerate(messages):
        role = ROLE_MAP.get(msg.get("role"), msg.get("role"))
        norm_content = normalize(msg.get("content"))
        matched_row = None
        ratio = 0.0

        # Step 1: direct hash anchor claim.
        if i in anchor_positions and anchor_positions[i]["message_id"] not in claimed_ids:
            matched_row = anchor_positions[i]
            ratio = 1.0
        else:
            # Step 3: exact normalized-content match (optionally windowed).
            key = (role, norm_content)
            candidates = [r for r in exact_index.get(key, []) if r["message_id"] not in claimed_ids]
            win = window_for(i)
            if win:
                candidates = [r for r in candidates if r["created_at"] and win[0] <= r["created_at"] <= win[1]]
            if candidates:
                matched_row = candidates[0]
                ratio = 1.0
            else:
                # Step 4: fuzzy fallback.
                matched_row, ratio = best_fuzzy_match(
                    norm_content, role, pool, claimed_ids, fuzzy_threshold, window=win
                )

        if matched_row:
            claimed_ids.add(matched_row["message_id"])

        results.append({
            "index": i,
            "role": role,
            "message_id": matched_row["message_id"] if matched_row else None,
            "created_at": matched_row["created_at"] if matched_row else None,
            "ratio": ratio,
        })

    return results, has_any_anchor


def derive_title(skeleton_title, first_matched_content):
    if not skeleton_title or skeleton_title.strip() == FALLBACK_TITLE:
        return normalize(first_matched_content)[:60] or "Untitled"
    return skeleton_title


def already_reconciled(cur, raw_ref):
    row = cur.execute(
        "SELECT 1 FROM threads WHERE source='gemini' AND raw_ref=? LIMIT 1", (raw_ref,)
    ).fetchone()
    return row is not None


def process_skeleton(cur, path: Path, fuzzy_threshold: float):
    skeleton = load_skeleton(path)
    share_id = share_id_from_url(skeleton.get("share_url") or path.stem)
    raw_ref = str(path.relative_to(CHRONICLER_ROOT))

    if already_reconciled(cur, raw_ref):
        return None  # idempotent — already processed in a prior run

    messages = skeleton.get("messages") or []
    if not messages:
        return None

    pool = fetch_unclaimed(cur)
    claimed_ids = set()
    matches, has_any_anchor = match_skeleton(messages, pool, claimed_ids, fuzzy_threshold)

    claimed = [m for m in matches if m["message_id"]]
    match_rate = len(claimed) / len(matches) if matches else 0.0

    thread_id = synth_id("gemini-share", share_id)
    first_content = next((m.get("content") for m in messages if m.get("role") == "user"), "")
    matched_contents = [messages[m["index"]]["content"] for m in claimed]
    title = derive_title(skeleton.get("title"), matched_contents[0] if matched_contents else first_content)

    timestamps = [m["created_at"] for m in claimed if m["created_at"]]
    created_at = min(timestamps) if timestamps else None
    updated_at = max(timestamps) if timestamps else None

    # 11.3 step 6 — zero anchors anywhere in this skeleton -> always pending,
    # regardless of match rate (collision risk with no time window at all).
    review_status = "pending" if (not has_any_anchor or match_rate < 1.0) else "auto"

    cur.execute(
        """INSERT INTO threads (thread_id, source, account, title, created_at, updated_at,
                                 gem_name, is_custom_gem, status, review_status, raw_ref, parser_version)
           VALUES (?, 'gemini', ?, ?, ?, ?, ?, ?, 'open', ?, ?, ?)
           ON CONFLICT(thread_id) DO UPDATE SET
             updated_at=excluded.updated_at, review_status=excluded.review_status""",
        (
            thread_id, ACCOUNT_LABEL, title, created_at, updated_at,
            skeleton.get("gem_name"), 1 if skeleton.get("is_custom_gem") else 0,
            review_status, raw_ref, PARSER_VERSION,
        ),
    )

    # 11.4 — seq is skeleton position, never the matched timestamp's order.
    for m in claimed:
        cur.execute(
            "UPDATE messages SET thread_id=?, seq=? WHERE message_id=?",
            (thread_id, m["index"], m["message_id"]),
        )

    # 11.5 — confidence / review_queue writes.
    if match_rate < 1.0:
        gaps = [str(m["index"]) for m in matches if not m["message_id"]]
        cur.execute(
            """INSERT INTO review_queue (type, thread_id, confidence, status, note, created_at)
               VALUES ('reconciliation_gap', ?, ?, 'pending', ?, datetime('now'))""",
            (thread_id, match_rate, f"Unmatched skeleton indices: {', '.join(gaps)}"),
        )

    for m in claimed:
        if m["ratio"] < EXACT_RATIO_THRESHOLD:
            cur.execute(
                """INSERT INTO review_queue (type, thread_id, confidence, status, note, created_at)
                   VALUES ('reconciliation_fuzzy_match', ?, ?, 'pending', ?, datetime('now'))""",
                (thread_id, m["ratio"], f"Skeleton index {m['index']} matched at ratio {m['ratio']:.3f}"),
            )

    ordered_ts = [m["created_at"] for m in claimed if m["created_at"]]
    if ordered_ts != sorted(ordered_ts):
        cur.execute(
            """INSERT INTO review_queue (type, thread_id, confidence, status, note, created_at)
               VALUES ('reconciliation_order_conflict', ?, NULL, 'pending', ?, datetime('now'))""",
            (thread_id, "Matched timestamps are not monotonically increasing across seq order."),
        )

    # Item 8 — log this skeleton's ingestion as its own batch.
    cur.execute(
        """INSERT INTO ingestion_log (source, account, file_hash, imported_at,
                                       rows_new, rows_changed, rows_skipped, parser_version)
           VALUES ('gemini', ?, ?, datetime('now'), ?, 0, ?, ?)""",
        (
            ACCOUNT_LABEL, file_hash(path), len(claimed),
            len(messages) - len(claimed), PARSER_VERSION,
        ),
    )

    return {
        "share_id": share_id,
        "thread_id": thread_id,
        "message_count": len(messages),
        "matched": len(claimed),
        "match_rate": match_rate,
        "review_status": review_status,
    }


def run(scraped_dir: Path, force: bool, fuzzy_threshold: float):
    init_db()
    conn = get_connection()
    cur = conn.cursor()

    if force:
        # Allow explicit reprocessing: drop prior threads/claims for these skeletons first.
        for path in sorted(scraped_dir.glob("*.json")):
            skeleton = load_skeleton(path)
            share_id = share_id_from_url(skeleton.get("share_url") or path.stem)
            thread_id = synth_id("gemini-share", share_id)
            cur.execute("UPDATE messages SET thread_id=NULL, seq=NULL WHERE thread_id=?", (thread_id,))
            cur.execute("DELETE FROM review_queue WHERE thread_id=?", (thread_id,))
            cur.execute("DELETE FROM threads WHERE thread_id=?", (thread_id,))

    results = []
    for path in sorted(scraped_dir.glob("*.json")):
        result = process_skeleton(cur, path, fuzzy_threshold)
        if result:
            results.append(result)

    conn.commit()
    conn.close()

    print(f"Skeletons processed: {len(results)}")
    for r in results:
        print(
            f"  {r['share_id']}: {r['matched']}/{r['message_count']} matched "
            f"({r['match_rate']:.0%}), review_status={r['review_status']}"
        )
    if not results:
        print("  (nothing new — all skeletons already reconciled; use --force to redo)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scraped-dir", type=Path, default=DEFAULT_SCRAPED_DIR)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--fuzzy-threshold", type=float, default=FUZZY_THRESHOLD_DEFAULT)
    args = parser.parse_args()
    run(args.scraped_dir, args.force, args.fuzzy_threshold)
