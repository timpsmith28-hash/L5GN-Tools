"""
S2 - Vocabulary fingerprints (per-project distinctive-term sets + evidence).

Two jobs in one runnable pass:

  1. FINGERPRINT (registry): per project, harvest candidate terms and keep the
     top ~50 most *distinctive* ones, stored as a `"vocabulary"` block on the
     registry entry:

         "vocabulary": {
           "built_at": "2026-07-16T...Z",
           "source_commit": "abc1234",       # git HEAD; skip rebuild if unchanged
           "source_signature": null,         # non-git md5 signature instead
           "terms": { "SpireApp": 3.2, "world_graph": 2.9, ... }
         }

     Candidate terms come from (spec S2.1):
       (a) filenames        - from file_inventory.paths (SHARED harvest; we do
                              NOT re-walk / re-run git ls-files - S4 already did)
       (b) code identifiers - light regex for class/def/const/function/exported
                              names in .py/.js/.ts/.tsx/.jsx files
       (c) markdown headings- '#'-prefixed lines in the project's own .md docs
       (d) shard titles     - smelt-gateway only: titles from data/shard_manifest.json

     Distinctiveness (S2.2): a TF-IDF-shaped weight,
       weight = tf_in_project * log(N_projects / doc_freq)
     Generic terms are removed by a stopword list + a cross-project commonality
     cutoff (a term in too many projects is not distinctive). Keep top ~50.

  2. EVIDENCE (link_evidence): scan thread message content for hits on any
     project's distinctive terms and emit `vocabulary` evidence rows
     (weight 0.3 each; S6/relink counts at most 3 per thread->project pair).
     This skill ONLY produces evidence - relink.py is the sole consumer that
     turns evidence into link decisions.

Skip-if-unchanged (S2.3): a project whose git HEAD (or non-git signature)
matches the stored `source_commit`/`source_signature` keeps its existing
vocabulary block untouched, mirroring build_inventory's change-detection.
(--force rebuilds all; a fingerprint-set change always re-emits ALL evidence,
since evidence weight depends on the whole term corpus.)

Standing rules: UTF-8 everywhere, UTC ISO-8601, whole-file atomic registry
write, loud failure (a broken registry/repo stops the run - no partial state),
--apply gates every write (default is a dry-run preview).

Usage:
    python3 pipeline/build_vocabulary.py             # dry-run: build + print top terms, write nothing
    python3 pipeline/build_vocabulary.py --apply     # write registry blocks + link_evidence rows
    python3 pipeline/build_vocabulary.py --force      # rebuild all fingerprints (ignore skip-if-unchanged)
    python3 pipeline/build_vocabulary.py --apply --top 50
"""
import argparse
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from db import get_connection, CHRONICLER_ROOT
# Reuse S4's harvest helpers - one source of truth for paths, git head, and IO.
from build_inventory import (
    REGISTRY_PATH, read_json, write_json_atomic, utc_now,
    resolve_fs, git_head, current_signature,
)

PRODUCER_VERSION = "build_vocabulary/1.0"
SIGNAL = "vocabulary"
EVIDENCE_WEIGHT = 0.3          # per S6 scoring; relink caps the count at 3
TOP_TERMS_DEFAULT = 50
MIN_TERM_LEN = 3               # keep short-but-distinctive tokens like 'tui'
COMMONALITY_CUTOFF = 0.34      # drop a term appearing in > this fraction of projects
MAX_EVIDENCE_PER_PAIR = 3      # emit at most the cap relink will count anyway
RESERVE_CODE = 12              # top-N slots reserved for clean code identifiers,
                               # so structural names (delve/plug/dispatcher) are
                               # not crowded out by a content-heavy repo's prose

# File classes we read for identifiers / headings (content harvest, not a walk -
# we only open paths already listed in file_inventory).
CODE_EXTS = {".py", ".js", ".ts", ".tsx", ".jsx"}
DOC_EXTS = {".md"}
MAX_FILE_BYTES = 400_000       # skip pathologically large files (generated blobs)

