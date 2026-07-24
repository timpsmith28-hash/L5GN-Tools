"""census -- each machine reports its own domain.

A consumer never runs ``build``. `file_census` therefore leaves the knight
invisible: the scanner covers a *producer's* project roots, and the knight has no
project roots — it has a deployed toolkit and a vault. So the census is
role-aware, and asks the machine it is running on to describe the ground it
actually stands on.

**Producer domain** — the configured ``roots``, which is the same ground
`file_census` already covers. It re-uses the scanner directly; there is no second
implementation of the walk, the tiering or the at-risk rule.

**Consumer (knight) domain** — two roots, because one answers a question the
other cannot:

1. **Code root** — the deployed toolkit, including its venv as Tier 3 mass.
   Answers *"is this deploy the same as the repo"*.
2. **Vault root** — ``CHRONICLER_HOME``: `chronicler.db` and its `-wal`/`-shm`
   sidecars, `chat_threads/vault_staging/`, `estates/`, the backup directory and
   `serve-snapshot/`. Answers *"what is actually on the box, and how big"*.

Both are resolved from config and the environment, never hardcoded — hardcoding a
vault path re-creates the fork-path problem (DECISIONS 0007 consequence a).

**On the wall (DECISIONS 0010).** The knight's census necessarily reports
``estates/personal`` and ``estates/work`` side by side, with their sizes, in one
document. That is *not* a deposit and *not* a wall breach. Both bundles already
sit in that directory on that disk; this counts bytes in a folder the knight
owns, and nothing crosses from one estate into the other — no content is read,
compared or merged. A machine report describing its own filesystem is the one
place the two names legitimately appear together. **Do not "fix" this.** If a
future change starts reading *inside* those bundles and relating one to the
other, that is a different thing and the wall applies to it.

This module is a **writer**, so it is deliberately not a scanner and is never
registered in `registry.py`. It writes through :func:`common.write_json` — the
only sanctioned writer — which confines it to the machine's own ``data/``
directory. Note that ``deposit`` ships only ``estate.json`` and the latest
history snapshot, so nothing here inflates the deposit no matter how large the
local report gets.
"""
from __future__ import annotations

import os
from pathlib import Path

from . import config
from .common import DATA_DIR, TOOLKIT_ROOT, discover_projects, now_iso, write_json
from .scanners import file_census

#: Written under the machine's own data dir. Never deposited.
CENSUS_FILE = "census.json"

#: Sidecars SQLite keeps beside the DB in WAL mode. Absent is normal (a clean
#: shutdown removes them); present and large means uncheckpointed writes, which
#: is worth seeing on a box whose whole job is holding the vault.
_DB_SIDECARS = ("-wal", "-shm")


# --- path resolution (config-driven, never hardcoded) ------------------------
def resolve_code_root(machine: dict | None = None) -> Path:
    """The deployed toolkit directory.

    Order: config ``code_root``, then the toolkit this process is running from.
    The fallback is a resolution, not a hardcode — ``run.py census`` is executed
    *by* the deploy, so ``TOOLKIT_ROOT`` is that deploy by definition, and it is
    correct on a machine that has never been configured.
    """
    if machine is None:
        machine = config.machine()
    configured = machine.get("code_root")
    return Path(configured) if configured else TOOLKIT_ROOT


def resolve_vault_root(machine: dict | None = None) -> Path:
    """The Chronicler runtime root. ``CHRONICLER_HOME`` env, then this machine's
    ``chronicler_home``, then the parent of the resolved DB. Raises rather than
    guessing — a census of the wrong directory is worse than a loud failure."""
    if machine is None:
        machine = config.machine()
    home = os.environ.get("CHRONICLER_HOME") or machine.get("chronicler_home")
    if home:
        return Path(home)
    from . import backup
    try:
        return backup.resolve_db_path(machine).parent
    except FileNotFoundError:
        raise FileNotFoundError(
            "cannot resolve the vault root -- set CHRONICLER_HOME, or "
            "'chronicler_home' / 'vault' for this machine in config/local.json."
        ) from None


