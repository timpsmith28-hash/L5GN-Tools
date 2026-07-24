"""tester_census -- role routing, config-driven paths, and the wall.

Hermetic. The knight is the machine this can least easily be tested *on*, which
is exactly why it needs a tester: a synthetic `CHRONICLER_HOME` is built in a
temp dir with a fake vault, WAL sidecars, backups, a serve-snapshot and two
estate bundles, and the consumer census is driven against it with an injected
machine dict. No real machine config is read and nothing outside the temp dir is
touched.

The assertions that matter:

* **Role routes the domain.** A producer must never produce a consumer report and
  vice versa; the command is useless if it describes the wrong machine.
* **Paths come from config.** The vault resolvers are driven with a machine dict
  pointing at a temp dir and must land there. If a hardcoded path ever creeps in,
  the resolved path stops matching the injected one and this fails.
* **The wall (DECISIONS 0010).** `estates/personal` and `estates/work` appear
  side by side by design, so this asserts the *sizes* are reported and that no
  bundle's content is read or compared. It is checked rather than trusted,
  because it is precisely the thing a future reader is most likely to "fix".
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from l5gntools import census
from l5gntools.common import DATA_DIR


def _make_vault(root: Path) -> Path:
    """A stand-in CHRONICLER_HOME with one of everything the knight holds."""
    home = root / "vault"
    (home / "chat_threads" / "vault_staging").mkdir(parents=True)
    (home / "backups").mkdir(parents=True)
    (home / "serve-snapshot").mkdir(parents=True)
    (home / "estates" / "personal" / "history").mkdir(parents=True)
    (home / "estates" / "work").mkdir(parents=True)

    (home / "chronicler.db").write_bytes(b"x" * 4096)
    (home / "chronicler.db-wal").write_bytes(b"w" * 512)
    # -shm deliberately absent: a clean shutdown removes it, and "absent" must
    # report as absent rather than as zero bytes.
    (home / "chat_threads" / "vault_staging" / "t.json").write_text("{}", encoding="utf-8")
    (home / "backups" / "chronicler-20260721T000000Z.db").write_bytes(b"b" * 2048)
    (home / "serve-snapshot" / "chronicler.db").write_bytes(b"s" * 1024)
    (home / "estates" / "personal" / "estate.json").write_text("{}" * 100, encoding="utf-8")
    (home / "estates" / "personal" / "history" / "estate-2026-07-21.json").write_text(
        "{}" * 50, encoding="utf-8")
    (home / "estates" / "work" / "estate.json").write_text("{}" * 10, encoding="utf-8")
    return home


def _knight(home: Path, code_root: Path) -> dict:
    return {"_hostname": "test-knight", "role": "consumer", "estate": "both",
            "vault": str(home / "chronicler.db"),
            "estates_dir": str(home / "estates"),
            "chronicler_home": str(home),
            "code_root": str(code_root)}


def _check_resolution(home: Path, code_root: Path) -> list[str]:
    v: list[str] = []
    m = _knight(home, code_root)
    if census.resolve_vault_root(m) != home:
        v.append(f"census: vault root resolved to {census.resolve_vault_root(m)}, "
                 f"not the configured {home} -- a path is hardcoded")
    if census.resolve_code_root(m) != code_root:
        v.append("census: code_root not taken from config")
    # No code_root configured -> the running toolkit, which IS the deploy.
    from l5gntools.common import TOOLKIT_ROOT
    bare = {k: val for k, val in m.items() if k != "code_root"}
    if census.resolve_code_root(bare) != TOOLKIT_ROOT:
        v.append("census: code_root fallback is not the running toolkit")
    # No config at all must fail loudly rather than guess a vault path.
    saved = os.environ.pop("CHRONICLER_HOME", None)
    try:
        census.resolve_vault_root({"_hostname": "nowhere"})
        v.append("census: resolved a vault root from empty config instead of raising")
    except FileNotFoundError:
        pass
    finally:
        if saved is not None:
            os.environ["CHRONICLER_HOME"] = saved
    return v


def _check_components(home: Path, code_root: Path) -> list[str]:
    v: list[str] = []
    comps = {c["name"]: c for c in census.vault_components(_knight(home, code_root))}
    for name in ("chronicler.db", "chronicler.db-wal", "chronicler.db-shm",
                 "chat_threads/vault_staging", "backups", "serve-snapshot", "estates"):
        if name not in comps:
            v.append(f"census: vault component {name!r} not reported")
    if not comps.get("chronicler.db", {}).get("exists"):
        v.append("census: the live vault DB was not detected")
    if comps.get("chronicler.db", {}).get("bytes") != 4096:
        v.append(f"census: DB size is {comps.get('chronicler.db', {}).get('bytes')}, "
                 f"expected 4096 -- this is the number UAT check C compares to ls -la")
    if not comps.get("chronicler.db-wal", {}).get("exists"):
        v.append("census: the -wal sidecar was not detected")
    if comps.get("chronicler.db-shm", {}).get("exists"):
        v.append("census: reported an absent -shm sidecar as present")
    if comps.get("serve-snapshot", {}).get("files") != 1:
        v.append("census: serve-snapshot contents not counted")
    return v


def _check_wall(home: Path, code_root: Path) -> list[str]:
    """The two estates appear together, with sizes, and nothing more."""
    v: list[str] = []
    comps = {c["name"]: c for c in census.vault_components(_knight(home, code_root))}
    bundles = {b["name"]: b for b in comps.get("estates", {}).get("bundles", [])}
    if set(bundles) != {"personal", "work"}:
        v.append(f"census: estate bundles reported as {sorted(bundles)}, "
                 f"expected both 'personal' and 'work' -- a machine report covers "
                 f"the whole directory it owns")
    for name, b in bundles.items():
        if not b.get("bytes"):
            v.append(f"census: bundle {name!r} reported without a size")
        # Sizes and counts only. Any key implying the bundles were opened,
        # compared or merged is a wall breach, not a feature.
        leaked = set(b) - {"name", "path", "exists", "files", "bytes", "note"}
        if leaked:
            v.append(f"census: bundle {name!r} carries {sorted(leaked)} -- a machine "
                     f"report counts bytes; it must not read across the wall")
    return v


def _check_routing(home: Path, code_root: Path) -> list[str]:
    v: list[str] = []
    consumer = census.consumer_domain(_knight(home, code_root))
    if consumer["domain"] != "consumer":
        v.append("census: consumer machine did not produce a consumer domain")
    if not consumer["code_root"]["exists"] or not consumer["code_root"]["census"]:
        v.append("census: consumer report has no code-root census")
    if consumer["vault_root"]["path"] != str(home):
        v.append("census: consumer report points at the wrong vault root")
    if not consumer["vault_root"].get("census"):
        v.append("census: consumer report has no vault-root census")

    # A missing vault must degrade to a stated error, never a crash and never a
    # silent empty report that reads as 'the box is empty'.
    broken = {"_hostname": "h", "role": "consumer", "code_root": str(code_root),
              "chronicler_home": str(home / "does-not-exist")}
    out = census.consumer_domain(broken)
    if out["vault_root"]["exists"] or out["vault_root"].get("census"):
        v.append("census: a missing vault root was not reported as missing")

    # The path escape hatch must bypass role routing entirely.
    report = census.run_census(machine=_knight(home, code_root), target=code_root)
    if report.get("domain") != "path":
        v.append("census: --target did not override role routing")
    if not report.get("written_to", "").startswith(str(DATA_DIR)):
        v.append(f"census: wrote to {report.get('written_to')} -- write_json is the "
                 f"only sanctioned writer and it must stay under {DATA_DIR}")
    lines = census.format_summary(report)
    if not lines or "role=consumer" not in lines[0]:
        v.append("census: printed summary does not name the machine's role")
    return v


def _check_producer_summary() -> list[str]:
    """format_summary must survive a producer report with no projects at all."""
    v: list[str] = []
    empty = {"generated_at": "now", "host": "h", "role": "producer", "estate": "x",
             "domain": "producer", "roots": [], "projects": [],
             "totals": {"projects": 0, "files": 0, "bytes": 0, "at_risk_files": 0},
             "written_to": "/tmp/x"}
    try:
        lines = census.format_summary(empty)
    except Exception as exc:  # noqa: BLE001 -- a crash printing is still a crash
        return [f"census: format_summary raised on an empty producer: {exc}"]
    if not any("producer domain" in line for line in lines):
        v.append("census: producer summary does not name the domain")
    return v


def run() -> list[str]:
    v: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        home = _make_vault(root)
        code_root = root / "L5GN-Tools"
        (code_root / "l5gntools").mkdir(parents=True)
        (code_root / "run.py").write_text("print(1)\n", encoding="utf-8")
        (code_root / "l5gntools" / "common.py").write_text("x=1\n", encoding="utf-8")

        v.extend(_check_resolution(home, code_root))
        v.extend(_check_components(home, code_root))
        v.extend(_check_wall(home, code_root))
        v.extend(_check_routing(home, code_root))
    v.extend(_check_producer_summary())
    return v
