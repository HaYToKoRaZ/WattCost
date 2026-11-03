# WattCost HaYTooL - Kok Dizin Derleme Calistiricisi
$script = Join-Path $PSScriptRoot ".agents\scripts\build.ps1"
if (Test-Path $script) {
    & $script @args
} else {
    Write-Host "[HATA] .agents/scripts/build.ps1 betigi bulunamadi!" -ForegroundColor Red
}
