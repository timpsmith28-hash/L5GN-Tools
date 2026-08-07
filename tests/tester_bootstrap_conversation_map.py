"""bootstrap_conversation_map (K0): matches a curated sheet's captured
opening prompts against the real Cowork transcript store to fill in each
row's session_id, as a CANDIDATE map for human ratification.

Hermetic: builds a synthetic Cowork store in a temp dir and a synthetic
sheet, drives `match()` end to end, and checks all six report counts plus
the specific ambiguity/pairing/floor rules named in
COWORK_BRIEF_knowledge_curator.md K0. Touches no real store, writes only
inside the temp dir.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

_PIPE = Path(__file__).resolve().parent.parent / "chronicler" / "pipeline"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _msg(role: str, text: str, ts: str, uuid: str) -> str:
    import json
    return json.dumps({
        "type": role, "message": {"role": role, "content": text},
        "uuid": uuid, "timestamp": ts, "entrypoint": "claude-desktop",
    })


def _build_store(root: Path) -> None:
    # Row A: unique, long opener -- clean pass-1 match.
    a = root / "ws" / "PricingModel" / "local_aaa1"
    nested_a = a / ".claude" / "projects" / "C--out-a"
    _write(nested_a / "s-a.jsonl", "\n".join([
        _msg("user", "Let's design the new tiered pricing model for the churn "
             "reduction initiative this quarter, starting with the base tier.",
             "2026-07-10T10:00:00Z", "ua1"),
        "",
    ]))

    # Row B: short opener (<32 chars, but exact-length pass-1 match still works).
    b = root / "ws" / "Setup" / "local_bbb1"
    nested_b = b / ".claude" / "projects" / "C--out-b"
    _write(nested_b / "s-b.jsonl", "\n".join([
        _msg("user", "/setup-cowork please", "2026-07-11T10:00:00Z", "ub1"),
        "",
    ]))

    # Row C: too-short sheet entry (<60 chars) with NO exact disk match at
    # all for pass 1 (opener differs) -- must never reach pass 2, must
    # report unmatched with the floor named.
    c = root / "ws" / "Other" / "local_ccc1"
    nested_c = c / ".claude" / "projects" / "C--out-c"
    _write(nested_c / "s-c.jsonl", "\n".join([
        _msg("user", "totally unrelated opener text here for project c",
             "2026-07-12T10:00:00Z", "uc1"),
        "",
    ]))

    # Rows D1/D2: broken-history duplicate openers, SAME on-disk project
    # (WizForgeAnalytics), two separate conversations, must pair by date.
    d1 = root / "ws" / "WizForgeAnalytics" / "local_ddd1"
    nested_d1 = d1 / ".claude" / "projects" / "C--out-d1"
    _write(nested_d1 / "s-d1.jsonl", "\n".join([
        _msg("user", "Configure the Salesforce MCP server integration for "
             "WizForge Analytics with the standard auth flow please thanks",
             "2026-07-07T10:00:00Z", "ud1"),
        "",
    ]))
    d2 = root / "ws" / "WizForgeAnalytics" / "local_ddd2"
    nested_d2 = d2 / ".claude" / "projects" / "C--out-d2"
    _write(nested_d2 / "s-d2.jsonl", "\n".join([
        _msg("user", "Configure the Salesforce MCP server integration for "
             "WizForge Analytics with the standard auth flow please thanks",
             "2026-07-08T10:00:00Z", "ud2"),
        "",
    ]))

    # Rows E1/E2: identical openers, DIFFERENT on-disk projects -- must be
    # refused, both left unmatched.
    e1 = root / "ws" / "ProjectOne" / "local_eee1"
    nested_e1 = e1 / ".claude" / "projects" / "C--out-e1"
    _write(nested_e1 / "s-e1.jsonl", "\n".join([
        _msg("user", "Generic kickoff message used to open several unrelated threads",
             "2026-07-09T10:00:00Z", "ue1"),
        "",
    ]))
    e2 = root / "ws" / "ProjectTwo" / "local_eee2"
    nested_e2 = e2 / ".claude" / "projects" / "C--out-e2"
    _write(nested_e2 / "s-e2.jsonl", "\n".join([
        _msg("user", "Generic kickoff message used to open several unrelated threads",
             "2026-07-09T11:00:00Z", "ue2"),
        "",
    ]))

    # An unmapped folder: on disk, matches no sheet row at all.
    f = root / "ws" / "Orphan" / "local_fff1"
    nested_f = f / ".claude" / "projects" / "C--out-f"
    _write(nested_f / "s-f.jsonl", "\n".join([
        _msg("user", "Nobody put this one on the sheet at all, ever, so it must "
             "surface as present-on-disk-not-in-map",
             "2026-07-13T10:00:00Z", "uf1"),
        "",
    ]))

    # Row G: opener text that reaches pass 2 (>=60 chars, no pass-1 exact
    # match because it's buried mid-conversation, not the opener).
    g = root / "ws" / "BrokenHistory" / "local_ggg1"
    nested_g = g / ".claude" / "projects" / "C--out-g"
    _write(nested_g / "s-g.jsonl", "\n".join([
        _msg("user", "some other opener entirely, history is broken here",
             "2026-07-14T09:00:00Z", "ug0"),
        _msg("user", "actually the real captured prompt shows up later in this "
             "thread because the history above it got lost during a resume",
             "2026-07-14T09:05:00Z", "ug1"),
        "",
    ]))


def _write_sheet(path: Path) -> None:
    rows = [
        ("PricingModel", "mcf-pricing-model", "Pricing - Design",
         "", "Let's design the new tiered pricing model for the churn "
             "reduction initiative this quarter, starting with the base tier."),
        ("Setup", "mcf-setup", "Setup thread", "", "/setup-cowork please"),
        ("Other", "mcf-other", "Other thread", "", "short opener under sixty chars"),
        ("WizForgeAnalytics", "mcf-wizforge", "Salesforce MCP server setup",
         "2026-07-07", "Configure the Salesforce MCP server integration for "
                        "WizForge Analytics with the standard auth flow please thanks"),
        ("WizForgeAnalytics", "mcf-wizforge", "Salesforce sheets audit",
         "2026-07-08", "Configure the Salesforce MCP server integration for "
                        "WizForge Analytics with the standard auth flow please thanks"),
        ("ProjectOne", "mcf-one", "Kickoff one", "",
         "Generic kickoff message used to open several unrelated threads"),
        ("ProjectTwo", "mcf-two", "Kickoff two", "",
         "Generic kickoff message used to open several unrelated threads"),
        ("BrokenHistory", "mcf-broken", "Broken history thread", "",
         "actually the real captured prompt shows up later in this thread "
         "because the history above it got lost during a resume"),
    ]
    lines = ["local_folder\tproject_id\tconversation_name\tdate\t1st User Message"]
    for r in rows:
        lines.append("\t".join(r))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run() -> list[str]:
    v: list[str] = []
    if str(_PIPE) not in sys.path:
        sys.path.insert(0, str(_PIPE))
    import bootstrap_conversation_map as k0
    import local_transcripts as lt

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        store_root = td / "cowork"
        sheet_path = td / "sheet.tsv"
        _build_store(store_root)
        _write_sheet(sheet_path)

        real_machine = lt.machine
        try:
            lt.machine = lambda host=None: {
                "_hostname": "test-host", "cowork_transcripts_home": str(store_root),
            }
            conversations, errors = k0.discover_conversations()
        finally:
            lt.machine = real_machine

        if errors:
            v.append(f"unexpected access errors discovering fixture store: {errors}")
        if len(conversations) != 9:
            v.append(f"expected 9 conversations in fixture store, got {len(conversations)}: "
                      f"{[c.conversation_id for c in conversations]}")

        rows = k0.load_sheet(sheet_path)
        if len(rows) != 8:
            v.append(f"sheet loader wrong row count: {len(rows)}")

        results = k0.match(rows, conversations)
        by_name = {r.row.conversation_name: r for r in results}

        # --- Row A: clean pass-1 match --------------------------------------
        ra = by_name.get("Pricing - Design")
        if ra is None or ra.status != "matched" or ra.match_pass != "pass1" or ra.session_id != "local_aaa1":
            v.append(f"row A (clean pass-1) resolved wrong: {ra}")

        # --- Row B: short-but-exact opener still matches in pass 1 ----------
        rb = by_name.get("Setup thread")
        if rb is None or rb.status != "matched" or rb.match_pass != "pass1" or rb.session_id != "local_bbb1":
            v.append(f"row B (short exact opener) should still match in pass 1: {rb}")

        # --- Row C: below the pass-2 floor, no pass-1 candidate --------------
        rc = by_name.get("Other thread")
        if rc is None or rc.status != "unmatched" or "60" not in rc.note:
            v.append(f"row C (<60 chars, no pass-1 hit) should be unmatched with the "
                      f"floor named in the note: {rc}")

        # --- Rows D1/D2: same-project duplicate openers, paired by date -----
        rd1 = by_name.get("Salesforce MCP server setup")
        rd2 = by_name.get("Salesforce sheets audit")
        if rd1 is None or rd2 is None:
            v.append("WizForge duplicate-opener rows missing from results")
        else:
            if rd1.status != "ambiguous-same-project" or rd2.status != "ambiguous-same-project":
                v.append(f"WizForge duplicate rows should be ambiguous-same-project "
                          f"(accepted+paired): rd1={rd1.status} rd2={rd2.status}")
            if rd1.session_id != "local_ddd1" or rd2.session_id != "local_ddd2":
                v.append(f"WizForge rows not paired by date correctly: "
                          f"rd1->{rd1.session_id} (want local_ddd1, Jul 7), "
                          f"rd2->{rd2.session_id} (want local_ddd2, Jul 8)")

        # --- Rows E1/E2: identical opener, different projects -> refused ----
        re1 = by_name.get("Kickoff one")
        re2 = by_name.get("Kickoff two")
        if re1 is None or re2 is None:
            v.append("cross-project collision rows missing from results")
        else:
            if re1.status != "ambiguous-different-project" or re2.status != "ambiguous-different-project":
                v.append(f"cross-project collision should be refused as "
                          f"ambiguous-different-project: re1={re1.status} re2={re2.status}")
            if re1.session_id or re2.session_id:
                v.append("a refused ambiguous-different-project row must not carry a session_id")

        # --- Row G: pass-2 substring match (broken history) ------------------
        rg = by_name.get("Broken history thread")
        if rg is None or rg.status != "matched" or rg.match_pass != "pass2" or rg.session_id != "local_ggg1":
            v.append(f"row G (broken history, pass-2 substring) resolved wrong: {rg}")

        # --- Six counts, all present, all correct -----------------------------
        all_conv_ids = [c.conversation_id for c in conversations]
        counts = k0.six_counts(results, all_conv_ids)
        expected_keys = {
            "matched_by_pass1", "matched_by_pass2", "ambiguous_same_project",
            "ambiguous_different_project", "unmatched_sheet_rows",
            "unmapped_local_folders_on_disk",
        }
        if set(counts) != expected_keys:
            v.append(f"six_counts missing/extra keys: {sorted(counts)}")
        if counts.get("matched_by_pass1") != 2:  # A, B
            v.append(f"matched_by_pass1 wrong: {counts.get('matched_by_pass1')}")
        if counts.get("matched_by_pass2") != 1:  # G
            v.append(f"matched_by_pass2 wrong: {counts.get('matched_by_pass2')}")
        if counts.get("ambiguous_same_project") != 2:  # D1, D2
            v.append(f"ambiguous_same_project wrong: {counts.get('ambiguous_same_project')}")
        if counts.get("ambiguous_different_project") != 2:  # E1, E2
            v.append(f"ambiguous_different_project wrong: {counts.get('ambiguous_different_project')}")
        if counts.get("unmatched_sheet_rows") != 1:  # C
            v.append(f"unmatched_sheet_rows wrong: {counts.get('unmatched_sheet_rows')}")
        # unclaimed folders: C's target (no sheet row matched it), E1/E2
        # (refused as ambiguous-different-project, so never get a
        # session_id), and F (never on the sheet at all) = 4.
        if counts.get("unmapped_local_folders_on_disk") != 4:
            v.append(f"unmapped_local_folders_on_disk wrong: "
                      f"{counts.get('unmapped_local_folders_on_disk')}")

        # --- output write, read-only on the source store ----------------------
        out_path = td / "candidate.tsv"
        before = (store_root / "ws" / "PricingModel" / "local_aaa1" / ".claude" /
                   "projects" / "C--out-a" / "s-a.jsonl").stat().st_mtime
        k0.write_candidate_map(results, out_path)
        after = (store_root / "ws" / "PricingModel" / "local_aaa1" / ".claude" /
                  "projects" / "C--out-a" / "s-a.jsonl").stat().st_mtime
        if before != after:
            v.append("write_candidate_map touched a source transcript's mtime")
        if not out_path.exists():
            v.append("candidate map file was not written")
        else:
            header = out_path.read_text(encoding="utf-8").splitlines()[0].split("\t")
            if header[0] != "session_id":
                v.append(f"candidate map header wrong: {header}")

        # --- normalisation: curly quote / em dash / doubled space still match -
        norm_a = k0.normalize("Let’s design — the new tiered   pricing model")
        norm_b = k0.normalize("Let's design - the new tiered pricing model")
        if norm_a != norm_b:
            v.append(f"normalize() did not fold curly quote/dash/whitespace: "
                      f"{norm_a!r} != {norm_b!r}")

    return v