# --- measurement -------------------------------------------------------------
def measure(path: Path) -> dict:
    """``files``/``bytes`` for a file or a whole directory tree. Read-only.

    Everything is counted, including nested vendored and dot directories: this
    answers "how much disk is this using", not "what is the working set".
    """
    entry: dict = {"path": str(path), "exists": path.exists(),
                   "files": 0, "bytes": 0}
    if not entry["exists"]:
        return entry
    if path.is_file():
        try:
            entry["files"], entry["bytes"] = 1, path.stat().st_size
        except OSError:
            pass
        return entry
    for dirpath, _dirnames, filenames in os.walk(path):
        for name in filenames:
            try:
                entry["bytes"] += (Path(dirpath) / name).stat().st_size
                entry["files"] += 1
            except OSError:
                continue
    return entry


def _component(name: str, path: Path, note: str | None = None) -> dict:
    out = {"name": name}
    out.update(measure(path))
    if note:
        out["note"] = note
    return out


def vault_components(machine: dict | None = None) -> list[dict]:
    """The named things on the knight worth reporting individually.

    A single rollup of ``CHRONICLER_HOME`` would say the vault root is 4GB
    without saying which 4GB, and every operational question ("is the DB
    growing", "are the backups rotating", "did serve leave a snapshot behind")
    needs the breakdown rather than the total.
    """
    if machine is None:
        machine = config.machine()
    from . import backup, viewer

    root = resolve_vault_root(machine)
    try:
        db = backup.resolve_db_path(machine)
    except FileNotFoundError:
        db = root / "chronicler.db"

    out = [_component("chronicler.db", db, "the live vault")]
    for suffix in _DB_SIDECARS:
        sidecar = Path(str(db) + suffix)
        out.append(_component(db.name + suffix, sidecar,
                              "SQLite WAL sidecar; absent after a clean shutdown"))
    out.append(_component("chat_threads/vault_staging",
                          root / "chat_threads" / "vault_staging",
                          "ingest staging"))
    out.append(_component("backups", backup.resolve_backup_dir(machine),
                          "keep-last-N off-box snapshots"))
    out.append(_component("serve-snapshot", viewer.resolve_snapshot_dir(machine),
                          "transient read copy; a large one means serve left it behind"))

    estates_dir = Path(machine["estates_dir"]) if machine.get("estates_dir") \
        else root / "estates"
    estates = _component("estates", estates_dir, "deposited producer bundles")
    # Per-bundle sizes. See the module docstring: naming personal and work side
    # by side here is a machine report, not a deposit -- nothing crosses.
    bundles: list[dict] = []
    if estates_dir.is_dir():
        for child in sorted(estates_dir.iterdir(), key=lambda p: p.name.lower()):
            if child.is_dir():
                bundles.append(_component(child.name, child))
    estates["bundles"] = bundles
    out.append(estates)
    return out


# --- the two domains ---------------------------------------------------------
def producer_domain(machine: dict | None = None) -> dict:
    """Every project under the configured roots, via `file_census` unchanged."""
    if machine is None:
        machine = config.machine()
    projects = discover_projects()
    scanned = [file_census.scan(p) for p in projects]
    return {
        "domain": "producer",
        "roots": [{"path": str(e["path"]), "scope": e.get("scope")}
                  for e in config.estate_roots_tagged()],
        "projects": scanned,
        "totals": _totals(c["summary"] for c in scanned),
    }


def consumer_domain(machine: dict | None = None) -> dict:
    """The knight's two roots: the deploy, and the vault."""
    if machine is None:
        machine = config.machine()
    code_root = resolve_code_root(machine)
    code = file_census.scan(code_root) if code_root.exists() else None

    out: dict = {
        "domain": "consumer",
        "code_root": {"path": str(code_root), "exists": code_root.exists(),
                      "census": code},
    }
    try:
        vault_root = resolve_vault_root(machine)
    except FileNotFoundError as exc:
        out["vault_root"] = {"path": None, "exists": False, "error": str(exc)}
        return out

    out["vault_root"] = {
        "path": str(vault_root),
        "exists": vault_root.exists(),
        "components": vault_components(machine),
        "census": file_census.scan(vault_root) if vault_root.exists() else None,
    }
    return out


