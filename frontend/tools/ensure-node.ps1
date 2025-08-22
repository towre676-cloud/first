param([string[]]$TryVersions = @("22.11.0","22.10.0","22.9.0","20.17.0"))

$ErrorActionPreference = "Stop"

function Get-Node($ver) {
  $zip  = Join-Path $PSScriptRoot "..\vendor\node-v$ver-win-x64.zip"
  $dir  = Join-Path $PSScriptRoot "..\vendor\node-v$ver-win-x64"
  $uri  = "https://nodejs.org/dist/v$ver/node-v$ver-win-x64.zip"
  if (!(Test-Path $dir)) {
    if (!(Test-Path $zip)) {
      Write-Host "Downloading Node v$ver ..."
      Invoke-WebRequest -UseBasicParsing -Uri $uri -OutFile $zip
    }
    Write-Host "Extracting $zip ..."
    Expand-Archive -Path $zip -DestinationPath (Split-Path $zip) -Force
  }
  return $dir
}

$nodeDir = $null
foreach ($v in $TryVersions) {
  try { $nodeDir = Get-Node $v; break } catch { Write-Warning "v$v failed: $($_.Exception.Message)" }
}
if (-not $nodeDir) { throw "Could not download any Node versions from the candidate list." }

# Create wrapper commands in tools/ so you can run .\tools\node.cmd and .\tools\npm.cmd from anywhere
$nodeExe = Join-Path $nodeDir "node.exe"
$npmCmd  = Join-Path $nodeDir "npm.cmd"

"@echo off
""$nodeExe"" %*" | Set-Content -Encoding ASCII (Join-Path $PSScriptRoot "node.cmd")

"@echo off
""$npmCmd"" %*" | Set-Content -Encoding ASCII (Join-Path $PSScriptRoot "npm.cmd")

Write-Host "Node ready at $nodeDir"
& "$nodeExe" -v
& "$npmCmd" -v
