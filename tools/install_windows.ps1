<#
BARG-CC v4 Windows installer. Tested by static review on Linux; Windows execution must be validated locally.
No administrator privilege or registry modification required.

Normal: double-click 00_INSTALL_WINDOWS.cmd from the extracted ZIP.
Advanced:
 powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\install_windows.ps1 -SourceDir . -InstallDev -Launch
#>
[CmdletBinding()]
param(
    [string]$SourceDir = '',
    [string]$AppDir = '',
    [string]$EnvironmentDir = '',
    [switch]$Launch,
    [switch]$SkipTests,
    [switch]$NoBackup,
    [string]$CondaExe = ''
)
$ErrorActionPreference = 'Stop'

function Check-Native([string]$What) {
    if ($LASTEXITCODE -ne 0) { throw "$What failed, exit code $LASTEXITCODE. Review the errors above." }
}
function Resolve-Conda([string]$Given) {
    if ($Given -and (Test-Path -LiteralPath $Given -PathType Leaf)) { return (Resolve-Path -LiteralPath $Given).Path }
    if ($env:CONDA_EXE -and (Test-Path -LiteralPath $env:CONDA_EXE -PathType Leaf)) { return $env:CONDA_EXE }
    $cmd = Get-Command conda.exe -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source -and (Test-Path -LiteralPath $cmd.Source -PathType Leaf)) { return $cmd.Source }
    $candidates = @(
        'E:\Miniconda3\Scripts\conda.exe',
        'C:\Miniconda3\Scripts\conda.exe',
        'C:\ProgramData\miniconda3\Scripts\conda.exe',
        (Join-Path $env:USERPROFILE 'miniconda3\Scripts\conda.exe'),
        (Join-Path $env:USERPROFILE 'anaconda3\Scripts\conda.exe')
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
    }
    throw 'Conda could not be found. Pass -CondaExe "E:\Miniconda3\Scripts\conda.exe" or inspect conda info --base.'
}
function Copy-Checked([string]$From,[string]$To) {
    & robocopy.exe $From $To /E /R:1 /W:1 /NFL /NDL /NJH /NJS /XD '.venv' '.git' '__pycache__' '.pytest_cache' 'node_modules' 'config' 'logs' /XF '*.pyc' '*.pyo' '*.log'
    $copyCode = $LASTEXITCODE
    if ($copyCode -gt 7) { throw "Robocopy failed (code $copyCode). If source paths are too long, extract ZIP to E:\BARGCC_SETUP first." }
}
function Ensure-InsideShortPath([string]$Value,[string]$Name) {
    if ($Value.Length -gt 90) { throw "$Name must be a short path (less than 90 characters): $Value" }
}

