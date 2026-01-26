# Claude Code ステータスライン表示スクリプト (Windows PowerShell版)
#
# 使い方: echo '{"model":{"display_name":"Claude"},...}' | powershell -File status-line.ps1

# UTF-8エンコーディングを設定（絵文字表示のため）
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 標準入力からJSONを読み込む
$inputJson = @()
while ($line = [Console]::In.ReadLine()) {
    $inputJson += $line
}
$inputText = $inputJson -join "`n"

try {
    $json = $inputText | ConvertFrom-Json
} catch {
    Write-Host "Error: Invalid JSON input"
    exit 1
}

# モデル名とディレクトリを取得
$model = if ($json.model.display_name) { $json.model.display_name } else { "Unknown" }
$currentDir = if ($json.workspace.current_dir) { $json.workspace.current_dir } else { "." }
$dirName = Split-Path -Leaf $currentDir
if (-not $dirName) { $dirName = "." }

# メイン出力（先頭部分）
Write-Host "[" -NoNewline
Write-Host $model -ForegroundColor Cyan -NoNewline
Write-Host "] " -NoNewline
Write-Host "📁 $dirName" -NoNewline

# Gitブランチ情報を取得
Push-Location $currentDir -ErrorAction SilentlyContinue
if (Test-Path .git) {
    try {
        $branch = git branch --show-current 2>$null
        if ($branch) {
            Write-Host " | " -NoNewline
            Write-Host $branch -ForegroundColor Green -NoNewline
        }
    } catch {
        # Git コマンドが失敗した場合は無視
    }
}
Pop-Location -ErrorAction SilentlyContinue

# コンテキスト使用率を計算
$contextSize = $json.context_window.context_window_size
$usage = $json.context_window.current_usage

if ($usage -and $contextSize -and $contextSize -gt 0) {
    $inputTokens = if ($usage.input_tokens) { $usage.input_tokens } else { 0 }
    $outputTokens = if ($usage.output_tokens) { $usage.output_tokens } else { 0 }
    $cacheCreate = if ($usage.cache_creation_input_tokens) { $usage.cache_creation_input_tokens } else { 0 }
    $cacheRead = if ($usage.cache_read_input_tokens) { $usage.cache_read_input_tokens } else { 0 }

    $currentTokens = $inputTokens + $outputTokens + $cacheCreate + $cacheRead
    $percentUsed = [math]::Floor($currentTokens * 100 / $contextSize)

    # パーセンテージに応じて色を変更
    $color = "Green"
    if ($percentUsed -ge 80) {
        $color = "Red"
    } elseif ($percentUsed -ge 50) {
        $color = "Yellow"
    }

    Write-Host " | Ctx:" -NoNewline
    Write-Host "$percentUsed%" -ForegroundColor $color -NoNewline
}

# 5時間ウィンドウのメッセージ使用状況をキャッシュから取得
$cacheFile = Join-Path $env:USERPROFILE ".claude\cache\ccusage-cache.json"

if (Test-Path $cacheFile) {
    try {
        # キャッシュファイルの年齢を確認（24時間以内のみ有効）
        $cacheAge = (Get-Date) - (Get-Item $cacheFile).LastWriteTime
        $maxAge = New-TimeSpan -Hours 24

        if ($cacheAge -lt $maxAge) {
            $cache = Get-Content $cacheFile -Raw | ConvertFrom-Json
            # tokenPercent を優先、なければ messagePercent を使用
            $tokenPercent = if ($cache.tokenPercent) { $cache.tokenPercent } else { $cache.messagePercent }

            if ($null -ne $tokenPercent) {
                # 色を決定
                $msgColor = "Green"
                if ($tokenPercent -ge 80) {
                    $msgColor = "Red"
                } elseif ($tokenPercent -ge 50) {
                    $msgColor = "Yellow"
                }

                Write-Host " | 5h:" -NoNewline
                Write-Host "$tokenPercent%" -ForegroundColor $msgColor -NoNewline
            }
        }
    } catch {
        # キャッシュ読み込みエラーは無視
    }
}

# 最終出力（改行）
Write-Host ""
