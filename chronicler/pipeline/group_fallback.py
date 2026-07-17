"""
Layered grouping fallback — build spec item 6 (design doc section 12).

Operates only on messages WHERE thread_id IS NULL left over after
reconcile_gemini.py — i.e. genuine personal Gemini usage that was never
shared/scraped. Three layers run in strict order (A -> B -> C), each
scoped only to what the previous layer left unresolved:

  A. Exact fingerprint  — group by shared source_turn_hash.
  B. Gem-context + idle-gap session segmentation — cheap, no ML.
  C. Semantic similarity (sentence-transformers, local-only) — last resort.

Every layer writes a review_queue row for what it grouped (none of this is
scrape-confirmed) and is idempotent: a message once assigned a non-NULL
thread_id is permanently out of scope for later layers and future reruns.

See chronicler_system_design.md section 12 for the full algorithm.

Usage:
    python3 pipeline/group_fallback.py [--idle-gap-minutes 30]
                                        [--semantic-window-days 14]
                                        [--similarity-threshold 0.6]
                                        [--skip-semantic]
"""
import argparse
import hashlib
import re
from datetime import datetime, timedelta

from db import get_connection, init_db

PARSER_VERSION = "group_fallback_v1"

IDLE_GAP_MINUTES_DEFAULT = 30      # section 7 item 4 — real tunable
SEMANTIC_WINDOW_DAYS_DEFAULT = 14  # ditto
SIMILARITY_THRESHOLD_DEFAULT = 0.6  # section 7 item 3 — explicitly an empirical guess

USED_GEM_RE = re.compile(r"^Used (.+)$")


def synth_id(*parts) -> str:
    return hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()[:32]


def parse_ts(ts):
    if not ts:
        return None
    # Takeout timestamps: e.g. 2026-07-11T17:30:26.464Z
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def fetch_unresolved(cur):
    rows = cur.execute(
        """SELECT message_id, role, content, created_at, source_turn_hash
           FROM messages WHERE thread_id IS NULL
           ORDER BY created_at ASC"""
    ).fetchall()
    return [dict(r) for r in rows]


def ensure_thread_row(cur, thread_id, account, title, created_at, updated_at, gem_name, review_status):
    cur.execute(
        """INSERT INTO threads (thread_id, source, account, title, created_at, updated_at,
                                 gem_name, status, review_status, parser_version)
           VALUES (?, 'gemini', ?, ?, ?, ?, ?, 'open', ?, ?)
           ON CONFLICT(thread_id) DO UPDATE SET
             updated_at=excluded.updated_at""",
        (thread_id, account, title, created_at, updated_at, gem_name, review_status, PARSER_VERSION),
    )


def layer_a_exact_fingerprint(cur, account):
    """12.1 — group unclaimed messages sharing the same source_turn_hash."""
    rows = fetch_unresolved(cur)
    by_hash = {}
    for row in rows:
        if row["source_turn_hash"]:
            by_hash.setdefault(row["source_turn_hash"], []).append(row)

    groups_formed = 0
    for turn_hash, members in by_hash.items():
        if len(members) < 1:
            continue
        thread_id = synth_id("gemini-fingerprint", turn_hash)
        members.sort(key=lambda r: r["created_at"] or "")
        title = (members[0]["content"] or "")[:60] or "Untitled"
        created_at = members[0]["created_at"]
        updated_at = members[-1]["created_at"]

        ensure_thread_row(cur, thread_id, account, title, created_at, updated_at, None, "pending")
        for seq, row in enumerate(members):
            cur.execute(
                "UPDATE messages SET thread_id=?, seq=? WHERE message_id=?",
                (thread_id, seq, row["message_id"]),
            )
        cur.execute(
            """INSERT INTO review_queue (type, thread_id, confidence, status, note, created_at)
               VALUES ('thread_grouping', ?, 1.0, 'pending', ?, datetime('now'))""",
            (thread_id, f"Layer A exact-fingerprint group, {len(members)} messages, hash={turn_hash}"),
        )
        groups_formed += 1

    return groups_formed


