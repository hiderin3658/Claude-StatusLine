#!/bin/bash

# Claude Code 起動時に実行されるフック
# ccusage デーモンをバックグラウンドで起動（重複起動は自動防止）

# ccusage デーモンをバックグラウンドで起動
# Note: デーモン内で重複起動チェックを行うため、複数回呼ばれても問題なし
nohup node ~/.claude/ccusage-daemon.mjs > /dev/null 2>&1 &

exit 0
