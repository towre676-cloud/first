# Creates/updates shared venv one level up (..\ .venv) and installs requirements
$root = Split-Path -Parent (Get-Location)
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
  py -3 -m venv (Join-Path $root ".venv")
  & $py -m pip install --upgrade pip
}
& (Join-Path $root ".venv\Scripts\pip.exe") install -r .\edu\requirements.txt
