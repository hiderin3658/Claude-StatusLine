#!/usr/bin/env python3
"""
Claude Code の /usage 画面から使用率を取得するスクリプト
使い方: Claude Code で /usage を表示した状態で実行
"""

import subprocess
import re
import json
from datetime import datetime, timezone
from pathlib import Path

# 設定
CACHE_FILE = Path("/tmp/claude-usage-cache.json")
SCREENSHOT_PATH = Path("/tmp/claude-usage-screenshot.png")

def capture_screenshot():
    """画面全体をスクリーンショット"""
    print("📸 スクリーンショットを取得中...")
    result = subprocess.run(
        ["screencapture", "-x", str(SCREENSHOT_PATH)],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise Exception(f"スクリーンショット取得失敗: {result.stderr}")

    print(f"✅ スクリーンショット保存: {SCREENSHOT_PATH}")

def extract_text_with_tesseract():
    """Tesseract OCRでテキストを抽出"""
    print("🔍 OCRでテキストを抽出中...")
    result = subprocess.run(
        ["tesseract", str(SCREENSHOT_PATH), "stdout"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise Exception(f"OCR失敗: {result.stderr}")

    return result.stdout

def extract_usage_percent(text):
    """テキストから使用率を抽出"""
    print("📊 使用率を解析中...")

    # パターン1: "Current session" の行から抽出
    pattern1 = r'Current\s+session[^\n]*?(\d+)%\s+used'
    match = re.search(pattern1, text, re.IGNORECASE)

    if match:
        percent = int(match.group(1))
        print(f"✅ 使用率を検出: {percent}%")
        return percent

    # パターン2: より柔軟なパターン
    pattern2 = r'(\d+)%\s+used'
    matches = re.findall(pattern2, text, re.IGNORECASE)

    if matches:
        # 最初に見つかった値を使用
        percent = int(matches[0])
        print(f"✅ 使用率を検出: {percent}% (フォールバック)")
        return percent

    # デバッグ: 抽出されたテキストを表示
    print("⚠️  使用率が見つかりませんでした")
    print("--- 抽出されたテキスト ---")
    print(text[:500])  # 最初の500文字のみ表示
    print("-------------------------")

    return None

def save_to_cache(percent):
    """キャッシュファイルに保存"""
    utilization = percent / 100.0
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    data = {
        "session": {
            "utilization": round(utilization, 4),
            "updated_at": timestamp
        }
    }

    with open(CACHE_FILE, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"💾 キャッシュに保存: {CACHE_FILE}")
    print(f"   使用率: {percent}% ({utilization})")

def main():
    try:
        print("=" * 50)
        print("Claude Code 使用率取得スクリプト")
        print("=" * 50)
        print()

        # 1. スクリーンショット取得
        capture_screenshot()

        # 2. OCRでテキスト抽出
        text = extract_text_with_tesseract()

        # 3. 使用率を抽出
        percent = extract_usage_percent(text)

        if percent is None:
            print()
            print("❌ エラー: 使用率を抽出できませんでした")
            print("   Claude Codeで /usage を表示していますか？")
            return 1

        # 4. キャッシュに保存
        save_to_cache(percent)

        print()
        print("=" * 50)
        print("✅ 完了！")
        print("=" * 50)

        # スクリーンショットを削除（オプション）
        # SCREENSHOT_PATH.unlink()

        return 0

    except Exception as e:
        print()
        print(f"❌ エラー: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
