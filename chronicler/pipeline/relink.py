"""
S6 - Re-Link Pass (the consumer / the engine).

Combines all available evidence into thread->project link decisions. Replaces
"link once at ingest, frozen forever" with "links improve as evidence
accumulates." Runs nightly; idempotent (a second run with no new evidence is a
no-op).

WHAT THIS PASS DOES
-------------------
Per thread, per candidate project it combines:

  * every persisted `link_evidence` row (filename_xref today; path_mention,
    vocabulary, time_window automatically as S2/S3/S5 start writing them), and
  * name/alias signals computed inline here from the registry aliases against
    the thread title (0.8) and body (0.6) - cheap, so not persisted separately,
    EXCEPT that when an alias signal helps *win* an auto-link we persist it so
    the decision's evidence chain has stable ids to point at.

Scoring (spec S6):
    score    = 1 - Prod(1 - weight_i)          # independent-evidence combination
    adjusted = score * time_plausibility(thread_date, project)

Every individual weight is capped at CAP (0.97) before combination so no single
signal is ever absolute. time_plausibility (S3, build_activity.py) is now LIVE:
it discounts candidates whose activity window doesn't contain the thread's date,
which is what separates same-vocabulary projects worked on in different eras
(e.g. legacy `v1 proto` vs current `L5GN_Armory_v4`). Undated threads take a
neutral 0.7 (never 1.0) and are flagged `time:unknown` in the evidence summary.

Decision rules (spec S6):
    adjusted >= 0.90 AND best leads 2nd-best by >= 0.25 -> AUTO-LINK
        project_confidence := 'evidence'; informational 'link_upgrade' row.
    two candidates both >= 0.60 within 0.25 of each other -> AMBIGUOUS
        queued 'link_ambiguous' with BOTH evidence sets. Never guess.
    adjusted >= 0.60 (single, clear) -> SUGGESTION
        queued 'project_link' pending, evidence list in the note.
    existing 'fuzzy' link -> re-scored: upgraded to 'evidence' if its own
        project clears the bar; DOWNGRADED (queued 'link_downgrade', pending)
        if new evidence points at a *different* project. old + new both shown.

AUTHORITY (who may overwrite what)
----------------------------------
    none < fuzzy < evidence < manual        ('exact' protected like 'manual')
Automation may create links on none/fuzzy threads and upgrade fuzzy->evidence.
It NEVER touches 'manual', 'exact', or 'evidence' links - only a human may
change an 'evidence' link. Because winners become 'evidence', the next run
skips them, which is what makes the pass idempotent.

Winning evidence ids are stored on the thread (`link_evidence_ids`, JSON), so
every automated link is inspectable after the fact.

Standing rules: --dry-run is the DEFAULT (same as bulk_review.py) - nothing is
written without --apply. Loud failure, UTF-8, UTC ISO-8601, single write
transaction. Manual/human-ruled rows are never auto-modified.

Usage:
    python3 pipeline/relink.py                 # dry-run (default): decision table only
    python3 pipeline/relink.py --apply         # write decisions
    python3 pipeline/relink.py --no-content-scan   # skip the alias-in-body scan (faster)
    python3 pipeline/relink.py --limit 50      # (dry-run) cap threads scanned, for spot checks
    python3 pipeline/relink.py --out relink_dryrun.txt   # also write report as UTF-8
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone

# Print clean UTF-8 regardless of the console codepage (Windows cp1252 chokes on
# emoji in thread titles; a shell redirect once produced UTF-16). This makes the
# report bytes deterministic; --out additionally writes an explicit UTF-8 file.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

from db import get_connection, CHRONICLER_ROOT, DB_PATH
# S3 time signal (replaces the old 1.0 stub): live plausibility + date parsing.
from build_activity import time_plausibility, parse_thread_date

GITHUB_ROOT_FS = CHRONICLER_ROOT.parent.parent
REGISTRY_PATH = GITHUB_ROOT_FS / "L5GN" / ".intel_sync" / "project_registry.json"
SCOPE_TO_ROOT = {"l5gn": "L5GN", "mcf": "MCF"}

PRODUCER_VERSION = "relink/1.0"

# ---------------------------------------------------------------------------
# ONE config block - every tunable lives here (spec S6: "tunable in one config
# block at the top of the script"). Starting values are the spec's.
# ---------------------------------------------------------------------------
CAP = 0.97                 # per-weight cap: no single signal is ever absolute
AUTO_LINK_THRESHOLD = 0.90 # adjusted score to auto-link
LEAD_MARGIN = 0.25         # best must beat 2nd-best by this to auto-link / avoid ambiguity
SUGGEST_THRESHOLD = 0.60   # adjusted score to queue a suggestion

# Inline signal weights (persisted signals carry their own weight from S4/S5).
WEIGHT_ALIAS_TITLE = 0.8
WEIGHT_ALIAS_CONTENT = 0.6
# Fix B: for projects flagged `low_signal_body` in the registry (meta-tools like
# Chronicler that get name-dropped inside conversations about *other* projects),
# an alias found only in the message BODY is near-worthless as a link signal.
# Title and filename matches are unaffected. This is a registry data decision -
# relink reads the flag; no project name is ever hardcoded here.
WEIGHT_ALIAS_CONTENT_LOWSIG = 0.15

# Per-signal-type "count only the strongest N" caps. Spec: vocabulary hits
# count max 3. Others uncapped (weight cap still applies to each).
SIGNAL_COUNT_CAP = {"vocabulary": 3}

MIN_ALIAS_LEN = 3          # ignore 1-2 char aliases as inline matchers (noise)

# Confidence values automation must never overwrite.
PROTECTED_CONFIDENCE = {"manual", "exact"}
# Automation-owned but human-locked once set (only a human may change these).
LOCKED_CONFIDENCE = {"evidence"}
# Actionable (a link may be created/changed): everything else, incl. NULL/'none'.


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Registry / alias loading
# ---------------------------------------------------------------------------
def _matchers_for(aliases):
    """Compile boundary-anchored matchers for an alias list."""
    matchers = []
    for a in aliases:
        a = (a or "").strip()
        if len(a) < MIN_ALIAS_LEN:
            continue
        # boundary that treats alnum as "word" chars so 'CID' won't match
        # 'acidic' but 'Armory v4' still matches inside a sentence.
        pat = re.compile(r"(?<![A-Za-z0-9])" + re.escape(a) + r"(?![A-Za-z0-9])",
                         re.IGNORECASE)
        matchers.append((a, pat))
    return matchers


def load_registry():
    """Return ``{id: {...}}`` for every link target across all three tiers.

    **Keyed by registry id, not canonical_name** (DECISIONS 0012 / round-3 D.3).
    This is the fix for the round-2 divergence: relink used to key by
    canonical_name and write `smelt-gateway` into `threads.project_link`, while
    the review endpoint wrote ids like `crystal-spire` into the same column, so
    one column held two incompatible vocabularies. The id wins because it is
    stable under folder renames -- this estate has actually renamed
    `L5GN-Armory` to `smelt-gateway`, which would have orphaned every
    canonical_name-keyed link.

    Each entry carries its place in the hierarchy (`tier`, `program`, `project`)
    so a repo-level match can roll up to its project and program for display
    without changing what gets written.

    Reads the tiered registry. A flat (schema v1) registry is refused loudly
    rather than half-understood -- run build_registry.py to regenerate.
    """
    if not REGISTRY_PATH.is_file():
        raise SystemExit(f"[relink] registry missing: {REGISTRY_PATH} "
                         "(run build_registry.py first)")
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        registry = json.load(f)

    if "programs" not in registry:
        raise SystemExit(
            f"[relink] {REGISTRY_PATH} is a flat (pre-0012) registry with no "
            "programs tier. Re-run build_registry.py to regenerate it in the "
            "three-tier shape -- relink will not guess at the hierarchy.")

    targets = {}
    prog_names = {p["id"]: p.get("name", p["id"]) for p in registry.get("programs", [])}

    def _add(tid, tier, canon, aliases, scope, program, project, low_sig, activity):
        alias_list = list(dict.fromkeys(list(aliases) + [canon]))
        targets[tid] = {
            "id": tid,
            "tier": tier,
            "canonical_name": canon,
            "aliases": alias_list,
            "matchers": _matchers_for(alias_list),
            "scope": scope,
            "program": program,
            "program_name": prog_names.get(program),
            "project": project,
            "repo_folder_path": (f"{SCOPE_TO_ROOT[scope]}/{canon}"
                                 if scope in SCOPE_TO_ROOT else None),
            # S3: activity window for time_plausibility (None if not built yet).
            "activity": activity,
            # Fix B: demote body-only alias hits for this target when set.
            "low_signal_body": bool(low_sig),
        }

    for prog in registry.get("programs", []):
        _add(prog["id"], "program", prog.get("name", prog["id"]),
             prog.get("aliases", []), prog.get("scope"), prog["id"], None,
             prog.get("low_signal_body"), prog.get("activity"))

    for proj in registry["projects"]:
        _add(proj["id"], "project", proj["canonical_name"], proj.get("aliases", []),
             proj.get("scope"), proj.get("program"), proj["id"],
             proj.get("low_signal_body"), proj.get("activity"))
        for repo in proj.get("repos", []):
            _add(repo["id"], "repo", repo["canonical_name"],
                 repo.get("aliases", []), repo.get("scope") or proj.get("scope"),
                 proj.get("program"), proj["id"],
                 repo.get("low_signal_body", proj.get("low_signal_body")),
                 repo.get("activity"))
    return targets


def rollup_label(registry, tid) -> str:
    """`program > project > repo` breadcrumb for one link target.

    Display only. A repo-level evidence match still *scores* and *links* as that
    repo -- the specific incarnation is the more precise answer and throwing it
    away would lose information. The breadcrumb is what makes the decision
    legible: seeing `L5GN OS > Citadel MicroIDE > smelt-gateway` is what tells
    Tim at a glance that three separate repo rows in the table are one effort.
    """
    meta = registry.get(tid)
    if not meta:
        return tid
    parts = []
    if meta.get("program_name"):
        parts.append(meta["program_name"])
    proj = meta.get("project")
    if proj and proj != tid and proj in registry:
        parts.append(registry[proj]["canonical_name"])
    parts.append(meta["canonical_name"])
    return " > ".join(parts)


def alias_hits(text, matchers):
    """Return set of aliases whose matcher fires in text (cheap substring gate
    first, then boundary regex)."""
    if not text:
        return set()
    low = text.lower()
    hits = set()
    for alias, pat in matchers:
        if alias.lower() in low and pat.search(text):
            hits.add(alias)
    return hits


# ---------------------------------------------------------------------------
# Evidence gathering
# ---------------------------------------------------------------------------
def load_persisted_evidence(conn):
    """thread_id -> project -> list of {id, signal, weight, detail}."""
    out = defaultdict(lambda: defaultdict(list))
    for r in conn.execute(
        "SELECT evidence_id, thread_id, project, signal, weight, detail "
        "FROM link_evidence WHERE thread_id IS NOT NULL AND project IS NOT NULL"
    ):
        out[r["thread_id"]][r["project"]].append({
            "id": r["evidence_id"], "signal": r["signal"],
            "weight": r["weight"], "detail": r["detail"],
        })
    return out


def thread_content(conn, thread_id):
    rows = conn.execute(
        "SELECT content FROM messages WHERE thread_id=? ORDER BY seq ASC",
        (thread_id,),
    ).fetchall()
    return "\n".join(r["content"] or "" for r in rows)


def project_name_of(conn, project_id, _cache={}):
    if project_id in _cache:
        return _cache[project_id]
    row = conn.execute("SELECT name FROM projects WHERE project_id=?",
                       (project_id,)).fetchone()
    name = row["name"] if row else None
    _cache[project_id] = name
    return name


def human_ruled_threads(conn):
    """thread_ids that already carry a human ruling on an S6 link queue row
    (confirmed / rejected / reassigned). We leave those threads alone so a
    nightly re-run never re-surfaces a suggestion a human already dismissed or
    accepted (standing rule: human-resolved rows are never auto-modified). The
    informational 'link_upgrade' rows relink writes itself are excluded — those
    live on already-'evidence' threads, which are skipped earlier anyway."""
    rows = conn.execute(
        "SELECT DISTINCT thread_id FROM review_queue "
        "WHERE status IN ('confirmed', 'rejected', 'reassigned') "
        "AND type IN ('project_link', 'link_ambiguous', 'link_downgrade')"
    ).fetchall()
    return {r["thread_id"] for r in rows if r["thread_id"]}


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------
def combine(signals):
    """signals: list of dicts {signal, weight, id?, detail}. Applies per-type
    count caps + the per-weight CAP, returns (adjusted_score, used_signals)."""
    by_type = defaultdict(list)
    for s in signals:
        by_type[s["signal"]].append(s)

    used = []
    for stype, group in by_type.items():
        group = sorted(group, key=lambda s: s["weight"] or 0.0, reverse=True)
        cap_n = SIGNAL_COUNT_CAP.get(stype)
        if cap_n is not None:
            group = group[:cap_n]
        used.extend(group)

    prod = 1.0
    for s in used:
        w = min(s["weight"] or 0.0, CAP)
        prod *= (1.0 - w)
    score = 1.0 - prod
    return score, used


def score_thread(thread, persisted, registry, content):
    """Return sorted list of candidate dicts:
       {project, score, adjusted, used, evidence_ids, summary}."""
    title = thread["title"] or ""
    # Collect signals per project: persisted rows + inline alias signals.
    per_project = defaultdict(list)
    for project, rows in persisted.get(thread["thread_id"], {}).items():
        per_project[project].extend(rows)

    for canon, meta in registry.items():
        title_hits = alias_hits(title, meta["matchers"])
        content_hits = alias_hits(content, meta["matchers"]) if content else set()
        # Fix B: a body-only alias hit for a low_signal_body project is demoted.
        body_weight = (WEIGHT_ALIAS_CONTENT_LOWSIG if meta.get("low_signal_body")
                       else WEIGHT_ALIAS_CONTENT)
        # per alias, keep the stronger placement (title beats content).
        for alias in title_hits | content_hits:
            in_title = alias in title_hits
            w = WEIGHT_ALIAS_TITLE if in_title else body_weight
            place = "title" if in_title else "body"
            per_project[canon].append({
                "id": None, "signal": "name_alias", "weight": w,
                "detail": f"{alias}@{place}",
            })

    # S3 time signal is a per-thread multiplier; parse the date once. An undated
    # thread yields a neutral 0.7 and is flagged 'time:unknown' in the summary.
    tdate = parse_thread_date(thread["created_at"])
    time_note = "" if tdate is not None else "; time:unknown"

    candidates = []
    for project, signals in per_project.items():
        score, used = combine(signals)
        activity = registry.get(project, {}).get("activity")
        tp = time_plausibility(tdate, activity)
        adjusted = score * tp
        evidence_ids = [s["id"] for s in used if s["id"] is not None]
        summary = ", ".join(
            f"{s['signal']}:{s['detail']}({min(s['weight'] or 0, CAP):.2f})"
            for s in sorted(used, key=lambda s: s["weight"] or 0, reverse=True)
        )
        summary += f"; time*{tp:.2f}{time_note}"
        candidates.append({
            "project": project, "score": score, "adjusted": adjusted,
            "used": used, "evidence_ids": evidence_ids, "summary": summary,
        })
    candidates.sort(key=lambda c: c["adjusted"], reverse=True)
    return candidates


# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------
TIER_SPECIFICITY = {"repo": 2, "project": 1, "program": 0}


def collapse_lineage(candidates, registry):
    """Collapse candidates that are the same effort at different tiers.

    Once the registry has three tiers, a title like "Crystal Spire world_graph"
    matches BOTH the project `crystal-spire` and its repo `l5gn-crystal-spire`,
    because the repo inherits the project's alias. The flat scorer sees two
    candidates with near-identical scores and declares AMBIGUOUS -- which is
    exactly wrong: those are not two rival answers, they are one answer at two
    zoom levels. Left alone, the tier change would have flooded the review queue
    with self-ambiguity for every project that has a repo.

    So before rivalry is judged, any candidate that is an ancestor or descendant
    of a stronger candidate is folded into it. The winner is the higher score;
    ties go to the MORE SPECIFIC tier, because naming the actual incarnation is
    more informative than naming the umbrella and can always be rolled up for
    display, whereas the reverse loses information.

    Returns the collapsed candidate list; each survivor gains `rolled_up`, the
    ids it absorbed, so the report can show the fold rather than hide it.
    """
    def lineage(cid):
        meta = registry.get(cid) or {}
        return {cid, meta.get("project"), meta.get("program")} - {None}

    survivors = []
    for cand in candidates:  # already sorted by adjusted, descending
        cid = cand["project"]
        absorbed_by = None
        for kept in survivors:
            kid = kept["project"]
            # related iff either is in the other's lineage chain
            if cid in lineage(kid) or kid in lineage(cid):
                absorbed_by = kept
                break
        if absorbed_by is None:
            survivors.append(dict(cand, rolled_up=[]))
            continue
        # Equal scores: prefer the more specific tier as the surviving identity.
        keep_tier = TIER_SPECIFICITY.get(
            (registry.get(absorbed_by["project"]) or {}).get("tier"), -1)
        cand_tier = TIER_SPECIFICITY.get(
            (registry.get(cid) or {}).get("tier"), -1)
        if (abs(cand["adjusted"] - absorbed_by["adjusted"]) < 1e-9
                and cand_tier > keep_tier):
            rolled = absorbed_by["rolled_up"] + [absorbed_by["project"]]
            survivors[survivors.index(absorbed_by)] = dict(cand, rolled_up=rolled)
        else:
            absorbed_by["rolled_up"].append(cid)
    return survivors


def decide(thread, candidates, conn, registry=None):
    """Return a decision dict: {category, project?, adjusted?, ...}. Category is
    one of: skip_manual / skip_exact / skip_evidence / none / auto_link /
    downgrade / ambiguous / suggest."""
    conf = (thread["project_confidence"] or "none").lower()
    if conf in PROTECTED_CONFIDENCE:
        return {"category": "skip_" + conf}
    if conf in LOCKED_CONFIDENCE:
        return {"category": "skip_evidence"}

    if not candidates:
        return {"category": "none"}

    # Fold same-lineage candidates (a project and its own repo) into one before
    # judging rivalry -- otherwise every project with a repo self-ambiguates.
    candidates = collapse_lineage(candidates, registry or {})

    best = candidates[0]
    second = candidates[1] if len(candidates) > 1 else None
    lead = best["adjusted"] - (second["adjusted"] if second else 0.0)

    # Is the existing link already pointing where the evidence points?
    # project_link now holds a registry id (0012 / D.3), so the id comparison is
    # the authoritative one. The name comparison is kept as a fallback for
    # legacy rows written before the id scheme -- a fuzzy link to a Claude-uuid
    # project stores that uuid, whose NAME is what matches a registry entry.
    cur_link = thread["project_link"]
    cur_name = project_name_of(conn, cur_link) if cur_link else None
    best_name = (registry or {}).get(best["project"], {}).get(
        "canonical_name", best["project"])
    same_project = bool(cur_link) and (
        cur_link == best["project"]
        or (cur_name is not None
            and cur_name.strip().lower() == best_name.strip().lower()))

    # Ambiguity takes precedence over auto-link (never guess between rivals).
    if (best["adjusted"] >= SUGGEST_THRESHOLD and second
            and second["adjusted"] >= SUGGEST_THRESHOLD and lead < LEAD_MARGIN):
        # SIBLING ROLL-UP: two rival *repos* of the SAME project are not really
        # a contested question -- "which Armory incarnation was this?" is
        # unanswerable from a title, but "this is Citadel MicroIDE" is certain.
        # Rather than queue an ambiguity a human cannot resolve either, suggest
        # the parent project, which is the most specific thing the evidence
        # actually supports. This is the practical payoff of the tier change.
        reg = registry or {}
        parent = (reg.get(best["project"]) or {}).get("project")
        sibling = (reg.get(second["project"]) or {}).get("project")
        if (parent and parent == sibling and parent in reg
                and parent not in (best["project"], second["project"])):
            rolled = dict(best, project=parent, rolled_up=sorted(
                {best["project"], second["project"]}))
            rolled["summary"] = (
                f"{best['summary']}; rolled up from rival repos "
                f"{best['project']} / {second['project']} of the same project")
            return {"category": "suggest", "best": rolled,
                    "rolled_from": [best["project"], second["project"]]}
        return {"category": "ambiguous", "best": best, "second": second}

    if best["adjusted"] >= AUTO_LINK_THRESHOLD and lead >= LEAD_MARGIN:
        if conf == "fuzzy" and not same_project:
            return {"category": "downgrade", "best": best, "cur_name": cur_name}
        return {"category": "auto_link", "best": best, "was": conf,
                "same_project": same_project}

    if best["adjusted"] >= SUGGEST_THRESHOLD:
        if conf == "fuzzy" and not same_project:
            return {"category": "downgrade", "best": best, "cur_name": cur_name}
        return {"category": "suggest", "best": best}

    return {"category": "none"}


# ---------------------------------------------------------------------------
# Apply
# ---------------------------------------------------------------------------
def upsert_project(conn, target_id, registry):
    """Ensure a projects row exists whose ``project_id`` is the REGISTRY ID, so
    ``threads.project_link`` (a FK) can reference it.

    The id is the primary key and the human-readable ``canonical_name`` goes in
    ``name`` -- the same shape the review endpoint writes, which is the point:
    both writers now produce identical rows for the same target instead of one
    keying on a folder name and the other on an id."""
    meta = registry.get(target_id, {})
    conn.execute(
        """INSERT INTO projects (project_id, name, repo_folder_path, source_system_id)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(project_id) DO UPDATE SET
             name=COALESCE(excluded.name, projects.name),
             repo_folder_path=COALESCE(projects.repo_folder_path, excluded.repo_folder_path)""",
        (target_id, meta.get("canonical_name", target_id),
         meta.get("repo_folder_path"), None),
    )


def persist_inline(conn, thread_id, best, now):
    """Insert this thread's winning inline name_alias signals as link_evidence
    rows (so link_evidence_ids can reference them) and return the full winning
    id list (existing persisted ids + freshly-inserted ones)."""
    ids = list(best["evidence_ids"])
    for s in best["used"]:
        if s["id"] is not None:
            continue  # already a persisted row
        cur = conn.execute(
            "INSERT INTO link_evidence "
            "(thread_id, project, signal, weight, detail, produced_at, producer_version) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (thread_id, best["project"], s["signal"], s["weight"], s["detail"],
             now, PRODUCER_VERSION),
        )
        ids.append(cur.lastrowid)
    return ids


def clear_pending_relink_rows(conn, thread_id):
    """Idempotency: drop this thread's still-pending S6 queue rows before we
    re-queue. Never touches rows a human already ruled on (status != pending)."""
    conn.execute(
        "DELETE FROM review_queue WHERE thread_id=? AND status='pending' "
        "AND type IN ('project_link', 'link_ambiguous', 'link_downgrade')",
        (thread_id,),
    )
    # Stale inline evidence from a previous relink run on this (still-actionable)
    # thread - safe to drop; locked/evidence threads are never reprocessed.
    conn.execute(
        "DELETE FROM link_evidence WHERE thread_id=? AND producer_version=?",
        (thread_id, PRODUCER_VERSION),
    )


def apply_decision(conn, thread, dec, registry, now):
    cat = dec["category"]
    tid = thread["thread_id"]

    # Notes carry the full `program > project > repo` breadcrumb, not the bare
    # id: the id is what gets written, but a human reading the queue needs to see
    # that a match on `smelt-gateway` is a match on Citadel MicroIDE.
    def lbl(pid):
        return f"{pid} ({rollup_label(registry, pid)})"

    if cat == "auto_link":
        clear_pending_relink_rows(conn, tid)
        best = dec["best"]
        upsert_project(conn, best["project"], registry)
        ids = persist_inline(conn, tid, best, now)
        conn.execute(
            "UPDATE threads SET project_link=?, project_confidence='evidence', "
            "link_evidence_ids=? WHERE thread_id=?",
            (best["project"], json.dumps(ids), tid),
        )
        verb = "fuzzy->evidence upgrade" if dec.get("was") == "fuzzy" else "new link"
        conn.execute(
            """INSERT INTO review_queue (type, thread_id, confidence, status, note, created_at, resolved_at)
               VALUES ('link_upgrade', ?, ?, 'confirmed', ?, ?, ?)""",
            (tid, best["adjusted"],
             f"[{verb}] -> {lbl(best['project'])} (adjusted={best['adjusted']:.3f}); "
             f"evidence: {best['summary']}", now, now),
        )

    elif cat == "suggest":
        clear_pending_relink_rows(conn, tid)
        best = dec["best"]
        conn.execute(
            """INSERT INTO review_queue (type, thread_id, confidence, status, note, created_at)
               VALUES ('project_link', ?, ?, 'pending', ?, ?)""",
            (tid, best["adjusted"],
             f"suggest -> {lbl(best['project'])} (adjusted={best['adjusted']:.3f}); "
             f"evidence: {best['summary']}", now),
        )
        conn.execute("UPDATE threads SET review_status='pending' WHERE thread_id=?", (tid,))

    elif cat == "ambiguous":
        clear_pending_relink_rows(conn, tid)
        b, s = dec["best"], dec["second"]
        conn.execute(
            """INSERT INTO review_queue (type, thread_id, confidence, status, note, created_at)
               VALUES ('link_ambiguous', ?, ?, 'pending', ?, ?)""",
            (tid, b["adjusted"],
             f"ambiguous: {lbl(b['project'])} (adjusted={b['adjusted']:.3f}; {b['summary']}) "
             f"VS {lbl(s['project'])} (adjusted={s['adjusted']:.3f}; {s['summary']})", now),
        )
        conn.execute("UPDATE threads SET review_status='pending' WHERE thread_id=?", (tid,))

    elif cat == "downgrade":
        clear_pending_relink_rows(conn, tid)
        best = dec["best"]
        conn.execute(
            """INSERT INTO review_queue (type, thread_id, confidence, status, note, created_at)
               VALUES ('link_downgrade', ?, ?, 'pending', ?, ?)""",
            (tid, best["adjusted"],
             f"downgrade: existing fuzzy link -> {dec.get('cur_name')!r} now contradicted; "
             f"new evidence points to {lbl(best['project'])} "
             f"(adjusted={best['adjusted']:.3f}); evidence: {best['summary']}", now),
        )
        conn.execute("UPDATE threads SET review_status='pending' WHERE thread_id=?", (tid,))
    # 'none' / 'skip_*' -> nothing written.


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def build_report(results, scanned, apply, registry=None):
    """Build the decision-table report as a list of lines (so it can be printed
    AND written to a file with deterministic UTF-8, independent of the shell)."""
    buckets = defaultdict(list)
    for r in results:
        buckets[r["decision"]["category"]].append(r)

    lines = []
    emit = lines.append
    n = lambda k: len(buckets.get(k, []))
    emit("=" * 74)
    emit("S6 relink decision table" + ("" if apply else " (dry-run)"))
    emit("=" * 74)
    emit(f"DB: {DB_PATH}")
    emit(f"Threads scanned: {scanned}\n")
    emit("Summary")
    emit(f"  auto-link         {n('auto_link'):>6}")
    emit(f"  suggestion        {n('suggest'):>6}")
    emit(f"  ambiguous         {n('ambiguous'):>6}")
    emit(f"  downgrade         {n('downgrade'):>6}")
    emit(f"  no-op             {n('none'):>6}")
    emit(f"  skipped: manual   {n('skip_manual'):>6}")
    emit(f"  skipped: exact    {n('skip_exact'):>6}")
    emit(f"  skipped: evidence {n('skip_evidence'):>6}  (locked - only a human may change)")
    emit(f"  skipped: ruled    {n('skip_ruled'):>6}  (human already ruled - not re-nagged)")

    # AUTO-LINKS: sample is fine.
    al = buckets.get("auto_link", [])
    emit("\n" + "-" * 74)
    emit(f"AUTO-LINKS ({len(al)}) - sample up to 15:")
    emit(f"  {'adjusted':>8}  {'project':<22}  thread / evidence")
    for r in al[:15]:
        b = r["decision"]["best"]
        title = (r["thread"]["title"] or "")[:34]
        emit(f"  {b['adjusted']:>8.3f}  {b['project']:<22}  {r['thread']['thread_id'][:12]}  {title}")
        emit(f"  {'':>8}  {'':<22}  = {b['summary']}")

    # SUGGESTIONS: list ALL. These are what the human actually works through, so
    # each line carries the `program > project > repo` breadcrumb -- the whole
    # point of the tier change is that Tim can see three separate repo rows are
    # one effort without having to remember the lineage himself.
    sg = buckets.get("suggest", [])
    emit("\n" + "-" * 74)
    emit(f"SUGGESTIONS ({len(sg)}) - ALL:")
    for r in sg:
        b = r["decision"]["best"]
        title = (r["thread"]["title"] or "")[:34]
        emit(f"  {b['adjusted']:>8.3f}  {r['thread']['thread_id'][:12]}  {title}")
        emit(f"  {'':>8}  -> {b['project']}  [{rollup_label(registry or {}, b['project'])}]")
        if r["decision"].get("rolled_from"):
            emit(f"  {'':>8}     rolled up from rival repos of the same project: "
                 f"{', '.join(r['decision']['rolled_from'])}")
        elif b.get("rolled_up"):
            emit(f"  {'':>8}     absorbed same-lineage candidates: "
                 f"{', '.join(b['rolled_up'])}")
        emit(f"  {'':>8}     evidence: {b['summary']}")

    # DOWNGRADES: list ALL.
    dg = buckets.get("downgrade", [])
    emit("\n" + "-" * 74)
    emit(f"DOWNGRADES ({len(dg)}) - ALL:")
    for r in dg:
        b = r["decision"]["best"]
        cur = r["decision"].get("cur_name")
        title = (r["thread"]["title"] or "")[:34]
        emit(f"  {r['thread']['thread_id'][:12]}  {title}")
        emit(f"      fuzzy link {cur!r} contradicted; new best -> {b['project']} "
             f"(adjusted={b['adjusted']:.3f})")
        emit(f"      evidence: {b['summary']}")

    # AMBIGUOUS: list ALL.
    am = buckets.get("ambiguous", [])
    emit("\n" + "-" * 74)
    emit(f"AMBIGUOUS ({len(am)}) - ALL:")
    for r in am:
        b, s = r["decision"]["best"], r["decision"]["second"]
        title = (r["thread"]["title"] or "")[:34]
        emit(f"  {r['thread']['thread_id'][:12]}  {title}")
        emit(f"      {b['project']} (adj={b['adjusted']:.3f}; {b['summary']})")
        emit(f"      {s['project']} (adj={s['adjusted']:.3f}; {s['summary']})")
    emit("-" * 74)
    return lines


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def run(apply, no_content_scan, limit, out=None):
    registry = load_registry()
    conn = get_connection()
    now = utc_now()
    try:
        persisted = load_persisted_evidence(conn)
        ruled = human_ruled_threads(conn)
        threads = conn.execute(
            "SELECT thread_id, title, created_at, project_link, project_confidence, "
            "review_status FROM threads"
        ).fetchall()

        results = []
        scanned = 0
        for thread in threads:
            conf = (thread["project_confidence"] or "none").lower()
            # Skip the locked/protected classes early - no scoring needed, and
            # (importantly) no content scan for them.
            if conf in PROTECTED_CONFIDENCE:
                results.append({"thread": thread, "decision": {"category": "skip_" + conf}})
                continue
            if conf in LOCKED_CONFIDENCE:
                results.append({"thread": thread, "decision": {"category": "skip_evidence"}})
                continue
            # A human already ruled on this thread's link suggestion - respect
            # it; never re-nag on the nightly pass.
            if thread["thread_id"] in ruled:
                results.append({"thread": thread, "decision": {"category": "skip_ruled"}})
                continue

            scanned += 1
            if limit and scanned > limit:
                scanned -= 1
                break
            content = "" if no_content_scan else thread_content(conn, thread["thread_id"])
            candidates = score_thread(thread, persisted, registry, content)
            decision = decide(thread, candidates, conn, registry)
            results.append({"thread": thread, "decision": decision})
            if apply:
                apply_decision(conn, thread, decision, registry, now)

        if apply:
            conn.commit()

        lines = build_report(results, scanned, apply, registry)
        if apply:
            written = sum(1 for r in results
                          if r["decision"]["category"] in
                          ("auto_link", "suggest", "ambiguous", "downgrade"))
            lines.append(f"\nApplied. {written} thread(s) changed / queued. "
                         "Winners are now 'evidence' (a re-run will skip them).")
        else:
            lines.append("\n[DRY RUN] Nothing written. Re-run with --apply to commit.")

        report = "\n".join(lines)
        print(report)
        if out:
            # Explicit UTF-8 file write - never depends on shell redirect encoding.
            with open(out, "w", encoding="utf-8") as f:
                f.write(report + "\n")
            print(f"\n[report written to {out}]")
    finally:
        conn.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="S6 re-link pass (evidence -> link decisions).")
    ap.add_argument("--apply", action="store_true",
                    help="Write decisions (default is dry-run, report only).")
    ap.add_argument("--no-content-scan", action="store_true",
                    help="Skip the alias-in-body scan (faster; title + persisted evidence only).")
    ap.add_argument("--limit", type=int, default=0,
                    help="Cap threads scanned (spot checks / dev). 0 = all.")
    ap.add_argument("--out", metavar="PATH", default=None,
                    help="Also write the report to PATH as explicit UTF-8 "
                         "(e.g. relink_dryrun.txt).")
    args = ap.parse_args()
    run(args.apply, args.no_content_scan, args.limit, args.out)
