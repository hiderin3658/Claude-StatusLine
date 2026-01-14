#!/usr/bin/env python3
"""
Claude Code 使用量キャリブレーションツール

/usage コマンドの表示値を入力することで、
トークン制限値を自動調整します。
"""

import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timezone
import statistics

# ホームディレクトリの .claude フォルダ
CLAUDE_DIR = Path.home() / '.claude'
CALIBRATION_FILE = CLAUDE_DIR / 'usage-calibration.json'
USAGE_SCRIPT = CLAUDE_DIR / 'get-message-usage.py'

# キャリブレーションデータの最大保存数
MAX_HISTORY = 10


def load_calibration_data():
    """キャリブレーションデータを読み込む"""
    if not CALIBRATION_FILE.exists():
        return {
            'plan': 'max-100',
            'history': [],
            'current_limit': None,
            'confidence': 0.0
        }

    try:
        with open(CALIBRATION_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"警告: キャリブレーションデータの読み込みに失敗: {e}", file=sys.stderr)
        return {
            'plan': 'max-100',
            'history': [],
            'current_limit': None,
            'confidence': 0.0
        }


def save_calibration_data(data):
    """キャリブレーションデータを保存"""
    try:
        CLAUDE_DIR.mkdir(parents=True, exist_ok=True)
        with open(CALIBRATION_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"エラー: キャリブレーションデータの保存に失敗: {e}", file=sys.stderr)
        sys.exit(1)


def get_current_usage():
    """get-message-usage.py を実行して現在の使用状況を取得"""
    try:
        result = subprocess.run(
            [sys.executable, str(USAGE_SCRIPT)],
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"エラー: get-message-usage.py の実行に失敗しました", file=sys.stderr)
        print(f"詳細: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"エラー: 使用状況データの解析に失敗しました", file=sys.stderr)
        sys.exit(1)


def calculate_limit(weighted_tokens, usage_percent):
    """使用率から制限値を逆算"""
    if usage_percent <= 0 or usage_percent > 100:
        print(f"エラー: 使用率は1～100の範囲で指定してください（入力値: {usage_percent}%）", file=sys.stderr)
        sys.exit(1)

    return weighted_tokens / (usage_percent / 100.0)


def calibrate(official_usage_percent):
    """キャリブレーションを実行"""
    print(f"[CALIBRATE] /usage コマンドの表示値: {official_usage_percent}%")
    print()

    # 現在の使用状況を取得
    print("現在の使用状況を取得中...")
    usage_data = get_current_usage()

    plan = usage_data.get('plan', 'max-100')
    weighted_tokens = usage_data['tokens']['weighted']['total']

    print(f"プラン: {plan}")
    print(f"重み付けトークン数: {weighted_tokens:,.0f}")
    print()

    # 制限値を逆算
    estimated_limit = calculate_limit(weighted_tokens, official_usage_percent)
    print(f"[TARGET] 推定制限値: {estimated_limit:,.0f} トークン")
    print()

    # キャリブレーションデータを読み込み
    calibration_data = load_calibration_data()
    calibration_data['plan'] = plan

    # 履歴に追加
    calibration_entry = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'official_percent': official_usage_percent,
        'weighted_tokens': weighted_tokens,
        'estimated_limit': estimated_limit
    }
    calibration_data['history'].append(calibration_entry)

    # 最大保存数を超えたら古いものを削除
    if len(calibration_data['history']) > MAX_HISTORY:
        calibration_data['history'] = calibration_data['history'][-MAX_HISTORY:]

    # 中央値を計算（外れ値に強い）
    limits = [entry['estimated_limit'] for entry in calibration_data['history']]

    if len(limits) >= 3:
        # 3つ以上のデータがある場合は中央値を使用
        calibrated_limit = statistics.median(limits)
        confidence = min(len(limits) / MAX_HISTORY, 1.0)
    elif len(limits) >= 1:
        # データが少ない場合は平均値
        calibrated_limit = statistics.mean(limits)
        confidence = len(limits) / 3.0  # 3つ揃うまでは低信頼度
    else:
        calibrated_limit = estimated_limit
        confidence = 0.1

    calibration_data['current_limit'] = calibrated_limit
    calibration_data['confidence'] = confidence

    # 保存
    save_calibration_data(calibration_data)

    # 結果を表示
    print("[OK] キャリブレーション完了")
    print()
    print(f"[RESULT] 調整後の制限値: {calibrated_limit:,.0f} トークン")
    print(f"[INFO] データポイント数: {len(limits)}")
    print(f"[INFO] 信頼度: {confidence*100:.0f}%")
    print()

    if len(limits) < 3:
        print("[HINT] 3回以上キャリブレーションを行うと精度が向上します")

    # 次回の使用率予測
    next_percent = (weighted_tokens / calibrated_limit) * 100
    print()
    print(f"次回の表示予測: {next_percent:.1f}%")

    return calibrated_limit


def show_status():
    """現在のキャリブレーション状態を表示"""
    calibration_data = load_calibration_data()

    if not calibration_data['history']:
        print("[ERROR] キャリブレーションデータがありません")
        print()
        print("使い方:")
        print("  python claude-calibrate.py <使用率>")
        print()
        print("例:")
        print("  python claude-calibrate.py 30")
        return

    print("[STATUS] キャリブレーション状態")
    print()
    print(f"プラン: {calibration_data['plan']}")
    print(f"現在の制限値: {calibration_data['current_limit']:,.0f} トークン")
    print(f"信頼度: {calibration_data['confidence']*100:.0f}%")
    print(f"データポイント数: {len(calibration_data['history'])}")
    print()

    print("[HISTORY] 履歴（最新5件）:")
    for entry in calibration_data['history'][-5:]:
        timestamp = datetime.fromisoformat(entry['timestamp']).astimezone()
        print(f"  {timestamp.strftime('%Y-%m-%d %H:%M')} - "
              f"{entry['official_percent']}% -> "
              f"推定制限値: {entry['estimated_limit']:,.0f}")


def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        show_status()
        return

    try:
        usage_percent = float(sys.argv[1])
    except ValueError:
        print(f"エラー: 使用率は数値で指定してください（入力値: {sys.argv[1]}）", file=sys.stderr)
        sys.exit(1)

    calibrate(usage_percent)


if __name__ == '__main__':
    main()
