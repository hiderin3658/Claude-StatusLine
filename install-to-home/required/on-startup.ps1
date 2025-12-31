# Claude Code 起動時フック (Windows PowerShell版)
#
# このスクリプトは Claude Code 起動時に ccusage-daemon を起動します

$daemonPath = Join-Path $env:USERPROFILE ".claude\ccusage-daemon.mjs"
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
# -RedirectStandardOutput/-RedirectStandardError: 出力をログファイルにリダイレクト
try {
    Start-Process -FilePath "node" `
        -ArgumentList $daemonPath `
        -WindowStyle Hidden `
        -RedirectStandardOutput $logPath `
        -RedirectStandardError $logPath `
        -WorkingDirectory $env:USERPROFILE

    Write-Host "ccusage-daemon started successfully" -ForegroundColor Green
    Write-Host "Log file: $logPath" -ForegroundColor Gray
} catch {
    Write-Host "Error: Failed to start daemon - $_" -ForegroundColor Red
    exit 1
}

exit 0
