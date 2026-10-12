@echo off
setlocal
cd /d "%~dp0"
title LÝ LÂM LAM - V311
where node >nul 2>nul
if errorlevel 1 (
  echo [LOI] May chua cai Node.js hoac Windows chua nhan lenh node.
  echo Cai Node.js ban LTS tu trang chinh thuc, sau do dong va mo lai cua so nay.
  pause
  exit /b 1
)
echo.
echo ========================================
echo  LY LAM LAM - KIEM TRA TRUOC KHI CHAY
echo ========================================
echo.
node tools\verify-startup.cjs
if errorlevel 1 (
  echo.
  echo [DUNG] Kiem tra that bai. Ung dung chua duoc khoi dong.
  pause
  exit /b 1
)
echo.
echo [PASS] Kiem tra tu dong hoan tat. Dang mo may chu xem truoc...
echo Khi URL hien ra ben duoi, giu cua so nay mo va mo URL do trong Chrome.
echo Nhan Ctrl+C trong cua so nay de dung may chu.
echo.
node tools\start-preview.cjs --local-three --open-browser
if errorlevel 1 (
  echo.
  echo [LOI] Khong the mo may chu xem truoc. Kiem tra thong bao phia tren.
  pause
  exit /b 1
)
endlocal
