@echo off
setlocal
cd /d "%~dp0.."
powershell -NoProfile -File "%~dp0connect-hermes-windows.ps1"
if errorlevel 1 (
  echo.
  echo Assistente interrompido. Leia docs\HERMES-LOCAL.md para diagnosticar.
)
pause
