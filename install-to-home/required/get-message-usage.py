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

# プラン別メッセージ制限（5時間ウィンドウ）- レガシー
MESSAGE_LIMITS = {
    'free': 15,        # Free プラン（推定）
    'pro': 45,         # Pro プラン（$20/月）
    'max-100': 225,    # MAX プラン $100/月（Pro の 5倍）
    'max-200': 900,    # MAX プラン $200/月（Pro の 20倍）
}

# プラン別コスト制限（5時間ウィンドウ）
# 公式の使用率表示から逆算した推定値
# Max $100: /usage 30%時点の実測値から逆算 (5,777,518 / 0.30 ≈ 19,000,000)
TOKEN_LIMITS = {
    'free': 170000,        # 15 msg × 約11K tokens
    'pro': 500000,         # 45 msg × 約11K tokens
    'max-100': 19000000,   # /usage との比較から調整（Sonnet使用時: 30%で校正）
    'max-200': 38000000,   # max-100 の 2倍
}

# モデル別の使用量倍率（API価格ベース: Opus $5, Sonnet $3, Haiku $1 per MTok）
# Opus: Sonnet の 1.67倍, Sonnet: 基準, Haiku: Sonnet の 0.33倍
MODEL_WEIGHTS = {
    'opus': 1.67,   # Opus モデル（$5/$3 = 1.67倍）
    'sonnet': 1.0,  # Sonnet モデル（基準）
    'haiku': 0.33,  # Haiku モデル（$1/$3 = 0.33倍）
}
DEFAULT_MODEL_WEIGHT = 1.0  # 不明なモデルのデフォルト倍率

# コスト係数（Anthropic 価格ベース）
CACHE_READ_COEFFICIENT = 0.1      # キャッシュ読み取り: 入力の 10%
CACHE_CREATION_COEFFICIENT = 1.25 # キャッシュ作成: 入力の 1.25倍
OUTPUT_COEFFICIENT = 5.0          # 出力: 入力の 5倍

