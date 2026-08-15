"""witness_uat_sidebar: the sidebar's own DOM half (COWORK_BRIEF_ui_witness.md
Task 4). Ported from the checks the build thread named as browser-only, and
no others:

  * refusal flags the correct `.uat-item` and shows a message (B3, B4)
  * the "already recorded" badge renders on the right items (B6)
  * the resume banner exists and populates correctly (B7)
  * pasted multi-line text survives the textarea round-trip into the
    emitted file (B1's UI half -- the backend half is already
    tester-covered by `tests.tester_uat_sidebar`)

**Explicitly not B2** (the judgement item, "does it surface the right
document") -- a witness that starts grading prose has become the
sidebar-that-grades-itself failure the sidebar brief rules out.

Asserts structure and state, never semantics: "the refusal flagged item W2
and rendered a message" is checked here; "the message was helpful" is not.

Fixture-only (Task 3): drives `tests/witness/fixtures/uat_sidebar/`, never
the real `docs/` tree -- see `harness.fixture_server`.
"""
from __future__ import annotations

from pathlib import Path

from .harness import commit_stamp, fixture_server
from .schema import Observation, WitnessRun, now_iso

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "uat_sidebar"
SHEET_STEM = "wsample"
#: The name this run files under in `data/witness/<SHEET_NAME>.json` -- the
#: sheet id the sidebar's real `uat_sidebar` results log cites, not the
#: fixture's own stem.
SHEET_NAME = "uat_sidebar"


def run() -> WitnessRun:
    from playwright.sync_api import sync_playwright

    observations: list[Observation] = []

    with fixture_server(FIXTURE_ROOT) as base_url:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page()
                page.goto(f"{base_url}/")
                page.click('.tab[data-pane="uat"]')
                page.fill("#uat-stem", SHEET_STEM)
                page.click('#uat-pick button.primary')  # "Open sheet"
                page.wait_for_selector(".uat-item")

                # --- W1: multi-line paste survives into the DOM's own state -
                pasted = "line one\nline two\nline three"
                w1 = page.locator('.uat-item[data-id="W1"]')
                w1.locator("select").select_option("walked")
                w1.locator("textarea").fill(pasted)
                w1.locator("textarea").blur()
                round_tripped = w1.locator("textarea").input_value() == pasted
                observations.append(Observation(
                    id="B1", outcome="matched" if round_tripped else "diverged",
                    detail=f"textarea round-trip of {len(pasted.splitlines())} "
                           f"pasted lines survived verbatim={round_tripped}"))

                # --- W2/W3: deferred/blocked, no reason -> refused + flagged -
                for iid, verdict in (("W2", "deferred"), ("W3", "blocked")):
                    it = page.locator(f'.uat-item[data-id="{iid}"]')
                    it.locator("select").select_option(verdict)
                page.click("#uat-bar button.primary")  # Emit results log
                page.wait_for_timeout(400)
                for iid, brief_id in (("W2", "B3"), ("W3", "B4")):
                    it = page.locator(f'.uat-item[data-id="{iid}"]')
                    cls = it.get_attribute("class") or ""
                    flagged = "err" in cls.split()
                    verr = it.locator(".verr")
                    visible = verr.is_visible() if flagged else False
                    message = verr.inner_text().strip() if visible else ""
                    matched = flagged and visible and bool(message)
                    observations.append(Observation(
                        id=brief_id,
                        outcome="matched" if matched else "diverged",
                        detail=f"item={iid} flagged={flagged} "
                               f"message_visible={visible} message={message!r}"))

            finally:
                browser.close()

    # --- W4: already-recorded badge + resume, on a FRESH page load ----------
    # A second fixture_server block: the emit above ran against the same
    # fixture tree and did not touch W4 (it only submitted W1/W2/W3), so
    # W4's prior results-log entry is untouched and this re-checks the badge
    # and resume behaviour in isolation from the refusal flow above.
    with fixture_server(FIXTURE_ROOT) as base_url:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page()
                page.goto(f"{base_url}/")
                page.click('.tab[data-pane="uat"]')
                page.fill("#uat-stem", SHEET_STEM)
                page.click('#uat-pick button.primary')
                page.wait_for_selector(".uat-item")

                badge = page.locator(
                    '.uat-item[data-id="W4"] .badge:has-text("already recorded")')
                has_badge = badge.count() > 0
                observations.append(Observation(
                    id="B6", outcome="matched" if has_badge else "diverged",
                    detail=f"'already recorded' badge present on W4={has_badge}"))

                resume_btn = page.locator("button:has-text('Resume')")
                has_resume = resume_btn.count() > 0
                resumed_ok = False
                if has_resume:
                    resume_btn.first.click()
                    page.wait_for_timeout(200)
                    val = page.locator(
                        '.uat-item[data-id="W4"] select').input_value()
                    resumed_ok = val == "walked"
                observations.append(Observation(
                    id="B7",
                    outcome="matched" if has_resume and resumed_ok else "diverged",
                    detail=f"resume_banner_present={has_resume} "
                           f"resumed_verdict_populated={resumed_ok}"))
            finally:
                browser.close()

    stamp = commit_stamp()
    repo_root = Path(__file__).resolve().parents[2]
    return WitnessRun(
        sheet=SHEET_NAME, ran_at=now_iso(), host=stamp["host"],
        commit=stamp["commit"], dirty=stamp["dirty"],
        fixture=str(FIXTURE_ROOT.relative_to(repo_root)).replace("\\", "/"),
        items=observations)


if __name__ == "__main__":
    result = run()
    for obs in result.items:
        print(f"[{obs.outcome:>8}] {obs.id}: {obs.detail}")
