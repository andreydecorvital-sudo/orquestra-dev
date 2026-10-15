@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if %errorlevel% equ 0 (
  py -3 -m cli.orquestra %*
) else (
  python -m cli.orquestra %*
)
exit /b %errorlevel%
