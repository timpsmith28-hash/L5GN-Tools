# Runbook — bundle the WizForge program repo on the work rig, carry it home, mirror it here

Produce git bundles of **WizForgeAnalytics** and every submodule beneath it on
the work rig, verify them there, carry them across by hand, and restore them
into containment on the gaming rig — replacing whatever mirror is already
held.

Steps are marked **▸ WORK** (`10280L`), **▸ CARRY**, or **▸ GAMING**
(`LucasGoonPC`). Rig commands are PowerShell.

**Authorised by DECISIONS 0051 clause 1(b)** — the repo mirror is replaced
whole, on demand, and never accumulated. That clause carries three conditions
and this runbook is mostly the act of meeting them. Clauses 2–6 apply
throughout at full strength.

---

## Before you start — the three conditions, checked not felt

**1. There is a stated reason.** The work side has asked the personal side for
something that requires reading the repo. Write the request down in the
manifest at Step 4 before you run anything.

**If you cannot name the request, stop.** This is not a schedule and must not
become one. A mirror taken because it has been a while is a sync, and 0036
stood the standing channel down. 0051's own falsifier is a count of refreshes
taken without a request — the failure looks like being organised, which is why
it needs checking rather than feeling.

**2. There is somewhere for it to land.** The declared path under 0051 clause
2, outside every scanner root. Confirmed at Step 6.

**3. You are prepared to delete the current mirror.** Landing a new one
removes the old one and everything cloned from it, as one act (Step 10). If
you are not ready to do that today, you are not ready to take a bundle today.

---

## Host and path map

| | |
|---|---|
| Work rig | `10280L`, program repo under the MCF root |
| Gaming rig | `LucasGoonPC`, corpus under the 0051 declared path |
| Program repo | `WizForgeAnalytics` — the program layer, not one of the seven projects |
| Submodule | `sf-data-service` — a project in its own right, nested one level in |

**Do not hardcode the MCF root from memory, and do not trust this repo's copy
of it.** `config/local.json`'s `10280L` entry says `D:/Work/Github/MCF`, while
the work rig's own `2026-08-23` baseline reports its roots at
`C:\Users\tim.smith\Github\MCF`. One of them is stale, and since `local.json`
is authored on the gaming rig and travels by hand, the gaming rig's copy is
the likelier suspect. Ask the machine:

```powershell
python run.py config          # on the work rig, in its own L5GN-Tools clone
```

Take the MCF root from that output. If it disagrees with `local.json`, that is
a second finding worth fixing separately — not something to work around here.

---

## Step 0 ▸ WORK — establish the state you are about to freeze

A bundle records commits, never a working tree. A bundle taken over a dirty
tree is a bundle of a moment nobody can name afterwards.

```powershell
$MCF  = "<root from run.py config>"
$WFA  = "$MCF\WizForgeAnalytics"
$DATE = Get-Date -Format "yyyy-MM-dd"
$OUT  = "$HOME\Desktop\wizforge-mirror-$DATE"
New-Item -ItemType Directory -Path $OUT -Force | Out-Null

git -C $WFA status --porcelain
git -C $WFA submodule status
git -C $WFA rev-parse HEAD
```

**Verify:** `status --porcelain` prints **nothing**. `submodule status` prints
one line per submodule, each starting with a space — not `-` (uninitialised)
and not `+` (checked out away from the recorded pointer).

A `+` is the case that quietly breaks everything downstream: the superproject
records one commit and the submodule is sitting on another, so the pointer you
bundle and the code you bundle disagree. Resolve it on this rig before going
further.

**Record the submodule pointers now** — they are what Step 9 proves.

---

## Step 1 ▸ WORK — bundle the superproject

```powershell
git -C $WFA bundle create "$OUT\WizForgeAnalytics-$DATE.bundle" --all
```

**`--all` is load-bearing.** `git bundle create <file> HEAD` carries one ref
and silently drops every other branch and tag. You will not notice until you
need one.

---

## Step 2 ▸ WORK — bundle every submodule, enumerated not assumed

There is one submodule today. Enumerate anyway — a second one added on the
work rig would otherwise be missed in silence, and this runbook is meant to
survive that.

```powershell
git -C $WFA submodule foreach --quiet 'echo $displaypath'
```

For each path printed:

```powershell
git -C "$WFA\sf-data-service" bundle create "$OUT\sf-data-service-$DATE.bundle" --all
```

---

## Step 3 ▸ WORK — verify by restoring, on the machine that can still fix it

