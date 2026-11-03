# WattCost HaYTooL - Kok Dizin 'websites' Dali Push Calistiricisi
$script = Join-Path $PSScriptRoot ".agents\scripts\push_websites.ps1"
if (Test-Path $script) {
    & $script @args
} else {
    Write-Host "[HATA] .agents/scripts/push_websites.ps1 betigi bulunamadi!" -ForegroundColor Red
}
