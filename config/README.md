# config/ — what's here, and how the untracked half travels

Read this before wondering why a fresh checkout behaves differently from this
one.

Most of this folder is committed and needs no explanation. **Three files are
untracked by design**, and the thing that cannot be derived from anywhere in the
repo is *how each of them gets to the machine that needs it.* That movement is
manual, it lives in one person's head, and writing it down here is the only
reason this document exists.

Everything else below defers: **why** a file is untracked is in `.gitignore`'s
comments and in the DECISIONS entry each one cites. This file does not restate
those reasons — two copies of a rationale is one more than can be kept correct.

---

## The tracked files

Committed, synced, and correct on every machine without intervention. Listed so
the untracked set is legible by contrast, not to describe them.

| File | Read by | Notes |
|---|---|---|
| `machines.json` | `l5gntools/config.py` | Per-host sections, keyed by `socket.gethostname()` |
| `local.json.example` | humans | The shape `local.json` must take |
| `authors.json` | `l5gntools/config.py`, `chronicler/review/estate_time.py` | Canonical name → aliases |
| `project_wizard.allow.json` | `chronicler/review/project_wizard.py` | The repo allowlist (0042) |
| `mcf_conversation_map.tsv.sha256` | *(nothing yet)* | The ratification fingerprint — see below |

## The untracked set

| File | Why untracked | Travels how |
|---|---|---|
| `local.json` | `.gitignore` — per-machine paths/secrets | **By hand.** Edit on the target machine from `local.json.example` |
| `project_registry.json` | `.gitignore` — real project names, employer codenames | **By hand or `scp`** from this rig |
| `mcf_conversation_map.tsv` | DECISIONS 0040 clause 4 — conversation titles | **By hand or `scp`** from this rig |

### How they move, stated plainly

**Authored here, on the gaming/dev rig. Copied outward manually.** Either
dragged across as single files, or pushed with `scp` over the existing key-based
ssh alias (the same alias `deploy/push-exports.ps1` uses for the knight).

There is **no script and no automation for config**, and that is deliberate, not
an omission. `deploy/` covers chat-export zips → knight; it has never covered
config. Three files, changing rarely, moved by the one person who authors them,
is a cost small enough that automating it would buy less than it costs to
maintain and to trust.

**Future state may take more control of this.** Recorded as a known, accepted
position rather than a gap someone should fix on sight — if it changes, it
changes because the cost changed, not because this document read like an
apology.

### `project_registry.json` is resolved, not just copied

Unlike the other two, the endpoint does not simply read `config/`. Per
`chronicler/review/core.py:resolve_registry_path`, most-explicit first:

1. `CHRONICLER_REGISTRY_PATH` — the recommended knob on the knight
2. relink's derived location, `<github_root>/L5GN/.intel_sync/project_registry.json`
3. the repo authoring copy, `config/project_registry.json` — dev / fallback

So the copy in this folder is the **authoring** copy. Putting it on a machine
does not guarantee it is the one being read there. Check the order before
concluding a registry change didn't take.

### The map carries a fingerprint, and the fingerprint is committed

`mcf_conversation_map.tsv` is untracked; `mcf_conversation_map.tsv.sha256` is
committed beside it. That is DECISIONS 0040 clause 4, and it is not decoration.

Untracking the map cost 0033's review mechanism — *"the human reads
`git diff --staged` and commits"* — because an untracked file produces no diff.
The fingerprint is the stated replacement: the repo records **that** a map was
ratified, when, and against what content, while carrying none of the titles.

The file holds one line in `sha256sum` format — `<hash>  <repo-relative path>` —
chosen so verification needs no bespoke code:

```bash
sha256sum -c config/mcf_conversation_map.tsv.sha256    # git bash / WSL
```

```powershell
certutil -hashfile config\mcf_conversation_map.tsv SHA256    # plain Windows
```

**Re-hash it whenever you ratify a change to the map, in the same commit.** The
`.sha256` is not swallowed by `/config/*conversation_map.tsv` — that pattern
ends at `.tsv`, so the fingerprint stays tracked with no negation rule needed.

Nothing checks this yet. A stale fingerprint is currently silent — it is an
audit trail you maintain, not a gate that maintains you.

---

## When one of these is missing

The failure modes differ, and only one of them is loud.

- **`local.json` missing, empty, or malformed** → `config._load` returns `{}`
  and **never raises**. Configuration silently falls back to
  `machines.json`'s values. This is deliberate (a broken overlay must not stop a
  scanner), but it means *a typo in `local.json` looks exactly like no
  `local.json` at all.* If a path setting seems to be ignored, validate the JSON
  before anything else.
- **`project_registry.json` missing at every location in the order above** →
  `resolve_registry_path` raises `FileNotFoundError` **loudly**, by design. It
  never validates against a silently-missing registry, because that would make
  every project id look unknown.
- **`mcf_conversation_map.tsv` missing** → the Curator's K-stages have no
  ratified join. `knowledge_index.py` and `match_claims.py` both default to
  `config/mcf_conversation_map.tsv`; the map is the join of record for that
  source (0040 clause 1), so its absence is not degraded operation, it is no
  operation.

The precedence for everything `config.py` resolves, lowest to highest:

```
machines.json["default"]  <  machines.json[host]  <  local.json["default"]  <  local.json[host]
```