`git bundle verify` checks the bundle is well-formed and names the commits it
needs to already have. It does **not** check that the superproject's recorded
pointer is reachable inside the submodule bundle, which is the failure that
matters.

So restore into a scratch directory and prove it end to end, here, where a
broken bundle can still be re-taken:

```powershell
git bundle verify "$OUT\WizForgeAnalytics-$DATE.bundle"
git bundle verify "$OUT\sf-data-service-$DATE.bundle"

$T = "$env:TEMP\mirror-check-$DATE"
Remove-Item -Recurse -Force $T -ErrorAction SilentlyContinue
git clone "$OUT\WizForgeAnalytics-$DATE.bundle" $T
git -C $T remote remove origin

# the pointer the superproject recorded, out of the restored clone
$PTR = (git -C $T ls-tree HEAD sf-data-service) -split '\s+' | Select-Object -Index 2
$PTR

# does the SUBMODULE bundle actually contain that commit?
$TS = "$env:TEMP\mirror-check-sub-$DATE"
Remove-Item -Recurse -Force $TS -ErrorAction SilentlyContinue
git clone "$OUT\sf-data-service-$DATE.bundle" $TS
git -C $TS cat-file -t $PTR
```

**Verify:** both `bundle verify` print `The bundle records a complete
history`. The last command prints `commit`. Anything else — `Not a valid
object name` above all — means the pointer commit is not in the submodule
bundle, the mirror would be unrestorable, and Step 2 needs re-running with the
submodule's refs sorted out first.

Then clean up the scratch clones:

```powershell
Remove-Item -Recurse -Force $T, $TS
```

---

## Step 4 ▸ WORK — write the manifest, including the reason

The manifest is what makes the mirror auditable later and it is the only place
the reason for this run is recorded.

```powershell
@"
# WizForge mirror — $DATE

**Taken on:** 10280L
**Reason:** <the request from the work side that required reading the repo>
**Authorised by:** DECISIONS 0051 clause 1(b)

| artefact | HEAD | sha256 |
|---|---|---|
"@ | Set-Content "$OUT\MANIFEST.md"

Get-ChildItem "$OUT\*.bundle" | ForEach-Object {
  "| $($_.Name) | | $((Get-FileHash $_.FullName -Algorithm SHA256).Hash) |"
} | Add-Content "$OUT\MANIFEST.md"

git -C $WFA rev-parse HEAD          | Add-Content "$OUT\MANIFEST.md"
git -C $WFA submodule status        | Add-Content "$OUT\MANIFEST.md"
```

Fill in the **Reason** line by hand. A manifest whose reason reads "refresh"
has not met condition 1.

---

## Step 5 ▸ CARRY — by hand, and the medium is a carrier too

No script, no automation, no remote. Whatever you carry this on holds the
content 0051 clause 4 names as the highest-risk in the pack —
`sf-data-service`'s commit metadata carries an employer email address, and its
`logs/sf_service_*.jsonl` service logs travel inside the bundle. The stick,
the share, the download folder: each is a copy until it is wiped, and none of
them is inside the declared path.

Wipe the source directory on the work rig once the transfer is confirmed.

---

## Step 6 ▸ GAMING — confirm the landing site is outside every scanner root

Before anything is written:

```powershell
cd C:\Users\timps\Documents\GitHub\L5GN-Tools
python run.py config
```

