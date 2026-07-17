-- ============================================================================
-- Chronicler FROZEN schema — schema_version 1.0-frozen (PRAGMA user_version = 1)
-- Frozen: 2026-07-17
--
-- ****************************************************************************
-- * FROZEN CONTRACT. Do NOT edit chronicler.db's schema in place.           *
-- * This is the read-only data store that L5GN-Tools `vault_reader` builds   *
-- * against. Linking is refined by RE-RUNNING the evidence/relink pipeline   *
-- * (which only rewrites rows), never by changing the schema.                *
-- *                                                                          *
-- * Any schema change requires a migration script AND a schema_version bump, *
-- * after which SCHEMA.md and this file must be regenerated                  *
-- * (`finalize_db.py --apply` dumps the live schema authoritatively).        *
-- ****************************************************************************
--
-- This file is a hand-authored reference reflecting the post-migration schema.
-- The authoritative dump is produced by `finalize_db.py --apply` at freeze time;
-- if the two ever disagree, the live-DB dump wins and this file is stale.
-- ============================================================================

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS projects (
    project_id          TEXT PRIMARY KEY,  -- registry canonical_name OR source-native project uuid
    name                TEXT NOT NULL,
    repo_folder_path    TEXT,
    source_system_id    TEXT               -- e.g. Claude project uuid
);

CREATE TABLE IF NOT EXISTS threads (
    thread_id           TEXT PRIMARY KEY,  -- source-native uuid where available, else synthetic
    source              TEXT NOT NULL,     -- claude / gemini
    account             TEXT NOT NULL,     -- free-form, e.g. claude-personal, gemini-personal, gemini-work
    title               TEXT,
    created_at          TEXT,              -- UTC ISO8601
    updated_at          TEXT,
    gem_name            TEXT,
    is_custom_gem       INTEGER DEFAULT 0,
    status              TEXT DEFAULT 'open',   -- open / closed
    closed_at           TEXT,
    project_link        TEXT REFERENCES projects(project_id),  -- NULL iff unlinked (the ONE representation)
    project_confidence  TEXT,              -- NULL / fuzzy / evidence / manual / exact
                                           --   authority (low->high): NULL < fuzzy < evidence < manual
                                           --   ('exact' is source-native and, like 'manual', automation never overwrites)
                                           --   automation may upgrade fuzzy->evidence; only a human changes an 'evidence' link.
                                           --   NOTE: legacy string 'none' has been migrated to SQL NULL (P2). Do not test for 'none'.
    review_status       TEXT DEFAULT 'auto',   -- auto / confirmed / pending
    raw_ref             TEXT,              -- path back to source file
    parser_version      TEXT,
    review_note         TEXT,              -- frontmatter-contract field (9.1)
    suggested_close     INTEGER DEFAULT 0,
    tags                TEXT DEFAULT '[]', -- JSON array
    link_evidence_ids   TEXT,              -- JSON array of link_evidence.evidence_id; NULL if never re-linked
    substantive         INTEGER DEFAULT 0  -- 1 iff thread has >= 4 messages, else 0 (honesty flag, P3)
);

CREATE TABLE IF NOT EXISTS messages (
    message_id          TEXT PRIMARY KEY,  -- source-native uuid where available, else synthetic hash
    thread_id           TEXT REFERENCES threads(thread_id),  -- nullable until resolved (Gemini pre-reconciliation)
    seq                 INTEGER,           -- order within thread; nullable until resolved
    role                TEXT,              -- user / assistant / activity_log
    content             TEXT,
    created_at          TEXT,
    source_turn_hash    TEXT               -- 16-hex attachment-batch id, secondary join anchor
);

CREATE TABLE IF NOT EXISTS attachments (
    attachment_id       TEXT PRIMARY KEY,  -- hash or uuid
    message_id          TEXT REFERENCES messages(message_id),  -- nullable until linked
    filename            TEXT,
    turn_hash           TEXT,
    file_path           TEXT,              -- archived location, nullable if not yet archived
    mime                TEXT,
    extracted_content   TEXT               -- Claude's inline extracted_content (strong project-link signal)
);

CREATE TABLE IF NOT EXISTS ingestion_log (
    batch_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    source              TEXT,
    account             TEXT,
    file_hash           TEXT,
    imported_at         TEXT,
    rows_new            INTEGER,
    rows_changed        INTEGER,
    rows_skipped        INTEGER,
    parser_version      TEXT
);

CREATE TABLE IF NOT EXISTS review_queue (
    item_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    type                TEXT,              -- thread_grouping / project_link / reopen_candidate / close_suggestion
                                           --   S6 adds: link_upgrade / link_ambiguous / link_downgrade
                                           --   finalize adds: link_repair (P1 leaked-thread-id reset)
    thread_id           TEXT,
    candidate_thread_id TEXT,
    confidence          REAL,
    status              TEXT DEFAULT 'pending',  -- pending / confirmed / rejected / reassigned
    note                TEXT,
    created_at          TEXT,
    resolved_at         TEXT
);

-- Evidence model. One row per (thread, project, signal) contribution.
-- NOTE: the 'vocabulary' signal was evaluated and DROPPED (it degraded linking);
-- no 'vocabulary' rows exist. build_vocabulary.py remains on disk unused.
CREATE TABLE IF NOT EXISTS link_evidence (
    evidence_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id        TEXT,
    project          TEXT,      -- canonical_name from the registry
    signal           TEXT,      -- name_alias | filename_xref | path_mention | time_window
    weight           REAL,      -- 0..1
    detail           TEXT,      -- e.g. the matched basename/alias/path
    produced_at      TEXT,      -- UTC ISO-8601
    producer_version TEXT
);

-- Single-row watermark for extract_path_mentions.py (incremental path scanning).
CREATE TABLE IF NOT EXISTS path_scan_log (
    id                 INTEGER PRIMARY KEY CHECK (id = 1),
    scanned_through    INTEGER NOT NULL,   -- highest messages.rowid scanned
    updated_at         TEXT NOT NULL
);

-- Per-thread snapshot of last-rendered editable fields — the 3-way base that lets
-- render_md.py sync-back distinguish a real Obsidian edit from a stale default.
CREATE TABLE IF NOT EXISTS render_log (
    thread_id       TEXT PRIMARY KEY,
    rendered_fields TEXT,
    rendered_at     TEXT
);

-- Schema stamp. vault_reader should assert schema_version (and/or PRAGMA user_version).
CREATE TABLE IF NOT EXISTS meta (
    key    TEXT PRIMARY KEY,
    value  TEXT
);
-- Seeded at freeze: schema_version='1.0-frozen', frozen_at=<ts>, substantive_min_messages='4'

CREATE INDEX IF NOT EXISTS idx_link_evidence_thread ON link_evidence(thread_id);
CREATE INDEX IF NOT EXISTS idx_link_evidence_signal ON link_evidence(signal);
CREATE INDEX IF NOT EXISTS idx_messages_thread ON messages(thread_id);
CREATE INDEX IF NOT EXISTS idx_messages_turnhash ON messages(source_turn_hash);
CREATE INDEX IF NOT EXISTS idx_attachments_message ON attachments(message_id);
CREATE INDEX IF NOT EXISTS idx_attachments_turnhash ON attachments(turn_hash);
CREATE INDEX IF NOT EXISTS idx_threads_source_account ON threads(source, account);
CREATE INDEX IF NOT EXISTS idx_review_queue_status ON review_queue(status);
