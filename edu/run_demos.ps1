# Runs all Phase-1 demos and writes outputs into edu_out\...
# Forces Mod 6 to use a small file so sizes_bytes + the explanatory note appear.

# --- Locate shared venv Python (..\ .venv) ---
$repoRoot = Get-Location
$venvPy   = Join-Path (Split-Path -Parent $repoRoot) ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) { Write-Error "Python venv not found. Run .\edu\setup.ps1 first."; exit 1 }

# Path to this folder (edu)
$EDU = $PSScriptRoot

# -------------------
# Module 1
# -------------------
& $venvPy (Join-Path $EDU "mod1_measure_shapes.py") --eps 0.001 --n 20000

# -------------------
# Module 2
# -------------------
& $venvPy (Join-Path $EDU "mod2_surface_area.py") --box 1.2 --dx 0.02 --sigma 0.02

# -------------------
# Module 3  (need an image; synth one if none found)
# -------------------
$img = Get-ChildItem -Path $repoRoot -File -Include *.jpg,*.png -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $img) {
  $synthPng = Join-Path $repoRoot "edu_out\mod3\synth.png"
  New-Item -ItemType Directory -Force -Path (Split-Path $synthPng) | Out-Null
  $tmpPy = Join-Path $EDU "_tmp_make_synth.py"
  @"
from PIL import Image, ImageDraw
im = Image.new('L',(256,256), 80)
d  = ImageDraw.Draw(im); d.ellipse((40,40,216,216), fill=190)
im.save(r'$synthPng')
"@ | Set-Content -Encoding ascii $tmpPy
  & $venvPy $tmpPy
  Remove-Item $tmpPy -Force
  $img = Get-Item $synthPng
}
& $venvPy (Join-Path $EDU "mod3_satellite_classifier.py") --image ($img.FullName) --lambda 0.2 --steps 100 --tau 0.1

# -------------------
# Module 4  (need a FASTA; toy if none)
# -------------------
$fasta = Get-ChildItem -Path $repoRoot -File -Include *.fa,*.fasta -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $fasta) {
  $toyFa = Join-Path $repoRoot "edu_out\mod4\toy.fa"
  New-Item -ItemType Directory -Force -Path (Split-Path $toyFa) | Out-Null
  $lines = @(">toy")
  1..2000 | ForEach-Object { $lines += "GCGCGCATATAT" }
  Set-Content -Encoding ascii $toyFa $lines
  $fasta = Get-Item $toyFa
}
& $venvPy (Join-Path $EDU "mod4_dna_bmo.py") --fasta ($fasta.FullName) --win 1000

# -------------------
# Module 5
# -------------------
& $venvPy (Join-Path $EDU "mod5_chaos.py") --r 4.0 --N 20000 --k 3

# -------------------
# Module 6 — force a tiny file so sizes_bytes + explanatory note are present
# -------------------
$file = Join-Path $EDU "requirements.txt"
# Optional: override the "small file" threshold (bytes) via env var if you want:
# $env:EDU_SMALL_NOTE_THRESHOLD = "4096"
& $venvPy (Join-Path $EDU "mod6_info.py") --file ($file)

Write-Host "`nAll demos done. See edu_out\ for manifests and PNGs."
