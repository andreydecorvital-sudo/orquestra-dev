@echo off
setlocal
title Login ChatGPT - Codex CLI
echo.
echo ===== CODEX / CHATGPT - CODIGO DO APARELHO =====
echo Aguarde o Codex gerar um codigo de uso unico.
echo Quando aparecer, volte a janela Orquestra e confirme.
echo NAO compartilhe este codigo com outras pessoas.
echo.
where codex >nul 2>&1
if errorlevel 1 (
  echo [ERRO] Codex nao encontrado. Instale usando Configurar instalacao.
  goto :end
)
codex login --device-auth
if errorlevel 1 (
  echo.
  echo [ERRO] O Codex nao conseguiu iniciar ou concluir o login.
  echo Confira a mensagem acima; se preciso, habilite login por codigo na seguranca do ChatGPT.
) else (
  echo.
  echo [OK] Login do Codex finalizado.
)
:end
echo.
echo Esta janela permanece aberta para que possa conferir o resultado.
pause