# Data / generated / dump directories: their filenames and contents are NOT
# project vocabulary (they flood the fingerprint with scaffolding like
# l5gn/txt/shard/saga, or - for Chronicler - its own rendered chat vault). Shard
# TITLES for smelt-gateway come from the manifest instead (terms_from_shards),
# so skipping the raw shard dumps here is intentional, not a loss.
DATA_DIRS = {
    "raw_history_txt", "wiki_shards", "saved_shards", "shards",
    "chat_threads", "vault_staging", "_archive",
    "node_modules", "dist", "build", ".git", "__pycache__",
    ".obsidian", ".venv", "venv", "fixtures",
}


def _in_data_dir(rel: str) -> bool:
    return any(seg in DATA_DIRS for seg in rel.split("/"))

# Generic terms that carry no project-distinctiveness. The commonality cutoff
# catches most cross-project noise; this list additionally kills terms that are
# generic even inside a single repo.
STOPWORDS = {
    "main", "utils", "util", "test", "tests", "testing", "readme", "index",
    "app", "src", "lib", "core", "common", "config", "configuration", "settings",
    "setup", "init", "install", "build", "run", "start", "stop", "get", "set",
    "add", "remove", "delete", "update", "create", "new", "old", "temp", "tmp",
    "data", "file", "files", "path", "paths", "dir", "directory", "name", "names",
    "value", "values", "key", "keys", "list", "dict", "map", "item", "items",
    "class", "def", "function", "func", "method", "return", "import", "from",
    "self", "args", "kwargs", "params", "param", "arg", "type", "types", "object",
    "string", "str", "int", "float", "bool", "none", "true", "false", "null",
    "error", "errors", "exception", "result", "results", "output", "input",
    "print", "log", "logs", "logger", "logging", "debug", "info", "warning",
    "the", "and", "for", "with", "this", "that", "your", "you", "our", "all",
    "use", "using", "used", "how", "what", "when", "where", "why", "can", "will",
    "changelog", "license", "licence", "notes", "todo", "doc", "docs", "documentation",
    "example", "examples", "usage", "overview", "introduction", "getting", "started",
    "version", "changes", "changed", "step", "steps", "section", "table", "contents",
    "python", "javascript", "typescript", "node", "npm", "pip", "json", "yaml",
    "html", "css", "api", "http", "https", "url", "uri", "server", "client",
    "module", "modules", "package", "packages", "script", "scripts", "code",
    "project", "projects", "repo", "repository", "folder", "system",
}

# --- identifier regexes (light pass, not real parsing) -----------------------
_PY_DEF_RE = re.compile(r"^\s*(?:class|def)\s+([A-Za-z_]\w+)", re.MULTILINE)
_PY_CONST_RE = re.compile(r"^([A-Z][A-Za-z0-9_]{2,})\s*=", re.MULTILINE)
_JS_DECL_RE = re.compile(
    r"\b(?:function|class|const|let|var)\s+([A-Za-z_$][\w$]+)")
_JS_EXPORT_RE = re.compile(
    r"\bexport\s+(?:default\s+)?(?:async\s+)?(?:function|class|const)\s+([A-Za-z_$][\w$]+)")
_MD_HEADING_RE = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)

# token splitters
_WORD_RE = re.compile(r"[A-Za-z0-9_]+")          # snake_case stays one token
_CAMEL_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z0-9]+|[A-Z]+|[0-9]+")
_IDENT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")   # a clean identifier token


def _norm(term: str) -> str:
    return term.strip().lower()


def _keep(t: str) -> bool:
    return len(t) >= MIN_TERM_LEN and not t.isdigit() and t not in STOPWORDS


