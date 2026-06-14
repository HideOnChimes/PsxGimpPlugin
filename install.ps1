# install.ps1 — GIMP PSX Plugin installer
# Copies the plugin, assigns keyboard shortcuts (auto-resolving conflicts),
# and writes psx_keys.txt so the automation knows which keys to send.
#
# Run with GIMP closed:
#   powershell -ExecutionPolicy Bypass -File install.ps1

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ── helpers ──────────────────────────────────────────────────────────────────

function Write-Step { param([string]$msg) Write-Host "  $msg" -ForegroundColor Cyan }
function Write-OK   { param([string]$msg) Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Warn { param([string]$msg) Write-Host "  [!]  $msg" -ForegroundColor Yellow }
function Abort      { param([string]$msg) Write-Host "`nERROR: $msg" -ForegroundColor Red; Read-Host "Press Enter to exit"; exit 1 }

Write-Host ""
Write-Host "============================================" -ForegroundColor Magenta
Write-Host "  GIMP PSX Plugin — Installer" -ForegroundColor Magenta
Write-Host "============================================" -ForegroundColor Magenta
Write-Host ""

# ── 1. Detect GIMP config folder ─────────────────────────────────────────────

Write-Step "Looking for GIMP 3.x config folder..."

$gimpBase = Join-Path $env:APPDATA 'GIMP'
if (-not (Test-Path $gimpBase)) { Abort "GIMP config not found at $gimpBase. Is GIMP 3.x installed?" }

$gimpConfig = Get-ChildItem $gimpBase -Directory |
    Where-Object { $_.Name -match '^\d+\.\d+$' -and ([version]$_.Name) -ge [version]'3.0' } |
    Sort-Object { [version]$_.Name } |
    Select-Object -Last 1

if (-not $gimpConfig) { Abort "No GIMP 3.x config folder found inside $gimpBase." }

$configPath   = $gimpConfig.FullName
$pluginDest   = Join-Path $configPath 'plug-ins\psx'
$shortcutsrc  = Join-Path $configPath 'shortcutsrc'

Write-OK "Found GIMP config: $configPath"

# ── 2. Wait for GIMP to be closed ────────────────────────────────────────────

$gimp = Get-Process -Name 'gimp-3*','gimp*' -ErrorAction SilentlyContinue |
        Where-Object { $_.MainWindowHandle -ne [IntPtr]::Zero }

if ($gimp) {
    Write-Warn "GIMP is open. Waiting for you to close it (shortcuts are saved on exit)..."
    while ($true) {
        Start-Sleep -Seconds 2
        $gimp = Get-Process -Name 'gimp-3*','gimp*' -ErrorAction SilentlyContinue |
                Where-Object { $_.MainWindowHandle -ne [IntPtr]::Zero }
        if (-not $gimp) { break }
        Write-Host "    still waiting..." -ForegroundColor DarkGray
    }
    Write-OK "GIMP closed."
}

# ── 3. Copy plugin files ──────────────────────────────────────────────────────

Write-Step "Copying plugin files to $pluginDest ..."
New-Item -ItemType Directory -Force $pluginDest | Out-Null

$srcDir = Join-Path $PSScriptRoot 'plug-ins\psx'
if (-not (Test-Path $srcDir)) { Abort "Source folder not found: $srcDir" }

Copy-Item (Join-Path $srcDir '*') $pluginDest -Force
Write-OK "Plugin files copied."

# ── 4. Assign keyboard shortcuts (conflict-safe) ──────────────────────────────

Write-Step "Configuring keyboard shortcuts..."

if (-not (Test-Path $shortcutsrc)) { Abort "shortcutsrc not found at $shortcutsrc" }

$lines = [System.IO.File]::ReadAllLines($shortcutsrc, [System.Text.Encoding]::UTF8)

# Collect ALL accelerators already in use (active + commented = reserved)
$usedAccels = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
foreach ($line in $lines) {
    if ($line -match '"([^"]+)"\s*\)') { $usedAccels.Add($Matches[1]) | Out-Null }
}

# Candidate pool: Ctrl+Shift+F1..F12, then Ctrl+Alt+F1..F12, then Ctrl+Shift+Alt+F1..F12
$pool = @()
foreach ($n in 1..12) { $pool += "<Primary><Shift>F$n" }
foreach ($n in 1..12) { $pool += "<Primary><Alt>F$n" }
foreach ($n in 1..12) { $pool += "<Primary><Shift><Alt>F$n" }

# GTK accelerator -> SendKeys string converter
function ConvertTo-SendKeys {
    param([string]$gtk)
    $sk = $gtk
    $sk = $sk -replace '<Primary>|<Control>', '^'
    $sk = $sk -replace '<Shift>',             '+'
    $sk = $sk -replace '<Alt>|<Mod1>',        '%'
    $sk = $sk -replace 'F(\d+)',              '{F$1}'
    return $sk
}

# The 4 actions in sequence order
$actions = [ordered]@{
    'image-scale'           = 'Scale Image'
    'filters-noise-rgb'     = 'RGB Noise'
    'image-convert-indexed' = 'Convert to Indexed'
    'filters-gaussian-blur' = 'Gaussian Blur'
}

$assigned  = [ordered]@{}   # action -> gtk accel
$newLines  = [System.Collections.Generic.List[string]]::new($lines)

foreach ($action in $actions.Keys) {
    $label = $actions[$action]

    # Check for existing active assignment
    $existing = $lines | Where-Object {
        $_ -match "^\(action\s+`"$([regex]::Escape($action))`"\s+`"([^`"]+)`"\)"
    } | Select-Object -First 1

    if ($existing -and $existing -match '"([^"]+)"\s*\)\s*$') {
        $accel = $Matches[1]
        $assigned[$action] = $accel
        Write-OK "$label -> already assigned: $accel (kept)"
        $usedAccels.Add($accel) | Out-Null
        continue
    }

    # Find first free candidate
    $chosen = $null
    foreach ($candidate in $pool) {
        if (-not $usedAccels.Contains($candidate)) {
            $chosen = $candidate
            break
        }
    }
    if (-not $chosen) { Abort "No free keyboard shortcut candidates left! Remove some shortcuts and re-run." }

    $newLines.Add("(action `"$action`" `"$chosen`")")
    $usedAccels.Add($chosen) | Out-Null
    $assigned[$action] = $chosen
    Write-OK "$label -> assigned: $chosen"
}

[System.IO.File]::WriteAllLines($shortcutsrc, $newLines, (New-Object System.Text.UTF8Encoding $false))
Write-OK "shortcutsrc updated."

# ── 5. Write psx_keys.txt ────────────────────────────────────────────────────

$keysFile = Join-Path $pluginDest 'psx_keys.txt'
$sendKeys = $assigned.Keys | ForEach-Object { ConvertTo-SendKeys $assigned[$_] }
[System.IO.File]::WriteAllLines($keysFile, $sendKeys, (New-Object System.Text.UTF8Encoding $false))
Write-OK "psx_keys.txt written to $keysFile"

# ── Done ─────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  Installation complete!" -ForegroundColor Green
Write-Host "  Open GIMP and use Filters > PSX..." -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
