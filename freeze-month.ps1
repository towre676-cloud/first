param(
  [string]$Month = "2019-04",
  [switch]$Push
)

$repo = Get-Location
$root = Split-Path -Parent $repo
$data = Join-Path $root "data"
$py   = Join-Path $root ".venv\Scripts\python.exe"

# venv + deps (only what we truly need)
if (-not (Test-Path $py)) {
  py -3 -m venv (Join-Path $root ".venv")
  & $py -m pip install --upgrade pip
  & (Join-Path $root ".venv\Scripts\pip.exe") install pandas pyarrow numpy networkx
}

# inputs
New-Item -ItemType Directory -Force -Path $data | Out-Null
$taxi = Join-Path $data ("yellow_{0}.parquet" -f $Month)
$rmsk = Join-Path $data "rmsk_hg38.txt.gz"
$snap = Join-Path $data "wiki-Vote.txt.gz"
if (-not (Test-Path $taxi)) { curl.exe -L -f -o $taxi ("https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_{0}.parquet" -f $Month) }
if (-not (Test-Path $rmsk)) { curl.exe -L -f -o $rmsk "https://hgdownload.cse.ucsc.edu/goldenPath/hg38/database/rmsk.txt.gz" }
if (-not (Test-Path $snap)) { curl.exe -L -f -o $snap "https://snap.stanford.edu/data/wiki-Vote.txt.gz" }

# run capsules (generalized)
New-Item -ItemType Directory -Force -Path ".\manifests" | Out-Null
& $py .\capsules_cli.py transition    --input $taxi --origin PULocationID --dest DOLocationID --stride 5 --lz-cap 500000 --out .\manifests\taxi_markov.json
& $py .\capsules_cli.py interval-bmo  --input $rmsk --chrom chr1 --win 100000 --out .\manifests\rmsk_chr1_bmo.json
& $py .\capsules_cli.py graph         --input $snap --n-max 400 --k-max 6 --seed 0 --out .\manifests\wiki_vote_trace.json

# package + verify
$env:MONTH = $Month
$zipline = & $py .\package_from_manifests.py
$zip = ($zipline -split '\s+')[1]
& $py .\verify_zip.py $zip

# commit, tag, (optional) push
$bundle = (Get-Content .\manifests\provenance.json | ConvertFrom-Json).bundle_sha256
git add .\manifests\*.json; git add $zip
git commit -m ("Freeze: TLC="+$Month+", bundle="+$bundle)
git tag -a ("freeze-"+$Month+"-"+$bundle.Substring(0,12)) -m ("bundle="+$bundle)
git tag --list
if ($Push) { git push -u origin main; git push --tags }
