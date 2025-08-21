param([string[]]$Months = @("2019-04","2019-05","2019-06"), [switch]$Push)

foreach($m in $Months){
  Write-Host "`n=== FREEZE $m ==="
  .\freeze-month.ps1 -Month $m
}
if ($Push){ git push -u origin main; git push --tags }
