# Claude Code プロセス検出スクリプト（Windows用）
#
# Claude Code および関連プロセス（MCPサーバーなど）を検出します。
# 検出したプロセス数を標準出力に出力し、プロセスが見つかった場合は exit code 0、
# 見つからなかった場合は exit code 1 を返します。

try {
    $count = 0

    # 1. claude.exe プロセスを検出（Claude Code本体）
    $claudeExeProcesses = Get-WmiObject Win32_Process -Filter "name='claude.exe'" -ErrorAction SilentlyContinue
    if ($claudeExeProcesses) {
        $claudeExeCount = if ($claudeExeProcesses.Count) { $claudeExeProcesses.Count } else { 1 }
        $count += $claudeExeCount
    }

    # 2. node.exe プロセスの中から Claude Code CLI および MCP サーバーを検出
    $nodeProcesses = Get-WmiObject Win32_Process -Filter "name='node.exe'" -ErrorAction SilentlyContinue
    if ($nodeProcesses) {
        $claudeNodeProcesses = $nodeProcesses | Where-Object {
            $_.CommandLine -and (
                $_.CommandLine -like '*@anthropic*' -or
                $_.CommandLine -like '*claude-code*' -or
                $_.CommandLine -like '*claude*cli*'
            )
        }

        if ($claudeNodeProcesses) {
            $nodeCount = if ($claudeNodeProcesses.Count) { $claudeNodeProcesses.Count } else { 1 }
            $count += $nodeCount
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
