param()
$ErrorActionPreference="Stop"

# repo root = ..\.. from frontend\tools
$repo     = (Get-Item $PSScriptRoot).Parent.Parent.FullName
$frontend = (Get-Item $PSScriptRoot).Parent.FullName

$discoverSrc  = Join-Path $repo "discover"
$discoverDest = Join-Path $frontend "public\discover"

# prefer claims_all.ndjson, else claims.ndjson
$claimsSrc = @(
  (Join-Path $repo "claims_all.ndjson"),
  (Join-Path $repo "claims.ndjson")
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $claimsSrc) { throw "No claims file at repo root (claims_all.ndjson or claims.ndjson)." }

$claimsDest = Join-Path $frontend "public\claims_all.ndjson"

New-Item -ItemType Directory -Force (Join-Path $frontend "public") | Out-Null

# junction for discover/
if (Test-Path $discoverDest) { Remove-Item -Recurse -Force $discoverDest }
cmd /c mklink /J "$discoverDest" "$discoverSrc" | Out-Null

# claims hardlink if same drive, else copy
if (Test-Path $claimsDest) { Remove-Item -Force $claimsDest }
$srcDrive = ([IO.Path]::GetPathRoot($claimsSrc)).ToLower()
$dstDrive = ([IO.Path]::GetPathRoot($claimsDest)).ToLower()
if ($srcDrive -eq $dstDrive) {
  cmd /c mklink /H "$claimsDest" "$claimsSrc" | Out-Null
  if (-not (Test-Path $claimsDest)) { Copy-Item $claimsSrc $claimsDest -Force }
} else {
  Copy-Item $claimsSrc $claimsDest -Force
}

"linked: $discoverDest -> $discoverSrc"
"linked: $claimsDest  -> $claimsSrc"