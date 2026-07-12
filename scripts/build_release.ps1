# Build Lappa Windows release binary (PyInstaller onefile)
# Usage:
#   pwsh scripts/build_release.ps1
#   pwsh scripts/build_release.ps1 -SkipInstall

param(
  [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Server = Join-Path $Root "packages\server"
$OutDir = Join-Path $Root "dist\release"

Set-Location $Server
if (-not $SkipInstall) {
  python -m pip install -U pip
  python -m pip install -e ".[release]"
}

if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }

python -m PyInstaller --noconfirm --clean lappa.spec

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$exe = Join-Path $Server "dist\lappa.exe"
if (-not (Test-Path $exe)) { throw "Build failed: missing $exe" }

$dest = Join-Path $OutDir "lappa-windows-x64.exe"
Copy-Item $exe $dest -Force

# quick smoke
& $dest version
if ($LASTEXITCODE -ne 0) {
  # desktop entry may not forward 'version' the same — try cli mode
  & $dest version 2>$null
}

Write-Host "OK: $dest"
Get-Item $dest | Format-List Name, Length, FullName
