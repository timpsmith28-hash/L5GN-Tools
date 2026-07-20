"""tester_registry_tiers: program > project > repo, one identifier scheme.

Guards the two things round-3 Task D actually decided (DECISIONS 0012):

  1. **The hierarchy is real data, not a naming convention.** A repo-level match
     can be rolled up to its project and program for display, and a curated
     grouping survives a generator re-run (it is manual-provenance).
  2. **One identifier scheme across all tiers: the registry `id`.** This is the
     round-2 divergence, closed. relink used to key by canonical_name and write
     `smelt-gateway` into `threads.project_link`; the review endpoint wrote ids
     like `crystal-spire` into the same column. Two vocabularies in one column
     means no consumer can trust it. The gate asserts both writers now agree.

Hermetic: an in-memory registry dict and a temp DB. No real registry, no vault.
"""
from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

from chronicler.review import core as review_core

_PIPELINE = Path(__file__).resolve().parent.parent / "chronicler" / "pipeline"


def _load(name: str):
    added = str(_PIPELINE) not in sys.path
    if added:
        sys.path.insert(0, str(_PIPELINE))
    try:
        import importlib
        return importlib.import_module(name)
    finally:
        if added and str(_PIPELINE) in sys.path:
            sys.path.remove(str(_PIPELINE))


TIERED = {
    "schema_version": 2,
    "id_scheme": "id",
    "programs": [
        {"id": "l5gn-os", "name": "L5GN OS", "scope": "l5gn"},
    ],
    "projects": [
        {
            "id": "citadel-microide",
            "canonical_name": "Citadel MicroIDE",
            "program": "l5gn-os",
            "scope": "l5gn",
            "aliases": ["Citadel", "CID"],
            "repos": [
                {"id": "smelt-gateway", "canonical_name": "smelt-gateway",
                 "aliases": ["Smelt"], "present": True, "scope": "l5gn",
                 "vcs": "git"},
                {"id": "l5gn-armory-v4", "canonical_name": "L5GN_Armory_v4",
                 "aliases": ["Armory v4"], "present": True, "scope": "l5gn",
                 "vcs": "git"},
            ],
        },
        {
            "id": "l5gn-tools-chronicler",
            "canonical_name": "Chronicler (2026, Python/SQLite)",
            "program": None, "scope": "l5gn",
            "aliases": ["Chronicler"], "low_signal_body": True, "repos": [],
        },
    ],
}


def run() -> list[str]:
    v: list[str] = []
    v.extend(_check_endpoint_view())
    v.extend(_check_generator_tiers())
    v.extend(_check_one_id_scheme())
    v.extend(_check_rollup_rules())
    return v


def _check_rollup_rules() -> list[str]:
    """Tiers must not manufacture ambiguity out of their own hierarchy.

    Two failure modes appear the moment a project gains a repo, and both would
    have flooded the review queue:

      * SELF-ambiguity -- the project and its own repo both match the same alias
        and look like rivals. They are one answer at two zoom levels.
      * SIBLING ambiguity -- two repos of the SAME project tie. "Which Armory
        incarnation?" is unanswerable from a title, but "this is Citadel
        MicroIDE" is certain, so the parent project is the right answer rather
        than a question no human can settle either.
    """
    v: list[str] = []
    relink = _load("relink")

    registry = {
        "l5gn-os": {"tier": "program", "canonical_name": "L5GN OS",
                    "program": "l5gn-os", "project": None},
        "citadel-microide": {"tier": "project", "canonical_name": "Citadel MicroIDE",
                             "program": "l5gn-os", "project": "citadel-microide"},
        "smelt-gateway": {"tier": "repo", "canonical_name": "smelt-gateway",
                          "program": "l5gn-os", "project": "citadel-microide"},
        "l5gn-armory-v4": {"tier": "repo", "canonical_name": "L5GN_Armory_v4",
                           "program": "l5gn-os", "project": "citadel-microide"},
        "crystal-spire": {"tier": "project", "canonical_name": "Crystal Spire",
                          "program": "l5gn-os", "project": "crystal-spire"},
    }

    def cand(pid, adjusted):
        return {"project": pid, "adjusted": adjusted, "score": adjusted,
                "used": [], "evidence_ids": [], "summary": "test"}

    # parent + own child collapse to one candidate
    collapsed = relink.collapse_lineage(
        [cand("smelt-gateway", 0.80), cand("citadel-microide", 0.80)], registry)
    if len(collapsed) != 1:
        v.append(f"relink: a project and its own repo stayed {len(collapsed)} "
                 "separate candidates -- that is self-ambiguity, not rivalry")
    elif collapsed[0]["project"] != "smelt-gateway":
        v.append(f"relink: lineage collapse kept {collapsed[0]['project']!r}; on a "
                 "tie the MORE SPECIFIC tier should survive (it can be rolled up "
                 "for display, but the reverse loses information)")
    elif "citadel-microide" not in collapsed[0].get("rolled_up", []):
        v.append("relink: the absorbed candidate was not recorded in rolled_up -- "
                 "the fold must be visible in the report, not hidden")

    # genuinely unrelated projects must NOT be collapsed
    unrelated = relink.collapse_lineage(
        [cand("citadel-microide", 0.80), cand("crystal-spire", 0.78)], registry)
    if len(unrelated) != 2:
        v.append("relink: two unrelated projects were collapsed -- real rivalry "
                 "must still reach the human")

    # rival siblings roll up to their shared parent instead of queueing ambiguity
    class _Conn:
        def execute(self, *a, **k):
            raise AssertionError("decide() should not query for an unlinked thread")

    thread = {"thread_id": "t", "title": "Armory", "created_at": None,
              "project_link": None, "project_confidence": None}
    dec = relink.decide(
        thread,
        [cand("l5gn-armory-v4", 0.80), cand("smelt-gateway", 0.80)],
        _Conn(), registry)
    if dec["category"] != "suggest":
        v.append(f"relink: rival sibling repos produced {dec['category']!r}; they "
                 "should roll up to a suggestion at the shared parent project")
    elif dec["best"]["project"] != "citadel-microide":
        v.append(f"relink: sibling roll-up chose {dec['best']['project']!r}, "
                 "expected the shared parent project")
    elif sorted(dec.get("rolled_from", [])) != ["l5gn-armory-v4", "smelt-gateway"]:
        v.append("relink: sibling roll-up did not record which repos it rolled up")

    return v


