# ==============================================================================
# WattCost HaYTooL - Web Sitesi (websites Dali) Push Betigi
# ==============================================================================
$ErrorActionPreference = "Stop"
Write-Host "`n========================================================" -ForegroundColor Cyan
Write-Host " [WattCost HaYTooL] 'websites' Dali Git Guncellemesi Baslatiliyor... " -ForegroundColor Cyan
Write-Host "========================================================`n" -ForegroundColor Cyan

# Calisma dizinine gec
$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $rootDir

# websites dalini kontrol et / gecis yap
git checkout websites 2>$null
if ($LASTEXITCODE -ne 0) {
    git checkout -B websites
}

# 1. Websites dali icin gerekli dosyalari ekle (main/ ve backup/ haric)
Write-Host "[1/3] Dosyalar hazirlaniyor (websites dali)..." -ForegroundColor Yellow
git add websites/
git add .gitignore
git add push_websites.ps1
git add push_app.ps1

# main klasoru websites dalinda izlenmemeli
git reset main/ 2>$null
git reset Baslat.bat 2>$null

# Commit mesajini belirle
$commitMsg = $args[0]
if (-not $commitMsg) {
    $dateStr = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $commitMsg = "chore(web): WattCost HaYTooL websites guncellemesi ($dateStr)"
}

Write-Host "[2/3] Commit olusturuluyor: $commitMsg" -ForegroundColor Yellow
git commit -m "$commitMsg" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Degisiklik tespit edilmedi veya commit gerekmiyor." -ForegroundColor Green
}

# Remote'a gonder
Write-Host "[3/3] GitHub 'websites' dalina gonderiliyor (origin websites)..." -ForegroundColor Yellow
git push -u origin websites

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n Tebrikler! 'websites' dali basariyla GitHub'a pushlandi." -ForegroundColor Green
} else {
    Write-Host "`n[HATA] Push islemi basarisiz oldu. Lutfen internet/yetki ayarlarini kontrol edin." -ForegroundColor Red
}

# Ana calisma ortami olarak tekrar main dalina don
Write-Host "`n Calisma dali olarak 'main' dalina donuluyor..." -ForegroundColor Gray
git checkout main 2>$null
