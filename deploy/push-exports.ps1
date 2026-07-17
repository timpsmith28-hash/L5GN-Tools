<#
push-exports.ps1 -- ship chat-export zips from this rig to the knight drop zone.

Uses the key-based ssh alias (no password). Uploads each zip atomically
(<name>.part -> rename) so a watcher never sees a partial file, then touches a
.ingest-request trigger last -- the knight's chronicler-ingest.path unit reacts
to that and runs `run.py ingest`. Processed zips are moved to a local _pushed/
folder so they are never re-sent.

Supports -WhatIf: preview exactly which zips would be sent without sending them.

    powershell -File deploy\push-exports.ps1 -WhatIf     # dry-run: show what would go
    powershell -File deploy\push-exports.ps1             # actually send
    powershell -File deploy\push-exports.ps1 -Source "D:\curated_exports"
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
  [string]$Source   = "$env:USERPROFILE\Downloads",
  [string]$Remote   = "l5gn-castle",
  [string]$DropZone = "vault/chat_threads/zip_downloads",   # home-relative on the knight
  [string]$Archive  = "$env:USERPROFILE\Downloads\_pushed"
)
$ErrorActionPreference = "Stop"

$patterns = @("data-*.zip", "takeout-*.zip")
$zips = foreach ($p in $patterns) {
  Get-ChildItem -Path $Source -Filter $p -File -ErrorAction SilentlyContinue
}
if (-not $zips) { Write-Host "push-exports: no export zips in $Source"; exit 0 }

Write-Host "push-exports: $($zips.Count) zip(s) matched in ${Source}:"
$zips | ForEach-Object { Write-Host "    $($_.Name)  ($([math]::Round($_.Length/1MB,1)) MB)" }

$sent = 0
foreach ($z in $zips) {
  $name = $z.Name
  if ($PSCmdlet.ShouldProcess("${Remote}:${DropZone}/${name}", "upload + archive")) {
    scp $z.FullName "${Remote}:${DropZone}/${name}.part"
    ssh $Remote "mkdir -p '$DropZone'; mv '$DropZone/$name.part' '$DropZone/$name'"   # atomic arrival
    New-Item -ItemType Directory -Force -Path $Archive | Out-Null
    Move-Item -Force $z.FullName (Join-Path $Archive $name)
    $sent++
  }
}

# Fire the trigger LAST so the knight only ingests once everything has landed.
if ($sent -gt 0 -and $PSCmdlet.ShouldProcess("${Remote}:${DropZone}/.ingest-request", "touch trigger")) {
  ssh $Remote "touch '$DropZone/.ingest-request'"
  Write-Host "push-exports: shipped $sent zip(s); knight will auto-ingest."
} elseif ($sent -eq 0) {
  Write-Host "push-exports: -WhatIf -- nothing sent."
}