**Verify:** the `roots` printed do **not** contain the declared corpus path.
The gaming rig's roots are `…\GitHub\L5GN` and the toolkit itself — not
`…\GitHub` — so a corpus sitting directly under `GitHub\` is outside them.
Confirm that rather than assuming it, because a root added since the last time
you looked is exactly how clause 2 gets broken without anyone deciding to.

**Also check for a stray derivative.** `GitHub\WizForgeAnalytics\` exists on
this rig as a sibling of `GitHub\WizForge\`. If that is an unpacked clone from
a previous mirror, it is a derivative living outside the declared path, and
0051 clause 3 says it should not be — that is the entry's own "what would show
this wrong", found. Fold it into the declared path or delete it before
continuing.

---

## Step 7 ▸ GAMING — prove what arrived is what left

```powershell
Get-FileHash *.bundle -Algorithm SHA256
git bundle verify .\WizForgeAnalytics-<date>.bundle
```

**Verify:** each hash matches `MANIFEST.md` exactly. A mismatch is a truncated
transfer — re-carry it, do not clone past it.

**Do not check this by reading files through a sandbox mount.** The mount
serves stale, byte-truncated content deterministically and without error
(`TOOLKIT_notes_2026-08-23` §4), so a second read confirms a false answer
rather than catching it. Hash on Windows, and for anything about what git
holds, ask git — it is the only authority for that question.

---

## Step 8 ▸ GAMING — restore, and cut the return path

```powershell
git clone .\WizForgeAnalytics-<date>.bundle WizForgeAnalytics
cd WizForgeAnalytics
git remote remove origin
```

**`git remote remove origin` is not tidiness.** A clone from a bundle records
the bundle file as its origin; leaving it means a `git fetch` here can reach
back into the corpus, and the habit of a repo that can be pulled is the first
step back toward the standing channel 0036 stood down. 0051 clause 1(b)'s
third condition is one-directional transport, and this line is where it is
enforced rather than intended.

The submodule cannot resolve its declared URL — that URL points at the work
rig or a remote neither of which exists here. Point it at the local bundle:

```powershell
git config submodule.sf-data-service.url "<full path>\sf-data-service-<date>.bundle"
git submodule update --init
git config --unset submodule.sf-data-service.url
```

This is the step most likely to trip, and the error it gives when skipped
(`repository ... does not exist`) reads like a missing file rather than a
missing configuration.

---

## Step 9 ▸ GAMING — prove the pointer survived

```powershell
git submodule status
```

**Verify:** the sha matches the pointer recorded in `MANIFEST.md`, and the
line begins with a **space** — not `-` (never initialised) and not `+`
(checked out somewhere else). This is the one check that proves the mirror is
a faithful restoration rather than two repos that happen to be nearby.

---

## Step 10 ▸ GAMING — replace, as one act

0051 clause 1(b): exactly one mirror exists at any moment.

```powershell
Remove-Item -Recurse -Force <previous clone>, <previous bundles>
```

Delete the previous clone, the previous bundles, and anything derived from
them, now — not "soon". The entry's second falsifier is a count of mirrors
held simultaneously, and the answer is one, always, by construction. Two means
"replaced whole" was aspirational.

Record in the new `MANIFEST.md` what was removed and on what date.

---

## Step 11 ▸ GAMING — declare the gap

0051 clause 6: a scanner that skips this path says so in its output.

```powershell
cd C:\Users\timps\Documents\GitHub\L5GN-Tools
python run.py build
```

**Verify:** the estate report names the omitted directory. A report that
silently omits a directory inside its own root is a confident wrong picture,
which is the thing INTENT §5 refuses everywhere else. If it does not say so,
that is a toolkit gap to brief, not something to note and move past.

---

## Order at a glance

0. WORK → clean tree, submodule pointers recorded
1. WORK → bundle the superproject `--all`
2. WORK → bundle each submodule, enumerated
3. WORK → `bundle verify` **and** restore-and-check the pointer resolves
4. WORK → `MANIFEST.md`, with the reason written by hand
5. CARRY → by hand; wipe the source and the medium after
6. GAMING → confirm the landing site is outside every scanner root
7. GAMING → hashes match; verify with git, never through a mount
8. GAMING → clone, **remove origin**, point the submodule at its bundle
9. GAMING → `submodule status` matches the manifest
10. GAMING → delete the previous mirror, as one act
11. GAMING → rebuild and confirm the omission is declared

## Gotchas

- **`--all`, or you silently ship one branch.**
- **A bundle is an object store, not a folder.** It cannot be browsed, grepped
  or partially extracted; the only way to see inside is to clone it.
- **A dirty tree bundles the last commit**, not what you were looking at.
- **You cannot exclude the service logs.** They are tracked history, so
  removing them means rewriting it — which breaks the pointer match Step 9
  depends on and produces a mirror that is no longer the repo. They travel, or
  the mirror does not. 0051 clause 4 names them for exactly this reason: so
  they are checked rather than assumed, not so they can be filtered.
- **The mirror grows even though the artefact count does not.** Each refresh
  carries every log written since the last one. One file is not less content.
- **Never run plain git against a mounted Windows repo from a sandbox**
  (0052 clause 4).

## Out of scope

- **The post-migration conversation export.** 0051 clause 1(a) authorises one
  further export so the new tenant's shape can be checked against the old, and
  it is a different artefact with different handling — exports accumulate,
  mirrors replace. It wants its own runbook, not a step here.
- **Anything reading the mirror.** This document lands it inside containment
  and stops. What may be derived from it is clause 3, and where those
  derivatives may go is clause 5.
- **Any remote.** When the BitBucket licence lands, a sanctioned remote is a
  different mechanism with different rulings, and adopting it is a decision,
  not a migration of this runbook.
