"""match_claims.py -- K4, COWORK_BRIEF_knowledge_curator.md.

Two-stage match, per the spec: shortlist candidate corpus chunks by
similarity, confirm by a second LM Studio call with the matched span quoted
back. **Both** the shortlist score and the confirm verdict are recorded --
a confirm step whose verdicts never disagree with the shortlist is doing
nothing, and that can only be seen if both are kept.

Claims are walked **newest-first per project** (the order K2 already
produced them in, conversation-by-conversation) so that "already
established" always means "from a newer conversation than the one under
test right now" -- ordering answers the K6-parked contradiction question
without ever having to decide which of two claims is true (brief).

Four outcomes:
  captured      -- confirmed match in the project's own corpus
  gap           -- no confirmed match anywhere, and no established claim it supersedes
  superseded    -- conflicts with an established claim from a newer conversation
  cross-project -- confirmed in another MCF project's corpus, absent from its own

``quoted_source``/matched-span verification is never downgraded to a
similarity score -- every confirm, corpus or claim-vs-claim, must quote a
literal substring of the text it claims to match, checked in Python, not
trusted from the model's own say-so.
"""
from __future__ import annotations

import argparse
import difflib
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

_PIPE = Path(__file__).resolve().parent
if str(_PIPE) not in sys.path:
    sys.path.insert(0, str(_PIPE))
import extract_claims as k2  # noqa: E402

DEFAULT_ENDPOINT = k2.DEFAULT_ENDPOINT
DEFAULT_TEMPERATURE = 0.0
DEFAULT_TIMEOUT = k2.DEFAULT_TIMEOUT
SHORTLIST_SIZE = 5
SHORTLIST_FLOOR = 0.15          # below this, not even worth a confirm call
SUPERSEDE_TOPIC_FLOOR = 0.5     # claim-vs-claim similarity to even ask "does this conflict?"

CONFIRM_CHUNK_SYSTEM = (
    "You check whether a candidate passage from a project's knowledge "
    "document actually supports a claim extracted from a conversation. "
    "Return ONLY a JSON object: {\"confirmed\": true|false, \"matched_span\": "
    "\"...\"}. `matched_span` MUST be a literal, verbatim substring of the "
    "candidate passage (not the claim) -- copy it character-for-character. "
    "If nothing in the passage supports the claim, set confirmed to false "
    "and matched_span to an empty string."
)

CONFIRM_SUPERSEDE_SYSTEM = (
    "You check whether an OLDER claim from an earlier conversation "
    "conflicts with a NEWER, already-established claim on the same topic. "
    "Return ONLY a JSON object: {\"conflicts\": true|false, \"matched_span\": "
    "\"...\"}. `matched_span` MUST be a literal, verbatim substring of the "
    "NEWER claim's quoted_source (not a summary) that shows what the current "
    "belief is. If the older claim merely agrees or is unrelated, conflicts "
    "is false."
)

# Grammar-constrained response_format schemas, keyed by system prompt so the
# transport can pick the right one without the caller having to say so
# separately (see extract_claims.CLAIMS_JSON_SCHEMA for why this exists at
# all: a model that ignores a prompt-only format instruction on a long
# input is a real, observed failure mode, not a hypothetical one).
CONFIRM_CHUNK_SCHEMA = {
    "type": "object",
    "properties": {
        "confirmed": {"type": "boolean"},
        "matched_span": {"type": "string"},
    },
    "required": ["confirmed", "matched_span"],
    "additionalProperties": False,
}
CONFIRM_SUPERSEDE_SCHEMA = {
    "type": "object",
    "properties": {
        "conflicts": {"type": "boolean"},
        "matched_span": {"type": "string"},
    },
    "required": ["conflicts", "matched_span"],
    "additionalProperties": False,
}
_SCHEMA_BY_SYSTEM = {
    CONFIRM_CHUNK_SYSTEM: ("confirm_chunk", CONFIRM_CHUNK_SCHEMA),
    CONFIRM_SUPERSEDE_SYSTEM: ("confirm_supersede", CONFIRM_SUPERSEDE_SCHEMA),
}


# ---------------------------------------------------------------------------
# Similarity -- stdlib only, deterministic. Shortlisting, never the final
# verdict; the confirm call + literal-span check is what decides an outcome.
# ---------------------------------------------------------------------------

def similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a.casefold(), b.casefold()).ratio()


def shortlist(claim_text: str, chunks: list[dict], k: int = SHORTLIST_SIZE) -> list[dict]:
    scored = [
        {**c, "shortlist_score": similarity(claim_text, c["text"])}
        for c in chunks
    ]
    scored.sort(key=lambda c: c["shortlist_score"], reverse=True)
    return [c for c in scored[:k] if c["shortlist_score"] >= SHORTLIST_FLOOR]


