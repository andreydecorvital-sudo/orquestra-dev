# Read-only backup of the shared Chatbot DB; run only on your Windows PC.
# Requires Supabase CLI authenticated, Docker Desktop running and DB access.
# Never upload generated SQL files to GitHub or ChatGPT.
[CmdletBinding()]
param([string]$OutputRoot = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Orquestra-Backups'))
$ErrorActionPreference = 'Stop'
$ref = 'ydyzjpcmavqffdazteib'
$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$target = Join-Path $OutputRoot ("chatbot-pre-orquestra-" + $timestamp)
if (-not (Get-Command supabase -ErrorAction SilentlyContinue)) {
 throw 'Instale o Supabase CLI oficial, depois execute supabase login.'
}
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
 throw 'Instale e inicie Docker Desktop para o export.'
}
& docker info --format '{{.ServerVersion}}' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Docker Desktop nao esta ativo.' }
if (Test-Path -LiteralPath $target) { throw 'Pasta ja existe. Nada foi sobrescrito.' }
New-Item -ItemType Directory -Path $target -Force | Out-Null
$workspace = Join-Path $target 'supabase-local-workspace'
New-Item -ItemType Directory -Path $workspace -Force | Out-Null
Write-Host 'Copiando schema e dados para seu computador. Nenhuma alteracao remota sera executada.'
Write-Host 'IMPORTANTE: Os arquivos incluem CRM e dados de autenticacao sensiveis.'
Write-Host 'Mantenha os arquivos em disco criptografado, nunca em um repositorio!'
try {
 Push-Location $workspace
 & supabase init --yes
 if ($LASTEXITCODE -ne 0) { throw 'Falha em supabase init; backup nao foi feito.' }
 & supabase link --project-ref $ref
 if ($LASTEXITCODE -ne 0) { throw 'Falha ao vincular ao Chatbot. Backup nao foi feito.' }
 $exports = @(
  @{ File = 'public-schema.sql'; Args = @('--linked','--file',(Join-Path $target 'public-schema.sql')) },
  @{ File = 'public-data.sql'; Args = @('--linked','--data-only','--file',(Join-Path $target 'public-data.sql')) },
  @{ File = 'managed-schema.sql'; Args = @('--linked','--schema','auth,storage','--file',(Join-Path $target 'managed-schema.sql')) },
  @{ File = 'managed-data.sql'; Args = @('--linked','--schema','auth,storage','--data-only','--file',(Join-Path $target 'managed-data.sql')) }
 )
 foreach ($export in $exports) {
  Write-Host ('Exportando ' + $export.File)
  $commandArgs = @('db','dump') + @($export.Args)
  & supabase @commandArgs
  if ($LASTEXITCODE -ne 0) { throw ('Falha em ' + $export.File + '. Backup incompleto; nao aplique migracao.') }
  $file = Join-Path $target $export.File
  if (-not (Test-Path -LiteralPath $file) -or (Get-Item -LiteralPath $file).Length -lt 20) {
   throw ('Arquivo vazio/invalido: ' + $export.File + '. Nao aplique migracao.')
  }
 }
 $manifest = @(
  ('PROJETO=' + $ref),
  ('DATA=' + (Get-Date).ToString('o')),
  'ORIGEM=Supabase CLI, exportacao somente leitura',
  'ATENCAO=SQL de dados sensiveis; criptografe antes de guardar',
  'ATENCAO=Validar a restauracao separadamente antes de qualquer migracao'
 )
 foreach ($export in $exports) {
  $file = Join-Path $target $export.File
  $hash = Get-FileHash -LiteralPath $file -Algorithm SHA256
  $manifest += ('SHA256 ' + $hash.Hash + ' ' + $export.File)
 }
 $manifest | Set-Content -LiteralPath (Join-Path $target 'MANIFEST.txt') -Encoding UTF8
 Write-Host ('Arquivos exportados em: ' + $target)
 Write-Host 'Backup NAO validado por restauracao: mantenha a migracao bloqueada ate testar restore.'
} finally { Pop-Location }
