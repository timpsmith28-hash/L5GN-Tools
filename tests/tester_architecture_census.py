"""tester_architecture_census -- the quality bar Task 2 of
`COWORK_BRIEF_architecture_census.md` names explicitly: determinism, no
absolute paths, and parse failure reported rather than counted as zero.

Two of the three cases are driven against a small synthetic tree (so a
planted broken file never touches this repository); determinism is also
proven once against the real checkout, since that is the tree the committed
render actually describes and the brief calls that proof out as "worth
doing by hand once" -- worth having in the gate too.
"""
from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

from l5gntools.common import TOOLKIT_ROOT
from l5gntools.scanners import architecture_census as ac
from l5gntools import report

_DRIVE_LETTER = re.compile(r"^[A-Za-z]:[\\/]")
# HTTP route paths (section 3) are the one legitimate "/"-leading string in
# this payload -- `/api/...`, this app's whole URL convention (verified
# against every route `chronicler/review/app.py` declares) -- and are not
# filesystem paths at all, so the no-absolute-path check must not flag them.
_ROUTE_PATH = re.compile(r"^/api/")


def _is_leaked_path(s: str) -> bool:
    if _ROUTE_PATH.match(s):
        return False
    return bool(s.startswith("/") or _DRIVE_LETTER.match(s))


def _strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _strings(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _strings(v)


def _make_fixture_tree(root: Path) -> None:
    """A minimal tree carrying just enough shape for `census()` to have
    something to say in every section, plus one deliberately broken module."""
    (root / "l5gntools" / "scanners").mkdir(parents=True)
    (root / "chronicler" / "review").mkdir(parents=True)
    (root / "chronicler" / "pipeline").mkdir(parents=True)
    (root / "docs").mkdir(parents=True)

    (root / "l5gntools" / "__init__.py").write_text("", encoding="utf-8")
    (root / "l5gntools" / "scanners" / "__init__.py").write_text("", encoding="utf-8")

    # A module that opens a DB and writes to one recognisable table.
    (root / "l5gntools" / "ok_writer.py").write_text(
        "import sqlite3\n"
        "def go(path):\n"
        "    conn = sqlite3.connect(path)\n"
        "    conn.execute(\"INSERT INTO widgets (id) VALUES (?)\", (1,))\n"
        "    return conn\n",
        encoding="utf-8")

    # Deliberately unparseable -- the case Task 2 cares about most.
    (root / "chronicler" / "pipeline" / "broken.py").write_text(
        "def totally_broken(:\n    pass\n", encoding="utf-8")

    (root / "verify.py").write_text(
        "AUDITORS: list[str] = ['auditors.a', 'auditors.b']\n"
        "TESTERS: list[str] = ['tests.t']\n", encoding="utf-8")

    (root / "chronicler" / "review" / "app.py").write_text(
        "from fastapi import FastAPI\n"
        "app = FastAPI()\n\n"
        "def _need_vault():\n"
        "    pass\n\n"
        "@app.get('/api/ping')\n"
        "def ping():\n"
        "    _need_vault()\n"
        "    return {}\n",
        encoding="utf-8")

    (root / "chronicler" / "pipeline" / "schema.sql").write_text(
        "CREATE TABLE widgets (id INTEGER PRIMARY KEY);\n", encoding="utf-8")
    (root / "chronicler" / "pipeline" / "schema_frozen.sql").write_text(
        "CREATE TABLE widgets (id INTEGER PRIMARY KEY);\n"
        "CREATE TABLE ghosts (id INTEGER PRIMARY KEY);\n", encoding="utf-8")

    (root / "pyproject.toml").write_text(
        "[project.optional-dependencies]\n"
        "review = [\"fastapi>=0.110\"]\n",
        encoding="utf-8")


def _check_fixture_tree() -> list[str]:
    v: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _make_fixture_tree(root)

        data = ac.census(root)

        # -- parse failure reported, never counted as zero --------------
        unparsed = {u["module"]: u for u in data["unparsed"]}
        if "chronicler/pipeline/broken.py" not in unparsed:
            v.append("architecture_census: planted unparseable file did not "
                     "surface in `unparsed`")
        else:
            entry = unparsed["chronicler/pipeline/broken.py"]
            if entry.get("status") != "unparsed" or not entry.get("reason"):
                v.append(f"architecture_census: malformed unparsed entry: {entry!r}")
        write_targets = {m["module"]: m for m in data["sections"]["write_targets"]}
        if "chronicler/pipeline/broken.py" in write_targets:
            v.append("architecture_census: an unparseable module must never "
                     "also appear in write_targets as 'no writes'")

        # -- the parseable sibling still contributes real facts ----------
        ok = write_targets.get("l5gntools/ok_writer.py")
        if ok is None or ok["writes"] != ["widgets"]:
            v.append(f"architecture_census: ok_writer.py write set wrong: {ok!r}")

        # -- routes / gate / schema sanity on the fixture -----------------
        routes = data["sections"]["routes"]
        if not any(r["path"] == "/api/ping" and r["requires"] == "vault" for r in routes):
            v.append(f"architecture_census: fixture route not captured correctly: {routes!r}")
        gate = data["sections"]["gate"]
        if gate["auditor_count"] != 2 or gate["tester_count"] != 1:
            v.append(f"architecture_census: fixture gate counts wrong: {gate!r}")
        delta = data["sections"]["schema"]["delta"]
        if delta["only_in_schema_frozen"] != ["ghosts"]:
            v.append(f"architecture_census: fixture schema delta wrong: {delta!r}")

        # -- no absolute paths, anywhere -----------------------------------
        for s in _strings(data):
            if _is_leaked_path(s):
                v.append(f"architecture_census: absolute-looking path leaked "
                         f"into fixture payload: {s!r}")
                break

        # -- determinism on the fixture -------------------------------------
        again = ac.census(root)
        if json.dumps(data, sort_keys=True) != json.dumps(again, sort_keys=True):
            v.append("architecture_census: two scans of an unchanged fixture "
                     "tree produced different output")

        # -- the render is a pure function of the data, also deterministic --
        r1 = report.render_architecture_shape(data)
        r2 = report.render_architecture_shape(again)
        if r1 != r2:
            v.append("architecture_census: render_architecture_shape is not "
                     "deterministic for identical input data")
    return v


def _check_real_repo_determinism() -> list[str]:
    v: list[str] = []
    a = ac.census(TOOLKIT_ROOT)
    b = ac.census(TOOLKIT_ROOT)
    ja, jb = json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True)
    if ja != jb:
        v.append("architecture_census: two scans of this checkout produced "
                 "different output (tree assumed unchanged mid-gate-run)")
    for s in _strings(a):
        if _is_leaked_path(s):
            v.append(f"architecture_census: absolute-looking path leaked "
                     f"into the real payload: {s!r}")
            break
    if str(TOOLKIT_ROOT) in ja:
        v.append("architecture_census: the toolkit root's own absolute path "
                 "appears in the payload")
    return v


def run() -> list[str]:
    v: list[str] = []
    v.extend(_check_fixture_tree())
    v.extend(_check_real_repo_determinism())
    return v
