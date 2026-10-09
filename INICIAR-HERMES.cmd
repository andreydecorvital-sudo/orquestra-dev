@echo off
setlocal
if not exist "%~dp0runner\conectar-hermes-windows.cmd" (
  echo [ERRO] Pasta runner nao encontrada.
  echo Extraia o ZIP completo antes de executar este arquivo.
  pause
  exit /b 1
)
call "%~dp0runner\conectar-hermes-windows.cmd"
exit /b %ERRORLEVEL%
