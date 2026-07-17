#!/usr/bin/env python3
"""
scrape_gemini_share.py — Scrape Gemini "share" conversation pages into the
same normalized JSON shape used elsewhere in the Chronicler pipeline:

    {
      "source": "gemini",
      "share_url": "...",
      "title": "...",
      "model": "...",           # e.g. "3.1 Flash-Lite" - shown on the share page
      "created_date": "...",   # ISO 8601, parsed from the page's "Created with X <date>"
      "published_date": "...", # ISO 8601, parsed from "Published on <date>"
      "message_count": N,
      "messages": [{"role": "user"|"model", "content": "..."}]
    }

WHY THIS EXISTS (not the network/batchexecute route):
Gemini's share pages are a client-rendered SPA. The data loads via a
`batchexecute` RPC call that's tied to YOUR live session cookies and a
versioned backend build id (`bl=boq_assistant-bard-web-server_<date>...`).
That's not a stable public API - it can break whenever Google ships a new
frontend build, and it doesn't even work reliably unauthenticated. Instead,
this script drives a real (headless) browser to the public URL and reads the
already-rendered DOM, same as a human would see it. That's what stays stable.

REQUIREMENTS (run locally - NOT from Claude's sandbox, which can't reach
gemini.google.com):
    pip install playwright
    playwright install chromium

STATUS: real selectors, confirmed against an actual Gemini share-page DOM
sample (2026-07). Angular apps like this one renumber their internal
`_ngcontent-ng-cXXXXXXX` attributes on every build, so we deliberately do
NOT rely on those - only on the stable-looking custom element name
(`message-content`) and class/id patterns below. If Google ships a frontend
update, this is the piece most likely to need re-confirming the same way
we did this round (Inspect -> Copy outerHTML -> compare).
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

# ── Selectors confirmed against real DOM (see chat history for the sample) ─
# User turns: div.query-content with id="user-query-content-N" (N = turn index)
# Model turns: the <message-content> custom element (tag name, not a class -
#   Gemini doesn't appear to number these, so we rely on the tag itself)
SELECTOR_USER_TURN = ".query-content[id^='user-query-content-']"
SELECTOR_MODEL_TURN = "message-content"
SELECTOR_COMBINED = f"{SELECTOR_USER_TURN}, {SELECTOR_MODEL_TURN}"
# ─────────────────────────────────────────────────────────────────────────

# JS run in-page via page.evaluate: walks both selectors in one shot, in
# real DOM order, so there's no separate query-then-sort step to get wrong.
EXTRACT_MESSAGES_JS = """
() => {
  const nodes = Array.from(document.querySelectorAll(%r));
  return nodes.map(node => {
    if (node.matches('.query-content')) {
      const lines = Array.from(node.querySelectorAll('p.query-text-line'))
        .map(p => p.innerText.trim())
        .filter(t => t.length > 0 && t !== 'Show more' && t !== 'Show less');
      return { role: 'user', content: lines.join('\\n').trim() };
    } else {
      return { role: 'model', content: node.innerText.trim() };
    }
  });
}
""" % SELECTOR_COMBINED

# Custom Gem detection: [data-test-id="created-with-gem"] is present only on
# chats run through a creator's custom Gem (not on plain threads), so it's
# used as the boolean signal. .bot-name-text carries the actual Gem name and
# can appear more than once (once per response) - we just want the first.
EXTRACT_GEM_JS = """
() => {
  const isGem = !!document.querySelector('[data-test-id="created-with-gem"]');
  const nameEl = document.querySelector('.bot-name-text');
  return {
    is_custom_gem: isGem,
    gem_name: nameEl ? nameEl.innerText.trim() : null,
  };
}
"""

META_LINE_RE = re.compile(
    r"Created with (?P<model>.+?) (?P<created>\d{1,2} \w+ \d{4} at \d{1,2}:\d{2})"
    r"\s+Published on (?P<published>\d{1,2} \w+ \d{4} at \d{1,2}:\d{2})"
)


def parse_meta_line(text: str) -> dict:
    """Extract model + created/published dates from the 'Created with X ... Published on Y' line."""
    m = META_LINE_RE.search(text)
    if not m:
        return {"model": None, "created_date": None, "published_date": None}
    return {
        "model": m.group("model").strip(),
        "created_date": m.group("created").strip(),   # TODO: normalize to ISO 8601 UTC
        "published_date": m.group("published").strip(),
    }


def extract_title(page, full_text: str) -> str | None:
    """
    Primary: the browser tab title, which Angular apps typically set to the
    real conversation title (usually suffixed with the app name).
    Fallback: the line of body text immediately preceding the share URL,
    which is where the title renders visually on the page.
    """
    doc_title = page.title().strip()
    if doc_title:
        # Strip a trailing " - Gemini" / " | Gemini" style suffix if present
        cleaned = re.sub(r"\s*[-|]\s*Gemini\s*$", "", doc_title).strip()
        if cleaned:
            return cleaned

    lines = [l.strip() for l in full_text.splitlines() if l.strip()]
    for i, line in enumerate(lines):
        if line.startswith("https://gemini.google.com/share/"):
            # walk back past the literal "Gemini" brand line if present
            for j in range(i - 1, -1, -1):
                if lines[j].lower() != "gemini":
                    return lines[j]
    return None


def scrape_one(page, url: str, timeout_ms: int = 30000, debug_dir: Path | None = None) -> dict:
    page.goto(url, wait_until="networkidle")

    # Wait for real content rather than a fixed sleep - fails fast and
    # loudly if the page structure has changed instead of silently
    # producing an empty result. Heavier/longer conversations can take a
    # while to hydrate, hence this being configurable rather than fixed.
    try:
        page.wait_for_selector(SELECTOR_COMBINED, timeout=timeout_ms)
    except Exception:
        if debug_dir is not None:
            share_id = url.rstrip("/").split("/")[-1]
            debug_dir.mkdir(parents=True, exist_ok=True)
            try:
                page.screenshot(path=str(debug_dir / f"{share_id}.png"), full_page=True)
                (debug_dir / f"{share_id}.html").write_text(page.content(), encoding="utf-8")
            except Exception:
                pass  # debugging aid only - never let this mask the real error
        raise

    full_text = page.inner_text("body")
    meta = parse_meta_line(full_text)
    title = extract_title(page, full_text)
    gem = page.evaluate(EXTRACT_GEM_JS)

    messages = page.evaluate(EXTRACT_MESSAGES_JS)

    if not messages:
        raise RuntimeError(
            "Selectors matched zero nodes. Google likely changed the page "
            "structure - re-confirm SELECTOR_USER_TURN / SELECTOR_MODEL_TURN "
            "against a fresh DOM sample (Inspect -> Copy outerHTML) before "
            "trusting output from this script again."
        )

    return {
        "source": "gemini",
        "share_url": url,
        "title": title,
        "model": meta["model"],
        "created_date": meta["created_date"],
        "published_date": meta["published_date"],
        "is_custom_gem": gem["is_custom_gem"],
        "gem_name": gem["gem_name"],
        "message_count": len(messages),
        "messages": messages,
    }


def append_manifest(out_dir: Path, record: dict) -> None:
    """
    Append one line to a running manifest.jsonl in the output directory -
    a lightweight audit trail across many separate batch runs over time
    (which share URL, when scraped, title, message count). Doesn't replace
    the SQLite ingestion_log discussed for the main pipeline, but gives you
    something to eyeball immediately without opening the DB.
    """
    manifest_path = out_dir / "manifest.jsonl"
    with manifest_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "urls_file",
        help="Text file with one Gemini share URL per line (a 'batch' - "
             "any size, run the script again with a new/updated file for "
             "the next batch)",
    )
    ap.add_argument(
        "-o", "--output-dir", default="scraped_gemini",
        help="Directory to write one JSON file per conversation, plus a "
             "running manifest.jsonl",
    )
    ap.add_argument(
        "--force", action="store_true",
        help="Re-scrape and overwrite even if a JSON file for this share_id "
             "already exists (default: skip URLs already scraped in a "
             "previous batch, safe for overlapping batch files)",
    )
    ap.add_argument(
        "--timeout", type=int, default=30000,
        help="Milliseconds to wait for message content to render before "
             "giving up on a page (default: 30000). Increase for very long "
             "conversations that take longer to hydrate.",
    )
    args = ap.parse_args()

    urls = [
        line.strip()
        for line in Path(args.urls_file).read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    debug_dir = out_dir / "_debug"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for i, url in enumerate(urls, 1):
            share_id = url.rstrip("/").split("/")[-1]
            out_path = out_dir / f"{share_id}.json"

            if out_path.exists() and not args.force:
                print(f"[{i}/{len(urls)}] Skipping {url} (already scraped - use --force to redo)")
                continue

            print(f"[{i}/{len(urls)}] Scraping {url}")
            try:
                data = scrape_one(page, url, timeout_ms=args.timeout, debug_dir=debug_dir)
            except Exception as e:
                print(f"  !! Failed: {e}", file=sys.stderr)
                print(f"     Debug artifacts (if captured): {debug_dir / share_id}.png / .html", file=sys.stderr)
                append_manifest(out_dir, {
                    "share_url": url, "share_id": share_id,
                    "status": "failed", "error": str(e),
                    "scraped_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                })
                continue

            out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"  -> {out_path} ({data['message_count']} messages)")
            append_manifest(out_dir, {
                "share_url": url, "share_id": share_id,
                "status": "ok", "title": data["title"],
                "message_count": data["message_count"],
                "scraped_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            })

        browser.close()


if __name__ == "__main__":
    main()