# ---------------------------------------------------------------------------
# Confirm calls
# ---------------------------------------------------------------------------

def confirm_chunk(claim_text: str, chunk_text: str, *, caller, endpoint: str,
                    model: str, temperature: float) -> dict:
    """Returns {"confirmed": bool, "matched_span": str, "span_verified": bool}.
    `span_verified` is Python's own check that matched_span is a literal
    substring of chunk_text -- confirmed can never be trusted true unless
    span_verified is also true."""
    prompt = f"CLAIM:\n{claim_text}\n\nCANDIDATE PASSAGE:\n{chunk_text}"
    raw = caller(prompt, system=CONFIRM_CHUNK_SYSTEM, endpoint=endpoint, model=model, temperature=temperature)
    obj = k2._extract_json_array("[" + raw + "]")  # reuse the bracket-matching parser on a wrapped object
    rec = obj[0] if obj else None
    if not isinstance(rec, dict):
        return {"confirmed": False, "matched_span": "", "span_verified": False, "parse_failed": True}
    confirmed = bool(rec.get("confirmed"))
    span = rec.get("matched_span") or ""
    span_ok = isinstance(span, str) and span != "" and span in chunk_text
    return {"confirmed": confirmed and span_ok, "matched_span": span, "span_verified": span_ok,
             "parse_failed": False}


def confirm_supersede(older_claim_text: str, newer_claim_text: str, newer_quoted_source: str,
                        *, caller, endpoint: str, model: str, temperature: float) -> dict:
    prompt = (f"OLDER CLAIM:\n{older_claim_text}\n\n"
              f"NEWER ESTABLISHED CLAIM:\n{newer_claim_text}\n\n"
              f"NEWER CLAIM'S SOURCE QUOTE:\n{newer_quoted_source}")
    raw = caller(prompt, system=CONFIRM_SUPERSEDE_SYSTEM, endpoint=endpoint, model=model, temperature=temperature)
    obj = k2._extract_json_array("[" + raw + "]")
    rec = obj[0] if obj else None
    if not isinstance(rec, dict):
        return {"conflicts": False, "matched_span": "", "span_verified": False, "parse_failed": True}
    conflicts = bool(rec.get("conflicts"))
    span = rec.get("matched_span") or ""
    span_ok = isinstance(span, str) and span != "" and span in newer_quoted_source
    return {"conflicts": conflicts and span_ok, "matched_span": span, "span_verified": span_ok,
             "parse_failed": False}


# ---------------------------------------------------------------------------
# Per-claim shape
# ---------------------------------------------------------------------------

@dataclass
class ClaimRecord:
    project_id: str
    conversation_id: str
    real_time: str | None
    claim_text: str
    quoted_source: str
    outcome: str = "gap"                # captured | gap | superseded | cross-project
    shortlist: list = field(default_factory=list)   # [{file, heading, shortlist_score}]
    confirm: dict | None = None
    supersedes: dict | None = None      # {older matched a newer established claim}


def _project_chunks(corpus_index: dict, project_id: str) -> list[dict]:
    for p in corpus_index.get("projects", []):
        if p["project_id"] == project_id:
            out = []
            for f in p["files"]:
                for c in f["chunks"]:
                    out.append({"file": f["file"], "heading": c.get("heading"), "text": c["text"]})
            return out
    return []


def match_against_corpus(claim_text: str, chunks: list[dict], *, caller, endpoint: str,
                           model: str, temperature: float) -> tuple[str | None, list, dict | None]:
    """Returns (matched_chunk_key or None, shortlist_with_scores, confirm_result or None)."""
    short = shortlist(claim_text, chunks)
    short_report = [{"file": c["file"], "heading": c.get("heading"),
                       "shortlist_score": c["shortlist_score"]} for c in short]
    for c in short:
        result = confirm_chunk(claim_text, c["text"], caller=caller, endpoint=endpoint,
                                 model=model, temperature=temperature)
        if result["confirmed"]:
            return f"{c['file']}#{c.get('heading') or 'whole-file'}", short_report, result
    return None, short_report, (None if not short else result)


