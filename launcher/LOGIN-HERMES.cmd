@echo off
setlocal
title Login ChatGPT - Hermes Nagi
echo.
echo ===== HERMES NAGI / CHATGPT - CODIGO DO APARELHO =====
echo Aguarde o Hermes gerar um codigo de uso unico.
echo Quando aparecer, volte a janela Orquestra e confirme.
echo NAO compartilhe este codigo com outras pessoas.
echo.
where hermes >nul 2>&1
if errorlevel 1 (
  echo [ERRO] Hermes nao encontrado. Instale usando Configurar instalacao.
  goto :end
)
hermes -p nagi auth add openai-codex --type oauth
if errorlevel 1 (
  echo.
  echo [ERRO] O Hermes nao conseguiu iniciar ou concluir o login.
  echo Confira a mensagem acima; nenhum navegador alternativo sera aberto.
) else (
  echo.
  echo [OK] Login do Hermes finalizado. Retorne a Orquestra.
)
:end
echo.
echo Esta janela permanece aberta para que possa conferir o resultado.
pause
