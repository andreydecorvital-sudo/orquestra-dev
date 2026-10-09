# Orquestra Dev: local Windows setup; NO paid provider APIs or cloud credentials.
# Run from the checked-out Orquestra Dev repository.
param([Parameter(Mandatory = $true)][string]$ConfigFile)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$source = (Resolve-Path -LiteralPath $ConfigFile).Path
$dest = Join-Path $PSScriptRoot 'agent-worker.json'

if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Instale Git para Windows antes de continuar.' }
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw 'Instale Python 3.10+ antes de continuar.' }
if (Test-Path -LiteralPath $dest) { throw 'Já existe um pareamento. Não sobrescrever credencial ativa.' }

$inputObject = Get-Content -LiteralPath $source -Raw -Encoding UTF8 | ConvertFrom-Json
if ($inputObject.supabase_url -ne 'https://kekxcvcgyexcbleifffq.supabase.co') {
  throw 'Este instalador somente aceita o Supabase dedicado da Orquestra.'
}
if ($inputObject.node_id -notmatch '^[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}$') { throw 'ID de dispositivo inválido.' }
if ($inputObject.node_secret -notmatch '^[0-9a-fA-F]{64}$') { throw 'Segredo de dispositivo inválido.' }
if (-not $inputObject.projects -or $inputObject.projects.PSObject.Properties.Count -ne 1) {
  throw 'O arquivo deve autorizar exatamente um projeto Git.'
}
$project = @($inputObject.projects.PSObject.Properties)[0]
if ($project.Name -notmatch '^[0-9a-fA-F-]{36}$') { throw 'ID remoto do projeto inválido.' }
if ($project.Value.slug -notmatch '^[a-z][a-z0-9_-]{1,45}$') { throw 'Slug inválido.' }
$gitPath = [string]$project.Value.path
if (-not (Test-Path -LiteralPath (Join-Path $gitPath '.git'))) {
  throw 'A pasta Git não existe no Windows. Clone primeiro o repositório informado no painel.'
}
if (-not (Get-Command icacls.exe -ErrorAction SilentlyContinue)) { throw 'Proteção ACL do Windows indisponível.' }

# Rebuild an allowlisted config; force read-only diagnostics at first launch.
$conf = [ordered]@{
  supabase_url='https://kekxcvcgyexcbleifffq.supabase.co'
  node_id=[string]$inputObject.node_id
  node_secret=[string]$inputObject.node_secret
  allow_execution=$false
  poll_seconds=25
  projects=@{ $project.Name = @{ slug=[string]$project.Value.slug; path=$gitPath } }
}
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($dest,($conf|ConvertTo-Json -Depth 8),$utf8NoBom)

# Restrict the long-lived device credential to the current user + system.
$sid=[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$ruleUser='*'+$sid+':(F)'
& icacls.exe $dest '/inheritance:r' '/grant:r' $ruleUser 'SYSTEM:(F)' 1>$null 2>$null
if ($LASTEXITCODE -ne 0) {
  Remove-Item -LiteralPath $dest -Force
  throw 'Não foi possível proteger as permissões do segredo local.'
}

Write-Host 'Pareamento local pronto (diagnóstico somente leitura).' -ForegroundColor Green
Write-Host 'Verifique login oficial: codex login status / claude auth status'
Write-Host 'Para executar missões com IA, autentique as CLIs e altere allow_execution manualmente para true.'
Write-Host 'Inicie com: python -m runner.agent_worker'
Write-Host 'Apague a cópia baixada do JSON após garantir que o pareamento local funciona.'
