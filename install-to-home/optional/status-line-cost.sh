#!/bin/bash

# 標準入力から JSON を読み込む
input=$(cat)

# jq を使って値を抽出
MODEL=$(echo "$input" | jq -r '.model.display_name')
CURRENT_DIR=$(echo "$input" | jq -r '.workspace.current_dir')
DIR_NAME="${CURRENT_DIR##*/}"

# Git ブランチ情報を取得
GIT_BRANCH=""
if git rev-parse --git-dir > /dev/null 2>&1; then
    BRANCH=$(git branch --show-current 2>/dev/null)
    if [ -n "$BRANCH" ]; then
        GIT_BRANCH=" | \033[32m$BRANCH\033[0m"
    fi
fi

# コンテキスト使用率を計算
CONTEXT_SIZE=$(echo "$input" | jq -r '.context_window.context_window_size')
USAGE=$(echo "$input" | jq '.context_window.current_usage')

CONTEXT_INFO=""
if [ "$USAGE" != "null" ]; then
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

# セッションコスト情報を取得
COST_INFO=""
COST=$(echo "$input" | jq -r '.cost.total_cost_usd // 0')

if [ "$COST" != "0" ] && [ "$COST" != "null" ]; then
    # USD を小数点2桁で表示
    COST_DISPLAY=$(printf "%.2f" "$COST")
    COST_INFO=" | \033[33m\$${COST_DISPLAY}\033[0m"
fi

echo -e "[\033[36m$MODEL\033[0m] 📁 $DIR_NAME$GIT_BRANCH$CONTEXT_INFO$COST_INFO"