def match_claims(claims_report: dict, corpus_index: dict, *, caller, endpoint: str,
                   model: str, temperature: float, progress=None) -> dict:
    """`claims_report` is K2's output (already newest-first per its own
    conversation order). Groups claims by project via the caller-supplied
    conversation->project map baked into each claim record before this is
    called (see `flatten_claims`)."""
    corpora_by_project = {
        p["project_id"]: _project_chunks(corpus_index, p["project_id"])
        for p in corpus_index.get("projects", [])
    }
    other_projects = {pid: chunks for pid, chunks in corpora_by_project.items()}

    established: dict[str, list[ClaimRecord]] = {}  # project_id -> newest-first established claims
    out: list[ClaimRecord] = []
    total = len(claims_report)

    for i, rec in enumerate(claims_report):  # already newest-first, per project interleaved as given
        cr = ClaimRecord(
            project_id=rec["project_id"], conversation_id=rec["conversation_id"],
            real_time=rec["real_time"], claim_text=rec["claim_text"],
            quoted_source=rec["quoted_source"],
        )
        own_chunks = corpora_by_project.get(cr.project_id, [])
        matched_key, short_report, confirm = match_against_corpus(
            cr.claim_text, own_chunks, caller=caller, endpoint=endpoint, model=model, temperature=temperature,
        )
        cr.shortlist = short_report
        cr.confirm = confirm

        if matched_key is not None:
            cr.outcome = "captured"
            out.append(cr)
            established.setdefault(cr.project_id, []).append(cr)
            if progress:
                progress(i + 1, total)
            continue

        # Not in its own corpus -- check supersession against established
        # (newer) claims in the SAME project first.
        proj_established = established.get(cr.project_id, [])
        topic_matches = sorted(
            proj_established, key=lambda e: similarity(cr.claim_text, e.claim_text), reverse=True,
        )
        superseded = False
        for newer in topic_matches:
            if similarity(cr.claim_text, newer.claim_text) < SUPERSEDE_TOPIC_FLOOR:
                break
            verdict = confirm_supersede(
                cr.claim_text, newer.claim_text, newer.quoted_source,
                caller=caller, endpoint=endpoint, model=model, temperature=temperature,
            )
            if verdict["conflicts"]:
                cr.outcome = "superseded"
                cr.supersedes = {
                    "newer_conversation_id": newer.conversation_id,
                    "newer_real_time": newer.real_time,
                    "newer_claim_text": newer.claim_text,
                    "newer_quoted_source": newer.quoted_source,
                    "matched_span": verdict["matched_span"],
                }
                superseded = True
                break

        if superseded:
            out.append(cr)
            if progress:
                progress(i + 1, total)
            continue

        # Cross-project: confirmed in another MCF project's corpus.
        cross_found = False
        for other_pid, chunks in other_projects.items():
            if other_pid == cr.project_id or not chunks:
                continue
            other_key, other_short, other_confirm = match_against_corpus(
                cr.claim_text, chunks, caller=caller, endpoint=endpoint, model=model, temperature=temperature,
            )
            if other_key is not None:
                cr.outcome = "cross-project"
                cr.confirm = other_confirm
                cr.shortlist = other_short
                cr.supersedes = {"found_in_project": other_pid, "chunk": other_key}
                cross_found = True
                break

        if not cross_found:
            cr.outcome = "gap"
        out.append(cr)
        # A gap/cross-project claim still ESTABLISHES current truth on its
        # topic (brief: "the newest claim on a topic establishes current
        # truth" -- that is not conditional on the corpus already holding
        # it). It becomes the reference point an even-older, conflicting
        # claim can be found to supersede. Only a claim that was ITSELF
        # superseded is excluded -- it lost, so it should not be what a
        # still-older claim gets compared against.
        established.setdefault(cr.project_id, []).append(cr)
        if progress:
            progress(i + 1, total)

    return {
        "model_id": model, "endpoint": endpoint, "temperature": temperature,
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        "claims": [
            {
                "project_id": c.project_id, "conversation_id": c.conversation_id,
                "real_time": c.real_time, "claim_text": c.claim_text,
                "quoted_source": c.quoted_source, "outcome": c.outcome,
                "shortlist": c.shortlist, "confirm": c.confirm, "supersedes": c.supersedes,
            }
            for c in out
        ],
    }


def flatten_claims(claims_report: dict, session_to_project: dict) -> list[dict]:
    """K2's report is per-conversation; K4 needs a flat, newest-first
    per-claim stream with each claim's project attached. `session_to_project`
    is `{conversation_id: project_id}`, built from the ratified map (K1)."""
    flat: list[dict] = []
    for conv in claims_report.get("conversations", []):
        project_id = session_to_project.get(conv["conversation_id"])
        if project_id is None:
            continue
        for claim in conv.get("claims", []):
            flat.append({
                "project_id": project_id, "conversation_id": conv["conversation_id"],
                "real_time": conv.get("real_time"), "claim_text": claim["claim_text"],
                "quoted_source": claim["quoted_source"],
            })
    return flat


