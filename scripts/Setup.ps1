param([switch]$PrepareData)
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$projectDir = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectDir
if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv sync --locked --extra dev
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar dependências com uv.' }
} else {
    if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
        py -3.12 -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Instale Python 3.12 ou uv e tente novamente.' }
    }
    & '.venv\Scripts\python.exe' -m pip install torch --index-url https://download.pytorch.org/whl/cpu
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar PyTorch CPU.' }
    & '.venv\Scripts\python.exe' -m pip install -e '.[dev]'
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar dependências.' }
}
if (-not (Test-Path -LiteralPath '.env')) { Copy-Item -LiteralPath '.env.example' -Destination '.env' }
if ($PrepareData) {
    foreach ($command in @('download','prepare','index')) {
        & '.venv\Scripts\python.exe' -m voc_olist $command
        if ($LASTEXITCODE -ne 0) { throw "Falha no comando $command" }
    }
}
Write-Host 'Ambiente pronto. Execute scripts\Start.ps1 para abrir a aplicação.'