def _totals(summaries) -> dict:
    total = {"projects": 0, "files": 0, "bytes": 0, "at_risk_files": 0}
    for s in summaries:
        total["projects"] += 1
        total["files"] += s.get("total_files", 0)
        total["bytes"] += s.get("total_bytes", 0)
        total["at_risk_files"] += (s.get("at_risk") or {}).get("files", 0)
    return total


def run_census(machine: dict | None = None, target: Path | None = None) -> dict:
    """Build the census for whichever machine this is, and write it.

    ``target`` overrides role routing entirely and censuses one path — the escape
    hatch for "just tell me about this folder" without arguing with config.
    """
    if machine is None:
        machine = config.machine()
    role = machine.get("role", "producer")

    if target is not None:
        body = {"domain": "path", "target": str(target),
                "census": file_census.scan(Path(target))}
    elif role == "consumer":
        body = consumer_domain(machine)
    else:
        body = producer_domain(machine)

    report = {
        "generated_at": now_iso(),
        "host": machine.get("_hostname"),
        "role": role,
        "estate": machine.get("estate"),
        # Said out loud so a reader of the file knows what it is and is not.
        "_note": "A machine report of this box's own filesystem. Not a deposit; "
                 "`deposit` ships estate.json and the latest history snapshot only.",
    }
    report.update(body)
    report["written_to"] = str(write_json(CENSUS_FILE, report))
    return report


# --- human-readable summary --------------------------------------------------
def _mb(n: int | None) -> str:
    return "-" if n is None else f"{(n or 0) / 1_000_000:,.1f} MB"


def format_summary(report: dict) -> list[str]:
    """The lines `run.py census` prints. Separated from the printing so a tester
    can assert what the operator actually sees."""
    lines = [f"census: host={report.get('host')} role={report.get('role')} "
             f"estate={report.get('estate')}"]
    domain = report.get("domain")

    if domain == "path":
        s = report["census"]["summary"]
        lines.append(f"  {report['target']}")
        lines.append(f"    {s['total_files']:,} files  {_mb(s['total_bytes'])}  "
                     f"at risk: {s['at_risk']['files']:,}")
    elif domain == "producer":
        t = report["totals"]
        lines.append(f"  producer domain: {t['projects']} project(s), "
                     f"{t['files']:,} files, {_mb(t['bytes'])}")
        for c in report["projects"]:
            s = c["summary"]
            risk = s["at_risk"]["files"]
            lines.append(f"    {c['project']:<34} {s['total_files']:>7,} files  "
                         f"{_mb(s['total_bytes']):>10}"
                         + (f"   AT RISK: {risk:,}" if risk else ""))
        if t["at_risk_files"]:
            lines.append(f"  {t['at_risk_files']:,} file(s) on disk and not in git.")
    elif domain == "consumer":
        code = report["code_root"]
        lines.append(f"  code root : {code['path']}")
        if code.get("census"):
            s = code["census"]["summary"]
            lines.append(f"    {s['total_files']:,} files  {_mb(s['total_bytes'])}  "
                         f"working set {s['working_set']['files']:,}  "
                         f"at risk {s['at_risk']['files']:,}")
        else:
            lines.append("    MISSING -- the deploy is not where config says it is.")
        vault = report["vault_root"]
        lines.append(f"  vault root: {vault['path'] or '(unresolved)'}")
        if vault.get("error"):
            lines.append(f"    {vault['error']}")
        for comp in vault.get("components", []):
            mark = " " if comp["exists"] else "!"
            lines.append(f"   {mark}  {comp['name']:<28} "
                         f"{(str(comp['files']) + ' files') if comp['exists'] else 'absent':>12}  "
                         f"{_mb(comp['bytes']) if comp['exists'] else '':>10}")
            for bundle in comp.get("bundles", []):
                lines.append(f"        - {bundle['name']:<24} "
                             f"{bundle['files']:>6} files  {_mb(bundle['bytes']):>10}")
    lines.append(f"  written   : {report.get('written_to')}")
    return lines
