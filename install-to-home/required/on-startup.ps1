# Claude Code 起動時フック (Windows PowerShell版)
#
# このスクリプトは Claude Code 起動時に以下を起動します:
# 1. ccusage-daemon (使用率監視)
# 2. AutoHotkey スクリプト (スクリーンショット貼り付け機能)

$daemonPath = Join-Path $env:USERPROFILE ".claude\ccusage-daemon.mjs"
$ahkScriptPath = Join-Path $env:USERPROFILE ".claude\claude-paste.ahk"
$logPath = Join-Path $env:TEMP "ccusage-daemon-startup.log"

# daemon ファイルの存在確認
if (-not (Test-Path $daemonPath)) {
    Write-Host "Error: daemon file not found at $daemonPath" -ForegroundColor Red
    exit 1
}

# Node.js の存在確認
try {
    $nodeVersion = node --version 2>$null
    if (-not $nodeVersion) {
        Write-Host "Error: Node.js is not installed or not in PATH" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Error: Node.js is not installed or not in PATH" -ForegroundColor Red
    exit 1
}

# daemon をバックグラウンドで起動
# -WindowStyle Hidden: ウィンドウを非表示
# Note: デーモンは自身で ~/.claude/cache/ccusage-daemon.log にログを出力します
try {
    Start-Process -FilePath "node" `
        -ArgumentList $daemonPath `
        -WindowStyle Hidden `
        -WorkingDirectory $env:USERPROFILE

    Write-Host "ccusage-daemon started successfully" -ForegroundColor Green
    Write-Host "Log file: $env:USERPROFILE\.claude\cache\ccusage-daemon.log" -ForegroundColor Gray
} catch {
    Write-Host "Error: Failed to start daemon - $_" -ForegroundColor Red
    exit 1
}

# ============================================================
# AutoHotkey スクリプトの起動
# ============================================================

# AutoHotkey スクリプトファイルの存在確認
if (-not (Test-Path $ahkScriptPath)) {
    Write-Host "Warning: AutoHotkey script not found at $ahkScriptPath" -ForegroundColor Yellow
    Write-Host "Skipping AutoHotkey startup" -ForegroundColor Gray
    exit 0
}

# AutoHotkey がインストールされているか確認
$ahkExe = $null
$ahkPaths = @(
    "$env:LOCALAPPDATA\Programs\AutoHotkey\v2\AutoHotkey64.exe",  # winget (user scope) - 64bit
    "$env:LOCALAPPDATA\Programs\AutoHotkey\v2\AutoHotkey32.exe",  # winget (user scope) - 32bit
    "$env:LOCALAPPDATA\Programs\AutoHotkey\v2\AutoHotkey.exe",    # winget (user scope) - generic
    "C:\Program Files\AutoHotkey\v2\AutoHotkey.exe",
    "C:\Program Files\AutoHotkey\AutoHotkey.exe",
    "C:\Program Files (x86)\AutoHotkey\AutoHotkey.exe"
)

foreach ($path in $ahkPaths) {
    if (Test-Path $path) {
        $ahkExe = $path
        break
    }
}

if (-not $ahkExe) {
    Write-Host "Warning: AutoHotkey is not installed" -ForegroundColor Yellow
    Write-Host "Skipping AutoHotkey startup" -ForegroundColor Gray
    exit 0
}

# 既に AutoHotkey プロセスが起動しているか確認
$ahkProcesses = Get-Process -Name "AutoHotkey*" -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -like "*AutoHotkey*" }

if ($ahkProcesses) {
    Write-Host "AutoHotkey is already running" -ForegroundColor Cyan
    exit 0
}

# AutoHotkey をバックグラウンドで起動
try {
    Start-Process -FilePath $ahkExe `
        -ArgumentList $ahkScriptPath `
        -WindowStyle Hidden `
        -WorkingDirectory $env:USERPROFILE

    Write-Host "AutoHotkey started successfully" -ForegroundColor Green
    Write-Host "Script: $ahkScriptPath" -ForegroundColor Gray
} catch {
    Write-Host "Warning: Failed to start AutoHotkey - $_" -ForegroundColor Yellow
}

exit 0
