"""Full-text search across the estate's authored documents (brief, Task 3).

This is the feature the work estate exists for: "I wrote that down somewhere"
becoming a query. It is a sibling of :mod:`estate_data` rather than more of it,
because an index has a lifecycle -- built, capability-checked, possibly degraded
-- and that is a different concern from loading a snapshot.

**The index lives in memory and nowhere else.** ``sqlite3.connect(":memory:")``
means there is no file to leave behind under ``data/``, which is 0027's
condition (1) enforced structurally rather than promised. The document text
that goes into it is read at startup and never written back out.

Why an index at all, rather than scanning per query: the estate's authored
corpus is small (a couple of hundred files) but the alternative is re-reading
every one of them on every keystroke's worth of query, and FTS5 gives ranked
results and snippets for free. Building once at boot costs a single pass over
files the machine has cached anyway.

**FTS5 is capability-checked, not assumed.** It is present in the bundled
sqlite3 here (3.37.2, confirmed), but a Python built against a library compiled
without it would raise on the first ``CREATE VIRTUAL TABLE``. Rather than crash
the surface, the index falls back to a plain substring scan and reports
``engine == "substring"`` so the UI can say plainly that ranking and snippets
are degraded. An honest lesser answer beats a stack trace.
"""
from __future__ import annotations

import re
import sqlite3
import threading

#: Characters either side of a match in a substring-mode snippet.
_SNIPPET_PAD = 90
#: Cap on results returned to the surface for one query.
DEFAULT_LIMIT = 60


def fts5_available() -> bool:
    """True iff this interpreter's sqlite3 can create an FTS5 table.

    Asked by doing it, not by parsing ``compile_options`` -- the only answer
    that matters is whether the statement we are about to run succeeds.
    """
    try:
        conn = sqlite3.connect(":memory:")
    except sqlite3.Error:
        return False
    try:
        conn.execute("CREATE VIRTUAL TABLE _probe USING fts5(body)")
        return True
    except sqlite3.Error:
        return False
    finally:
        conn.close()


def _read_text(path) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return ""


def _rank_key(doc_type: str) -> int:
    """`knowledge` documents sort ahead of equally-relevant others (0026 makes
    them the artefact of record). Everything else keeps relevance order."""
    return 0 if doc_type == "knowledge" else 1