def layer_b_gem_context_session(cur, account, idle_gap_minutes):
    """12.2 — gem-context inference from activity_log rows + idle-gap segmentation."""
    rows = fetch_unresolved(cur)
    if not rows:
        return 0

    # Walk chronologically, tracking the most recent "Used <Gem>" context.
    current_gem = None
    tagged = []
    for row in rows:
        if row["role"] == "activity_log":
            m = USED_GEM_RE.match((row["content"] or "").strip())
            if m:
                current_gem = m.group(1).strip()
            continue  # activity_log rows themselves aren't grouped into threads
        tagged.append((row, current_gem))

    groups_formed = 0
    current_group = []
    current_group_gem = None
    prev_dt = None

    def flush():
        nonlocal groups_formed
        if not current_group:
            return
        thread_id = synth_id("gemini-session", current_group[0]["message_id"])
        title = (current_group[0]["content"] or "")[:60] or "Untitled"
        created_at = current_group[0]["created_at"]
        updated_at = current_group[-1]["created_at"]

        # Confidence: tightness of adjacent gaps relative to the idle threshold.
        gaps = []
        for a, b in zip(current_group, current_group[1:]):
            dt_a, dt_b = parse_ts(a["created_at"]), parse_ts(b["created_at"])
            if dt_a and dt_b:
                gaps.append((dt_b - dt_a).total_seconds() / 60.0)
        if gaps:
            avg_gap = sum(gaps) / len(gaps)
            confidence = max(0.0, min(1.0, 1 - (avg_gap / idle_gap_minutes)))
        else:
            confidence = 1.0  # single-message group, nothing to measure

        ensure_thread_row(cur, thread_id, account, title, created_at, updated_at, current_group_gem, "pending")
        for seq, row in enumerate(current_group):
            cur.execute(
                "UPDATE messages SET thread_id=?, seq=? WHERE message_id=?",
                (thread_id, seq, row["message_id"]),
            )
        cur.execute(
            """INSERT INTO review_queue (type, thread_id, confidence, status, note, created_at)
               VALUES ('thread_grouping', ?, ?, 'pending', ?, datetime('now'))""",
            (thread_id, confidence, f"Layer B session group, {len(current_group)} messages, gem={current_group_gem}"),
        )
        groups_formed += 1

    for row, gem in tagged:
        dt = parse_ts(row["created_at"])
        gap_exceeded = (
            prev_dt is not None and dt is not None
            and (dt - prev_dt) > timedelta(minutes=idle_gap_minutes)
        )
        gem_changed = current_group and gem != current_group_gem
        if gap_exceeded or gem_changed:
            flush()
            current_group = []
        current_group.append(row)
        current_group_gem = gem
        prev_dt = dt if dt else prev_dt

    flush()
    return groups_formed


