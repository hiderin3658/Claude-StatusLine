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

# 5時間リミット情報を取得
USAGE_INFO=""
CACHE_FILE="/tmp/claude-usage-cache.json"
CACHE_MAX_AGE=60  # キャッシュの有効期間（秒）

# キャッシュファイルの年齢を確認
if [ -f "$CACHE_FILE" ]; then
    CACHE_AGE=$(($(date +%s) - $(stat -f %m "$CACHE_FILE" 2>/dev/null || echo 0)))
else
    CACHE_AGE=999999
fi

# キャッシュが古い場合、または存在しない場合は API を呼び出す
if [ $CACHE_AGE -gt $CACHE_MAX_AGE ]; then
    # macOS Keychain から認証トークンを取得
    CREDENTIALS=$(security find-generic-password -s "Claude Code-credentials" -w 2>/dev/null)

    if [ -n "$CREDENTIALS" ]; then
        # JSON から accessToken を抽出
        ACCESS_TOKEN=$(echo "$CREDENTIALS" | jq -r '.claudeAiOauth.accessToken' 2>/dev/null)

        if [ -n "$ACCESS_TOKEN" ] && [ "$ACCESS_TOKEN" != "null" ]; then
            # API エンドポイントを呼び出し
            USAGE_DATA=$(curl -s -H "Authorization: Bearer $ACCESS_TOKEN" \
                "https://api.anthropic.com/api/oauth/usage" 2>/dev/null)

            # キャッシュに保存
            echo "$USAGE_DATA" > "$CACHE_FILE" 2>/dev/null
        fi
    fi
fi

# キャッシュから使用率を取得
if [ -f "$CACHE_FILE" ]; then
    FIVE_HOUR_UTIL=$(jq -r '.five_hour.utilization // 0' "$CACHE_FILE" 2>/dev/null)

    if [ -n "$FIVE_HOUR_UTIL" ] && [ "$FIVE_HOUR_UTIL" != "0" ] && [ "$FIVE_HOUR_UTIL" != "null" ]; then
        # パーセント表示に変換（0.03 → 3%）四捨五入（0.5加算方式）
        FIVE_HOUR_PERCENT=$(echo "($FIVE_HOUR_UTIL * 100 + 0.5) / 1" | bc 2>/dev/null || echo "0")

        # 色を決定
        if [ "$FIVE_HOUR_PERCENT" -lt 50 ]; then
            USAGE_COLOR="\033[32m"  # 緑
        elif [ "$FIVE_HOUR_PERCENT" -lt 80 ]; then
            USAGE_COLOR="\033[33m"  # 黄
        else
            USAGE_COLOR="\033[31m"  # 赤
        fi

        USAGE_INFO=" | 5h:${USAGE_COLOR}${FIVE_HOUR_PERCENT}%\033[0m"
    fi
fi

echo -e "[\033[36m$MODEL\033[0m] 📁 $DIR_NAME$GIT_BRANCH$CONTEXT_INFO$USAGE_INFO"