def merge_matches(old: dict | None, new: dict, touched_projects: set) -> dict:
    """Merge a scoped (--project-filtered) match_claims() run into the
    existing --out file. Unlike K2's merge_report (which merges by
    conversation_id), K4's unit of "ownership" is the project: a scoped run
    recomputes supersession for one project end-to-end using that project's
    full claim history (see match_claims -- established/superseded is only
    ever compared within a project), so every prior claim belonging to a
    touched project is replaced wholesale by this run's claims for that
    project, and every claim belonging to an untouched project is carried
    over unchanged."""
    if old is None:
        return new
    kept = [c for c in old.get("claims", []) if c["project_id"] not in touched_projects]
    merged = dict(new)
    merged["claims"] = kept + new["claims"]
    merged["partial_run_projects"] = sorted(touched_projects)
    return merged


def call_lmstudio_generic(prompt: str, *, system: str, endpoint: str, model: str,
                            temperature: float, timeout: float = DEFAULT_TIMEOUT,
                            json_mode: bool = True) -> str:
    """As extract_claims.call_lmstudio, but for K4's two confirm shapes --
    ``response_format`` is selected by matching ``system`` against the two
    known prompts (``CONFIRM_CHUNK_SYSTEM`` / ``CONFIRM_SUPERSEDE_SYSTEM``),
    so callers never have to say which schema applies."""
    import urllib.request
    body: dict = {
        "model": model, "temperature": temperature,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
    }
    if json_mode:
        entry = _SCHEMA_BY_SYSTEM.get(system)
        if entry is not None:
            name, schema = entry
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": name, "strict": True, "schema": schema},
            }
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(endpoint, data=payload, method="POST",
                                   headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        response_body = json.loads(resp.read().decode("utf-8"))
    return response_body["choices"][0]["message"]["content"]


def main() -> None:
    import functools

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--claims", type=Path, default=k2.DEFAULT_OUT)
    ap.add_argument("--corpus", type=Path, default=Path("data/knowledge_curator/corpus_index.json"))
    ap.add_argument("--map", type=Path, default=Path("config/mcf_conversation_map.tsv"))
    ap.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    ap.add_argument("--model", required=True)
    ap.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE)
    ap.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT,
                     help="per-request timeout in seconds (default 900)")
    ap.add_argument("--no-json-mode", dest="json_mode", action="store_false",
                     help="disable response_format grammar constraint, if the "
                          "endpoint errors on it")
    ap.add_argument("--out", type=Path, default=Path("data/knowledge_curator/matches.json"))
    ap.add_argument("--project", action="append",
                     help="limit to this MCF project_id (repeatable); refresh a single "
                          "project's matches without re-matching every other project. "
                          "Result is merged into --out rather than overwriting it.")
    ap.add_argument("--no-progress", dest="progress", action="store_false",
                     help="suppress the 'matching: done/total' terminal progress line")
    args = ap.parse_args()

    bound_caller = functools.partial(call_lmstudio_generic, timeout=args.timeout, json_mode=args.json_mode)

    import knowledge_index as k1
    claims_report = json.loads(args.claims.read_text(encoding="utf-8"))
    corpus_index = json.loads(args.corpus.read_text(encoding="utf-8"))
    map_rows = k1.load_map(args.map)
    session_to_project = {r.session_id: r.project_id for r in map_rows}

    project_filter = set(args.project) if args.project else None
    if project_filter:
        known = {r.project_id for r in map_rows}
        unknown = project_filter - known
        if unknown:
            print(f"warning: --project value(s) not found in {args.map}: {sorted(unknown)}",
                  file=sys.stderr)

    flat = flatten_claims(claims_report, session_to_project)
    if project_filter:
        flat = [c for c in flat if c["project_id"] in project_filter]

    reporter = k2.make_progress_reporter("matching") if args.progress else None
    result = match_claims(flat, corpus_index, caller=bound_caller, endpoint=args.endpoint,
                            model=args.model, temperature=args.temperature, progress=reporter)

    if project_filter:
        old = None
        if args.out.exists():
            try:
                old = json.loads(args.out.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                old = None
        result = merge_matches(old, result, project_filter)
        print(f"scoped to project(s): {sorted(project_filter)}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    counts: dict[str, int] = {}
    for c in result["claims"]:
        counts[c["outcome"]] = counts.get(c["outcome"], 0) + 1
    print("outcomes (in --out, all projects):", counts)
    print(f"\nmatches written: {args.out}")


if __name__ == "__main__":
    main()
