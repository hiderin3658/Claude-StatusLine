#!/bin/bash

# 標準入力から JSON を読み込む
input=$(cat)

# jq を使って値を抽出
MODEL=$(echo "$input" | jq -r '.model.display_name // "Unknown"')
CURRENT_DIR=$(echo "$input" | jq -r '.workspace.current_dir // "."')
DIR_NAME="${CURRENT_DIR##*/}"
[ -z "$DIR_NAME" ] && DIR_NAME="."

# Git ブランチ情報を取得
GIT_BRANCH=""
if git rev-parse --git-dir > /dev/null 2>&1; then
    BRANCH=$(git branch --show-current 2>/dev/null)
    if [ -n "$BRANCH" ]; then
        GIT_BRANCH=" | \033[32m$BRANCH\033[0m"
    fi
fi

# コンテキスト使用率を計算
CONTEXT_SIZE=$(echo "$input" | jq -r '.context_window.context_window_size // 0')
USAGE=$(echo "$input" | jq '.context_window.current_usage // null')

CONTEXT_INFO=""
if [ "$USAGE" != "null" ] && [ -n "$CONTEXT_SIZE" ] && [ "$CONTEXT_SIZE" -gt 0 ] 2>/dev/null; then
    INPUT_TOKENS=$(echo "$USAGE" | jq -r '.input_tokens // 0')
    OUTPUT_TOKENS=$(echo "$USAGE" | jq -r '.output_tokens // 0')
    CACHE_CREATE=$(echo "$USAGE" | jq -r '.cache_creation_input_tokens // 0')
    CACHE_READ=$(echo "$USAGE" | jq -r '.cache_read_input_tokens // 0')

    CURRENT_TOKENS=$((INPUT_TOKENS + OUTPUT_TOKENS + CACHE_CREATE + CACHE_READ))
    PERCENT_USED=$((CURRENT_TOKENS * 100 / CONTEXT_SIZE))

    # パーセンテージに応じて色を変更
    if [ $PERCENT_USED -lt 50 ]; then
        COLOR="\033[32m"  # 緑
    elif [ $PERCENT_USED -lt 80 ]; then
        COLOR="\033[33m"  # 黄
    else
        COLOR="\033[31m"  # 赤
    fi

    CONTEXT_INFO=" | Ctx:${COLOR}${PERCENT_USED}%\033[0m"
fi

# セッション使用率情報をキャッシュから取得
USAGE_INFO=""
CACHE_FILE="/tmp/claude-usage-cache.json"

if [ -f "$CACHE_FILE" ]; then
    # キャッシュファイルの年齢を確認（24時間以内のみ有効）
    # エラーを完全に抑制
    CACHE_MOD_TIME=$(stat -f %m "$CACHE_FILE" 2>/dev/null || stat -c %Y "$CACHE_FILE" 2>/dev/null || echo 0)
    CURRENT_TIME=$(date +%s)
    CACHE_AGE=$((CURRENT_TIME - CACHE_MOD_TIME))
    MAX_AGE=86400  # 24時間

    if [ "$CACHE_AGE" -lt "$MAX_AGE" ] 2>/dev/null; then
        SESSION_UTIL=$(jq -r '.session.utilization // 0' "$CACHE_FILE" 2>/dev/null)

        if [ -n "$SESSION_UTIL" ] && [ "$SESSION_UTIL" != "0" ] && [ "$SESSION_UTIL" != "null" ]; then
            # パーセント表示に変換（0.03 → 3%）
            SESSION_PERCENT=$(awk "BEGIN {printf \"%.0f\", $SESSION_UTIL * 100}" 2>/dev/null || echo 0)

            # 色を決定
            if [ "$SESSION_PERCENT" -lt 50 ] 2>/dev/null; then
                USAGE_COLOR="\033[32m"  # 緑
            elif [ "$SESSION_PERCENT" -lt 80 ] 2>/dev/null; then
                USAGE_COLOR="\033[33m"  # 黄
            else
                USAGE_COLOR="\033[31m"  # 赤
            fi

            USAGE_INFO=" | Session:${USAGE_COLOR}${SESSION_PERCENT}%\033[0m"
        fi
    fi
fi

# 5時間ウィンドウのメッセージ使用状況をキャッシュから取得
MESSAGE_INFO=""
MESSAGE_CACHE="/tmp/ccusage-cache.json"

if [ -f "$MESSAGE_CACHE" ]; then
    # キャッシュファイルが存在する場合
    MESSAGE_PERCENT=$(jq -r '.messagePercent // 0' "$MESSAGE_CACHE" 2>/dev/null)

    if [ -n "$MESSAGE_PERCENT" ] && [ "$MESSAGE_PERCENT" != "null" ]; then
        # 使用率から色を決定
        # 50%未満 → 緑
        # 50-80% → 黄色
        # 80%以上 → 赤
        if [ "$MESSAGE_PERCENT" -ge 80 ] 2>/dev/null; then
            MESSAGE_COLOR="\033[31m"  # 赤
        elif [ "$MESSAGE_PERCENT" -ge 50 ] 2>/dev/null; then
            MESSAGE_COLOR="\033[33m"  # 黄
        else
            MESSAGE_COLOR="\033[32m"  # 緑
        fi

        MESSAGE_INFO=" | 5h:${MESSAGE_COLOR}${MESSAGE_PERCENT}%\033[0m"
    fi
fi

echo -e "[\033[36m$MODEL\033[0m] 📁 $DIR_NAME$GIT_BRANCH$CONTEXT_INFO$USAGE_INFO$MESSAGE_INFO"
