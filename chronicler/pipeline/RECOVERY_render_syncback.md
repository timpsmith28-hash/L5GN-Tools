# Recovery runbook — render_md sync-back clobber

Run these **on your machine** (the sandbox holds only a pre-apply snapshot, so
the damaged rows exist only in your real `chronicler.db`). Every step previews
before it writes. Do them in order. `cd` into the Chronicler repo first.

The code is already fixed and tested (see "What changed" at the bottom). This
runbook undoes the *data* damage the old code did on the bad run, then re-applies
cleanly with the fixed renderer.

---

## 0. Back up the DB (non-negotiable)

```bash
cp chronicler.db chronicler.db.bak-$(date -u +%Y%m%dT%H%M%SZ)
```

## 1. Find the bad-run window

The bad render logged all its spurious `manual_override` rows in one burst.
Cluster by minute to spot it:

```sql
SELECT substr(created_at,1,16) AS minute, COUNT(*) AS n
FROM review_queue
WHERE type='manual_override'
GROUP BY minute
ORDER BY created_at;
```

You're looking for the cluster totalling ~359. Note its start/end timestamps —
call them `<START>` and `<END>` (use full `YYYY-MM-DD HH:MM:SS` values that
bracket the burst). If **all** your `manual_override` rows are from that one run
(likely — this feature just shipped), you can skip the window filter entirely and
scope by `type='manual_override'` alone. Confirm that first:

```sql
SELECT COUNT(*) AS total_manual_override FROM review_queue WHERE type='manual_override';
```

If that total ≈ 359 and you have no *earlier* legitimate manual overrides, treat
the whole set as bogus. Otherwise keep the `<START>`/`<END>` window on every
statement below.

## 2. Preview the bogus rows

```sql
SELECT id, thread_id, note, created_at
FROM review_queue
WHERE type='manual_override'
  AND created_at BETWEEN '<START>' AND '<END>'
ORDER BY created_at;
```

Sanity check: count ≈ 359, and notes read like
`project_link: 'L5GN-Crystal-Spire' -> None` (the clobber signature — a real
link being overwritten to null).

## 3. Check WHICH fields were clobbered

Each note is `field: old -> new`. This tells you if anything beyond
`project_link` / `project_confidence` got touched (those two are re-derivable by
relink; anything else would need manual attention):

```sql
SELECT substr(note, 1, instr(note, ':') - 1) AS field, COUNT(*) AS n
FROM review_queue
WHERE type='manual_override'
  AND created_at BETWEEN '<START>' AND '<END>'
GROUP BY field
ORDER BY n DESC;
```

**Expected:** only `project_link` and `project_confidence`. If other fields
(`status`, `tags`, `review_note`, `review_status`, `suggested_close`) appear,
stop and tell me — those aren't restored by relink and we'll recover their old
values from the `note` column before proceeding.

## 4. See the affected threads' current state

```sql
SELECT thread_id, project_link, project_confidence
FROM threads
WHERE thread_id IN (
  SELECT DISTINCT thread_id FROM review_queue
  WHERE type='manual_override'
    AND created_at BETWEEN '<START>' AND '<END>'
);
```

The clobber signature is `project_link IS NULL` and `project_confidence='manual'`
(the old sync-back set confidence to 'manual' as it wiped the link). That bogus
'manual' is what would block relink from re-linking, so we clear it next.

## 5. Delete the bogus review_queue rows

```sql
BEGIN;
DELETE FROM review_queue
WHERE type='manual_override'
  AND created_at BETWEEN '<START>' AND '<END>';
-- check "changes()" ≈ 359 before committing:
SELECT changes();
COMMIT;
```

## 6. Clear the bogus 'manual' confidence so relink can re-apply

Preview first:

```sql
SELECT thread_id, project_link, project_confidence
FROM threads
WHERE project_link IS NULL
  AND project_confidence='manual'
  AND thread_id IN (
    SELECT DISTINCT thread_id FROM review_queue  -- pre-delete list; run this in step 4
    WHERE type='manual_override'
      AND created_at BETWEEN '<START>' AND '<END>'
  );
```

Because step 5 already deleted those review_queue rows, capture the affected
`thread_id` list in step 4 **before** deleting, or run step 6's SELECT/UPDATE
before step 5. Simplest ordering: **do step 6 before step 5.** The clobber
signature alone is a safe filter:

```sql
BEGIN;
UPDATE threads
SET project_confidence = NULL
WHERE project_link IS NULL
  AND project_confidence = 'manual';
SELECT changes();   -- expect ~133
COMMIT;
```

A genuine manual override points at a real project, not null, so
`project_link IS NULL AND project_confidence='manual'` matches only the clobbered
rows. (If step 3 showed non-link fields clobbered, we handle those first.)

## 7. Re-apply links from evidence (evidence rows were never touched)

```bash
python3 pipeline/relink.py --apply
```

Expect it to auto-link the ~133 now-unprotected threads back to
`project_confidence='evidence'`. `link_evidence` was untouched by the bug, so the
scores are identical to the baseline run (133 auto / 5 downgrade / 10 ambiguous).

## 8. Render DB→file only (fixed renderer, sync-back suppressed)

```bash
python3 pipeline/render_md.py --no-syncback
```

This rewrites every `.md` from the DB **and** seeds `render_log` with correct
bases, without reading stale frontmatter back. It cannot re-clobber.

## 9. Verify evidence count held constant through render

```sql
SELECT COUNT(*) AS evidence_links
FROM threads
WHERE project_link IS NOT NULL AND project_confidence='evidence';   -- expect 133

SELECT COUNT(*) AS new_bogus_overrides
FROM review_queue
WHERE type='manual_override';                                       -- expect 0
```

133 before render == 133 after render, and zero fresh `manual_override` rows =
the bug is dead. From now on, run the full pipeline via
`run_pipeline.py` (it forces `--no-syncback` on render after any DB write); use
`run_pipeline.py --render-only` only when you deliberately want to pull Obsidian
edits back.

---

## What changed in the code (already applied + tested)

- **`render_md.py`** — sync-back now uses a `render_log` 3-way base: a file field
  is honored as a human edit only if it differs from the value we last *rendered*
  to that file. A stale default (base missing, or file == base) is declined, so
  the DB wins. Added `--no-syncback` for the DB-authoritative pass. Also creates
  `render_log` on every run path (a first-cut of the fix would have crashed under
  `--no-syncback` because the table was only created inside sync-back — caught and
  fixed in testing).
- **`run_pipeline.py`** — render runs `--no-syncback` in the full chain; only
  `--render-only` renders with sync-back on.

Reproduction test (`/tmp/s4test/repro_test.py`) proves: old code wipes both
evidence links and logs bogus overrides; new code preserves links with sync-back
on (base-missing decline), preserves them with `--no-syncback`, and still honors
a genuine Obsidian edit (file differs from recorded base → written to DB,
confidence set to 'manual', one override logged). All assertions pass.