def load_calibration_data():
    """
    キャリブレーションデータを読み込む

    Returns:
        dict or None: キャリブレーションデータ（存在しない場合はNone）
    """
    calibration_file = Path.home() / '.claude' / 'usage-calibration.json'

    if not calibration_file.exists():
        return None

    try:
        with open(calibration_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 有効なキャリブレーションデータか確認
            if data.get('current_limit') and data.get('confidence', 0) > 0:
                return data
            return None
    except (json.JSONDecodeError, OSError):
        return None

def get_token_limit(plan):
    """
    プランのトークン制限値を取得（キャリブレーションデータ優先）

    Args:
        plan: プラン名（'free', 'pro', 'max-100', 'max-200'）

    Returns:
        int: トークン制限値
    """
    # キャリブレーションデータを確認
    calibration_data = load_calibration_data()

    if calibration_data and calibration_data.get('plan') == plan:
        limit = calibration_data.get('current_limit')
        confidence = calibration_data.get('confidence', 0)

        if limit and confidence > 0:
            # デバッグ情報（stderr に出力）
            print(f"[INFO] キャリブレーション済み制限値を使用: {limit:,.0f} (信頼度: {confidence*100:.0f}%)",
                  file=sys.stderr)
            return int(limit)

    # キャリブレーションデータがない場合はデフォルト値
    return TOKEN_LIMITS.get(plan, 500000)

def get_model_weight(model_name):
    """モデル名から使用量倍率を取得"""
    if not model_name:
        return DEFAULT_MODEL_WEIGHT

    model_lower = model_name.lower()
    for key, weight in MODEL_WEIGHTS.items():
        if key in model_lower:
            return weight

    return DEFAULT_MODEL_WEIGHT

def calculate_weighted_tokens(usage, model_name):
    """
    重み付けトークン数を計算（コストベース）

    Args:
        usage: usage オブジェクト（assistant イベントから取得）
        model_name: モデル名

    Returns:
        dict: 重み付け後のトークン情報

    計算式:
        effective_cost = (input * 1.0 + cache_creation * 1.25 + cache_read * 0.1 + output * 5.0) * model_weight
    """
    weight = get_model_weight(model_name)

    # 入力トークン（各種）
    input_tokens = usage.get('input_tokens', 0)
    cache_creation = usage.get('cache_creation_input_tokens', 0)
    cache_read = usage.get('cache_read_input_tokens', 0)

    # 出力トークン
    output_tokens = usage.get('output_tokens', 0)

    # コストベースの実効トークン数を計算
    # - 入力: 1.0倍（基準）
    # - キャッシュ作成: 1.25倍
    # - キャッシュ読み取り: 0.1倍（90%割引）
    # - 出力: 5.0倍
    effective_input = (
        input_tokens * 1.0 +
        cache_creation * CACHE_CREATION_COEFFICIENT +
        cache_read * CACHE_READ_COEFFICIENT
    )
    effective_output = output_tokens * OUTPUT_COEFFICIENT

    # モデル重み付け適用
    weighted_input = effective_input * weight
    weighted_output = effective_output * weight

    return {
        'raw_input': input_tokens + cache_creation + cache_read,
        'raw_output': output_tokens,
        'weighted_input': weighted_input,
        'weighted_output': weighted_output,
        'total_weighted': weighted_input + weighted_output
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
    except (json.JSONDecodeError, OSError) as e:
        # 設定ファイルの読み込みに失敗した場合はデフォルトを使用
        print(f"Warning: Failed to read config file: {e}", file=sys.stderr)
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
            result = {
                'windowStart': datetime.fromisoformat(state['windowStart']),
                'firstMessageTimestamp': datetime.fromisoformat(state.get('firstMessageTimestamp', state['windowStart']))
            }
            # リセットタイムスタンプがあれば含める
            if 'resetTimestamp' in state:
                result['resetTimestamp'] = datetime.fromisoformat(state['resetTimestamp'])
            return result
    except (json.JSONDecodeError, KeyError, ValueError, OSError) as e:
        print(f"Warning: Failed to read window state: {e}", file=sys.stderr)
        return None

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

    # ウィンドウ状態の確認
    if window_state is None:
        # usage-window.json が存在しない
        # デーモンが起動していないか、まだウィンドウが初期化されていない
        # トークン制限値を取得
        token_limit = get_token_limit(plan)

        print(f"Warning: Window state not found. Daemon may not be running.", file=sys.stderr)

        # 0%を返す（デーモン起動待ち）
        return {
            "plan": plan,
            "windowHours": window_hours,
            "windowStart": None,
            "windowEnd": None,
            "timeUntilReset": 0,
            "calculatedAt": now.isoformat(),

            # トークンベースの使用量（待機中は0）
            "tokens": {
                "raw": {"input": 0, "output": 0, "cache_creation": 0, "cache_read": 0, "total": 0},
                "weighted": {"input": 0, "output": 0, "total": 0}
            },
            "modelBreakdown": {},

            # トークン制限と使用率（待機中は0%）
            "tokenLimit": token_limit,
            "tokenPercent": 0,
            "remainingTokens": token_limit,

            # レガシー: メッセージベースの情報
            "legacy": {
                "messageCount": 0,
                "rawMessageCount": 0,
                "messageLimit": message_limit,
                "messagePercent": 0,
                "remainingMessages": message_limit,
                "modelCounts": {},
                "modelWeights": MODEL_WEIGHTS
            },

            # 後方互換性
            "messagePercent": 0,
            "resetStatus": "Waiting for daemon to initialize window"
        }

    if 'resetTimestamp' in window_state:
        # リセット直後（resetTimestamp が記録されている）
        # リセット時点以降のメッセージのみをカウントするため、
        # リセットタイムスタンプを window_start として使用
        reset_timestamp = window_state['resetTimestamp']
        window_start = reset_timestamp
    else:
        # 通常動作（既存のウィンドウを継続）
        window_start = window_state['windowStart']
        reset_timestamp = None

    messages = []
    # アシスタント応答のモデル情報を保存（parentUuid -> model_name）
    assistant_models = {}
    # トークン使用量情報を保存
    token_usage_data = {
        'raw': {'input': 0, 'output': 0, 'cache_creation': 0, 'cache_read': 0, 'total': 0},
        'weighted': {'input': 0, 'output': 0, 'total': 0},
        'by_model': {}
    }

    # 全プロジェクトのログファイルを1回で走査（パフォーマンス改善）
    for jsonl_file in log_dir.rglob('*.jsonl'):
        try:
            # ファイルの最終更新日時がウィンドウ内かチェック（高速化）
            # タイムゾーン混在を防ぐため、明示的にUTC変換
            mtime_local = datetime.fromtimestamp(jsonl_file.stat().st_mtime)
            mtime = mtime_local.astimezone(timezone.utc)
            if mtime < window_start:
                continue

            # JSONLファイルを1行ずつ読み込み（assistantとuserを同時に処理）
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue

                    try:
                        entry = json.loads(line)
                        event_type = entry.get('type', '')

                        # アシスタント応答からモデル情報とトークン使用量を収集
                        if event_type == 'assistant':
                            parent_uuid = entry.get('parentUuid')
                            message = entry.get('message', {})
                            if isinstance(message, dict):
                                model_name = message.get('model', '')
                                if parent_uuid and model_name:
                                    assistant_models[parent_uuid] = model_name

                                # トークン使用量を取得
                                usage = message.get('usage', {})
                                ts_str = entry.get('timestamp')

                                # 最終応答のみをカウント（usage が存在し、output_tokens > 0）
                                # stop_reasonがnullの場合もカウント（ストリーミング中のイベント対応）
                                if usage and ts_str and usage.get('output_tokens', 0) > 0:
                                    ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                                    if ts > window_start:
                                        # 重み付けトークン数を計算
                                        weighted = calculate_weighted_tokens(usage, model_name)

                                        # 生トークン数を集計
                                        input_tokens = usage.get('input_tokens', 0)
                                        output_tokens = usage.get('output_tokens', 0)
                                        cache_creation = usage.get('cache_creation_input_tokens', 0)
                                        cache_read = usage.get('cache_read_input_tokens', 0)

                                        token_usage_data['raw']['input'] += input_tokens
                                        token_usage_data['raw']['output'] += output_tokens
                                        token_usage_data['raw']['cache_creation'] += cache_creation
                                        token_usage_data['raw']['cache_read'] += cache_read

                                        # 重み付けトークン数を集計
                                        token_usage_data['weighted']['input'] += weighted['weighted_input']
                                        token_usage_data['weighted']['output'] += weighted['weighted_output']
                                        token_usage_data['weighted']['total'] += weighted['total_weighted']

                                        # モデル別の集計
                                        model_key = 'unknown'
                                        if 'opus' in model_name.lower():
                                            model_key = 'opus'
                                        elif 'sonnet' in model_name.lower():
                                            model_key = 'sonnet'
                                        elif 'haiku' in model_name.lower():
                                            model_key = 'haiku'

                                        if model_key not in token_usage_data['by_model']:
                                            token_usage_data['by_model'][model_key] = {
                                                'requests': 0,
                                                'rawTokens': 0,
                                                'weightedTokens': 0
                                            }

                                        token_usage_data['by_model'][model_key]['requests'] += 1
                                        token_usage_data['by_model'][model_key]['rawTokens'] += weighted['raw_input'] + weighted['raw_output']
                                        token_usage_data['by_model'][model_key]['weightedTokens'] += weighted['total_weighted']

                        # ユーザーメッセージ送信イベントを処理
                        elif event_type in ['UserPromptSubmit', 'user_prompt', 'user']:
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

                    except (json.JSONDecodeError, ValueError, KeyError) as e:
                        # JSONパースエラーや予期されるキーエラーは無視
                        continue
        except OSError as e:
            # ファイル読み込みエラー
            print(f"Warning: Failed to read file {jsonl_file}: {e}", file=sys.stderr)
            continue
        except Exception as e:
            # その他の予期しないエラー
            print(f"Error processing file {jsonl_file}: {e}", file=sys.stderr)
            continue

    # 新しいウィンドウを開始する場合（初回 or リセット後の最初のメッセージ）
    # reset_timestamp が存在する場合もリセット後の最初のメッセージとして扱う
    should_start_new_window = (window_state is None or reset_timestamp is not None) and messages

    if should_start_new_window:
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

        # ウィンドウ状態を保存（resetTimestamp をクリア）
        save_window_state(window_start, oldest_message_ts, reset_timestamp=None)

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

    # トークン使用量の合計値を計算
    total_raw_tokens = (
        token_usage_data['raw']['input'] +
        token_usage_data['raw']['output'] +
        token_usage_data['raw']['cache_creation'] +
        token_usage_data['raw']['cache_read']
    )
    token_usage_data['raw']['total'] = total_raw_tokens

    # トークン制限値を取得（キャリブレーション値または推定値）
    token_limit = get_token_limit(plan)

    # トークンベースの使用率を計算
    weighted_tokens = token_usage_data['weighted']['total']
    token_percent = round((weighted_tokens / token_limit) * 100) if token_limit > 0 else 0
    remaining_tokens = max(0, token_limit - weighted_tokens)

    # 結果を返す
    return {
        "plan": plan,
        "windowHours": window_hours,
        "windowStart": window_start.isoformat(),
        "windowEnd": reset_at,
        "timeUntilReset": time_until_reset_seconds,
        "calculatedAt": now.isoformat(),

        # トークンベースの使用量（メイン）
        "tokens": {
            "raw": token_usage_data['raw'],
            "weighted": token_usage_data['weighted']
        },
        "modelBreakdown": token_usage_data['by_model'],

        # トークン制限と使用率
        "tokenLimit": token_limit,
        "tokenPercent": token_percent,
        "remainingTokens": remaining_tokens,

        # レガシー: メッセージベースの情報（後方互換性）
        "legacy": {
            "messageCount": weighted_message_count,
            "rawMessageCount": raw_message_count,
            "messageLimit": message_limit,
            "messagePercent": message_percent,
            "remainingMessages": remaining,
            "modelCounts": model_counts,
            "modelWeights": MODEL_WEIGHTS
        },

        # 後方互換性のため、トップレベルにも messagePercent を残す
        "messagePercent": token_percent  # トークンベースの使用率を表示
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
