#!/bin/bash

# 手動で /usage の情報を保存するヘルパースクリプト
# 使い方: ~/.claude/save-usage.sh <5時間制限のパーセント>
# 例: ~/.claude/save-usage.sh 3

CACHE_FILE="/tmp/claude-usage-cache.json"

if [ $# -eq 0 ]; then
    echo "使い方: $0 <5時間制限のパーセント>"
    echo "例: $0 3  # 3% の場合"
    exit 1
fi

FIVE_HOUR_PERCENT=$1

# 現在時刻を記録
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# JSON ファイルを作成
cat > "$CACHE_FILE" <<EOF
{
  "five_hour": {
    "utilization": $(echo "scale=2; $FIVE_HOUR_PERCENT / 100" | bc),
    "updated_at": "$TIMESTAMP"
  }
}
EOF

echo "✅ 使用率 ${FIVE_HOUR_PERCENT}% を保存しました"
echo "📁 保存先: $CACHE_FILE"
