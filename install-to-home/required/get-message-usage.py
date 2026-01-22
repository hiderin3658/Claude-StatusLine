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
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ウィンドウ状態管理ファイル
WINDOW_STATE_FILE = Path.home() / '.claude' / 'usage-window.json'

# パフォーマンスチューニング定数
MAX_FILES_TO_CHECK = 10  # 初回起動時にチェックする最新ファイル数
MAX_LINES_TO_READ = 1000  # 大きなファイルからの逆順読み込み行数制限

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

# モデル別の重み係数（weighted_tokens計算用、後方互換性のため維持）
# 注: 使用率計算は model-calibration.json の設定を使用
MODEL_WEIGHTS = {
    'sonnet': 1.0,  # Sonnet モデル（基準）
    'haiku': 0.33,  # Haiku モデル（API価格ベース: $1/$3）
    'opus': 1.0,    # Opus モデル（使用率計算は補間関数を使用）
}
DEFAULT_MODEL_WEIGHT = 1.0  # 不明なモデルのデフォルト倍率

# コスト係数（Anthropic 価格ベース）
CACHE_READ_COEFFICIENT = 0.1      # キャッシュ読み取り: 入力の 10%
CACHE_CREATION_COEFFICIENT = 1.25 # キャッシュ作成: 入力の 1.25倍
OUTPUT_COEFFICIENT = 5.0          # 出力: 入力の 5倍

# モデルキャリブレーション設定ファイル
MODEL_CALIBRATION_FILE = Path.home() / '.claude' / 'model-calibration.json'

# デフォルトのモデル設定（設定ファイルがない場合のフォールバック）
DEFAULT_MODEL_CONFIG = {
    "type": "weight",
    "weight": 1.0,
    "base_limit": 24000000
}

# キャッシュ（設定ファイルの再読み込みを防ぐ）
_model_calibration_cache = None

def load_model_calibration():
    """
    モデルキャリブレーション設定を読み込む（キャッシュ付き）

    Returns:
        dict: キャリブレーション設定
    """
    global _model_calibration_cache

    if _model_calibration_cache is not None:
        return _model_calibration_cache

    if not MODEL_CALIBRATION_FILE.exists():
        # デフォルト設定を返す
        _model_calibration_cache = {
            "models": {},
            "fallback_patterns": {},
            "default": DEFAULT_MODEL_CONFIG
        }
        return _model_calibration_cache

    try:
        with open(MODEL_CALIBRATION_FILE, 'r', encoding='utf-8') as f:
            _model_calibration_cache = json.load(f)
            return _model_calibration_cache
    except (json.JSONDecodeError, OSError) as e:
        print(f"Warning: Failed to load model calibration: {e}", file=sys.stderr)
        _model_calibration_cache = {
            "models": {},
            "fallback_patterns": {},
            "default": DEFAULT_MODEL_CONFIG
        }
        return _model_calibration_cache

def get_model_config(model_name):
    """
    モデル名からキャリブレーション設定を取得

    Args:
        model_name: モデル名（例: 'claude-opus-4-5-20251101'）

    Returns:
        tuple: (model_key, config) - モデルキーと設定のタプル
    """
    calibration = load_model_calibration()
    model_lower = model_name.lower() if model_name else ''

    # 1. 完全一致を試す（models）
    for model_key, config in calibration.get('models', {}).items():
        patterns = config.get('match_patterns', [])
        for pattern in patterns:
            if pattern.lower() in model_lower:
                # inherit_from があれば継承元の設定を取得
                if 'inherit_from' in config:
                    inherited = calibration.get('models', {}).get(config['inherit_from'], {})
                    merged = {**inherited, **config}
                    return model_key, merged
                return model_key, config

    # 2. フォールバックパターンを試す
    for model_key, config in calibration.get('fallback_patterns', {}).items():
        patterns = config.get('match_patterns', [])
        for pattern in patterns:
            if pattern.lower() in model_lower:
                # inherit_from があれば継承元の設定を取得
                if 'inherit_from' in config:
                    inherited = calibration.get('models', {}).get(config['inherit_from'], {})
                    merged = {**inherited, **config}
                    return model_key, merged
                return model_key, config

    # 3. デフォルト設定を返す
    return 'unknown', calibration.get('default', DEFAULT_MODEL_CONFIG)

