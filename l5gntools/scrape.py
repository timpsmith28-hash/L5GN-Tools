"""scrape -- drive the Gemini share-scraper as a pipeline-adjacent stage (Task E).

Design-thread decision: **the URL list travels to the knight; the knight scrapes.**
`chronicler/scrape_gemini_share.py` drives a *headless* browser against the
*public* share URL and explicitly rejects the session-cookie route -- so no
logged-in session is required and a headless Ubuntu box can scrape directly. That
keeps vault input originating only on the writer (single-writer doctrine) and
moves a tiny `urls.txt` instead of megabytes of JSON.

`playwright` + headless chromium are an OPTIONAL extra (``pip install -e .[scrape]``
then ``playwright install chromium`` / on Ubuntu ``playwright install-deps``).
Absent, the scrape is silently un-runnable -- exactly the Layer-C dormant-dep
trap -- so this reports status explicitly and skips loudly rather than no-opping.

The scraper writes into ``CHRONICLER_HOME/scraped_gemini`` -- the same intake
location the pipeline's reconcile stage already consumes -- so a scrape feeds
straight into ingest, and (Task B) relink then lifts the new threads out of
"unlinked". Paths are resolved from ``CHRONICLER_HOME``, never hardcoded.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path

from . import config

SCRAPE_SCRIPT = (Path(__file__).resolve().parent.parent
                 / "chronicler" / "scrape_gemini_share.py")


def playwright_available() -> bool:
    """True iff the optional ``playwright`` package is importable. (Chromium being
    *installed* is a further step this cannot see -- see KNIGHT_PLAYBOOK.)"""
    return importlib.util.find_spec("playwright") is not None


def _home(machine: dict | None) -> Path:
    home = os.environ.get("CHRONICLER_HOME") or (machine or {}).get("chronicler_home")
    if not home:
        raise FileNotFoundError(
            "cannot resolve CHRONICLER_HOME -- set it, or 'chronicler_home' for "
            "this machine in config/local.json.")
    return Path(home)


def resolve_urls_file(machine: dict | None = None) -> Path:
    """Where the batch URL list lives: machine ``urls_file`` override, else
    ``CHRONICLER_HOME/urls.txt``."""
    if machine is None:
        machine = config.machine()
    if machine.get("urls_file"):
        return Path(machine["urls_file"])
    return _home(machine) / "urls.txt"


def resolve_scraped_dir(machine: dict | None = None) -> Path:
    """The scrape output / pipeline intake dir: ``CHRONICLER_HOME/scraped_gemini``
    (matches reconcile_gemini.DEFAULT_SCRAPED_DIR)."""
    if machine is None:
        machine = config.machine()
    return _home(machine) / "scraped_gemini"


def scrape_argv(urls_file: Path | str, out_dir: Path | str, force: bool = False,
                timeout: int | None = None, python: str = "python3",
                script: Path | str | None = None) -> list[str]:
    """The scraper invocation. Preserves the script's own idempotency (skips
    already-scraped share-ids; ``--force`` to redo) and batch-native design."""
    argv = [python, str(script or SCRAPE_SCRIPT), str(urls_file), "-o", str(out_dir)]
    if force:
        argv.append("--force")
    if timeout is not None:
        argv += ["--timeout", str(timeout)]
    return argv
