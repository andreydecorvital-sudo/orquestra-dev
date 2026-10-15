@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0launcher\OrquestraMenu.ps1" (
  echo [ERRO] Extraia o ZIP inteiro antes de abrir a Orquestra.
  pause
  exit /b 1
)
if exist "%~dp0launcher\OrquestraUpdater.ps1" (
  powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0launcher\OrquestraUpdater.ps1" -Quiet
  set "ORQ_UPDATE_EXIT=%ERRORLEVEL%"
  if "%ORQ_UPDATE_EXIT%"=="1" echo [AVISO] Atualizacao indisponivel. A Orquestra abrira com os arquivos locais.
)
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0launcher\OrquestraMenu.ps1"
if errorlevel 1 (
  echo [ERRO] Falha ao abrir a Orquestra. Verifique o PowerShell.
  pause
  exit /b 1
)
exit /b 0
