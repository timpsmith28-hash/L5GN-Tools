# Runbook — collect the reconciliation evidence (READ-ONLY, knight)

**Purpose.** Task A of `COWORK_BRIEF_projects_reconciliation.md` reconciles six
sources. Three of them — the live `projects` table, the generated registry, and
the two deposited estates — live on the knight, which the Cowork session cannot
reach. This runbook dumps all of them into one file you bring back to the rig.

**It writes nothing to the vault.** Every query opens the DB with `sqlite3
-readonly`; the only file created is the output bundle in `/tmp`. No backup is
required because nothing is written — the backup rule (DECISIONS 0005/0006)
applies to Task C, not to this.

---

## Step 1 — run it on the knight

SSH in and paste this whole block in one go.

```bash
ssh l5gn-castle
```

```bash
set -u
cd ~/L5GN-Tools
VAULT="$HOME/vault/chronicler.db"
ESTATES="$HOME/vault/estates"
GENREG="$HOME/L5GN/.intel_sync/project_registry.json"
OUT="/tmp/reconcile_evidence_$(date -u +%Y%m%dT%H%M%SZ).txt"
Q() { sqlite3 -readonly -cmd ".mode tabs" -cmd ".headers on" "$VAULT" "$1"; }

{
echo "=== S1 META ==="
echo "host=$(hostname)  utc=$(date -u +%FT%TZ)"
echo "git=$(git -C ~/L5GN-Tools rev-parse --short HEAD 2>/dev/null) dirty=$(test -n "$(git -C ~/L5GN-Tools status --porcelain 2>/dev/null)" && echo true || echo false)"
echo "vault=$VAULT  bytes=$(stat -c %s "$VAULT" 2>/dev/null)"
sqlite3 -readonly "$VAULT" "SELECT 'schema_version='||value FROM meta WHERE key='schema_version';"
Q "SELECT (SELECT COUNT(*) FROM threads) AS threads, (SELECT COUNT(*) FROM projects) AS projects, (SELECT COUNT(*) FROM messages) AS messages, (SELECT COUNT(*) FROM link_evidence) AS link_evidence, (SELECT COUNT(*) FROM review_queue WHERE status='pending') AS pending_reviews;"

echo; echo "=== S2 PROJECTS — every row, with its link count ==="
Q "SELECT p.project_id, p.name, p.source_system_id, p.repo_folder_path,
          (SELECT COUNT(*) FROM threads t WHERE t.project_link = p.project_id) AS linked_threads
   FROM projects p ORDER BY linked_threads DESC, p.project_id;"

echo; echo "=== S3 LINK CENSUS — by target and confidence (Task B query 1) ==="
Q "SELECT project_link, project_confidence, COUNT(*) AS n FROM threads
   WHERE project_link IS NOT NULL GROUP BY 1,2 ORDER BY 3 DESC;"

echo; echo "=== S4 CONFIDENCE CENSUS — all threads ==="
Q "SELECT COALESCE(project_confidence,'(null)') AS conf, COUNT(*) AS n FROM threads GROUP BY 1 ORDER BY 2 DESC;"

echo; echo "=== S5 MANUAL RULINGS — Tim's own, listed in full ==="
Q "SELECT thread_id, project_link, project_confidence, review_status, title FROM threads
   WHERE project_confidence IN ('manual','exact') ORDER BY project_link, title;"

echo; echo "=== S6 ORPHAN CHECK — links with no projects row (expect 0) ==="
Q "SELECT t.project_link, COUNT(*) AS n FROM threads t
   LEFT JOIN projects p ON p.project_id = t.project_link
   WHERE t.project_link IS NOT NULL AND p.project_id IS NULL GROUP BY 1;"

echo; echo "=== S7 REVIEW QUEUE — pending project_link items by type ==="
Q "SELECT type, status, COUNT(*) AS n FROM review_queue GROUP BY 1,2 ORDER BY 3 DESC;"

echo; echo "=== S8 LINK_EVIDENCE — by project and signal ==="
Q "SELECT project, signal, COUNT(*) AS n, ROUND(AVG(weight),3) AS avg_w FROM link_evidence
   GROUP BY 1,2 ORDER BY 3 DESC;"

echo; echo "=== S9 THREAD TITLES — every thread (alias mining, Task A source 6) ==="
Q "SELECT thread_id, source, account, substr(COALESCE(created_at,''),1,10) AS created,
          substantive, COALESCE(project_link,'') AS link, COALESCE(project_confidence,'') AS conf, title
   FROM threads ORDER BY created, title;"

echo; echo "=== S10 GENERATED REGISTRY — sha256 + full contents ==="
echo "path=$GENREG"
sha256sum "$GENREG" 2>/dev/null || echo "MISSING: $GENREG"
echo "--- begin generated registry ---"
cat "$GENREG" 2>/dev/null
echo "--- end generated registry ---"

echo; echo "=== S11 DEPOSITED ESTATES — project inventories ==="
for E in personal work; do
  F="$ESTATES/$E/estate.json"
  echo "--- estate=$E path=$F ---"
  if [ -f "$F" ]; then
    sha256sum "$F"
    python3 - "$F" <<'PY'
import json,sys
d=json.load(open(sys.argv[1],encoding='utf-8'))
print("generated_at=",d.get("generated_at"),"estate_root=",d.get("estate_root"))
for p in d.get("projects",[]):
    g=p.get("git_summary") or {}
    print("\t".join(str(x) for x in [
        p.get("name"), p.get("scope"), p.get("path"),
        g.get("first_commit_date"), g.get("latest_date"), g.get("commit_count")]))
PY
  else
    echo "MISSING"
  fi
  ls -la "$ESTATES/$E" 2>/dev/null | head -20
done

echo; echo "=== S12 PATH DERIVATION (Task G) ==="
echo "CHRONICLER_HOME=${CHRONICLER_HOME:-(unset)}"
echo "CHRONICLER_REGISTRY_PATH=${CHRONICLER_REGISTRY_PATH:-(unset)}"
echo "CHRONICLER_DB_PATH=${CHRONICLER_DB_PATH:-(unset)}"
.venv/bin/python - <<'PY'
import sys, pathlib
sys.path.insert(0, "chronicler/pipeline")
try:
    import relink
    print("relink.REGISTRY_PATH =", relink.REGISTRY_PATH, "exists=", relink.REGISTRY_PATH.is_file())
except Exception as e:
    print("relink import failed:", type(e).__name__, e)
try:
    from chronicler.review import core
    from l5gntools.config import load_machine  # may differ; fall back below
except Exception:
    core = None
try:
    if core is None:
        from chronicler.review import core
    p = core.resolve_registry_path()
    print("review.resolve_registry_path() =", p, "exists=", p.is_file())
except Exception as e:
    print("review resolve failed:", type(e).__name__, e)
PY
ls -la ~/L5GN/.intel_sync/ 2>/dev/null || echo "no ~/L5GN/.intel_sync"

echo; echo "=== S13 ALIAS REPORT — build_registry HITL output (dry-run, writes nothing) ==="
.venv/bin/python chronicler/pipeline/build_registry.py --report-aliases 2>&1

echo; echo "=== END ==="
} > "$OUT" 2>&1

echo "WROTE $OUT"
wc -l "$OUT"
```

`--report-aliases` is a dry-run: `build_registry.py` writes the registry only
when run *without* a dry-run flag, so S13 changes nothing on disk.

## Step 2 — bring it back to the rig

From a PowerShell window **on the gaming rig** (not on the knight):

```powershell
scp l5gn-castle:/tmp/reconcile_evidence_*.txt "C:\Users\timps\Documents\GitHub\L5GN-Tools\data\"
```

`data/` is gitignored, so nothing lands in the commit. Tell the Cowork session
the file is there and it will read it directly.

## If something fails

- `sqlite3: not found` → `sudo apt install sqlite3`, or tell the session and it
  will re-issue the queries through `.venv/bin/python`.
- `no such column: substantive` → the vault predates the frozen schema; report
  the error rather than editing the query.
- A whole section erroring is fine — the bundle captures stderr per section, so
  bring back whatever it produced. A partial bundle is still evidence.
