"""Shared scan-scope filter -- one place that decides what a content-walking
scanner is allowed to read.

Three exclusions, one uniform accounting:

* **gitignored** -- resolved by *reusing* `file_census`'s single .gitignore
  implementation (:func:`file_census._git_lookup` / :func:`file_census.status_of`).
  The bugfix brief is explicit: reuse it, never add a second ignore parser.
* **vendored** -- bundled dependencies / model weights (`common.is_vendored`).
* **data / chat dirs** -- personal chat archives and bulk exports, out of scope
  *even when a project forgot to gitignore them*. The wall doctrine keeps chat
  transcripts out of every governance scan; `todo_adr_scanner` mining 298
  "TODO"-shaped strings out of `raw_claude_files/conversations.json` was both a
  report-bloating bug and a doctrine breach (Task A).

A scanner builds one :class:`Scope` per project and calls :meth:`Scope.skip` on
every candidate path. Skips are counted by reason so each scanner can report
"how many paths were skipped and why" -- the skip count is itself a governance
signal ("we did not read your chat archive").

Not a scanner and not registered, so the read-only/stdlib auditors do not walk
this file; it is nonetheless read-only and stdlib-only by construction.
"""
from __future__ import annotations

from pathlib import Path

from ..common import is_vendored, rel
from .file_census import _git_lookup, status_of

#: Directory names that hold personal chat archives or bulk data exports. Out of
#: scope for every content scanner. Matched against each path *segment* by exact
#: name, or by the families ``raw_*`` and ``*_files``.
DATA_DIR_NAMES: frozenset[str] = frozenset({
    "chat_threads", "vault_staging", "Takeout",
    "raw_claude_files", "raw_gemini_files", "conversations",
})
DATA_DIR_PREFIXES: tuple[str, ...] = ("raw_",)
DATA_DIR_SUFFIXES: tuple[str, ...] = ("_files",)

SKIP_REASONS: tuple[str, ...] = ("data_dir", "vendored", "gitignored")


def is_data_dir_name(name: str) -> bool:
    """True when a single path segment names a data/chat directory."""
    return (name in DATA_DIR_NAMES
            or name.startswith(DATA_DIR_PREFIXES)
            or name.endswith(DATA_DIR_SUFFIXES))


class Scope:
    """Per-project scope decision + skip accounting.

    ``git`` is loaded once (one `ls-files` + one `status`, via file_census). For a
    non-git project it is ``None`` and nothing is skipped as gitignored -- there is
    no ignore authority to consult -- but data-dir and vendored skips still apply.
    """

    def __init__(self, target: Path):
        self.target = Path(target)
        self.git = _git_lookup(self.target)
        self.skipped: dict[str, int] = {r: 0 for r in SKIP_REASONS}

    def reason_to_skip(self, path: Path) -> str | None:
        """Why ``path`` is out of scope, or ``None`` if it may be read.

        Data-dir wins over gitignore so the *reason* reported is the doctrine one
        ("we did not read your chat archive") rather than the incidental one.
        """
        relpath = rel(path, self.target)
        segments = relpath.split("/")
        if any(is_data_dir_name(seg) for seg in segments[:-1]):
            return "data_dir"
        if is_vendored(path):
            return "vendored"
        if status_of(relpath, self.git) == "ignored":
            return "gitignored"
        return None

    def skip(self, path: Path, honor: tuple[str, ...] = SKIP_REASONS) -> bool:
        """True if ``path`` is out of scope; records the reason for reporting.

        ``honor`` narrows which exclusions apply. `env_scanner` passes
        ``("data_dir", "vendored")`` because it must still *see* a gitignored
        ``.env`` in order to label it ``ignored`` -- the correct state is a finding,
        not a thing to hide. Everyone else skips all three."""
        reason = self.reason_to_skip(path)
        if reason is None or reason not in honor:
            return False
        self.skipped[reason] += 1
        return True

    def skip_dir(self, name: str) -> bool:
        """True when a bare directory *name* (not a full path) is a data
        directory -- for callers that prune whole subtrees before walking them
        (``file_census``) rather than filtering individual file paths one at a
        time. Only the data-dir reason applies here: a directory-pruning caller
        already has its own git-status classification for gitignored/vendored
        (that is precisely the tier system `file_census` reports), so this is
        deliberately narrower than :meth:`skip`.

        Recorded as one skip per pruned directory, not one per file inside it --
        counting the files would mean walking the tree, which is the thing this
        guards against. The doctrine is "we did not read your chat archive", not
        "we read it only far enough to count it".
        """
        if is_data_dir_name(name):
            self.skipped["data_dir"] += 1
            return True
        return False

    def report(self) -> dict:
        """The skip census a scanner embeds so the exclusion is visible, not silent."""
        return {
            "skipped_paths": sum(self.skipped.values()),
            "skipped_by_reason": {k: v for k, v in self.skipped.items() if v},
        }