def interpolate_percent(raw_tokens, data_points):
    """
    生トークン数から使用率を補間計算（汎用関数）

    Args:
        raw_tokens: 生トークン数
        data_points: キャリブレーションデータポイントのリスト

    Returns:
        float: 推定使用率（%）
    """
    if not data_points or len(data_points) < 1:
        return 0.0

    # データポイントをトークン数でソート
    sorted_points = sorted(data_points, key=lambda x: x.get('raw_tokens', 0))

    if raw_tokens <= 0:
        return 0.0

    # 最小値より小さい場合：比例計算
    first_point = sorted_points[0]
    if raw_tokens <= first_point.get('raw_tokens', 0):
        if first_point.get('raw_tokens', 0) > 0:
            ratio = raw_tokens / first_point['raw_tokens']
            return first_point.get('percent', 0) * ratio
        return 0.0

    # 最大値より大きい場合：外挿
    last_point = sorted_points[-1]
    if raw_tokens >= last_point.get('raw_tokens', 0):
        if len(sorted_points) >= 2:
            x1 = sorted_points[-2].get('raw_tokens', 0)
            y1 = sorted_points[-2].get('percent', 0)
            x2 = last_point.get('raw_tokens', 0)
            y2 = last_point.get('percent', 0)
            slope = (y2 - y1) / (x2 - x1) if x2 != x1 else 0
            return y2 + slope * (raw_tokens - x2)
        else:
            return last_point.get('percent', 0)

    # 補間：該当する区間を探す
    for i in range(len(sorted_points) - 1):
        x1 = sorted_points[i].get('raw_tokens', 0)
        y1 = sorted_points[i].get('percent', 0)
        x2 = sorted_points[i + 1].get('raw_tokens', 0)
        y2 = sorted_points[i + 1].get('percent', 0)

        if x1 <= raw_tokens <= x2:
            # 線形補間
            if x2 == x1:
                return y1
            ratio = (raw_tokens - x1) / (x2 - x1)
            return y1 + (y2 - y1) * ratio

    # フォールバック
    return last_point.get('percent', 0)

def calculate_model_percent(model_key, config, raw_tokens, weighted_tokens, base_limit):
    """
    モデルの使用率を計算（汎用関数）

    Args:
        model_key: モデルキー
        config: モデルのキャリブレーション設定
        raw_tokens: 生トークン数
        weighted_tokens: 重み付けトークン数
        base_limit: ベース制限値

    Returns:
        float: 使用率（%）
    """
    calc_type = config.get('type', 'weight')

    if calc_type == 'interpolate':
        # 非線形補間
        data_points = config.get('data_points', [])
        if data_points:
            return interpolate_percent(raw_tokens, data_points)
        # データポイントがない場合はweight方式にフォールバック
        calc_type = 'weight'

    if calc_type == 'limit':
        # 制限値ベース
        limit = config.get('limit', base_limit)
        if limit > 0:
            return (weighted_tokens / limit) * 100
        return 0.0

    # weight方式（デフォルト）
    weight = config.get('weight', 1.0)
    model_limit = config.get('base_limit', base_limit)
    if model_limit > 0:
        return (weighted_tokens / model_limit) * 100
    return 0.0

def get_model_key_from_name(model_name):
    """
    モデル名から簡略化されたモデルキーを取得

    Args:
        model_name: フルモデル名

    Returns:
        str: 簡略化されたモデルキー（opus, sonnet, haiku, unknown）
    """
    model_key, _ = get_model_config(model_name)

    # モデルキーからベース名を抽出（opus-4.5 → opus）
    if 'opus' in model_key.lower():
        return 'opus'
    elif 'sonnet' in model_key.lower():
        return 'sonnet'
    elif 'haiku' in model_key.lower():
        return 'haiku'
    return 'unknown'

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

def save_window_state(window_start, first_message_timestamp=None, reset_timestamp=None):
    """ウィンドウ状態を保存"""
    if first_message_timestamp is None:
        first_message_timestamp = window_start

    state = {
        'windowStart': window_start.isoformat(),
        'firstMessageTimestamp': first_message_timestamp.isoformat()
    }

    # リセットタイムスタンプがあれば保存
    if reset_timestamp is not None:
        state['resetTimestamp'] = reset_timestamp.isoformat()

    WINDOW_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(WINDOW_STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)