if (-not $SourceDir) { $SourceDir = (Get-Location).Path }
$SourceDir = [IO.Path]::GetFullPath($SourceDir).TrimEnd('\')
if (-not (Test-Path -LiteralPath (Join-Path $SourceDir 'app\main.py') -PathType Leaf) -or
    -not (Test-Path -LiteralPath (Join-Path $SourceDir 'requirements.txt') -PathType Leaf)) {
    throw "Source directory not recognized: $SourceDir. Extract the full application ZIP first."
}
$driveRoot = if (Test-Path 'E:\') { 'E:\' } else { 'C:\' }
if (-not $AppDir) { $AppDir = Join-Path $driveRoot 'BARGCC' }
if (-not $EnvironmentDir) { $EnvironmentDir = Join-Path $driveRoot 'BARGCC_ENV' }
$AppDir = [IO.Path]::GetFullPath($AppDir).TrimEnd('\')
$EnvironmentDir = [IO.Path]::GetFullPath($EnvironmentDir).TrimEnd('\')
Ensure-InsideShortPath $AppDir 'AppDir'
Ensure-InsideShortPath $EnvironmentDir 'EnvironmentDir'
if ($AppDir.Equals($EnvironmentDir,[StringComparison]::OrdinalIgnoreCase)) { throw 'AppDir and EnvironmentDir must differ.' }
if ($SourceDir.Equals($AppDir,[StringComparison]::OrdinalIgnoreCase)) { throw 'Extract to a separate setup folder before installing into AppDir.' }
if ($SourceDir.StartsWith($AppDir+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'The source folder must not be inside the target app folder.' }
if ($AppDir.StartsWith($SourceDir+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Do not install the application inside its extracted source folder.' }
$conda = Resolve-Conda $CondaExe
Write-Host '========================================================' -ForegroundColor Cyan
Write-Host 'BARG-CC RAG v4 - Windows safe-path installer' -ForegroundColor Cyan
Write-Host '========================================================' -ForegroundColor Cyan
Write-Host "Source:      $SourceDir"
Write-Host "Destination: $AppDir"
Write-Host "Python:      $EnvironmentDir"
Write-Host "Conda:       $conda"
Write-Host 'Your old research folder remains unchanged.'

if (Test-Path -LiteralPath $AppDir -PathType Leaf) { throw "App destination is a file: $AppDir" }
$previous = Test-Path -LiteralPath (Join-Path $AppDir 'app\main.py') -PathType Leaf
if ($previous -and -not $NoBackup) {
    $backup = Join-Path $driveRoot ('BARGCC_Backup_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
    Write-Host "Existing installation detected. Creating backup: $backup" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $backup -Force | Out-Null
    Copy-Checked $AppDir $backup
    if (-not (Test-Path -LiteralPath (Join-Path $backup 'app\main.py'))) { throw 'Backup validation failed.' }
}
if (-not (Test-Path -LiteralPath $AppDir)) { New-Item -ItemType Directory -Path $AppDir -Force | Out-Null }
Write-Host 'Copying application without old .venv or Python binaries...' -ForegroundColor Cyan
Copy-Checked $SourceDir $AppDir
if (-not (Test-Path -LiteralPath (Join-Path $AppDir 'app\main.py') -PathType Leaf)) { throw 'Application copy failed.' }

$python = Join-Path $EnvironmentDir 'python.exe'
if (Test-Path -LiteralPath $EnvironmentDir -PathType Container) {
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
        throw "Environment folder exists without Python: $EnvironmentDir. Rename it and retry; no directories were removed."
    }
} else {
    Write-Host 'Creating a new Python 3.11 Conda environment (internet may be required)...' -ForegroundColor Cyan
    & $conda create --yes --prefix $EnvironmentDir 'python=3.11' 'pip'
    Check-Native 'Conda environment creation'
}
& $python -c 'import sys; print("Python:",sys.version); assert sys.version_info[:2]==(3,11), "Python 3.11 required"'
Check-Native 'Python 3.11 interpreter validation'

Push-Location -LiteralPath $AppDir
try {
    New-Item -ItemType Directory -Path 'config' -Force | Out-Null
    New-Item -ItemType Directory -Path 'logs' -Force | Out-Null
    # Local, non-secret configuration only; token values are NOT written into this file.
    @('REM Generated by installer (no secrets)', 'set "BARGCC_PYTHON=' + $python + '"') | Set-Content -LiteralPath 'config\windows_paths.cmd' -Encoding ASCII
    $env:PIP_DISABLE_PIP_VERSION_CHECK = '1'
    $env:PIP_NO_CACHE_DIR = '1'
    $env:OPENBLAS_NUM_THREADS='1'
    $env:OMP_NUM_THREADS='1'
    $env:MKL_NUM_THREADS='1'
    Write-Host 'Installing dependencies into isolated short-path Python...' -ForegroundColor Cyan
    & $python -m pip install --only-binary=:all: -r requirements.txt
    Check-Native 'Application dependency installation'
    & $python -m pip install --only-binary=:all: -r requirements-dev.txt
    Check-Native 'Test dependency installation'
    Write-Host 'Running dependency and knowledge-base preflight...' -ForegroundColor Cyan
    & $python tools\preflight.py
    Check-Native 'Application preflight'
    if (-not $SkipTests) {
        Write-Host 'Running application test suite...' -ForegroundColor Cyan
        & $python -m pytest -q tests
        Check-Native 'Automated tests'
    }
    Write-Host '========================================================' -ForegroundColor Green
    Write-Host 'INSTALLATION AND VERIFICATION SUCCESSFUL' -ForegroundColor Green
    Write-Host "Folder:     $AppDir" -ForegroundColor Green
    Write-Host "Python:     $python" -ForegroundColor Green
    Write-Host 'URL:        http://127.0.0.1:7860/' -ForegroundColor Green
    Write-Host 'Run 01_START_WINDOWS.cmd again for future sessions.' -ForegroundColor Green
    Write-Host '========================================================' -ForegroundColor Green
    if ($Launch) {
        Write-Host 'Starting local FastAPI server; Ctrl+C to stop...' -ForegroundColor Cyan
        $env:BARG_REQUIRE_TOKEN='0'
        $env:BARG_ACCESS_TOKEN=''
        & $python -m uvicorn app.main:app --host 127.0.0.1 --port 7860 --workers 1
        Check-Native 'Uvicorn server'
    }
} finally { Pop-Location }
