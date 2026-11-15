$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$projectDir = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectDir
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    throw 'Execute scripts\Setup.ps1 antes de iniciar.'
}
& '.venv\Scripts\python.exe' -m streamlit run app.py
