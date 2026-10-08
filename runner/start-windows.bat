@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% equ 0 (
  py -3 worker.py
) else (
  python worker.py
)
if errorlevel 1 pause
