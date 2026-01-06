#!/bin/bash
# Claude Code プロセス検出スクリプト（macOS/Linux用）
#
# Claude Code および関連プロセス（MCPサーバーなど）を検出します。
# 検出したプロセス数を標準出力に出力し、プロセスが見つかった場合は exit code 0、
# 見つからなかった場合は exit code 1 を返します。

# ps コマンドで node プロセスを検索し、claude-code または @anthropic を含むものをカウント
count=$(ps aux | grep -E "(claude-code|@anthropic)" | grep -v grep | wc -l)

# プロセス数を出力
echo "$count"

# exit code を設定
if [ "$count" -gt 0 ]; then
    exit 0
else
    exit 1
fi
