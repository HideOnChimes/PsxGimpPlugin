# uninstall.ps1 - GIMP PSX Plugin uninstaller
# Removes the plug-ins\psx folder from the GIMP user config folder.
# NOTE: ASCII-only (PowerShell 5.1 reads .ps1 as ANSI).

Set-StrictMode -Version Latest

function Abort { param([string]$msg) Write-Host "`nERROR: $msg" -ForegroundColor Red; Read-Host "Press Enter to exit"; exit 1 }

Write-Host ""
Write-Host "============================================" -ForegroundColor Magenta
Write-Host "  GIMP PSX Plugin - Uninstaller" -ForegroundColor Magenta
Write-Host "============================================" -ForegroundColor Magenta
Write-Host ""

$gimpBase = Join-Path $env:APPDATA 'GIMP'
$gimpConfig = Get-ChildItem $gimpBase -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match '^\d+\.\d+$' -and ([version]$_.Name) -ge [version]'3.0' } |
    Sort-Object { [version]$_.Name } | Select-Object -Last 1

if (-not $gimpConfig) { Abort "No GIMP 3.x config folder found." }

$pluginDest = Join-Path $gimpConfig.FullName 'plug-ins\psx'

if (Test-Path $pluginDest) {
    Remove-Item $pluginDest -Recurse -Force
    Write-Host "  [OK] Removed $pluginDest" -ForegroundColor Green
} else {
    Write-Host "  [!]  Plugin folder not found (already removed?): $pluginDest" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "  Uninstall complete. Restart GIMP to confirm." -ForegroundColor Green
Write-Host ""
