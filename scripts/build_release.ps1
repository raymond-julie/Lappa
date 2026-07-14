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

# CLI smoke must succeed before an artifact is accepted.
& $dest version
if ($LASTEXITCODE -ne 0) { throw "Release smoke failed: version command" }

$runtimeData = Join-Path $OutDir "lappa_data"
if (Test-Path $runtimeData) { Remove-Item -LiteralPath $runtimeData -Recurse -Force }

$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $dest).Hash.ToLowerInvariant()
$checksum = Join-Path $OutDir "SHA256SUMS.txt"
Set-Content -LiteralPath $checksum -Encoding ascii -Value "$hash  lappa-windows-x64.exe"

Write-Host "OK: $dest"
Get-Item $dest, $checksum | Format-Table Name, Length, FullName -AutoSize
