"""tester_file_census -- the census tiers, the cap, and the at-risk set.

Hermetic: builds its own synthetic tree in a temp dir with one file of each kind
the scanner must tell apart -- tracked, untracked, git-ignored, and vendored --
then asserts where each one landed. Shells out to `git` only to create the
fixture, exactly as `tests/_fixture.py` already does.

The load-bearing assertion is the at-risk one. Everything else in this scanner is
an inventory; `at_risk` is the answer to "what will I lose if I delete this
folder", and a wrong answer there is the failure mode that costs a file. It is
checked for *exact* membership, not for containment: a list that happens to
include the right file among six wrong ones is not a working scanner.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from l5gntools.scanners import file_census

_GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}


def _git(proj: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(proj), *args], check=True,
                   env={**os.environ, **_GIT_ENV},
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def make_census_project(root: Path, extra_files: int = 0) -> Path:
    """A repo holding one of every classification the census must distinguish."""
    proj = root / "CensusProj"
    (proj / "src").mkdir(parents=True)
    (proj / ".venv" / "lib").mkdir(parents=True)
    (proj / "logs").mkdir(parents=True)
    (proj / "deep" / "a" / "b" / "c" / "d").mkdir(parents=True)

    (proj / ".gitignore").write_text("logs/\nsecret.txt\n", encoding="utf-8")
    (proj / "src" / "tracked.py").write_text("x = 1\n" * 10, encoding="utf-8")
    (proj / "README.md").write_text("# Census fixture\n", encoding="utf-8")
    # The one file the at-risk set must name, and nothing else.
    (proj / "src" / "untracked.py").write_text("y = 2\n" * 20, encoding="utf-8")
    (proj / "secret.txt").write_text("hunter2\n", encoding="utf-8")          # ignored file
    (proj / "logs" / "run.log").write_text("noise\n" * 50, encoding="utf-8")  # ignored tree
    (proj / ".venv" / "lib" / "dep.py").write_text("z = 3\n" * 200, encoding="utf-8")
    # Below DEPTH_CAP, so its bytes must fold into a capped ancestor.
    (proj / "deep" / "a" / "b" / "c" / "d" / "buried.txt").write_text(
        "deep\n", encoding="utf-8")

    # Bulk files carry DUPLICATE basenames across sibling directories, because
    # real repo trees do (__init__.py, index.md, per-module names) and a fixture
    # of all-unique basenames cannot detect a beyond-cap set that redundantly
    # repeats names already emitted in files[].
    for i in range(extra_files):
        d = proj / "src" / f"pkg_{i:05d}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "mod.py").write_text("pass\n", encoding="utf-8")

    _git(proj, "init", "-q")
    _git(proj, "add", ".gitignore", "src/tracked.py", "README.md")
    for i in range(extra_files):
        _git(proj, "add", f"src/pkg_{i:05d}/mod.py")
    _git(proj, "add", "deep/a/b/c/d/buried.txt")
    _git(proj, "commit", "-qm", "init")
    return proj


def _check_tiering(out: dict) -> list[str]:
    v: list[str] = []
    ws = {f["path"] for f in out["files"]}

    if not out["is_git"]:
        v.append("file_census: fixture is a git repo but is_git is False")

    for expected in ("src/tracked.py", "src/untracked.py", "README.md"):
        if expected not in ws:
            v.append(f"file_census: working set is missing {expected!r}")
    for excluded in ("secret.txt", "logs/run.log", ".venv/lib/dep.py"):
        if excluded in ws:
            v.append(f"file_census: {excluded!r} is mass but appears per-file in tier 2")

    states = {f["path"]: f["git"] for f in out["files"]}
    if states.get("src/tracked.py") != "tracked":
        v.append(f"file_census: tracked.py reported as {states.get('src/tracked.py')!r}")
    if states.get("src/untracked.py") != "untracked":
        v.append(f"file_census: untracked.py reported as {states.get('src/untracked.py')!r}")

    reasons = {m["path"]: m["reason"] for m in out["mass"]}
    if reasons.get(".venv") != "vendored":
        v.append(f"file_census: .venv reason is {reasons.get('.venv')!r}, expected 'vendored'")
    if reasons.get("logs") != "ignored":
        v.append(f"file_census: logs/ reason is {reasons.get('logs')!r}, expected 'ignored'")
    if ".git" not in reasons:
        v.append("file_census: .git is not reported as mass -- repo storage is invisible")
    if not any(m.get("partial") and m["reason"] == "ignored" for m in out["mass"]):
        v.append("file_census: the loose ignored file (secret.txt) has no mass entry")

    # Depth cap: the buried file's bytes must survive, folded into an ancestor.
    by_path = {d["path"]: d for d in out["directories"]}
    if "deep/a/b/c/d" in by_path:
        v.append("file_census: a depth-5 directory earned its own entry despite DEPTH_CAP=4")
    holder = by_path.get("deep/a/b/c")
    if not holder or not holder["depth_collapsed"] or holder["files"] < 1:
        v.append("file_census: depth-5 content did not fold into its capped ancestor "
                 "with depth_collapsed set")

    # The invariant that proves no file was counted twice or dropped.
    tier1 = sum(d["files"] for d in out["directories"])
    tier3 = sum(m["files"] for m in out["mass"])
    if tier1 + tier3 != out["summary"]["total_files"]:
        v.append(f"file_census: tier1({tier1}) + tier3({tier3}) != "
                 f"total_files({out['summary']['total_files']})")

    if not out["outliers"]:
        v.append("file_census: no outliers reported for a non-empty project")
    elif out["summary"]["largest"] != out["outliers"][0]["path"]:
        v.append("file_census: summary.largest disagrees with outliers[0]")
    return v


def _check_at_risk(out: dict) -> list[str]:
    """at_risk must name the untracked-not-ignored file, and nothing else."""
    v: list[str] = []
    named = {e["path"] for e in out["at_risk"] if not e.get("rollup")}
    if named != {"src/untracked.py"}:
        v.append(f"file_census: at_risk names {sorted(named)}, expected "
                 f"exactly ['src/untracked.py']")
    if out["at_risk_note"] is not None:
        v.append("file_census: at_risk_note set on a project that IS a git repo")
    # .venv is vendored but NOT gitignored in this fixture, so it is genuinely
    # unprotected -- and must appear as an exact rollup, never as silence.
    rollups = {e["path"]: e for e in out["at_risk"] if e.get("rollup")}
    if ".venv" not in rollups:
        v.append("file_census: an unprotected vendored tree (.venv) is absent from at_risk")
    elif rollups[".venv"]["files"] != 1:
        v.append(f"file_census: .venv at-risk rollup counts "
                 f"{rollups['.venv']['files']} files, expected 1")
    return v


def _check_cap(td: Path) -> list[str]:
    """The cap must be honest: flag set, and file_count the TRUE count."""
    v: list[str] = []
    original = file_census.FILE_CAP
    file_census.FILE_CAP = 5
    try:
        proj = make_census_project(td, extra_files=12)
        out = file_census.scan(proj)
    finally:
        file_census.FILE_CAP = original

    if len(out["files"]) > 5:
        v.append(f"file_census: cap of 5 not honoured -- {len(out['files'])} entries emitted")
    if not out["truncated"]:
        v.append("file_census: capped output did not set truncated=True")
    if out["file_count"] <= 5:
        v.append(f"file_census: file_count is {out['file_count']} -- a capped run must "
                 f"report the TRUE working-set count, not the emitted one")
    if out["file_count"] != out["summary"]["working_set"]["files"]:
        v.append("file_census: file_count disagrees with summary.working_set.files")

    # Beyond the cap, the BASENAMES still ride along. S4's filename cross-
    # reference matches on basename alone, so without these a capped project is
    # a silent blind spot in the strongest automatic link signal the system has.
    beyond = out.get("basenames_beyond_cap")
    if beyond is None:
        v.append("file_census: no basenames_beyond_cap key -- a capped project "
                 "is a silent blind spot for S4")
    else:
        emitted = {e["path"].rsplit("/", 1)[-1] for e in out["files"]}
        union = emitted | set(beyond)

        # The union must cover every working-set basename on disk. Compared
        # against the truth on disk, not against file_count -- file_count counts
        # FILES and the union counts NAMES, and the fixture deliberately repeats
        # basenames across directories.
        truth = {p.name for p in proj.rglob("*")
                 if p.is_file()
                 and ".venv" not in p.parts and "logs" not in p.parts
                 and ".git" not in p.parts and p.name != "secret.txt"}
        if not truth <= union:
            v.append(f"file_census: basename set is incomplete past the cap -- "
                     f"missing {sorted(truth - union)[:5]}")

        # And it must not pay for names it already had. This is the assertion an
        # all-unique-basename fixture cannot make: the beyond-cap set is only
        # cheap if it excludes what files[] already carries.
        if set(beyond) & emitted:
            v.append(f"file_census: basenames_beyond_cap repeats "
                     f"{len(set(beyond) & emitted)} basename(s) already present "
                     f"in files[] -- the set is redundantly large")
    # The at-risk set is exempt from the cap by design.
    if not any(e["path"] == "src/untracked.py" for e in out["at_risk"]):
        v.append("file_census: at_risk lost its entry to the cap -- it must never truncate")
    return v


def _check_non_git(td: Path) -> list[str]:
    v: list[str] = []
    plain = td / "PlainFolder"
    (plain / "sub").mkdir(parents=True)
    (plain / "sub" / "note.txt").write_text("hello\n", encoding="utf-8")
    out = file_census.scan(plain)
    if out["is_git"]:
        v.append("file_census: a non-repo folder reported is_git=True")
    if any(f["git"] is not None for f in out["files"]):
        v.append("file_census: git status must be null outside a repository")
    if not out["at_risk_note"]:
        v.append("file_census: a non-repo project must SAY nothing is in version "
                 "control, not report an empty at_risk list")
    return v


def _check_no_optional_locks() -> list[str]:
    """Task B, at the level the census depends on: the census's own git reads
    must carry --no-optional-locks, or the scan writes into the scanned folder."""
    from l5gntools import common
    v: list[str] = []
    argv = common.git_argv(Path("/x"), ("status", "--porcelain"))
    if common.NO_OPTIONAL_LOCKS not in argv:
        v.append("common.git_argv: 'status' did not get --no-optional-locks injected")
    elif argv.index(common.NO_OPTIONAL_LOCKS) > argv.index("status"):
        v.append("common.git_argv: --no-optional-locks placed after the subcommand "
                 "(it is a global option and git will reject it there)")
    explicit = common.git_argv(Path("/x"), (common.NO_OPTIONAL_LOCKS, "status"))
    if explicit.count(common.NO_OPTIONAL_LOCKS) != 1:
        v.append("common.git_argv: injection is not idempotent -- an explicit flag "
                 "was duplicated")
    if common.NO_OPTIONAL_LOCKS in common.git_argv(Path("/x"), ("commit", "-m", "x")):
        v.append("common.git_argv: injected --no-optional-locks into a non-read "
                 "subcommand (the allowlist leaked)")
    return v


def run() -> list[str]:
    v: list[str] = []
    v.extend(_check_no_optional_locks())
    with tempfile.TemporaryDirectory() as td:
        proj = make_census_project(Path(td))
        out = file_census.scan(proj)
        v.extend(_check_tiering(out))
        v.extend(_check_at_risk(out))
        v.extend(_check_non_git(Path(td)))
    with tempfile.TemporaryDirectory() as td:
        v.extend(_check_cap(Path(td)))
    return v
