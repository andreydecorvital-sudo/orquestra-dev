@echo off
setlocal
cd /d "%~dp0.." || (
  echo [ERRO] Nao consegui abrir a pasta principal da Orquestra.
  pause
  exit /b 1
)
echo.
echo [ORQUESTRA] Iniciando Hermes...
echo A politica do PowerShell sera liberada SOMENTE neste processo.
echo Nenhuma configuracao permanente do Windows sera alterada.
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0connect-hermes-windows.ps1"
set "result=%ERRORLEVEL%"
if not "%result%"=="0" (
  echo.
  echo [ERRO] Assistente nao concluido ^(codigo %result%^).
  echo Se a politica for imposta pelo administrador, o Windows podera bloquear mesmo assim.
  echo Consulte docs\HERMES-LOCAL.md.
)
echo.
pause
exit /b %result%