class DocumentIndex:
    """An in-memory search index over one :class:`~.estate_data.EstateData`.

    ``engine`` is ``"fts5"`` or ``"substring"``; ``notice`` is a sentence for
    the UI when the engine is degraded, and ``None`` when it is not.
    """

    def __init__(self, estate, force_substring: bool = False):
        self.estate = estate
        self.engine = "substring"
        self.notice: str | None = None
        self.indexed = 0
        self.skipped: list[dict] = []
        self._conn: sqlite3.Connection | None = None
        self._rows: list[tuple[dict, str]] = []
        # The index is built once on the main thread and then queried from
        # uvicorn's threadpool, which is a different thread per request --
        # sqlite3 refuses that by default and the failure only appears under
        # the real server, never in a single-threaded tester. So the connection
        # is opened with check_same_thread=False and every query takes this
        # lock. The index is read-only after construction, so the lock is
        # uncontended in practice and correctness costs nothing.
        self._lock = threading.Lock()
        self._build(force_substring=force_substring)

    # --- construction ------------------------------------------------------

    def _corpus(self):
        """Yield ``(entry, text)`` for every authored document that resolves
        safely and reads. Resolution goes through
        :meth:`EstateData.resolve_document_path`, so the index is subject to
        exactly the same containment check as a render -- a document the
        surface would refuse to show is also one it will not search."""
        from .estate_data import DocumentRefused

        for entry in self.estate.documents:
            try:
                path = self.estate.resolve_document_path(entry["id"])
            except DocumentRefused as exc:
                self.skipped.append({"id": entry["id"], "project": entry["project"],
                                     "path": entry["path"], "reason": exc.reason})
                continue
            if not path.is_file():
                self.skipped.append({"id": entry["id"], "project": entry["project"],
                                     "path": entry["path"], "reason": "not_a_file"})
                continue
            text = _read_text(path)
            if text:
                yield entry, text

    def _build(self, force_substring: bool = False) -> None:
        rows = list(self._corpus())
        self._rows = rows
        self.indexed = len(rows)
        if force_substring or not fts5_available():
            self.engine = "substring"
            self.notice = (
                "FTS5 is not available in this interpreter's sqlite3, so search "
                "is a plain case-insensitive substring scan: no relevance "
                "ranking and no phrase syntax. Results are still complete."
                if not force_substring else
                "Search is running in substring mode by request: no relevance "
                "ranking and no phrase syntax.")
            return
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        conn.execute("CREATE VIRTUAL TABLE docs USING fts5(doc_id UNINDEXED, body)")
        conn.executemany("INSERT INTO docs (doc_id, body) VALUES (?, ?)",
                         [(entry["id"], text) for entry, text in rows])
        conn.commit()
        self._conn = conn
        self.engine = "fts5"
        self.notice = None

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    # --- querying ----------------------------------------------------------

    def status(self) -> dict:
        return {
            "engine": self.engine,
            "notice": self.notice,
            "indexed": self.indexed,
            "skipped": len(self.skipped),
            "skipped_detail": self.skipped[:20],
            "persisted": False,
        }

    def search(self, query: str, project: str | None = None,
               limit: int = DEFAULT_LIMIT) -> dict:
        """Search the corpus, optionally scoped to one project.

        Returns ``{"engine", "notice", "query", "project", "results", ...}``
        where each result carries the project, title, ``doc_type``, the opaque
        id (so a hit opens directly) and a snippet with the match in context.
        """
        text = (query or "").strip()
        if not text:
            return {"engine": self.engine, "notice": self.notice, "query": "",
                    "project": project, "count": 0, "results": [],
                    "error": None}
        if self.engine == "fts5":
            try:
                results = self._search_fts(text, project, limit)
                error = None
            except sqlite3.OperationalError as exc:
                # A malformed FTS5 expression (an unbalanced quote, a bare
                # `AND`) is a user typo, not a fault. Say so and fall back to
                # substring for this one query rather than returning nothing.
                results = self._search_substring(text, project, limit)
                error = (f"That query is not valid FTS5 syntax ({exc}); "
                         "answered as a plain substring search instead.")
        else:
            results = self._search_substring(text, project, limit)
            error = None
        return {
            "engine": self.engine,
            "notice": self.notice,
            "query": text,
            "project": project,
            "count": len(results),
            "results": results,
            "error": error,
        }

    def _entries(self, project: str | None):
        for entry, body in self._rows:
            if project and entry["project"] != project:
                continue
            yield entry, body

    def _search_fts(self, query: str, project: str | None, limit: int) -> list[dict]:
        by_id = {entry["id"]: entry for entry, _ in self._entries(project)}
        if not by_id:
            return []
        with self._lock:
            if self._conn is None:
                return []
            rows = self._conn.execute(
                "SELECT doc_id, snippet(docs, 1, '\x02', '\x03', ' … ', 24) AS snip, "
                "       rank AS score "
                "FROM docs WHERE docs MATCH ? ORDER BY rank",
                (query,)).fetchall()
        out = []
        for doc_id, snip, score in rows:
            entry = by_id.get(doc_id)
            if entry is None:
                continue  # filtered out by project scope
            out.append(self._result(entry, snip, score))
        out.sort(key=lambda r: (_rank_key(r["doc_type"]), r["score"]))
        return out[:limit]

    def _search_substring(self, query: str, project: str | None, limit: int) -> list[dict]:
        needle = query.lower()
        out = []
        for entry, body in self._entries(project):
            haystack = body.lower()
            pos = haystack.find(needle)
            if pos < 0:
                continue
            hits = haystack.count(needle)
            start = max(0, pos - _SNIPPET_PAD)
            end = min(len(body), pos + len(needle) + _SNIPPET_PAD)
            snip = ("… " if start else "") + body[start:pos] + "\x02" + \
                   body[pos:pos + len(needle)] + "\x03" + \
                   body[pos + len(needle):end] + (" …" if end < len(body) else "")
            # No relevance model in this mode, so rank by hit count descending
            # and say (via `engine`) that this is what is happening.
            out.append(self._result(entry, snip, -hits))
        out.sort(key=lambda r: (_rank_key(r["doc_type"]), r["score"]))
        return out[:limit]

    @staticmethod
    def _result(entry: dict, snippet: str, score: float) -> dict:
        return {
            "id": entry["id"],
            "project": entry["project"],
            "path": entry["path"],
            "title": entry["title"],
            "doc_type": entry["doc_type"],
            "is_knowledge": entry["doc_type"] == "knowledge",
            "snippet": re.sub(r"\s+", " ", snippet).strip(),
            "score": score,
        }