def round_to_hour_utc(dt):
    """
    日時をUTC基準で正時（〇〇:00:00）に切り捨てる

    Args:
        dt: datetime オブジェクト（タイムゾーン付き）

    Returns:
        datetime: 正時に丸められた datetime
    """
    if dt is None:
        return None

    # UTCに変換
    dt_utc = dt.astimezone(timezone.utc)

    # 分・秒・マイクロ秒を0にして正時に丸める
    rounded = dt_utc.replace(minute=0, second=0, microsecond=0)

    return rounded


def should_reset_window(window_start, now):
    """ウィンドウをリセットすべきか判定（5時間経過したか）"""
    if window_start is None:
        return True

    # 正時に丸めた開始時刻から5時間経過したかチェック
    rounded_start = round_to_hour_utc(window_start)
    elapsed = now - rounded_start
    return elapsed >= timedelta(hours=5)

def find_latest_activity(log_dir):
    """
    ログから最新のアクティビティ（assistant応答）のタイムスタンプを探す

    Args:
        log_dir: Claude Code のログディレクトリパス

    Returns:
        datetime: 最新のアクティビティタイムスタンプ（見つからない場合はNone）
    """
    latest_ts = None

    try:
        # 全プロジェクトのログファイルを走査（更新日時でソート）
        jsonl_files = sorted(log_dir.rglob('*.jsonl'), key=lambda f: f.stat().st_mtime, reverse=True)

        # 最新のN個のファイルのみチェック（パフォーマンス考慮）
        for jsonl_file in jsonl_files[:MAX_FILES_TO_CHECK]:
            try:
                with open(jsonl_file, 'r', encoding='utf-8') as f:
                    # メモリ枯渇を防ぐため、末尾の限られた行数のみ読み込む
                    lines = deque(f, maxlen=MAX_LINES_TO_READ)

                    # ファイルを逆順で読む（最新イベントから）
                    for line in reversed(lines):
                        if not line.strip():
                            continue

                        try:
                            entry = json.loads(line)

                            # assistant応答を探す
                            if entry.get('type') == 'assistant':
                                ts_str = entry.get('timestamp')
                                if ts_str:
                                    ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                                    if latest_ts is None or ts > latest_ts:
                                        latest_ts = ts
                        except (json.JSONDecodeError, ValueError, KeyError):
                            continue
            except OSError as e:
                print(f"Warning: Failed to read file {jsonl_file}: {e}", file=sys.stderr)
                continue
    except Exception as e:
        print(f"Warning: Failed to find latest activity: {e}", file=sys.stderr)

    return latest_ts

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
        # リセットタイムスタンプを記録（この時点以降のメッセージのみカウントする）
        save_window_state(
            window_start=now,  # ダミー（すぐに上書きされる）
            first_message_timestamp=now,  # ダミー
            reset_timestamp=now  # リセット時点のタイムスタンプを記録
        )

        # トークン制限値を取得
        token_limit = get_token_limit(plan)

        # 0%を返す（次のメッセージで新しいウィンドウ開始）
        return {
            "plan": plan,
            "windowHours": window_hours,
            "windowStart": None,
            "windowEnd": None,
            "timeUntilReset": 0,
            "calculatedAt": now.isoformat(),

            # トークンベースの使用量（リセット時は0）
            "tokens": {
                "raw": {"input": 0, "output": 0, "cache_creation": 0, "cache_read": 0, "total": 0},
                "weighted": {"input": 0, "output": 0, "total": 0}
            },
            "modelBreakdown": {},

            # トークン制限と使用率（リセット時は0%）
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
            "resetStatus": "Window expired - waiting for next message"
        }

    # ウィンドウ状態の確認
    if window_state is None:
        # 完全な初回起動（usage-window.json が存在しない）
        # ログから最新のアクティビティを探して、そこからウィンドウを開始
        # ただし、5時間以上前のアクティビティは無視（期限切れとして扱う）
        latest_activity = find_latest_activity(log_dir)
        if latest_activity and (now - latest_activity) < timedelta(hours=5):
            # 5時間以内のアクティビティがある → そこからウィンドウ開始
            window_start = latest_activity
            save_window_state(window_start=window_start, first_message_timestamp=window_start)
        else:
            # 5時間以上前 or アクティビティなし → 新規ウィンドウ待機状態（0%表示）
            # 現在時刻をウィンドウ開始として保存（次のアクティビティから本格的にカウント開始）
            window_start = now
            save_window_state(window_start=window_start, first_message_timestamp=window_start)
        reset_timestamp = None
    elif 'resetTimestamp' in window_state:
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

                                        # モデル別の集計（汎用関数を使用）
                                        model_key = get_model_key_from_name(model_name)

                                        if model_key not in token_usage_data['by_model']:
                                            token_usage_data['by_model'][model_key] = {
                                                'requests': 0,
                                                'inputTokens': 0,
                                                'outputTokens': 0,
                                                'rawTokens': 0,
                                                'weightedTokens': 0
                                            }

                                        token_usage_data['by_model'][model_key]['requests'] += 1
                                        token_usage_data['by_model'][model_key]['inputTokens'] += weighted['raw_input']
                                        token_usage_data['by_model'][model_key]['outputTokens'] += weighted['raw_output']
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

        # ウィンドウ終了時刻を計算（正時に丸めた開始時刻 + 5時間）
        rounded_window_start = round_to_hour_utc(window_start)
        window_end = rounded_window_start + timedelta(hours=window_hours)

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

    # モデル別の集計（汎用関数を使用）
    model_counts = {}
    for m in messages:
        model = m.get('model', 'unknown') or 'unknown'
        model_key = get_model_key_from_name(model)
        model_counts[model_key] = model_counts.get(model_key, 0) + 1

    # ウィンドウ終了時刻を計算（正時に丸めた開始時刻から5時間後）
    rounded_window_start = round_to_hour_utc(window_start)
    window_end = rounded_window_start + timedelta(hours=window_hours)
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

    # ベース制限値を取得（キャリブレーション値または推定値）
    base_limit = get_token_limit(plan)

    # モデル別使用率を計算（設定ファイルベースで汎用的に処理）
    model_percents = {}

    for model_key, model_data in token_usage_data['by_model'].items():
        raw_tokens = model_data.get('rawTokens', 0)
        weighted_tokens = model_data.get('weightedTokens', 0)

        if raw_tokens > 0 or weighted_tokens > 0:
            # モデルキーからフルモデル名を推測してキャリブレーション設定を取得
            _, config = get_model_config(model_key)

            # 使用率を計算
            percent = calculate_model_percent(
                model_key, config, raw_tokens, weighted_tokens, base_limit
            )
            model_percents[model_key] = percent
            model_data['calculatedPercent'] = round(percent, 1)
            model_data['calculationType'] = config.get('type', 'weight')

    # 全体使用率 = 各モデルの使用率の合計
    token_percent = round(sum(model_percents.values()))
    sonnet_limit = base_limit  # 後方互換性

    # 後方互換性のための値（レガシー計算）
    weighted_tokens = token_usage_data['weighted']['total']
    token_limit = sonnet_limit  # 後方互換性
    remaining_tokens = max(0, 100 - token_percent)  # パーセントベースの残り

    # モデル別比率を計算
    total_raw_by_model = sum(m.get('rawTokens', 0) for m in token_usage_data['by_model'].values())
    total_weighted_by_model = sum(m.get('weightedTokens', 0) for m in token_usage_data['by_model'].values())

    for model_key, model_data in token_usage_data['by_model'].items():
        # 生トークン比率（モデル使用量の割合を見るため）
        raw_ratio = (model_data['rawTokens'] / total_raw_by_model * 100) if total_raw_by_model > 0 else 0
        # 重み付けトークン比率（コスト寄与度を見るため）
        weighted_ratio = (model_data['weightedTokens'] / total_weighted_by_model * 100) if total_weighted_by_model > 0 else 0

        model_data['rawRatio'] = round(raw_ratio, 1)
        model_data['weightedRatio'] = round(weighted_ratio, 1)

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

        # モデル別使用率（新方式）
        "modelPercents": model_percents,
        "tokenPercent": token_percent,
        "remainingPercent": max(0, 100 - token_percent),

        # Sonnet用制限値（参考情報）
        "sonnetLimit": sonnet_limit,

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
        "messagePercent": token_percent  # モデル別合算の使用率を表示
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