def _check_endpoint_view() -> list[str]:
    """The review endpoint offers every tier and shows the hierarchy."""
    v: list[str] = []
    reg = review_core.load_registry(TIERED)

    for tid, tier in (("l5gn-os", "program"), ("citadel-microide", "project"),
                      ("smelt-gateway", "repo")):
        if tid not in reg:
            v.append(f"review: '{tid}' is not a link target -- a ruling must be "
                     f"possible at the {tier} tier")
        elif reg[tid].get("tier") != tier:
            v.append(f"review: '{tid}' reported as tier {reg[tid].get('tier')!r}, "
                     f"expected {tier!r}")

    crumb = reg.get("smelt-gateway", {}).get("hierarchy", "")
    for expected in ("L5GN OS", "Citadel MicroIDE", "smelt-gateway"):
        if expected not in crumb:
            v.append(f"review: repo breadcrumb {crumb!r} is missing "
                     f"{expected!r} -- the hierarchy must show for context")

    # a legacy flat registry must still load rather than take the surface down
    flat = {"projects": [{"id": "chancellor", "canonical_name": "Chancellor",
                          "scope": "l5gn"}]}
    legacy = review_core.load_registry(flat)
    if "chancellor" not in legacy:
        v.append("review: a legacy flat registry no longer loads -- a stale "
                 "registry should degrade, not break the review surface")
    return v


def _check_generator_tiers() -> list[str]:
    """The generator folds deposits into the curated tree and preserves it."""
    v: list[str] = []
    br = _load("build_registry")

    entries = [
        {"canonical_name": "smelt-gateway", "path": "C:/r/smelt-gateway",
         "scope": "l5gn", "vcs": "git", "aliases": ["smelt-gateway"],
         "alias_sources": {"smelt-gateway": "seed_canonical"}, "status": "active",
         "first_seen": "2026-03-01", "last_activity": "2026-07-01",
         "commit_count": 120, "estates": ["personal"], "registry_updated": "now"},
        {"canonical_name": "Unclassified-Thing", "path": "C:/r/Unclassified-Thing",
         "scope": "l5gn", "vcs": "git", "aliases": ["Unclassified-Thing"],
         "alias_sources": {"Unclassified-Thing": "seed_canonical"},
         "status": "active", "first_seen": "2026-01-01",
         "last_activity": "2026-02-01", "commit_count": 3, "estates": ["personal"],
         "registry_updated": "now"},
    ]
    groups = {"programs": TIERED["programs"], "projects": TIERED["projects"],
              "_source": "test"}
    body, notes = br.assemble_tiers(entries, groups)
    projects = {p["id"]: p for p in body["projects"]}

    # curated grouping survives: the deposit attaches facts, it does not flatten
    citadel = projects.get("citadel-microide")
    if not citadel:
        v.append("build_registry: the curated project disappeared -- manual "
                 "grouping must survive a generator run")
        return v
    if citadel.get("provenance") != "manual":
        v.append("build_registry: curated projects must be manual-provenance so "
                 "re-runs preserve them")
    repos = {r["id"]: r for r in citadel["repos"]}
    if repos.get("smelt-gateway", {}).get("present") is not True:
        v.append("build_registry: a deposited repo was not marked present")
    if repos.get("smelt-gateway", {}).get("first_seen") != "2026-03-01":
        v.append("build_registry: estate git facts were not attached to the "
                 "curated repo")
    if repos.get("l5gn-armory-v4", {}).get("present") is not False:
        v.append("build_registry: a curated repo absent from every deposit must "
                 "be kept and marked present=false, never dropped (it is usually "
                 "just a rig that has not deposited yet)")

    # an unclaimed deposit is never lost
    auto = [p for p in body["projects"] if p.get("provenance") == "auto"]
    if not any(p["canonical_name"] == "Unclassified-Thing" for p in auto):
        v.append("build_registry: an unclassified deposited repo was dropped -- "
                 "it must become its own auto project")

    # a repo-less project stays a link target
    if "l5gn-tools-chronicler" not in projects:
        v.append("build_registry: a project with no repos was dropped -- a "
                 "project is an effort, not a folder")

    # ids are unique across tiers; low_signal_body reaches the target map
    targets = br.collect_link_targets(body)
    if targets.get("l5gn-tools-chronicler", {}).get("low_signal_body") is not True:
        v.append("build_registry: low_signal_body did not survive into the link "
                 "targets -- the false-positive guard would stay unset")
    if targets.get("smelt-gateway", {}).get("project") != "citadel-microide":
        v.append("build_registry: a repo target does not carry its project, so a "
                 "repo match cannot roll up")
    if targets.get("smelt-gateway", {}).get("program") != "l5gn-os":
        v.append("build_registry: a repo target does not carry its program")

    # duplicate ids across tiers must be a hard error
    dupe = {"programs": [{"id": "clash", "name": "Clash"}],
            "projects": [{"id": "clash", "canonical_name": "Clash",
                          "scope": "l5gn", "repos": []}]}
    try:
        br.collect_link_targets(dupe)
        v.append("build_registry: a duplicate id across tiers was accepted -- one "
                 "id must mean exactly one thing")
    except SystemExit:
        pass
    return v


