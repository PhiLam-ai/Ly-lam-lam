@echo off
setlocal
cd /d "%~dp0"

where node.exe >nul 2>&1
if errorlevel 1 (
  echo Khong tim thay Node.js.
  echo Hay cai Node.js LTS, sau do dong mo lai cua so nay.
  pause
  exit /b 1
)

node tools\start-windows-preview.cjs
if errorlevel 1 (
  echo.
  echo LÝ LÂM LAM chua khoi dong duoc. Hay doc loi o phia tren.
  pause
)
endlocal
