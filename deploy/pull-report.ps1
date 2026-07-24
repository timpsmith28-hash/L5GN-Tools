<#
pull-report.ps1 -- fetch the knight's latest report + census back to this rig.

The mirror of push-exports.ps1. Both directions have keys now, so the knight no
longer has to be visited to be read: it builds its own census (`run.py census`)
and this pulls the result down and opens it locally.

Same conventions as its sibling, deliberately:
  * -WhatIf dry run,
  * everything that WILL transfer is listed, with sizes and ages, BEFORE anything
    transfers,
  * loud failure -- a missing file or a failed scp says so and sets a non-zero
    exit code; it never quietly pulls three of four files and reports success,
  * scp over the existing ssh alias. No new transport.

Lands in data\knight\ (gitignored, machine-local) and NOT in the repo root --
pulling the knight's report.html over this rig's own report.html would destroy
the local build, and the two are answers to different questions.

    powershell -File deploy\pull-report.ps1 -WhatIf    # dry-run: show what would come
    powershell -File deploy\pull-report.ps1            # pull + open
    powershell -File deploy\pull-report.ps1 -NoOpen
    powershell -File deploy\pull-report.ps1 -Remote l5gn-castle -RemoteRoot L5GN-Tools
#>
[CmdletBinding(SupportsShouldProcess = $true)]
param(
  [string]$Remote      = "l5gn-castle",
  [string]$RemoteRoot  = "L5GN-Tools",                       # home-relative on the knight
  [string]$Destination = (Join-Path $PSScriptRoot "..\data\knight"),
  [switch]$NoOpen
)
$ErrorActionPreference = "Stop"

# name -> remote path, home-relative. The report is the point; the census is the
# machine report behind it and is worth having beside it.
$wanted = [ordered]@{
  "report.html" = "$RemoteRoot/report.html"
  "census.json" = "$RemoteRoot/data/census.json"
  "estate.json" = "$RemoteRoot/data/estate.json"
}

Write-Host "pull-report: querying ${Remote} ..."

# One ssh round trip to find out what is actually there. Asking first is what
# makes the -WhatIf listing honest rather than a guess at what might exist.
$paths  = ($wanted.Values | ForEach-Object { "'$_'" }) -join " "
$probe  = "for f in $paths; do if [ -f `"`$f`" ]; then stat -c '%n|%s|%Y' `"`$f`"; else echo `"`$f|MISSING|0`"; fi; done"
$listing = ssh $Remote $probe
if ($LASTEXITCODE -ne 0) {
  throw "pull-report: ssh to ${Remote} FAILED (exit $LASTEXITCODE). Nothing pulled."
}

$now   = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$plan  = @()
$absent = @()
foreach ($line in $listing) {
  if (-not $line) { continue }
  $bits = $line.Split("|")
  $remotePath = $bits[0]
  $name = ($wanted.GetEnumerator() | Where-Object { $_.Value -eq $remotePath }).Key
  if ($bits[1] -eq "MISSING") { $absent += $name; continue }
  $plan += [pscustomobject]@{
    Name   = $name
    Remote = $remotePath
    MB     = [math]::Round([int64]$bits[1] / 1MB, 2)
    AgeHrs = [math]::Round(($now - [int64]$bits[2]) / 3600, 1)
  }
}

if ($plan.Count -eq 0) {
  throw ("pull-report: NOTHING to pull -- none of [{0}] exist on {1}:{2}. " +
         "Has 'python run.py census' / 'build' been run there?" -f
         (($wanted.Keys) -join ", "), $Remote, $RemoteRoot)
}

# List everything before moving a single byte.
Write-Host "pull-report: $($plan.Count) file(s) available on ${Remote}:"
$plan | ForEach-Object {
  Write-Host ("    {0,-12} {1,8} MB   {2,6} h old   ({3})" -f $_.Name, $_.MB, $_.AgeHrs, $_.Remote)
}
if ($absent.Count -gt 0) {
  Write-Warning "pull-report: NOT on the knight: $($absent -join ', ')"
}

# A stale report is the failure mode this whole pull exists to avoid, so say it
# out loud rather than letting a day-old page pass for today's state.
$stalest = ($plan | Sort-Object AgeHrs -Descending | Select-Object -First 1)
if ($stalest.AgeHrs -gt 24) {
  Write-Warning ("pull-report: the knight's {0} is {1} h old -- it may predate the " +
                 "state you are looking for. Run 'python run.py census' there first." -f
                 $stalest.Name, $stalest.AgeHrs)
}

# -WhatIf:$false deliberately. SupportsShouldProcess propagates -WhatIf to every
# cmdlet called here, so without this the dry run would skip the mkdir and then
# die on Resolve-Path -- a dry run that fails is not a dry run. An empty folder
# in this machine's own gitignored data area is not a side effect worth guarding.
New-Item -ItemType Directory -Force -Path $Destination -WhatIf:$false | Out-Null
$Destination = (Resolve-Path $Destination).Path

$pulled = 0
$failed = @()
foreach ($item in $plan) {
  $local = Join-Path $Destination $item.Name
  if ($PSCmdlet.ShouldProcess("${Remote}:$($item.Remote)", "scp -> $local")) {
    # .part then rename, same as push-exports: a half-pulled report must never
    # sit there looking like a whole one.
    scp "${Remote}:$($item.Remote)" "$local.part"
    if ($LASTEXITCODE -ne 0) {
      $failed += $item.Name
      Remove-Item -Force -ErrorAction SilentlyContinue "$local.part"
      continue
    }
    Move-Item -Force "$local.part" $local
    $pulled++
  }
}

if ($failed.Count -gt 0) {
  throw "pull-report: scp FAILED for: $($failed -join ', '). Pulled $pulled of $($plan.Count)."
}

if ($pulled -eq 0) {
  Write-Host "pull-report: -WhatIf -- nothing pulled."
  exit 0
}

Write-Host "pull-report: pulled $pulled file(s) -> $Destination"
$report = Join-Path $Destination "report.html"
if ($NoOpen) {
  Write-Host "pull-report: -NoOpen -- open it yourself: $report"
} elseif (Test-Path $report) {
  Write-Host "pull-report: opening $report"
  Invoke-Item $report
} else {
  Write-Warning "pull-report: no report.html came down -- nothing to open."
}
