# Orquestra Hermes guided setup: no API billing, no cookies or private chat endpoints.
$ErrorActionPreference='Stop'
$root=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Write-Host 'ORQUESTRA DEV: HERMES + CODEX VIA CHROME' -ForegroundColor Cyan
if(-not (Get-Command hermes -ErrorAction SilentlyContinue)){
 Write-Host 'Hermes não instalado. Abra a página oficial e instale pelo Windows (sem WSL).' -ForegroundColor Yellow
 Start-Process 'https://hermes-agent.nousresearch.com/docs/getting-started/installation/'
 throw 'Instale Hermes e execute este assistente novamente.'
}
Write-Host '1/3 Autorização oficial via navegador; nenhuma senha será coletada pela Orquestra.'
& hermes auth add openai-codex --browser
if($LASTEXITCODE -ne 0){throw 'Autorização Codex não concluída. Tente novamente quando estiver pronto.'}
Write-Host '2/3 Escolha SOMENTE ChatGPT/Codex Subscription no seletor de modelos.'
Write-Host 'Não selecione OpenAI API Key, OpenRouter ou Nous Portal com créditos.'
& hermes model
if($LASTEXITCODE -ne 0){throw 'Seleção de modelo falhou; não vou continuar.'}
Write-Host '3/3 Preparando API apenas em 127.0.0.1:8642, com chave local privada.'
# Reuse this SAME process: the launcher's Process-only execution policy applies here.
# Do not spawn a second PowerShell process, which would lose that scope.
& (Join-Path $PSScriptRoot 'prepare-hermes-windows.ps1')
Write-Host 'Importante: Hermes por padrão possui terminal/arquivo. Vamos configurar ferramentas.'
Write-Host 'No menu hermes tools, selecione o perfil API server e DESATIVE todas as ferramentas.'
& hermes tools
if($LASTEXITCODE -ne 0){throw 'Ferramentas não verificadas. O adaptador continuará bloqueado.'}
Write-Host 'Concluído o assistente inicial.' -ForegroundColor Green
Write-Host 'Inicie Hermes em outro PowerShell: hermes gateway'
Write-Host 'Depois abra a Orquestra, cadastre projeto e executor.'
Write-Host 'Somente após parear e revisar o perfil, habilite allow_execution e allow_hermes_planning.'
Write-Host 'O conector bloqueia qualquer ferramenta ativa, provedor pago ou fallback.'
