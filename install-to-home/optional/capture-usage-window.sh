#!/bin/bash
# /usage を表示しているターミナルウィンドウからパーセントを取得するスクリプト

CACHE_FILE="/tmp/claude-usage-cache.json"
WORK_DIR="$HOME/.claude/ocr-temp"
LOG_FILE="$WORK_DIR/capture.log"

mkdir -p "$WORK_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Terminalウィンドウの位置とサイズを取得
get_terminal_windows() {
    osascript -l JavaScript -e '
    var app = Application("System Events");
    var terminalApp = app.processes.byName("Terminal");
    var windows = terminalApp.windows();
    var result = [];

    for (var i = 0; i < windows.length; i++) {
        var w = windows[i];
        var pos = w.position();
        var size = w.size();
        result.push({
            index: i,
            name: w.name(),
            x: pos[0],
            y: pos[1],
            width: size[0],
            height: size[1]
        });
    }
    JSON.stringify(result);
    ' 2>/dev/null
}

# 指定領域をキャプチャしてOCR
capture_and_ocr() {
    local x=$1
    local y=$2
    local width=$3
    local height=$4
    local screenshot="$WORK_DIR/usage_window.png"

    # 指定領域をキャプチャ
    screencapture -R"$x,$y,$width,$height" -x "$screenshot" 2>/dev/null

    if [[ ! -f "$screenshot" ]]; then
        log "Screenshot failed"
        return 1
    fi

    # OCR実行
    local ocr_output=$(tesseract "$screenshot" stdout 2>/dev/null)

    # パーセントを抽出（"X% used" または "X%" パターン）
    local percentage=$(echo "$ocr_output" | grep -oE '[0-9]+%' | head -1 | tr -d '%')

    if [[ -n "$percentage" ]]; then
        echo "$percentage"
        return 0
    fi

    return 1
}

# メイン処理
main() {
    log "Starting capture..."

    # ウィンドウ一覧を取得
    local windows=$(get_terminal_windows)
    log "Windows: $windows"

    if [[ -z "$windows" || "$windows" == "[]" ]]; then
        log "No Terminal windows found"
        exit 1
    fi

    # 複数ウィンドウがある場合、最初のウィンドウ以外を対象とする
    # （最初のウィンドウはclaude実行中と仮定）
    local window_count=$(echo "$windows" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null)

    if [[ "$window_count" -lt 2 ]]; then
        log "Need at least 2 Terminal windows (one for claude, one for /usage)"
        echo "Error: /usage用の別ウィンドウが必要です"
        exit 1
    fi

    # 2番目のウィンドウ（/usage表示用）の情報を取得
    local x=$(echo "$windows" | python3 -c "import sys,json; w=json.load(sys.stdin)[1]; print(int(w['x']))" 2>/dev/null)
    local y=$(echo "$windows" | python3 -c "import sys,json; w=json.load(sys.stdin)[1]; print(int(w['y']))" 2>/dev/null)
    local width=$(echo "$windows" | python3 -c "import sys,json; w=json.load(sys.stdin)[1]; print(int(w['width']))" 2>/dev/null)
    local height=$(echo "$windows" | python3 -c "import sys,json; w=json.load(sys.stdin)[1]; print(int(w['height']))" 2>/dev/null)

    log "Target window: x=$x, y=$y, width=$width, height=$height"

    # キャプチャしてOCR
    local percentage=$(capture_and_ocr "$x" "$y" "$width" "$height")

    if [[ -n "$percentage" ]]; then
        log "Extracted percentage: $percentage%"

        # キャッシュファイルを更新
        cat > "$CACHE_FILE" << EOF
{
  "session": {
    "utilization": $(echo "scale=4; $percentage / 100" | bc),
    "updated_at": "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  }
}
EOF
        echo "Success: $percentage%"
    else
        log "Failed to extract percentage"
        echo "Error: パーセントの抽出に失敗しました"
        exit 1
    fi
}

main "$@"
