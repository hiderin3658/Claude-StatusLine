#!/bin/bash

# 標準入力から JSON を読み込む
input=$(cat)

# jq を使って値を抽出
CURRENT_DIR=$(echo "$input" | jq -r '.workspace.current_dir // "."')
DIR_NAME="${CURRENT_DIR##*/}"
[ -z "$DIR_NAME" ] && DIR_NAME="."

# モデル情報をJSONLログファイルから直接取得（個別インスタンス用）
# （Claude Codeが渡すモデル情報は/model切り替え時に更新されないバグがあるため）
TRANSCRIPT_PATH=$(echo "$input" | jq -r '.transcript_path // ""')
MODEL="Unknown"

if [ -n "$TRANSCRIPT_PATH" ] && [ -f "$TRANSCRIPT_PATH" ]; then
    # JSONLファイルの最後から100行を取得し、最新のassistantイベントのモデルを抽出
    RAW_MODEL=$(tail -100 "$TRANSCRIPT_PATH" 2>/dev/null | \
        grep '"type":"assistant"' | \
        tail -1 | \
        grep -o '"model":"[^"]*"' | \
        sed 's/"model":"//;s/"//')

    if [ -n "$RAW_MODEL" ]; then
        # モデル名を表示用にフォーマット（例: claude-opus-4-5-20251101 → Opus 4.5）
        if echo "$RAW_MODEL" | grep -qi "opus"; then
            MODEL="Opus 4.5"
        elif echo "$RAW_MODEL" | grep -qi "sonnet"; then
            MODEL="Sonnet 4.5"
        elif echo "$RAW_MODEL" | grep -qi "haiku"; then
            MODEL="Haiku"
        else
            # 不明なモデルの場合はそのまま表示
            MODEL="$RAW_MODEL"
        fi
    fi
fi

# フォールバック: JSONLから取得できなかった場合はClaude Codeが渡す情報を使用
if [ "$MODEL" = "Unknown" ]; then
    MODEL=$(echo "$input" | jq -r '.model.display_name // "Unknown"')
fi

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

# 5時間ウィンドウのトークン使用状況をキャッシュから取得
TOKEN_INFO=""
# キャッシュファイルのパス（ホームディレクトリ配下の .claude/cache/ を使用）
USAGE_CACHE="$HOME/.claude/cache/ccusage-cache.json"

if [ -f "$USAGE_CACHE" ]; then
    # キャッシュファイルが存在する場合
    # windowEnd を確認して、5時間ウィンドウが終了しているかチェック
    WINDOW_END=$(jq -r '.windowEnd // ""' "$USAGE_CACHE" 2>/dev/null)

    # ウィンドウ終了判定
    WINDOW_EXPIRED=false
    if [ -n "$WINDOW_END" ] && [ "$WINDOW_END" != "null" ]; then
        # windowEnd を Unix タイムスタンプに変換
        # タイムゾーン情報とミリ秒を除去してUTCとして扱う
        WINDOW_END_CLEAN="${WINDOW_END%%+*}"  # +00:00 を削除
        WINDOW_END_CLEAN="${WINDOW_END_CLEAN%%Z*}"  # Z を削除（ISO 8601形式対応）
        WINDOW_END_CLEAN="${WINDOW_END_CLEAN%%.*}"  # ミリ秒を削除
        # date コマンドの互換性対応（GNU date vs BSD date）
        # -u オプションで UTC として明示的に扱う
        WINDOW_END_EPOCH=$(date -u -d "$WINDOW_END_CLEAN" +%s 2>/dev/null || date -u -j -f "%Y-%m-%dT%H:%M:%S" "$WINDOW_END_CLEAN" +%s 2>/dev/null || echo 0)
        CURRENT_EPOCH=$(date -u +%s)

        if [ "$WINDOW_END_EPOCH" -gt 0 ] && [ "$CURRENT_EPOCH" -gt "$WINDOW_END_EPOCH" ]; then
            WINDOW_EXPIRED=true
        fi
    fi

    if [ "$WINDOW_EXPIRED" = true ]; then
        # ウィンドウが終了している場合は 0% を表示（緑色）
        TOKEN_INFO=" | 5h:\033[32m0%\033[0m"
    else
        # トークンベースの使用率を取得（tokenPercent を優先、なければ messagePercent を使用）
        TOKEN_PERCENT=$(jq -r '.tokenPercent // .messagePercent // 0' "$USAGE_CACHE" 2>/dev/null)

        if [ -n "$TOKEN_PERCENT" ] && [ "$TOKEN_PERCENT" != "null" ]; then
            # 使用率から色を決定
            # 50%未満 → 緑
            # 50-80% → 黄色
            # 80%以上 → 赤
            if [ "$TOKEN_PERCENT" -ge 80 ] 2>/dev/null; then
                TOKEN_COLOR="\033[31m"  # 赤
            elif [ "$TOKEN_PERCENT" -ge 50 ] 2>/dev/null; then
                TOKEN_COLOR="\033[33m"  # 黄
            else
                TOKEN_COLOR="\033[32m"  # 緑
            fi

            TOKEN_INFO=" | 5h:${TOKEN_COLOR}${TOKEN_PERCENT}%\033[0m"
        fi
    fi
fi

echo -e "[\033[36m$MODEL\033[0m] 📁 $DIR_NAME$GIT_BRANCH$CONTEXT_INFO$USAGE_INFO$TOKEN_INFO"
