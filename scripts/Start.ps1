$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$projectDir = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectDir
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    throw 'Run scripts\Setup.ps1 before starting the application.'
}
& '.venv\Scripts\python.exe' -m streamlit run app.py
exit $LASTEXITCODE
