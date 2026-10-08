@echo off
setlocal
cd /d "%~dp0.."
if not exist "gateway\config.json" (
 echo Copie gateway\config.example.json para gateway\config.json e configure o projeto.
 exit /b 1
)
if "%ORQ_LOCAL_TOKEN%"=="" (
 echo Configure ORQ_LOCAL_TOKEN na sessao local com 32+ caracteres antes de iniciar.
 exit /b 1
)
python -m gateway.server
