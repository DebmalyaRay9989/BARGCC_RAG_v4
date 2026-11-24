[CmdletBinding()]
param([string]$AppDir = '')
$ErrorActionPreference='Continue'
if (-not $AppDir) { $AppDir=(Get-Location).Path }
$AppDir=[IO.Path]::GetFullPath($AppDir)
$drive = [IO.Path]::GetPathRoot($AppDir)
$python=Join-Path $drive 'BARGCC_ENV\python.exe'
$config=Join-Path $AppDir 'config\windows_paths.cmd'
if (Test-Path -LiteralPath $config) {
  $match=Select-String -LiteralPath $config -Pattern '^set "BARGCC_PYTHON=(.+)"$'
  if ($match -and $match.Matches.Count -gt 0) { $python=$match.Matches[0].Groups[1].Value }
}
$report=New-Object System.Collections.Generic.List[string]
function Log([string]$s) { Write-Host $s; $script:report.Add($s) }
Log 'BARG-CC Windows Diagnostic (does not print secrets)'
Log ('Date: '+(Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))
Log ('AppDir length: '+$AppDir.Length)
Log ('AppDir: '+$AppDir)
Log ('Python: '+$python)
Log ('Conda registered: '+[bool](Get-Command conda.exe -ErrorAction SilentlyContinue))
Log ('app\main.py exists: '+(Test-Path -LiteralPath (Join-Path $AppDir 'app\main.py')))
Log ('requirements.txt exists: '+(Test-Path -LiteralPath (Join-Path $AppDir 'requirements.txt')))
Log ('Python exists: '+(Test-Path -LiteralPath $python -PathType Leaf))
if (Test-Path -LiteralPath $python -PathType Leaf) {
    & $python -c 'import sys; print("PYTHON VERSION",sys.version); import numpy,scipy,sklearn; print("NUMPY",numpy.__version__,"SCIPY",scipy.__version__,"SKLEARN",sklearn.__version__); import app.main; print("APPLICATION IMPORT OK")' 2>&1 | ForEach-Object { Log ([string]$_) }
    Log ('Import process exit code: '+$LASTEXITCODE)
}
try {
  $tcp=New-Object Net.Sockets.TcpClient
  $result=$tcp.BeginConnect('127.0.0.1',7860,$null,$null)
  $connected=$result.AsyncWaitHandle.WaitOne(1200)
  if ($connected) { $tcp.EndConnect($result) }
  $tcp.Close()
  Log ('Local port 7860 listening: '+$connected)
} catch { Log ('Local server connection result: '+$_.Exception.Message) }
if (Test-Path -LiteralPath $AppDir -PathType Container) {
  $dir=Join-Path $AppDir 'logs';New-Item -Path $dir -ItemType Directory -Force | Out-Null
  $dest=Join-Path $dir 'windows_diagnostics.txt'
  $report | Set-Content -LiteralPath $dest -Encoding UTF8
  Write-Host "Diagnostic report saved: $dest" -ForegroundColor Cyan
}
Log 'If WinError 206 persists, rerun 00_INSTALL_WINDOWS.cmd from a short extraction folder (E:\BARGCC_SETUP).'
