#!/bin/bash
# Claude Code ステータスライン ラッパースクリプト
# OS を自動判定して適切なスクリプトを呼び出す

# 標準入力を一時ファイルに保存（両OS で使用するため）
TEMP_INPUT=$(mktemp)
cat > "$TEMP_INPUT"

# OS 判定
OS_TYPE=$(uname -s)

case "$OS_TYPE" in
  MINGW* | MSYS* | CYGWIN*)
    # Windows (Git Bash)
    # PowerShell を呼び出して標準入力を渡す
    cat "$TEMP_INPUT" | powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$HOME/.claude/status-line.ps1"
    ;;
  Darwin | Linux)
    # macOS / Linux
    cat "$TEMP_INPUT" | bash "$HOME/.claude/status-line.sh"
    ;;
  *)
    echo "Unknown OS: $OS_TYPE"
    ;;
esac

# 一時ファイル削除
rm -f "$TEMP_INPUT"
