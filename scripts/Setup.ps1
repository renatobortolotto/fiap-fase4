param(
    [switch]$PrepareData,
    [string]$ArchivePath
)

$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$projectDir = Split-Path -Parent $PSScriptRoot

# Resolve a relative archive against the caller's directory before changing it.
$archiveFile = $null
if (-not [string]::IsNullOrWhiteSpace($ArchivePath)) {
    if (-not (Test-Path -LiteralPath $ArchivePath -PathType Leaf)) {
        throw "Archive file not found: $ArchivePath"
    }
    $archiveFile = (Resolve-Path -LiteralPath $ArchivePath).ProviderPath
}
Set-Location -LiteralPath $projectDir

Write-Host '[1/4] Creating runtime directories...'
foreach ($directory in @('artifacts', 'data\raw', 'data\processed', 'reports')) {
    [System.IO.Directory]::CreateDirectory((Join-Path $projectDir $directory)) | Out-Null
}

$pythonExe = Join-Path $projectDir '.venv\Scripts\python.exe'
Write-Host '[2/4] Installing dependencies for Python 3.12...'
if (Get-Command uv -ErrorAction SilentlyContinue) {
    uv sync --locked --extra dev --python 3.12
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed (uv).' }
} else {
    Write-Host 'uv not found; using pip. This fallback does not use uv.lock.'
    if (-not (Test-Path -LiteralPath $pythonExe -PathType Leaf)) {
        py -3.12 -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12 or uv, then try again.' }
    }
    & $pythonExe -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)'
    if ($LASTEXITCODE -ne 0) { throw 'The existing virtual environment must use Python 3.12.' }
    & $pythonExe -m pip install torch --index-url https://download.pytorch.org/whl/cpu
    if ($LASTEXITCODE -ne 0) { throw 'PyTorch CPU installation failed.' }
    & $pythonExe -m pip install -e '.[dev]'
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed (pip).' }
}
if (-not (Test-Path -LiteralPath $pythonExe -PathType Leaf)) {
    throw 'The installer did not create .venv\Scripts\python.exe.'
}

Write-Host '[3/4] Checking local configuration...'
$environmentFile = Join-Path $projectDir '.env'
if (Test-Path -LiteralPath $environmentFile) {
    Write-Host 'Existing .env preserved.'
} else {
    [System.IO.File]::Copy((Join-Path $projectDir '.env.example'), $environmentFile, $false)
    Write-Host 'Created .env from .env.example.'
}

if ($PrepareData.IsPresent -or $null -ne $archiveFile) {
    if ($null -ne $archiveFile) {
        Write-Host "[4/4] Importing local archive: $archiveFile"
        & $pythonExe -m voc_olist download --archive $archiveFile
    } else {
        Write-Host '[4/4] Downloading the official Olist dataset...'
        & $pythonExe -m voc_olist download
    }
    if ($LASTEXITCODE -ne 0) { throw 'Dataset download or archive import failed.' }
    Write-Host '[4/4] Preparing reviews and metadata...'
    & $pythonExe -m voc_olist prepare
    if ($LASTEXITCODE -ne 0) { throw 'Dataset preparation failed.' }
    Write-Host '[4/4] Building the semantic index (CPU; this can take several minutes)...'
    & $pythonExe -m voc_olist index
    if ($LASTEXITCODE -ne 0) { throw 'Semantic index creation failed.' }
    Write-Host '[4/4] Preparing local generation models and runtime...'
    & $pythonExe -m voc_olist models
    if ($LASTEXITCODE -ne 0) { throw 'Local model preparation failed.' }
} else {
    Write-Host '[4/4] Data preparation skipped.'
    Write-Host 'To import an archive: .\scripts\Setup.ps1 -ArchivePath "C:\path\archive.zip"'
}
Write-Host 'Environment ready. Run scripts\Start.ps1 to open the application.'
