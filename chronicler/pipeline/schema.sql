-- Chronicler SQLite schema (section 5 of chronicler_system_design.md, v1)
-- Includes the account-as-string convention (9.5), attachment scope (9.6),
-- and the extra threads columns needed by the frontmatter contract (9.1):
-- review_note, suggested_close, tags.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS projects (
    project_id          TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    repo_folder_path    TEXT,
    source_system_id    TEXT              -- e.g. Claude project uuid
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
    project_link        TEXT REFERENCES projects(project_id),
    project_confidence  TEXT,              -- exact / fuzzy / evidence / manual / none
                                           --   authority (low->high): none < fuzzy < evidence < manual
                                           --   ('exact' is source-native and, like 'manual', automation never overwrites)
                                           --   S6 rule: automation may upgrade fuzzy->evidence, but only a
                                           --   human may change an 'evidence' link to anything else.
    review_status       TEXT DEFAULT 'auto',   -- auto / confirmed / pending
    raw_ref             TEXT,              -- path back to source file
    parser_version      TEXT,
    -- derived: 1 if the thread has >= SUBSTANTIVE_MIN_MESSAGES (4) messages, else 0.
    -- NULL on fresh insert; backfilled by set_substantive.py (a DB-only pipeline stage
    -- that runs every pass, keeping the frozen-schema 'substantive is always set'
    -- contract true after new ingests). Was missing from schema.sql -- present in the
    -- live DB via an old migration, so only a from-scratch build surfaced the gap.
    substantive         INTEGER,
    -- frontmatter-contract fields (9.1), stored here so renderer/sync-back has one home:
    review_note         TEXT,
    suggested_close     INTEGER DEFAULT 0,
    tags                TEXT DEFAULT '[]', -- JSON array, e.g. ["tag1","tag2"]
    -- S6 re-link pass: JSON array of link_evidence.evidence_id values that justify
    -- the current link, so every automated link is explainable after the fact.
    link_evidence_ids   TEXT               -- JSON array, e.g. [12, 87, 340]; NULL if never re-linked
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
    extracted_content   TEXT               -- Claude's inline extracted_content when present (strong project-link signal)
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
                                           --   S6 adds: link_upgrade (informational, auto-resolved),
                                           --   link_ambiguous (rival candidates), link_downgrade (fuzzy demoted)
    thread_id           TEXT,
    candidate_thread_id TEXT,
    confidence          REAL,
    status              TEXT DEFAULT 'pending',  -- pending / confirmed / rejected / reassigned
    note                TEXT,
    created_at          TEXT,
    resolved_at         TEXT,
    -- Command Deck prototype (COWORK_BRIEF_command_deck_proto Task 1): a
    -- structured registry id for the candidate project this row suggests, so the
    -- deck can GROUP BY it instead of parsing `note` prose. candidate_project is
    -- the best candidate for every row type that carries one (project_link,
    -- link_ambiguous, link_downgrade); rival_project is the second candidate,
    -- populated only for link_ambiguous rows (two real rivals) so a thread never
    -- silently drops out of the batch of the project it might actually belong to.
    candidate_project   TEXT,              -- registry id, nullable
    rival_project       TEXT               -- registry id, nullable (link_ambiguous only)
);

-- DECISIONS 0024: project-link rejections are an endpoint-owned, append-only
-- log, deliberately separate from review_queue (pipeline-owned, single-writer
-- since 0007). "Not this project" inserts a row here; review_queue is never
-- touched by the review endpoint. A (thread_id, candidate_project) pair with
-- verdict='rejected' is excluded from that project's batch by the read side
-- (core.pending_rulings / core.queue_by_project), the same join-based
-- exclusion pattern as the existing project_confidence='manual' rule.
CREATE TABLE IF NOT EXISTS review_rulings (
    item_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id           TEXT NOT NULL,
    candidate_project   TEXT NOT NULL,
    verdict             TEXT NOT NULL,     -- 'rejected' (only verdict this round writes)
    ruled_at            TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_review_rulings_thread_project
    ON review_rulings(thread_id, candidate_project);

-- S6 evidence model. One row per (thread, project, signal) contribution. S4/S5
-- write rows here (filename_xref, path_mention); relink.py additionally persists
-- the inline name/alias signals it computes for a *winning* decision so those
-- contributions have stable evidence_ids to reference from threads.link_evidence_ids.
-- Created with IF NOT EXISTS so it is safe whether S4 or this migration lands first.
CREATE TABLE IF NOT EXISTS link_evidence (
    evidence_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id        TEXT,
    project          TEXT,      -- canonical_name from the registry
    signal           TEXT,      -- name_alias|vocabulary|filename_xref|path_mention|time_window
    weight           REAL,      -- 0..1
    detail           TEXT,      -- e.g. the matched basename/alias/path
    produced_at      TEXT,      -- UTC ISO-8601
    producer_version TEXT
);
CREATE INDEX IF NOT EXISTS idx_link_evidence_thread ON link_evidence(thread_id);
CREATE INDEX IF NOT EXISTS idx_link_evidence_signal ON link_evidence(signal);

CREATE INDEX IF NOT EXISTS idx_messages_thread ON messages(thread_id);
CREATE INDEX IF NOT EXISTS idx_messages_turnhash ON messages(source_turn_hash);
CREATE INDEX IF NOT EXISTS idx_attachments_message ON attachments(message_id);
CREATE INDEX IF NOT EXISTS idx_attachments_turnhash ON attachments(turn_hash);
CREATE INDEX IF NOT EXISTS idx_threads_source_account ON threads(source, account);
CREATE INDEX IF NOT EXISTS idx_review_queue_status ON review_queue(status);
