"""deposit -- package this machine's estate snapshot and push it to the knight.

A *writer*, deliberately outside the read-only scanner contract (it is not a
scanner and is never registered). It stages the current ``estate.json`` plus the
latest history snapshot into a namespaced outbox with a sha256 manifest, then
pushes that namespace to the knight.

The load-bearing safety property is **namespace enforcement**: a machine may only
deposit into its own declared estate (``work`` vs ``personal``). Depositing an
``unknown`` estate is refused, so a misconfigured rig can never cross the streams
onto the knight -- the work/personal wall is structural, not a matter of trust.

Transport is a direct rig -> knight push (rsync by default); no cloud in the pipe.

**data/knowledge_curator/ never travels** (DECISIONS 0044 clauses 1-2). A
Curator report quotes source spans verbatim -- content, not summary -- and
0027 keeps content out of anything that leaves this machine. Today's
``files`` list is a fixed, explicit whitelist (estate.json + one history
snapshot), built by named ``shutil.copy2`` calls rather than a directory
walk, so nothing under ``data/knowledge_curator/`` can reach it as the code
stands -- but that safety is accidental unless it is also declared and
checked. EXCLUDED_FROM_DEPOSIT names the rule; the assertion in
build_bundle is the wall the next directory-walk runs into;
auditors/auditor_deposit_exclusion.py is the second, independent proof
(0044 clause 2: "one states the rule, the other proves it held").
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

from . import __version__, config
from .common import DATA_DIR, now_iso

#: DECISIONS 0044 clause 1: data/knowledge_curator/ is outside the deposit
#: contract, declared here rather than left to build_bundle's current
#: whitelist-by-omission. A path segment, checked against every relative
#: path this module is about to copy into the outbox.
EXCLUDED_FROM_DEPOSIT: tuple[str, ...] = ("knowledge_curator",)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _latest_snapshot(history_dir: Path) -> Path | None:
    if not history_dir.exists():
        return None
    snaps = sorted(history_dir.glob("estate-*.json"))
    return snaps[-1] if snaps else None


def build_bundle(estate: str | None, data_dir: Path = DATA_DIR,
                 force: bool = False) -> dict:
    """Stage a namespaced deposit bundle under ``data_dir/outbox/<estate>/``.

    Refuses an empty/``unknown`` estate unless ``force`` -- the namespace guard.
    """
    if not estate or estate == "unknown":
        if not force:
            raise ValueError(
                "refusing to deposit an 'unknown' estate namespace -- set 'estate' "
                "in config/machines.json (work|personal) so the bundle lands in the "
                "right place on the knight, or pass force=True to override.")
        estate = "unknown"

    estate_json = data_dir / "estate.json"
    if not estate_json.exists():
        raise FileNotFoundError(
            f"no {estate_json} -- run 'python run.py build' before depositing.")

    snapshot = _latest_snapshot(data_dir / "history")
    outbox = data_dir / "outbox" / estate
    if outbox.exists():
        shutil.rmtree(outbox)
    (outbox / "history").mkdir(parents=True, exist_ok=True)

    shutil.copy2(estate_json, outbox / "estate.json")
    files = ["estate.json"]
    if snapshot is not None:
        shutil.copy2(snapshot, outbox / "history" / snapshot.name)
        files.append(f"history/{snapshot.name}")

    # 0044 clause 2's first enforcement: state the rule where the bundle is
    # actually assembled, so the day someone widens `files` into a
    # directory walk (e.g. `shutil.copytree(data_dir, outbox)`), this is
    # the wall they hit, not a silent leak caught only by an auditor
    # running later. Checked against both the logical file list AND
    # whatever the copy calls above actually put on disk, so a future
    # change that writes into outbox() without going through `files`
    # cannot slip past this check either.
    for rel in files:
        if any(seg == excluded for seg in Path(rel).parts
               for excluded in EXCLUDED_FROM_DEPOSIT):
            raise RuntimeError(
                f"refusing to deposit {rel!r} -- it falls under an "
                f"EXCLUDED_FROM_DEPOSIT path {EXCLUDED_FROM_DEPOSIT!r} "
                "(DECISIONS 0044 clause 1).")
    for path in outbox.rglob("*"):
        if path.is_file():
            rel = path.relative_to(outbox)
            if any(seg == excluded for seg in rel.parts
                   for excluded in EXCLUDED_FROM_DEPOSIT):
                raise RuntimeError(
                    f"deposit outbox carries {rel!r} under an "
                    f"EXCLUDED_FROM_DEPOSIT path {EXCLUDED_FROM_DEPOSIT!r} "
                    "(DECISIONS 0044 clause 1) -- refusing to manifest it.")

    estate_meta = json.loads(estate_json.read_text(encoding="utf-8"))
    manifest = {
        "machine": config.hostname(),
        "estate": estate,
        "role": config.machine().get("role"),
        "toolkit_version": __version__,
        "estate_generated_at": estate_meta.get("generated_at"),
        "deposited_at": now_iso(),
        "files": {f: _sha256(outbox / f) for f in files},
    }
    (outbox / "deposit_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")

    return {"estate": estate, "outbox": outbox,
            "snapshot": snapshot.name if snapshot else None, "manifest": manifest}


def default_transport() -> str:
    """rsync everywhere except Windows, which ships OpenSSH's scp but not rsync."""
    return "scp" if os.name == "nt" else "rsync"


def push_command(outbox: Path, push_target: str, estate: str,
                 transport: str = "rsync") -> list[str]:
    """The command that mirrors this namespace to the knight over ssh.

    ``push_target`` may be an ssh alias (e.g. ``l5gn-castle:/vault/estates``), which
    both rsync and scp resolve via ``~/.ssh/config``. The estate namespace appears
    on BOTH ends, so a work bundle can only ever land under work/:
      * rsync -> ``<push_target>/<estate>/`` (with --delete, true mirror)
      * scp   -> copies the ``<estate>``-named dir into ``<push_target>/``
    """
    target = push_target.rstrip("/")
    if transport == "scp":
        return ["scp", "-r", str(outbox), target + "/"]
    return ["rsync", "-az", "--delete", str(outbox) + "/", target + "/" + estate + "/"]


def deposit(push: bool = False, force: bool = False) -> dict:
    m = config.machine()
    bundle = build_bundle(m.get("estate"), force=force)
    push_target = m.get("push_target")
    transport = m.get("push_transport") or default_transport()
    cmd = (push_command(bundle["outbox"], push_target, bundle["estate"], transport)
           if push_target else None)

    result = {
        "estate": bundle["estate"],
        "role": m.get("role"),
        "outbox": str(bundle["outbox"]),
        "snapshot": bundle["snapshot"],
        "push_target": push_target,
        "transport": transport,
        "push_command": " ".join(cmd) if cmd else None,
        "pushed": False,
    }
    if push:
        if not cmd:
            result["note"] = ("--push given but no push_target configured "
                              "(set it in config/local.json).")
        else:
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                result["pushed"] = proc.returncode == 0
                if proc.returncode != 0:
                    result["push_stderr"] = proc.stderr.strip()[-500:]
            except (OSError, subprocess.SubprocessError) as exc:
                result["push_error"] = str(exc)
    return result
