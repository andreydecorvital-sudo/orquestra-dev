@echo off
setlocal
cd /d "%~dp0.."
if not exist "runner\agent-worker.json" (
  echo Copie runner\agent-worker.example.json para runner\agent-worker.json e configure o pareamento.
  pause
  exit /b 2
)
where python >nul 2>&1
if errorlevel 1 (
  echo Python nao encontrado. Instale Python 3.10+.
  pause
  exit /b 1
)
python -m runner.agent_worker
pause
