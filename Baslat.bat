@echo off
title WattCost HaYTooL Launcher
cd /d "%~dp0main"

:: 1. pythonw ile sessiz arka plan başlatma (Öncelikli)
where pythonw >nul 2>nul
if %ERRORLEVEL% equ 0 (
    start "" pythonw app.py %*
    exit
)

:: 2. pyw başlatıcı ile deneme
where pyw >nul 2>nul
if %ERRORLEVEL% equ 0 (
    start "" pyw app.py %*
    exit
)

:: 3. python ile başlatma (Konsollu yedek yol)
where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    start "" python app.py %*
    exit
)

:: 4. Hiçbiri bulunamazsa kullanıcıya net hata göster
echo ========================================================
echo [HATA] Sistemde Python bulunamadi!
echo Lutfen Python'in kurulu ve PATH'e ekli oldugundan emin olun.
echo ========================================================
pause
