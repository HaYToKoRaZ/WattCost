# ==============================================================================
# WattCost HaYTooL - Masaustu Uygulamasi (main Dali) Push Betigi
# ==============================================================================
$ErrorActionPreference = "Stop"
Write-Host "`n========================================================" -ForegroundColor Cyan
Write-Host " [WattCost HaYTooL] 'main' Dali Git Guncellemesi Baslatiliyor... " -ForegroundColor Cyan
Write-Host "========================================================`n" -ForegroundColor Cyan

# Calisma dizinine gec
$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $rootDir

# Git durumunu kontrol et
git checkout main 2>$null
if ($LASTEXITCODE -ne 0) {
    git checkout -B main
}

# 1. Main dali icin gerekli dosyalari ekle (websites/ klasoru haric)
Write-Host "[1/3] Dosyalar hazirlaniyor (main dali)..." -ForegroundColor Yellow
git add .agent/
git add .gitignore
git add Baslat.bat
git add push_app.ps1
git add push_websites.ps1
git add main/

# websites klasoru main dalinda izlenmemeli
git reset websites/ 2>$null

# Commit mesajini belirle
$commitMsg = $args[0]
if (-not $commitMsg) {
    $dateStr = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $commitMsg = "chore(app): WattCost HaYTooL guncellemesi ($dateStr)"
}

Write-Host "[2/3] Commit olusturuluyor: $commitMsg" -ForegroundColor Yellow
git commit -m "$commitMsg" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Degisiklik tespit edilmedi veya commit gerekmiyor." -ForegroundColor Green
}

# Remote'a gonder
Write-Host "[3/3] GitHub 'main' dalina gonderiliyor (origin main)..." -ForegroundColor Yellow
git push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n Tebrikler! 'main' dali basariyla GitHub'a pushlandi." -ForegroundColor Green
} else {
    Write-Host "`n[HATA] Push islemi basarisiz oldu. Lutfen internet/yetki ayarlarini kontrol edin." -ForegroundColor Red
}
