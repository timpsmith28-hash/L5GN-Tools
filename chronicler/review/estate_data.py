"""Read-only estate layer for the local deck (COWORK brief: local deck slice 1).

Loads ``data/estate.json`` once at startup and exposes it to the surface: the
build header, the authored-document catalogue, and the render-time document
read that DECISIONS 0027 authorises.

Three rules govern every line here, and each is load-bearing:

  * **Read-only.** This module opens files for reading and nothing else. There
    is no write path in this slice at all -- no cache, no index file, no copy
    under ``data/``. 0027's condition (1) is met by the absence of a writer,
    not by a policy we promise to keep.

  * **The route never sees a path.** A document is addressed by an opaque
    identifier (:func:`document_id`, a digest of project + relative path)
    resolved against the in-memory catalogue built from ``estate.json``. A
    caller cannot name a file; it can only name a document the scanner already
    found. That is check one.

  * **The resolved path is re-verified before a byte is read.** Even for an id
    that resolved cleanly, the absolute path must sit inside a *configured*
    estate root (``l5gntools.config.estate_roots``), compared after
    ``realpath`` so a symlink out of the estate is caught. That is check two.

The two checks are deliberately independent and both are enforced: check one
would be enough if ``estate.json`` were trusted, and check two would be enough
if the identifier were trusted. Neither assumption is one to build a file
reader on, so we make both.

The safety anchor is the *running machine's* configured roots, not the
``roots`` recorded inside ``estate.json``. A snapshot is data; data that names
its own safe directories is not a boundary. If the snapshot was produced on
another machine, its projects simply fall outside this machine's roots and are
refused -- the honest outcome.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from l5gntools import config
from l5gntools.common import DATA_DIR

#: Where the estate snapshot lives. A parameter everywhere below; this is only
#: the default, so testers point at a temp dir without touching the real one.
DEFAULT_ESTATE_PATH: Path = DATA_DIR / "estate.json"

#: Documents larger than this are truncated rather than streamed whole into a
#: browser. A 2 MiB markdown file is already pathological; the reader says so
#: instead of hanging the tab (honest failure, house style).
MAX_DOC_BYTES: int = 2 * 1024 * 1024

#: Render order for the document nav. `knowledge` leads because 0026 makes it
#: the artefact of record; `unclassified` trails because it is ordinary prose,
#: not a gap. Any type not listed sorts alphabetically between the two.
DOC_TYPE_ORDER: tuple[str, ...] = (
    "knowledge", "decisions", "adr", "intent", "architecture",
    "brief", "report", "uat", "plan", "runbook", "glossary",
    "claude_md", "readme", "unclassified",
)

#: The provenance this slice will read. Generated documents are machine output;
#: browsing them is a different feature with a different justification, so they
#: never enter the catalogue and therefore have no identifier to request.
AUTHORED = "authored"


class DocumentRefused(Exception):
    """A document read was refused. ``reason`` is a stable machine-readable tag
    so the surface renders the refusal without string-matching a message."""

    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason
        self.message = message


def _type_rank(doc_type: str) -> tuple[int, str]:
    try:
        return (DOC_TYPE_ORDER.index(doc_type), "")
    except ValueError:
        # Unknown type: between `readme` and `unclassified`, alphabetically.
        return (len(DOC_TYPE_ORDER) - 1, doc_type)


def document_id(project: str, relpath: str) -> str:
    """The opaque handle for a document.

    A digest of ``project`` + ``relpath``, which means it is stable across
    builds (unlike a list index, which shifts when a document is added) and
    carries no path information a caller could manipulate. The NUL separator
    keeps ``("ab", "c")`` and ``("a", "bc")`` distinct.
    """
    payload = f"{project}\x00{relpath}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def _norm(path) -> str:
    """A path normalised for comparison: symlinks resolved, case folded on the
    platforms that need it. ``realpath`` is what makes the containment check
    hold against a symlink pointing out of the estate."""
    return os.path.normcase(os.path.realpath(str(path)))


def path_within_roots(candidate, roots) -> bool:
    """True iff ``candidate`` sits inside one of ``roots`` after both are fully
    resolved. This is check two, and it is the last thing that happens before a
    file is opened.

    Compared with ``os.sep`` appended so ``/estate-evil`` is not read as being
    inside ``/estate``, which a bare ``startswith`` would allow.
    """
    if not roots:
        return False
    try:
        target = _norm(candidate)
    except (OSError, ValueError):
        return False
    for root in roots:
        try:
            base = _norm(root)
        except (OSError, ValueError):
            continue
        if target == base or target.startswith(base + os.sep):
            return True
    return False


def parse_timestamp(value) -> datetime | None:
    """Parse an ISO timestamp from the snapshot. Tolerates a trailing ``Z``,
    which ``fromisoformat`` rejects before 3.11 and this package supports 3.10."""
    if not isinstance(value, str) or not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


class EstateData:
    """The loaded snapshot, or an honest account of why there isn't one.

    ``available`` is False when ``estate.json`` is absent or unreadable. Every
    accessor still works in that state and returns empty results, so the estate
    routes report the gap cleanly and the rest of the app keeps serving --
    which is the whole point of the preflight split.
    """

    def __init__(self, snapshot: dict | None, roots: list[Path],
                 source: Path, reason: str | None = None):
        self.source = Path(source)
        self.roots: list[Path] = [Path(r) for r in (roots or [])]
        self.reason = reason
        self.available = snapshot is not None and reason is None
        self._snapshot: dict = snapshot or {}
        self.warnings: list[str] = []
        self._documents: list[dict] = []
        self._by_id: dict[str, dict] = {}
        if self.available:
            self._build_catalogue()

    # --- construction ------------------------------------------------------

    @classmethod
    def load(cls, estate_path=None, roots=None) -> "EstateData":
        """Load the snapshot once. ``roots`` defaults to this machine's
        configured estate roots -- the safety anchor, deliberately not taken
        from the snapshot itself."""
        path = Path(estate_path) if estate_path else DEFAULT_ESTATE_PATH
        if roots is None:
            roots = config.estate_roots() or []
        if not path.exists():
            return cls(None, roots, path, reason="estate_missing")
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            return cls(None, roots, path, reason=f"estate_unreadable: {exc}")
        if not isinstance(raw, dict):
            return cls(None, roots, path, reason="estate_malformed: not an object")
        return cls(raw, roots, path)

    def _build_catalogue(self) -> None:
        """Flatten every project's authored documents into one addressable list.

        A relative path containing a ``..`` segment, or an absolute one, is
        dropped here with a warning rather than admitted and caught later. The
        catalogue is the thing the identifier resolves against, so keeping it
        clean means a poisoned snapshot cannot mint an identifier that points
        anywhere interesting in the first place.
        """
        for project in self._snapshot.get("projects", []):
            if not isinstance(project, dict):
                continue
            name = project.get("name") or ""
            proj_path = project.get("path") or ""
            census = project.get("doc_census") or {}
            for doc in census.get("docs", []):
                if not isinstance(doc, dict):
                    continue
                if doc.get("provenance") != AUTHORED:
                    continue  # generated documents are not offered (brief, Task 2)
                relpath = doc.get("path") or ""
                if not relpath:
                    continue
                parts = relpath.replace("\\", "/").split("/")
                if ".." in parts or os.path.isabs(relpath) or relpath[1:2] == ":":
                    self.warnings.append(
                        f"{name}: dropped document with a non-relative path {relpath!r}")
                    continue
                doc_id = document_id(name, relpath)
                if doc_id in self._by_id:
                    existing = self._by_id[doc_id]
                    if (existing["project"], existing["path"]) == (name, relpath):
                        continue  # exact duplicate row in the census; harmless
                    self.warnings.append(
                        f"identifier collision on {doc_id}: "
                        f"{existing['project']}/{existing['path']} vs {name}/{relpath}")
                    continue
                entry = {
                    "id": doc_id,
                    "project": name,
                    "project_path": proj_path,
                    "path": relpath,
                    "title": doc.get("title") or relpath.rsplit("/", 1)[-1],
                    "doc_type": doc.get("doc_type") or "unclassified",
                    "words": doc.get("words"),
                    "bytes": doc.get("bytes"),
                    "headings": doc.get("headings"),
                }
                self._documents.append(entry)
                self._by_id[doc_id] = entry

    # --- the build header --------------------------------------------------

    def header(self) -> dict:
        """What the deck must state above everything else: which build this is,
        when it ran, and whether the toolkit was dirty when it did.

        A deck rendering a three-day-old snapshot has to say so, which is why
        ``age_seconds`` is computed here rather than left to the browser's
        clock -- the answer should not depend on the reader's timezone.
        """
        snap = self._snapshot
        generated_at = snap.get("generated_at")
        parsed = parse_timestamp(generated_at)
        age_seconds = None
        if parsed is not None:
            age_seconds = max(0.0, (datetime.now(timezone.utc) - parsed).total_seconds())
        return {
            "available": self.available,
            "reason": self.reason,
            "source": str(self.source),
            "generated_at": generated_at,
            "age_seconds": age_seconds,
            "toolkit_version": snap.get("toolkit_version"),
            "toolkit_commit": snap.get("toolkit_commit"),
            "toolkit_dirty": snap.get("toolkit_dirty"),
            "estate_name": snap.get("estate_name"),
            "estate_root": snap.get("estate_root"),
            "producer_host": snap.get("producer_host"),
            "project_count": len(snap.get("projects", [])),
            "authored_document_count": len(self._documents),
            "roots": [str(r) for r in self.roots],
            "warnings": list(self.warnings),
        }

    # --- the document catalogue -------------------------------------------

    @property
    def snapshot(self) -> dict:
        """The raw loaded snapshot. Read-only by convention -- callers that
        want a view over it (the timeline) take it from here rather than
        re-reading the file, so the whole surface renders one build."""
        return self._snapshot

    @property
    def documents(self) -> list[dict]:
        """Every authored document across the estate, catalogue order."""
        return list(self._documents)

    def projects(self) -> list[dict]:
        """The nav's top level: one row per project with its authored/generated
        split, so a project with 288 generated docs and 2 authored ones reads
        as exactly that rather than as a well-documented project."""
        out = []
        for project in self._snapshot.get("projects", []):
            if not isinstance(project, dict):
                continue
            census = project.get("doc_census") or {}
            git = project.get("git_summary") or {}
            name = project.get("name") or ""
            authored = [d for d in self._documents if d["project"] == name]
            types = sorted({d["doc_type"] for d in authored}, key=_type_rank)
            out.append({
                "project": name,
                "scope": project.get("scope"),
                "is_git": bool(git.get("is_git")),
                "authored_count": len(authored),
                "generated_count": census.get("generated_count"),
                "doc_count": census.get("doc_count"),
                "doc_types": types,
                "has_knowledge": any(d["doc_type"] == "knowledge" for d in authored),
            })
        out.sort(key=lambda p: p["project"].lower())
        return out

    def documents_for(self, project: str) -> list[dict]:
        """One project's authored documents grouped by type, ``knowledge`` first.

        Returns groups rather than a flat list because the grouping *is* the
        navigation: 0026's point is that a knowledge document is a different
        kind of thing from a README, and a flat alphabetical list hides that.
        """
        docs = [d for d in self._documents if d["project"] == project]
        groups: dict[str, list[dict]] = {}
        for doc in docs:
            groups.setdefault(doc["doc_type"], []).append(doc)
        out = []
        for doc_type in sorted(groups, key=_type_rank):
            entries = sorted(groups[doc_type], key=lambda d: d["path"].lower())
            out.append({"doc_type": doc_type, "count": len(entries),
                        "documents": entries})
        return out

    def document(self, doc_id: str) -> dict:
        """Catalogue metadata for an identifier, or refuse. **Check one.**

        A traversal attempt arrives here as an identifier that is not in the
        map -- ``../../etc/passwd`` is not a digest, so it resolves to nothing.
        This is why the route takes an identifier and not a path.
        """
        entry = self._by_id.get(str(doc_id))
        if entry is None:
            raise DocumentRefused(
                "unknown_document",
                "No authored document with that identifier is in this build.")
        return entry

    def resolve_document_path(self, doc_id: str) -> Path:
        """The absolute path for an identifier, verified inside the configured
        estate roots. **Check two**, run even though check one has passed.

        The refusal is the same shape whether the path escaped the roots or the
        roots are unconfigured: in both cases the surface has no authority to
        read the file, and distinguishing them tells a caller about the
        machine's configuration for no benefit.
        """
        entry = self.document(doc_id)
        base = Path(entry["project_path"])
        candidate = base.joinpath(*entry["path"].replace("\\", "/").split("/"))
        if not self.roots:
            raise DocumentRefused(
                "no_configured_roots",
                "This machine declares no estate roots, so no file is inside "
                "the boundary 0027 requires. Set 'roots' in config.")
        if not path_within_roots(candidate, self.roots):
            raise DocumentRefused(
                "outside_estate_roots",
                "That document resolves outside this machine's configured "
                "estate roots and will not be read (DECISIONS 0027).")
        return Path(os.path.realpath(str(candidate)))

    def read_document(self, doc_id: str) -> dict:
        """Read a document from disk **at render time** and return its text.

        Nothing is cached, here or anywhere. The next request re-reads the file,
        which is both 0027's condition (1) and the reason the deck never shows
        a document that no longer matches what is on disk.

        The text is returned raw. It is *not* converted to HTML: the surface
        renders it into a ``<pre>`` via ``textContent``. A hand-rolled markdown
        pass would be a second parser to maintain and an HTML-injection surface
        for a cosmetic gain, and there is no markdown library to reach for --
        so the simpler option is also the safer one.
        """
        path = self.resolve_document_path(doc_id)
        entry = self.document(doc_id)
        if not path.is_file():
            raise DocumentRefused(
                "not_a_file",
                f"{entry['path']} is in the build but is not a readable file "
                "on disk now -- the snapshot is stale or the file moved.")
        try:
            size = path.stat().st_size
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                text = handle.read(MAX_DOC_BYTES)
        except OSError as exc:
            raise DocumentRefused("unreadable", f"Could not read that document: {exc}")
        truncated = size > MAX_DOC_BYTES
        return {
            **entry,
            "text": text,
            "bytes_on_disk": size,
            "truncated": truncated,
            "note": (f"Truncated at {MAX_DOC_BYTES} bytes of {size}."
                     if truncated else None),
        }
