# Claude Code プロセス検出スクリプト（Windows用）
#
# Claude Code および関連プロセス（MCPサーバーなど）を検出します。
# 検出したプロセス数を標準出力に出力し、プロセスが見つかった場合は exit code 0、
# 見つからなかった場合は exit code 1 を返します。

try {
    # すべての node.exe プロセスを取得
    $processes = Get-WmiObject Win32_Process -Filter "name='node.exe'" -ErrorAction Stop

    # Claude Code 関連のプロセスをフィルタリング
    # - @anthropic-ai/claude-code/cli.js を含むプロセス
    # - @anthropic を含むプロセス（MCPサーバーなども含む）
    $claudeProcesses = $processes | Where-Object {
        $_.CommandLine -and (
            $_.CommandLine -like '*@anthropic*' -or
            $_.CommandLine -like '*claude-code*'
        )
    }

    $count = 0
    if ($claudeProcesses) {
        $count = $claudeProcesses.Count
        if ($count -eq $null) {
            # 単一のプロセスの場合、Count プロパティは null になる
            $count = 1
        }
    }

    # プロセス数を標準出力に出力
    Write-Output $count

    # exit code を設定
    if ($count -gt 0) {
        exit 0
    } else {
        exit 1
    }
} catch {
    # エラーが発生した場合は 0 を出力して exit code 1 を返す
    Write-Output 0
    exit 1
}