def _subtokens(word: str):
    """One raw word -> {clean compound (if identifier-shaped), camel/snake parts}.
    Emoji, punctuation and whitespace never survive - only alphanumeric tokens."""
    out = set()
    w = word.strip().strip("_")
    if not w:
        return out
    if _IDENT_RE.match(w):
        out.add(_norm(w))                    # keep clean compound, e.g. SpireApp
    for part in w.replace("-", "_").split("_"):
        if part and part.isalnum():
            out.add(_norm(part))
            for sub in _CAMEL_RE.findall(part):
                if sub.isalnum():
                    out.add(_norm(sub))
    return {t for t in out if _keep(t)}


def split_identifier(name: str):
    """Code identifier -> its distinctive tokens (compound + camel/snake parts)."""
    return _subtokens(name)


def clean_tokens(text: str):
    """Free text (headings, titles) -> word tokens only (never whole phrases)."""
    out = set()
    for word in _WORD_RE.findall(text):
        out |= _subtokens(word)
    return out


def terms_from_filenames(paths):
    c = Counter()
    for rel in paths:
        if _in_data_dir(rel):
            continue
        base = rel.split("/")[-1]
        stem = base.rsplit(".", 1)[0] if "." in base else base
        for t in clean_tokens(stem):
            c[t] += 1
    return c


def _read_text(p: Path):
    try:
        if p.stat().st_size > MAX_FILE_BYTES:
            return None
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def terms_from_code_and_docs(fs_path: Path, paths):
    """Returns (code_counter, doc_counter). Kept separate so the fingerprint can
    reserve slots for clean code identifiers (class/def/const names) - otherwise
    a content-heavy repo's prose headings crowd all code terms out of the top N."""
    code = Counter()
    doc = Counter()
    for rel in paths:
        if _in_data_dir(rel):
            continue
        ext = ("." + rel.rsplit(".", 1)[1].lower()) if "." in rel else ""
        if ext not in CODE_EXTS and ext not in DOC_EXTS:
            continue
        text = _read_text(fs_path / rel)
        if not text:
            continue
        if ext in CODE_EXTS:
            names = (_PY_DEF_RE.findall(text) + _PY_CONST_RE.findall(text)
                     + _JS_DECL_RE.findall(text) + _JS_EXPORT_RE.findall(text))
            for nm in names:
                for t in split_identifier(nm):
                    code[t] += 1
        if ext in DOC_EXTS:
            for heading in _MD_HEADING_RE.findall(text):
                for t in clean_tokens(heading):
                    doc[t] += 1
    return code, doc


