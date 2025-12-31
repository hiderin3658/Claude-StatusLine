#!/usr/bin/env python3
"""
Claude Code メッセージ使用率計算スクリプト

5時間ローリングウィンドウ内のメッセージ数を計算し、JSON形式で出力します。
クロスプラットフォーム対応（Windows/Mac/Linux）
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Claude Code のログディレクトリ（クロスプラットフォーム対応）
def get_log_directory():
    """Claude Code のログディレクトリパスを取得"""
    home = Path.home()

    # 優先順位で複数のパスを確認
    possible_paths = [
        home / '.claude' / 'projects',  # 新バージョン（全OS共通）
        home / '.config' / 'claude' / 'projects',  # 旧バージョン（macOS/Linux）
    ]

    if sys.platform == 'win32':
        # Windows の APPDATA も確認
        appdata = os.environ.get('APPDATA', '')
        if appdata:
            possible_paths.append(Path(appdata) / 'Claude' / 'projects')

    # 存在するパスを返す
    for path in possible_paths:
        if path.exists():
            return path

    # 見つからない場合はデフォルトパスを返す
    return home / '.claude' / 'projects'

# プラン別メッセージ制限（5時間ウィンドウ）
MESSAGE_LIMITS = {
    'free': 15,        # Free プラン（推定）
    'pro': 45,         # Pro プラン（$20/月）
    'max-100': 225,    # MAX プラン $100/月（Pro の 5倍）
    'max-200': 900,    # MAX プラン $200/月（Pro の 20倍）
}

DEFAULT_PLAN = 'pro'

def get_plan_config():
    """プラン設定を読み込む"""
    config_file = Path.home() / '.claude' / 'usage-config.json'

    try:
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                plan = config.get('plan', DEFAULT_PLAN)
                return plan
    except Exception:
        pass

    return DEFAULT_PLAN

def get_message_limit():
    """現在のプランに応じたメッセージ制限を取得"""
    plan = get_plan_config()
    return MESSAGE_LIMITS.get(plan, MESSAGE_LIMITS[DEFAULT_PLAN])

def calculate_message_usage(window_hours=5, message_limit=None):
    """
    5時間ウィンドウ内のメッセージ使用数を計算

    Args:
        window_hours: ウィンドウの時間（デフォルト5時間）
        message_limit: メッセージ数の上限（デフォルト250）

    Returns:
        dict: メッセージ使用状況
    """
    # メッセージ制限が指定されていない場合、プラン設定から取得
    if message_limit is None:
        message_limit = get_message_limit()

    plan = get_plan_config()
    log_dir = get_log_directory()

    if not log_dir.exists():
        return {
            "error": f"Log directory not found: {log_dir}",
            "messageCount": 0,
            "messageLimit": message_limit,
            "messagePercent": 0
        }

    messages = []
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=window_hours)

    # 全プロジェクトのログファイルを走査
    for jsonl_file in log_dir.rglob('*.jsonl'):
        try:
            # ファイルの最終更新日時がウィンドウ内かチェック（高速化）
            mtime = datetime.fromtimestamp(jsonl_file.stat().st_mtime, timezone.utc)
            if mtime < window_start:
                continue

            # JSONLファイルを1行ずつ読み込み
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue

                    try:
                        entry = json.loads(line)

                        # ユーザーメッセージ送信イベントを特定
                        event_type = entry.get('type', '')
                        if event_type in ['UserPromptSubmit', 'user_prompt', 'user']:
                            # サイドチェーン（サブエージェント）のメッセージを除外
                            is_sidechain = entry.get('isSidechain', False)
                            if is_sidechain:
                                continue

                            # 実際のユーザーメッセージのみをカウント
                            # contentが文字列型で、かつ空でない場合のみ
                            message = entry.get('message', {})
                            if isinstance(message, dict):
                                content = message.get('content', '')
                                # contentが文字列でない、または空の場合は除外
                                if not isinstance(content, str) or len(content.strip()) == 0:
                                    continue

                            # タイムスタンプの解析
                            ts_str = entry.get('timestamp')
                            if ts_str:
                                # ISO 8601形式をパース
                                ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                                if ts > window_start:
                                    messages.append({
                                        'timestamp': ts.isoformat(),
                                        'file': str(jsonl_file.name)
                                    })
                    except (json.JSONDecodeError, ValueError, KeyError):
                        continue
        except Exception:
            continue

    # メッセージ数を集計
    message_count = len(messages)
    message_percent = round((message_count / message_limit) * 100) if message_limit > 0 else 0
    remaining = max(0, message_limit - message_count)

    # 結果を返す
    return {
        "plan": plan,
        "messageCount": message_count,
        "messageLimit": message_limit,
        "messagePercent": message_percent,
        "remainingMessages": remaining,
        "windowHours": window_hours,
        "windowStart": window_start.isoformat(),
        "calculatedAt": now.isoformat()
    }

def main():
    """メイン処理"""
    try:
        # メッセージ使用率を計算
        usage = calculate_message_usage()

        # JSON形式で出力
        print(json.dumps(usage, indent=2))

        # 終了コード（使用率が80%以上なら警告）
        if usage.get('messagePercent', 0) >= 80:
            sys.exit(1)
        else:
            sys.exit(0)
    except Exception as e:
        # エラー時もJSON形式で出力
        error_data = {
            "error": str(e),
            "plan": get_plan_config(),
            "messageCount": 0,
            "messageLimit": get_message_limit(),
            "messagePercent": 0
        }
        print(json.dumps(error_data, indent=2))
        sys.exit(2)

if __name__ == "__main__":
    main()
