# install.ps1 - GIMP PSX Plugin installer
# Copies plug-ins\psx\psx.py to the GIMP user config folder.
# Run from the repo root:
#   powershell -ExecutionPolicy Bypass -File install.ps1
# NOTE: ASCII-only (PowerShell 5.1 reads .ps1 as ANSI).

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Step { param([string]$msg) Write-Host "  $msg" -ForegroundColor Cyan }
function Write-OK   { param([string]$msg) Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Warn { param([string]$msg) Write-Host "  [!]  $msg" -ForegroundColor Yellow }
function Abort      { param([string]$msg) Write-Host "`nERROR: $msg" -ForegroundColor Red; Read-Host "Press Enter to exit"; exit 1 }

Write-Host ""
Write-Host "============================================" -ForegroundColor Magenta
Write-Host "  GIMP PSX Plugin - Installer" -ForegroundColor Magenta
Write-Host "============================================" -ForegroundColor Magenta
Write-Host ""

# 1. Detect GIMP config folder
Write-Step "Looking for GIMP 3.x config folder..."

$gimpBase = Join-Path $env:APPDATA 'GIMP'
if (-not (Test-Path $gimpBase)) { Abort "GIMP config not found at $gimpBase. Is GIMP 3.x installed?" }

$gimpConfig = Get-ChildItem $gimpBase -Directory |
    Where-Object { $_.Name -match '^\d+\.\d+$' -and ([version]$_.Name) -ge [version]'3.0' } |
    Sort-Object { [version]$_.Name } |
    Select-Object -Last 1

if (-not $gimpConfig) { Abort "No GIMP 3.x config folder found inside $gimpBase." }

$configPath = $gimpConfig.FullName
$pluginDest = Join-Path $configPath 'plug-ins\psx'
Write-OK "Found GIMP config: $configPath"

# 2. Copy plugin
Write-Step "Copying plugin to $pluginDest ..."
New-Item -ItemType Directory -Force $pluginDest | Out-Null

$srcDir = Join-Path $PSScriptRoot 'plug-ins\psx'
if (-not (Test-Path $srcDir)) { Abort "Source folder not found: $srcDir" }

Copy-Item (Join-Path $srcDir 'psx.py') $pluginDest -Force
Write-OK "psx.py copied."

# 3. Remove residual files from the old automation approach
$oldFiles = @('psx_sequence.ps1', 'psx_keys.txt', 'psx_log.txt', 'install_shortcuts.ps1')
foreach ($f in $oldFiles) {
    $p = Join-Path $pluginDest $f
    if (Test-Path $p) {
        Remove-Item $p -Force
        Write-Warn "Removed old file: $f"
    }
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  Installation complete!" -ForegroundColor Green
Write-Host "  Restart GIMP and open Filters > PSX..." -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