def terms_from_shards(fs_path: Path):
    """smelt-gateway (S2.1.d): distinctive tokens from shard titles in
    data/shard_manifest.json. Titles look like
    'L5GN_BLUE_ChefDeProjet_Kanban_<longID>.txt' -> ChefDeProjet, Kanban."""
    c = Counter()
    man = fs_path / "data" / "shard_manifest.json"
    if not man.is_file():
        return c
    try:
        obj = json.loads(man.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return c
    files = obj.get("sharded_files", []) if isinstance(obj, dict) else []
    id_seg = re.compile(r"^1[A-Za-z0-9_\-]{20,}$")   # drive-style long IDs
    for fn in files:
        stem = fn.split("/")[-1]
        stem = re.sub(r"\.(txt|md|json)$", "", stem, flags=re.IGNORECASE)
        segs = stem.split("_")
        # drop scope prefixes and the long drive IDs; keep human title segments
        for seg in segs:
            if seg in {"L5GN", "BLUE", "CORE", "PRJ", "SAGA", "SHARD",
                       "Part", "PartA", "PartB", "Vol"} or not seg:
                continue
            if id_seg.match(seg):
                continue
            for t in clean_tokens(seg):
                c[t] += 1
    return c


def harvest_terms(entry, fs_path: Path):
    """All candidate terms for one project. Returns (combined, code_only):
    `combined` = filenames + code identifiers + doc headings (+shard titles);
    `code_only` = code identifiers alone, used to reserve fingerprint slots for
    clean structural terms. Both are Counter(term -> raw frequency)."""
    paths = entry.get("file_inventory", {}).get("paths", [])
    code, doc = terms_from_code_and_docs(fs_path, paths)
    combined = Counter()
    combined.update(terms_from_filenames(paths))
    combined.update(code)
    combined.update(doc)
    if entry["canonical_name"] == "smelt-gateway":
        combined.update(terms_from_shards(fs_path))
    for c in (combined, code):
        for t in list(c):
            if t in STOPWORDS or len(t) < MIN_TERM_LEN or t.isdigit():
                del c[t]
    return combined, code


def score_distinctive(per_project_counts, n_projects, top_n):
    """TF-IDF-shaped scoring + commonality cutoff. Returns
    {canonical_name: {term: weight}} keeping the top_n per project."""
    doc_freq = Counter()
    for counts in per_project_counts.values():
        for term in counts:
            doc_freq[term] += 1
    max_df = max(1, int(COMMONALITY_CUTOFF * n_projects))
    out = {}
    for name, counts in per_project_counts.items():
        scored = {}
        for term, tf in counts.items():
            df = doc_freq[term]
            if df > max_df:
                continue                       # too common to be distinctive
            if df >= n_projects:
                continue                       # in every project -> zero idf
            # Sublinear tf so one giant doc that repeats a heading 500x cannot
            # swamp a term that genuinely characterises the project.
            weight = (1.0 + math.log(tf)) * math.log(n_projects / df)
            if weight <= 0:
                continue
            scored[term] = round(weight, 4)
        top = dict(sorted(scored.items(), key=lambda kv: (-kv[1], kv[0]))[:top_n])
        out[name] = top
    return out


def select_terms(scored, code_terms, top_n, reserve):
    """Compose one project's final term set from a wide scored pool.

    Takes the top (top_n - reserve) terms outright (bulk distinctive vocabulary),
    then fills the remaining `reserve` slots with the highest-weight CODE
    identifiers not already chosen. This guarantees a content-heavy repo still
    surfaces clean structural names (delve, plug, dispatcher) that its prose
    headings would otherwise outrank. Any reserve slots code can't fill are
    topped up with the next-best bulk terms, so we always return up to top_n.

      scored     : {term: weight} distinctiveness-scored (already cutoff-filtered)
      code_terms : set of terms that originated from code identifiers
    """
    ordered = sorted(scored.items(), key=lambda kv: (-kv[1], kv[0]))
    bulk_n = max(0, top_n - reserve)
    chosen = dict(ordered[:bulk_n])
    # fill reserved slots with best code identifiers not yet chosen
    for term, weight in ordered:
        if len(chosen) >= top_n:
            break
        if term not in chosen and term in code_terms:
            chosen[term] = weight
    # top up any unfilled reserve with next-best bulk terms
    for term, weight in ordered:
        if len(chosen) >= top_n:
            break
        if term not in chosen:
            chosen[term] = weight
    return dict(sorted(chosen.items(), key=lambda kv: (-kv[1], kv[0])))


# ---------------------------------------------------------------------------
# Fingerprint build (registry)
# ---------------------------------------------------------------------------
def build_fingerprints(registry, force, top_n):
    """Returns (vocab_by_project, rebuilt_names, skipped_names, missing_names).
    vocab_by_project covers ALL projects (fresh or reused) so the evidence pass
    sees the complete corpus even when only some fingerprints were rebuilt."""
    projects = registry["projects"]
    n = len(projects)

    fresh_combined = {}        # name -> Counter (filenames + code + docs [+shards])
    fresh_code = {}            # name -> set(code-identifier terms) for the reserve
    reuse_terms = {}           # projects whose stored block we keep
    rebuilt, skipped, missing = [], [], []

    for entry in projects:
        name = entry["canonical_name"]
        if entry.get("_orphaned"):
            missing.append(name)
            continue
        fs_path = resolve_fs(entry)
        if not fs_path.is_dir():
            missing.append(name)
            continue
        is_git = entry.get("vcs") == "git"
        sig = current_signature(fs_path, is_git)      # ('git', head) | ('sig', md5)
        vocab = entry.get("vocabulary")
        if not force and vocab and _sig_matches(vocab, sig):
            skipped.append(name)
            reuse_terms[name] = vocab.get("terms", {})
            continue
        combined, code = harvest_terms(entry, fs_path)
        fresh_combined[name] = combined
        fresh_code[name] = set(code)
        rebuilt.append((entry, fs_path, is_git, sig))

    # Distinctiveness needs the WHOLE corpus. Combine reused term-sets (as
    # presence-only counts) with freshly harvested counts so doc-freq is global.
    per_project_counts = {name: Counter(fresh_combined[name]) for name in fresh_combined}
    for name, terms in reuse_terms.items():
        per_project_counts[name] = Counter({t: 1 for t in terms})

    # Score a WIDE pool (not just top_n) so select_terms has room to reserve
    # code-identifier slots below the bulk cut.
    scored = score_distinctive(per_project_counts, max(1, n), top_n * 8)

    # Write fresh vocabulary blocks; reused blocks keep their stored terms but
    # are represented in `scored` too (for the evidence pass).
    vocab_by_project = dict(reuse_terms)
    for entry, fs_path, is_git, sig in rebuilt:
        name = entry["canonical_name"]
        terms = select_terms(scored.get(name, {}), fresh_code.get(name, set()),
                             top_n, RESERVE_CODE)
        entry["vocabulary"] = {
            "built_at": utc_now(),
            "source_commit": sig[1] if sig[0] == "git" else None,
            "source_signature": sig[1] if sig[0] == "sig" else None,
            "terms": terms,
        }
        entry["registry_updated"] = utc_now()
        vocab_by_project[name] = terms

    return vocab_by_project, rebuilt, skipped, missing


def _sig_matches(vocab, sig):
    kind, val = sig
    if val is None:
        return False
    if kind == "git":
        return vocab.get("source_commit") == val
    return vocab.get("source_signature") == val


# ---------------------------------------------------------------------------
# Evidence build (link_evidence) - needs the DB
# ---------------------------------------------------------------------------
LINK_EVIDENCE_DDL = """
CREATE TABLE IF NOT EXISTS link_evidence (
    evidence_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id        TEXT,
    project          TEXT,
    signal           TEXT,
    weight           REAL,
    detail           TEXT,
    produced_at      TEXT,
    producer_version TEXT
);
CREATE INDEX IF NOT EXISTS idx_link_evidence_thread ON link_evidence(thread_id);
CREATE INDEX IF NOT EXISTS idx_link_evidence_signal ON link_evidence(signal);
"""


def build_term_index(vocab_by_project):
    """term(lower) -> {project: weight}. Only distinctive terms exist here."""
    idx = defaultdict(dict)
    for project, terms in vocab_by_project.items():
        for term, weight in terms.items():
            idx[_norm(term)][project] = weight
    return idx


def thread_word_sets(conn):
    """thread_id -> set(lowercased word tokens) over all its message content."""
    words = defaultdict(set)
    cur = conn.execute("""
        SELECT thread_id, content FROM messages
        WHERE thread_id IS NOT NULL AND content IS NOT NULL AND TRIM(content) <> ''
    """)
    for row in cur:
        toks = _WORD_RE.findall(row["content"].lower())
        if toks:
            words[row["thread_id"]].update(toks)
    return words


def compute_vocab_votes(word_sets, term_index):
    """Yield (thread_id, project, weight, detail). At most MAX_EVIDENCE_PER_PAIR
    rows per thread->project pair, choosing the highest-weight matched terms."""
    votes = []
    for thread_id, words in word_sets.items():
        per_project = defaultdict(list)     # project -> [(fp_weight, term)]
        for term, projects in term_index.items():
            if term in words:
                for project, fp_weight in projects.items():
                    per_project[project].append((fp_weight, term))
        for project, hits in per_project.items():
            hits.sort(key=lambda x: (-x[0], x[1]))
            for _, term in hits[:MAX_EVIDENCE_PER_PAIR]:
                votes.append((thread_id, project, EVIDENCE_WEIGHT, term))
    return votes


def write_evidence(conn, votes):
    now = utc_now()
    conn.executescript(LINK_EVIDENCE_DDL)
    conn.execute("DELETE FROM link_evidence WHERE signal = ?", (SIGNAL,))
    conn.executemany(
        "INSERT INTO link_evidence "
        "(thread_id, project, signal, weight, detail, produced_at, producer_version) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [(t, p, SIGNAL, w, d, now, PRODUCER_VERSION) for (t, p, w, d) in votes],
    )
    conn.commit()


# ---------------------------------------------------------------------------
def report_fingerprints(vocab_by_project, rebuilt, skipped, missing):
    print("=" * 68)
    print("build_vocabulary - fingerprints")
    print("=" * 68)
    rebuilt_names = {e["canonical_name"] for e, *_ in rebuilt}
    for name in sorted(vocab_by_project):
        terms = vocab_by_project[name]
        tag = "rebuilt" if name in rebuilt_names else "reused "
        top = list(terms.items())[:8]
        preview = ", ".join(f"{t}({w})" for t, w in top)
        print(f"  [{tag}] {name:28} {len(terms):3} terms | {preview}")
    for name in skipped:
        if name not in vocab_by_project:
            print(f"  [skip ] {name:28} (unchanged, no stored terms)")
    for name in missing:
        print(f"  [MISS ] {name:28} (no folder / orphaned)")
    print("-" * 68)
    print(f"{len(rebuilt)} rebuilt, {len(skipped)} unchanged, {len(missing)} missing.")


def report_evidence(votes):
    per_project = Counter(p for _, p, _, _ in votes)
    threads = len({t for t, _, _, _ in votes})
    print("=" * 68)
    print("build_vocabulary - evidence (vocabulary signal, weight 0.3)")
    print("=" * 68)
    for project in sorted(per_project):
        print(f"  {project:28} {per_project[project]:5} votes")
    print("-" * 68)
    print(f"{len(votes)} evidence rows across {threads} threads.")


def run(apply, force, top_n):
    if not REGISTRY_PATH.is_file():
        raise SystemExit(f"[build_vocabulary] registry missing: {REGISTRY_PATH} "
                         "(run build_registry.py / build_inventory.py first)")
    registry = read_json(REGISTRY_PATH)

    vocab_by_project, rebuilt, skipped, missing = build_fingerprints(
        registry, force, top_n)
    report_fingerprints(vocab_by_project, rebuilt, skipped, missing)

    if apply:
        registry["generated_at"] = utc_now()
        write_json_atomic(REGISTRY_PATH, registry)
        print(f"\nWrote vocabulary blocks to {REGISTRY_PATH}")

    # Evidence pass (needs the DB). In dry-run we still compute + report counts.
    term_index = build_term_index(vocab_by_project)
    conn = get_connection()
    try:
        word_sets = thread_word_sets(conn)
        votes = compute_vocab_votes(word_sets, term_index)
        if apply:
            write_evidence(conn, votes)
    finally:
        conn.close()

    report_evidence(votes)
    if apply:
        print(f"\nWrote {len(votes)} '{SIGNAL}' rows to link_evidence.")
    else:
        print("\n(dry-run - nothing written. Re-run with --apply to persist.)")
    return vocab_by_project, votes


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Per-project vocabulary fingerprints + evidence (S2).")
    ap.add_argument("--apply", action="store_true",
                    help="Write vocabulary blocks to the registry AND vocabulary "
                         "rows to link_evidence (default is dry-run preview).")
    ap.add_argument("--force", action="store_true",
                    help="Rebuild all fingerprints, ignoring skip-if-unchanged.")
    ap.add_argument("--top", type=int, default=TOP_TERMS_DEFAULT,
                    help=f"Terms kept per project (default {TOP_TERMS_DEFAULT}).")
    args = ap.parse_args()
    run(args.apply, args.force, args.top)
