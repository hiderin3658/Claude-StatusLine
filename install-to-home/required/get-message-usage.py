#!/usr/bin/env python3
"""
Claude Code メッセージ使用率計算スクリプト

5時間固定ウィンドウ内のメッセージ数を計算し、JSON形式で出力します。
ウィンドウ開始時刻から5時間経過したら自動的にリセットします。
クロスプラットフォーム対応（Windows/Mac/Linux）
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ウィンドウ状態管理ファイル
WINDOW_STATE_FILE = Path.home() / '.claude' / 'usage-window.json'

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

# モデル別の使用量倍率
# Opus は Sonnet の約7倍のリソースを消費する（実測値に基づく）
MODEL_WEIGHTS = {
    'opus': 7,      # Opus モデル（高性能・高コスト）
    'sonnet': 1,    # Sonnet モデル（標準）
    'haiku': 1,     # Haiku モデル（軽量）
}
DEFAULT_MODEL_WEIGHT = 1  # 不明なモデルのデフォルト倍率

def get_model_weight(model_name):
    """モデル名から使用量倍率を取得"""
    if not model_name:
        return DEFAULT_MODEL_WEIGHT

    model_lower = model_name.lower()
    for key, weight in MODEL_WEIGHTS.items():
        if key in model_lower:
            return weight

    return DEFAULT_MODEL_WEIGHT

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

def get_window_state():
    """ウィンドウ状態を取得"""
    if not WINDOW_STATE_FILE.exists():
        return None

    try:
        with open(WINDOW_STATE_FILE, 'r', encoding='utf-8') as f:
            state = json.load(f)
            return {
                'windowStart': datetime.fromisoformat(state['windowStart']),
                'firstMessageTimestamp': datetime.fromisoformat(state.get('firstMessageTimestamp', state['windowStart']))
            }
    except Exception:
        return None

def save_window_state(window_start, first_message_timestamp=None):
    """ウィンドウ状態を保存"""
    if first_message_timestamp is None:
        first_message_timestamp = window_start

    state = {
        'windowStart': window_start.isoformat(),
        'firstMessageTimestamp': first_message_timestamp.isoformat()
    }

    WINDOW_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(WINDOW_STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)

def should_reset_window(window_start, now):
    """ウィンドウをリセットすべきか判定（5時間経過したか）"""
    if window_start is None:
        return True

    elapsed = now - window_start
    return elapsed >= timedelta(hours=5)

def calculate_message_usage(window_hours=5, message_limit=None):
    """
    5時間固定ウィンドウ内のメッセージ使用数を計算（リセット機能付き）

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

    now = datetime.now(timezone.utc)

    # ウィンドウ状態を取得
    window_state = get_window_state()

    # リセット判定：5時間経過したかチェック
    if window_state is not None and should_reset_window(window_state['windowStart'], now):
        # 5時間経過 → ウィンドウをリセット（0%に戻す）
        if WINDOW_STATE_FILE.exists():
            WINDOW_STATE_FILE.unlink()

        # 0%を返す（次のメッセージで新しいウィンドウ開始）
        return {
            "plan": plan,
            "messageCount": 0,
            "messageLimit": message_limit,
            "messagePercent": 0,
            "remainingMessages": message_limit,
            "windowHours": window_hours,
            "windowStart": None,
            "windowEnd": None,
            "timeUntilReset": 0,
            "calculatedAt": now.isoformat(),
            "resetStatus": "Window expired - waiting for next message"
        }

    # ウィンドウ状態がない場合（初回 or リセット後の最初のメッセージ）
    if window_state is None:
        # 過去5時間以内のメッセージを検索して新しいウィンドウを開始
        window_start = now - timedelta(hours=window_hours)
    else:
        # 既存のウィンドウを使用
        window_start = window_state['windowStart']

    messages = []
    # アシスタント応答のモデル情報を保存（parentUuid -> model_name）
    assistant_models = {}

    # 全プロジェクトのログファイルを走査
    for jsonl_file in log_dir.rglob('*.jsonl'):
        try:
            # ファイルの最終更新日時がウィンドウ内かチェック（高速化）
            mtime = datetime.fromtimestamp(jsonl_file.stat().st_mtime, timezone.utc)
            if mtime < window_start:
                continue

            # JSONLファイルを1行ずつ読み込み（2パス：1回目でアシスタント応答を収集）
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue

                    try:
                        entry = json.loads(line)

                        # アシスタント応答からモデル情報を収集
                        event_type = entry.get('type', '')
                        if event_type == 'assistant':
                            parent_uuid = entry.get('parentUuid')
                            message = entry.get('message', {})
                            if isinstance(message, dict):
                                model_name = message.get('model', '')
                                if parent_uuid and model_name:
                                    assistant_models[parent_uuid] = model_name

                    except (json.JSONDecodeError, ValueError, KeyError):
                        continue
        except Exception:
            continue

    # 2回目のパス：ユーザーメッセージをカウント
    for jsonl_file in log_dir.rglob('*.jsonl'):
        try:
            mtime = datetime.fromtimestamp(jsonl_file.stat().st_mtime, timezone.utc)
            if mtime < window_start:
                continue

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
                            message = entry.get('message', {})
                            if isinstance(message, dict):
                                content = message.get('content', '')

                                # content が配列形式の場合の処理
                                if isinstance(content, list):
                                    # 配列が空の場合は除外
                                    if len(content) == 0:
                                        continue
                                    # 最初の要素が text オブジェクトかチェック
                                    first_item = content[0]
                                    if not isinstance(first_item, dict) or first_item.get('type') != 'text':
                                        continue
                                    # text の内容が空の場合は除外
                                    text_content = first_item.get('text', '')
                                    if not isinstance(text_content, str) or len(text_content.strip()) == 0:
                                        continue
                                # content が文字列形式の場合の処理
                                elif isinstance(content, str):
                                    if len(content.strip()) == 0:
                                        continue
                                else:
                                    # その他の形式は除外
                                    continue

                            # タイムスタンプの解析
                            ts_str = entry.get('timestamp')
                            msg_uuid = entry.get('uuid')
                            if ts_str:
                                # ISO 8601形式をパース
                                ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                                if ts > window_start:
                                    # 対応するアシスタント応答のモデルを取得
                                    model_name = assistant_models.get(msg_uuid, '')
                                    model_weight = get_model_weight(model_name)

                                    messages.append({
                                        'timestamp': ts.isoformat(),
                                        'file': str(jsonl_file.name),
                                        'model': model_name,
                                        'weight': model_weight
                                    })
                    except (json.JSONDecodeError, ValueError, KeyError):
                        continue
        except Exception:
            continue

    # 新しいウィンドウを開始する場合（初回 or リセット後の最初のメッセージ）
    if window_state is None and messages:
        # メッセージを時刻順にソート
        messages.sort(key=lambda m: m['timestamp'])

        # 最も古いメッセージの時刻を新しいウィンドウ開始時刻とする
        oldest_message_ts = datetime.fromisoformat(messages[0]['timestamp'])
        window_start = oldest_message_ts

        # ウィンドウ終了時刻を計算（開始時刻 + 5時間）
        window_end = window_start + timedelta(hours=window_hours)

        # ウィンドウ内（開始時刻から5時間以内）のメッセージのみに絞る
        messages = [
            m for m in messages
            if datetime.fromisoformat(m['timestamp']) < window_end
        ]

        # ウィンドウ状態を保存
        save_window_state(window_start, oldest_message_ts)

    # メッセージ数を集計（重み付けを適用）
    raw_message_count = len(messages)
    weighted_message_count = sum(m.get('weight', 1) for m in messages)
    message_percent = round((weighted_message_count / message_limit) * 100) if message_limit > 0 else 0
    remaining = max(0, message_limit - weighted_message_count)

    # モデル別の集計
    model_counts = {}
    for m in messages:
        model = m.get('model', 'unknown') or 'unknown'
        # モデル名を簡略化（例: claude-opus-4-5-20251101 → opus）
        if 'opus' in model.lower():
            model_key = 'opus'
        elif 'sonnet' in model.lower():
            model_key = 'sonnet'
        elif 'haiku' in model.lower():
            model_key = 'haiku'
        else:
            model_key = 'unknown'
        model_counts[model_key] = model_counts.get(model_key, 0) + 1

    # ウィンドウ終了時刻を計算
    window_end = window_start + timedelta(hours=window_hours)
    time_until_reset = window_end - now
    # リセットまでの時間が負の場合は0にする（既に期限切れ）
    time_until_reset_seconds = max(0, int(time_until_reset.total_seconds()))
    reset_at = window_end.isoformat()

    # 結果を返す
    return {
        "plan": plan,
        "messageCount": weighted_message_count,  # 重み付け後のカウント
        "rawMessageCount": raw_message_count,    # 重み付け前の実際のメッセージ数
        "messageLimit": message_limit,
        "messagePercent": message_percent,
        "remainingMessages": remaining,
        "windowHours": window_hours,
        "windowStart": window_start.isoformat(),
        "windowEnd": reset_at,
        "timeUntilReset": time_until_reset_seconds,
        "calculatedAt": now.isoformat(),
        "modelCounts": model_counts,  # モデル別のメッセージ数
        "modelWeights": MODEL_WEIGHTS  # 適用された倍率
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
