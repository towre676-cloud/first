# Repo snapshot
$ErrorActionPreference = "Stop"
"== STATUS =="; git status -sb
"`n== COMMITS (last 12) =="; git log --oneline --graph --decorate -n 12
"`n== TAGS (freeze-2019-*) =="; git tag --list "freeze-2019-*" | sort
"`n== FREEZE ZIPs =="; Get-ChildItem . -Filter "freeze_*.zip" | Format-Table -Auto Length, Name | Out-String
"`n== MANIFESTS =="; Get-ChildItem .\manifests\*.json | Format-Table -Auto Length, Name | Out-String
"`n== PROVENANCE =="; (Get-Content .\manifests\provenance.json | ConvertFrom-Json |
  Select-Object bundle_sha256, timestamp, packages) | Format-List | Out-String
"`n== EDU OUTPUTS =="; Get-ChildItem .\edu_out -Recurse -File | Format-Table -Auto Length, FullName | Out-String