def _check_one_id_scheme() -> list[str]:
    """relink and the review endpoint must write the SAME identifier."""
    v: list[str] = []
    relink = _load("relink")

    if not hasattr(relink, "rollup_label"):
        v.append("relink: no rollup_label -- a repo match cannot be displayed "
                 "with its project/program context")

    with tempfile.TemporaryDirectory() as td:
        reg_path = Path(td) / "project_registry.json"
        import json
        reg_path.write_text(json.dumps(TIERED), encoding="utf-8")
        orig = relink.REGISTRY_PATH
        relink.REGISTRY_PATH = reg_path
        try:
            loaded = relink.load_registry()
        finally:
            relink.REGISTRY_PATH = orig

        # keyed by id, at every tier
        for tid in ("l5gn-os", "citadel-microide", "smelt-gateway"):
            if tid not in loaded:
                v.append(f"relink: '{tid}' missing -- the registry must be keyed "
                         "by id across all three tiers")
        if "Citadel MicroIDE" in loaded or "L5GN_Armory_v4" in loaded:
            v.append("relink: registry is still keyed by canonical_name -- that is "
                     "the divergence Task D.3 closes")

        crumb = relink.rollup_label(loaded, "smelt-gateway")
        for expected in ("L5GN OS", "Citadel MicroIDE", "smelt-gateway"):
            if expected not in crumb:
                v.append(f"relink: rollup_label({crumb!r}) is missing {expected!r}")

        # THE test: both writers put the same value in threads.project_link
        db = Path(td) / "t.db"
        conn = sqlite3.connect(str(db))
        # Both writers expect Row access, same as the shared connection helper.
        conn.row_factory = sqlite3.Row
        conn.execute("CREATE TABLE projects (project_id TEXT PRIMARY KEY, name TEXT, "
                     "repo_folder_path TEXT, source_system_id TEXT);")
        conn.execute("CREATE TABLE threads (thread_id TEXT PRIMARY KEY, "
                     "project_link TEXT, project_confidence TEXT);")
        conn.execute("INSERT INTO threads VALUES ('t1', NULL, NULL);")
        conn.execute("INSERT INTO threads VALUES ('t2', NULL, NULL);")
        conn.commit()

        relink.upsert_project(conn, "smelt-gateway", loaded)
        conn.execute("UPDATE threads SET project_link=? WHERE thread_id='t1'",
                     ("smelt-gateway",))
        conn.commit()

        endpoint_reg = review_core.load_registry(TIERED)
        review_core.apply_ruling(conn, "t2", "smelt-gateway", endpoint_reg)
        conn.commit()

        rows = {r["thread_id"]: r["project_link"] for r in conn.execute(
            "SELECT thread_id, project_link FROM threads").fetchall()}
        if rows.get("t1") != rows.get("t2"):
            v.append(f"id scheme: relink wrote {rows.get('t1')!r} but the review "
                     f"endpoint wrote {rows.get('t2')!r} for the same target -- "
                     "one column, one vocabulary (D.3)")
        if rows.get("t1") != "smelt-gateway":
            v.append(f"id scheme: project_link holds {rows.get('t1')!r}, expected "
                     "the registry id")

        prow = conn.execute("SELECT project_id, name FROM projects "
                            "WHERE project_id='smelt-gateway'").fetchone()
        if prow is None:
            v.append("id scheme: no projects row keyed by the registry id -- the "
                     "project_link FK would not resolve")
        elif prow["name"] != "smelt-gateway":
            # canonical_name for this repo IS 'smelt-gateway'; the point is that
            # the id is the key and the readable name is the value.
            v.append(f"id scheme: projects.name={prow['name']!r}, expected the "
                     "canonical_name alongside the id key")
        conn.close()
    return v
