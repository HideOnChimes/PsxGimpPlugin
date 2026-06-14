# uninstall.ps1 - GIMP PSX Plugin uninstaller
# Removes the plugin folder and cleans up PSX shortcut entries from shortcutsrc.
# Run with GIMP closed.

Set-StrictMode -Version Latest

function Abort { param([string]$msg) Write-Host "`nERROR: $msg" -ForegroundColor Red; Read-Host "Press Enter to exit"; exit 1 }

Write-Host ""
Write-Host "============================================" -ForegroundColor Magenta
Write-Host "  GIMP PSX Plugin - Uninstaller" -ForegroundColor Magenta
Write-Host "============================================" -ForegroundColor Magenta
Write-Host ""

# Detect GIMP config
$gimpBase = Join-Path $env:APPDATA 'GIMP'
$gimpConfig = Get-ChildItem $gimpBase -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match '^\d+\.\d+$' -and ([version]$_.Name) -ge [version]'3.0' } |
    Sort-Object { [version]$_.Name } | Select-Object -Last 1

if (-not $gimpConfig) { Abort "No GIMP 3.x config folder found." }
$configPath  = $gimpConfig.FullName
$pluginDest  = Join-Path $configPath 'plug-ins\psx'
$shortcutsrc = Join-Path $configPath 'shortcutsrc'

# Wait for GIMP to close
$gimp = Get-Process -Name 'gimp-3*','gimp*' -ErrorAction SilentlyContinue |
        Where-Object { $_.MainWindowHandle -ne [IntPtr]::Zero }
if ($gimp) {
    Write-Host "  [!] GIMP is open. Please close it first and re-run this script." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Remove plugin folder
if (Test-Path $pluginDest) {
    Remove-Item $pluginDest -Recurse -Force
    Write-Host "  [OK] Removed $pluginDest" -ForegroundColor Green
} else {
    Write-Host "  [!]  Plugin folder not found (already removed?): $pluginDest" -ForegroundColor Yellow
}

# Remove PSX shortcut lines from shortcutsrc
$psxActions = @('image-scale','filters-noise-rgb','image-convert-indexed','filters-gaussian-blur')
if (Test-Path $shortcutsrc) {
    $lines    = [System.IO.File]::ReadAllLines($shortcutsrc, [System.Text.Encoding]::UTF8)
    $filtered = $lines | Where-Object {
        $line = $_
        -not ($psxActions | Where-Object { $line -match "^\(action\s+`"$([regex]::Escape($_))`"" })
    }
    [System.IO.File]::WriteAllLines($shortcutsrc, $filtered, (New-Object System.Text.UTF8Encoding $false))
    Write-Host "  [OK] Cleaned PSX shortcuts from shortcutsrc" -ForegroundColor Green
}

Write-Host ""
Write-Host "  Uninstall complete. Re-open GIMP to confirm." -ForegroundColor Green
Write-Host ""