def layer_c_semantic(cur, account, window_days, similarity_threshold):
    """12.3 — sentence-transformers similarity against existing thread anchors."""
    try:
        from sentence_transformers import SentenceTransformer, util
    except ImportError:
        print(
            "  [Layer C skipped] sentence-transformers not installed in this environment.\n"
            "  Install with: pip install sentence-transformers --break-system-packages\n"
            "  (This is expected to work fine on Tim's own machine; not required for A/B to run.)"
        )
        return 0

    rows = fetch_unresolved(cur)
    remaining = [r for r in rows if r["role"] in ("user", "assistant")]
    if not remaining:
        return 0

    model = SentenceTransformer("all-MiniLM-L6-v2")

    threads = cur.execute(
        """SELECT thread_id, updated_at FROM threads WHERE source='gemini' AND account=?"""
    ).fetchall()
    anchors = []  # (thread_id, text, updated_at, embedding)
    for t in threads:
        msgs = cur.execute(
            """SELECT content FROM messages WHERE thread_id=? ORDER BY seq ASC""", (t["thread_id"],)
        ).fetchall()
        if not msgs:
            continue
        text = (msgs[0]["content"] or "") + " " + (msgs[-1]["content"] or "")
        anchors.append({"thread_id": t["thread_id"], "text": text.strip(), "updated_at": t["updated_at"]})

    if not anchors:
        print("  [Layer C] no existing threads to anchor against yet — nothing to do this run.")
        return 0

    anchor_embeddings = model.encode([a["text"] for a in anchors], convert_to_tensor=True)
    groups_formed = 0

    for row in remaining:
        dt = parse_ts(row["created_at"])
        candidate_idxs = list(range(len(anchors)))
        if dt is not None:
            windowed = []
            for i, a in enumerate(anchors):
                a_dt = parse_ts(a["updated_at"])
                if a_dt is None or abs((dt - a_dt).days) <= window_days:
                    windowed.append(i)
            if windowed:
                candidate_idxs = windowed

        row_embedding = model.encode(row["content"] or "", convert_to_tensor=True)
        sims = util.cos_sim(row_embedding, anchor_embeddings[candidate_idxs])[0]
        best_i = int(sims.argmax())
        best_score = float(sims[best_i])
        best_thread = anchors[candidate_idxs[best_i]]["thread_id"]

        if best_score >= similarity_threshold:
            max_seq_row = cur.execute(
                "SELECT COALESCE(MAX(seq), -1) AS m FROM messages WHERE thread_id=?", (best_thread,)
            ).fetchone()
            next_seq = max_seq_row["m"] + 1
            cur.execute(
                "UPDATE messages SET thread_id=?, seq=? WHERE message_id=?",
                (best_thread, next_seq, row["message_id"]),
            )
            cur.execute("UPDATE threads SET updated_at=? WHERE thread_id=?", (row["created_at"], best_thread))
            target_thread = best_thread
        else:
            new_thread_id = synth_id("gemini-singleton", row["message_id"])
            title = (row["content"] or "")[:60] or "Untitled"
            ensure_thread_row(cur, new_thread_id, account, title, row["created_at"], row["created_at"], None, "pending")
            cur.execute(
                "UPDATE messages SET thread_id=?, seq=0 WHERE message_id=?",
                (new_thread_id, row["message_id"]),
            )
            target_thread = new_thread_id

        cur.execute(
            """INSERT INTO review_queue (type, thread_id, confidence, status, note, created_at)
               VALUES ('thread_grouping', ?, ?, 'pending', ?, datetime('now'))""",
            (target_thread, best_score, f"Layer C semantic match, message_id={row['message_id']}"),
        )
        groups_formed += 1

    return groups_formed


def run(idle_gap_minutes, window_days, similarity_threshold, skip_semantic, account):
    init_db()
    conn = get_connection()
    cur = conn.cursor()

    a_count = layer_a_exact_fingerprint(cur, account)
    conn.commit()
    print(f"Layer A (exact fingerprint): {a_count} threads formed")

    b_count = layer_b_gem_context_session(cur, account, idle_gap_minutes)
    conn.commit()
    print(f"Layer B (gem-context + idle-gap): {b_count} threads formed")

    if skip_semantic:
        print("Layer C (semantic similarity): skipped (--skip-semantic)")
        c_count = 0
    else:
        c_count = layer_c_semantic(cur, account, window_days, similarity_threshold)
        conn.commit()
        print(f"Layer C (semantic similarity): {c_count} messages placed")

    remaining = cur.execute(
        "SELECT COUNT(*) AS c FROM messages WHERE thread_id IS NULL"
    ).fetchone()["c"]

    # Item 8 — one summary batch row per invocation (no single raw file to hash).
    cur.execute(
        """INSERT INTO ingestion_log (source, account, file_hash, imported_at,
                                       rows_new, rows_changed, rows_skipped, parser_version)
           VALUES ('gemini', ?, NULL, datetime('now'), ?, 0, ?, ?)""",
        (account, a_count + b_count + c_count, remaining, PARSER_VERSION),
    )
    conn.commit()
    conn.close()
    print(f"Still unresolved (thread_id IS NULL): {remaining}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--idle-gap-minutes", type=int, default=IDLE_GAP_MINUTES_DEFAULT)
    parser.add_argument("--semantic-window-days", type=int, default=SEMANTIC_WINDOW_DAYS_DEFAULT)
    parser.add_argument("--similarity-threshold", type=float, default=SIMILARITY_THRESHOLD_DEFAULT)
    parser.add_argument("--skip-semantic", action="store_true")
    parser.add_argument("--account", default="gemini-personal")
    args = parser.parse_args()
    run(args.idle_gap_minutes, args.semantic_window_days, args.similarity_threshold, args.skip_semantic, args.account)
