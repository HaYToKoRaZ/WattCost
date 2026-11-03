# WattCost HaYTooL - Kok Dizin Yedekleme Calistiricisi
$script = Join-Path $PSScriptRoot ".agents\scripts\backup.ps1"
if (Test-Path $script) {
    & $script @args
} else {
    Write-Host "[HATA] .agents/scripts/backup.ps1 betigi bulunamadi!" -ForegroundColor Red
}
