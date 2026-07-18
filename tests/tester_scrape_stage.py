"""tester_scrape_stage: the Gemini scrape wiring (Task E).

Hermetic: exercises the pure scrape helpers -- dep detection, config-driven path
resolution, and the argv the `scrape` command builds. playwright is NOT required
to run this test (only the dep-absent signal and the command shape are checked).
"""
from __future__ import annotations

import os
from pathlib import Path

from l5gntools import scrape


def run() -> list[str]:
    v: list[str] = []

    # --- dep detection returns a bool (skip-cleanly signal) ---
    if not isinstance(scrape.playwright_available(), bool):
        v.append("scrape: playwright_available() must return a bool")

    # --- the scraper script actually exists where we point at it ---
    if not scrape.SCRAPE_SCRIPT.exists():
        v.append(f"scrape: SCRAPE_SCRIPT missing at {scrape.SCRAPE_SCRIPT}")
    if scrape.SCRAPE_SCRIPT.name != "scrape_gemini_share.py":
        v.append("scrape: SCRAPE_SCRIPT is not scrape_gemini_share.py")

    # --- argv shape: script, urls_file, -o out_dir; flags only when asked ---
    argv = scrape.scrape_argv("/data/urls.txt", "/data/scraped_gemini",
                              python="python3", script="/x/scrape.py")
    if argv[:3] != ["python3", "/x/scrape.py", "/data/urls.txt"]:
        v.append(f"scrape: argv head wrong: {argv}")
    if "-o" not in argv or argv[argv.index("-o") + 1] != "/data/scraped_gemini":
        v.append("scrape: output dir not passed via -o")
    if "--force" in argv or "--timeout" in argv:
        v.append("scrape: flags leaked into a plain invocation")
    argv2 = scrape.scrape_argv("u.txt", "o", force=True, timeout=60000, script="s")
    if "--force" not in argv2 or argv2[argv2.index("--timeout") + 1] != "60000":
        v.append(f"scrape: --force/--timeout not honoured: {argv2}")

    # --- config-driven paths (never hardcoded); scraped dir == pipeline intake ---
    saved = {k: os.environ.pop(k, None) for k in ("CHRONICLER_HOME",)}
    try:
        os.environ["CHRONICLER_HOME"] = "/home/l5gn/vault"
        if scrape.resolve_urls_file({}) != Path("/home/l5gn/vault/urls.txt"):
            v.append("scrape: resolve_urls_file did not derive from CHRONICLER_HOME")
        if scrape.resolve_scraped_dir({}) != Path("/home/l5gn/vault/scraped_gemini"):
            v.append("scrape: resolve_scraped_dir not CHRONICLER_HOME/scraped_gemini")
        # machine urls_file override wins
        if scrape.resolve_urls_file({"urls_file": "/tmp/u.txt"}) != Path("/tmp/u.txt"):
            v.append("scrape: machine 'urls_file' override not honoured")
        del os.environ["CHRONICLER_HOME"]
        # HOME unresolved -> loud FileNotFoundError, not a silent default
        try:
            scrape.resolve_scraped_dir({})
            v.append("scrape: unresolved CHRONICLER_HOME should raise, not default")
        except FileNotFoundError:
            pass
    finally:
        for k, val in saved.items():
            if val is not None:
                os.environ[k] = val
    return v
