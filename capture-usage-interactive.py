#!/usr/bin/env python3
"""
Claude Code の /usage 画面から使用率を取得するスクリプト（インタラクティブ版）
使い方: Claude Code で /usage を表示した状態で実行し、画面範囲を選択
"""

import subprocess
import re
import json
from datetime import datetime, timezone
from pathlib import Path

# 設定
CACHE_FILE = Path("/tmp/claude-usage-cache.json")
SCREENSHOT_PATH = Path("/tmp/claude-usage-screenshot.png")

def capture_screenshot_interactive():
    """画面範囲を選択してスクリーンショット（インタラクティブモード）"""
    print("=" * 60)
    print("📸 スクリーンショット取得")
    print("=" * 60)
    print()
    print("次の手順で /usage 画面をキャプチャしてください：")
    print()
    print("1. Claude Code の /usage 画面を表示")
    print("2. Enterキーを押す")
    print("3. マウスで /usage 画面の範囲をドラッグして選択")
    print("   （または、スペースキーでウィンドウ全体を選択）")
    print()
    input("準備ができたら Enter キーを押してください... ")

    print()
    print("📸 範囲を選択してください...")
    result = subprocess.run(
        ["screencapture", "-i", str(SCREENSHOT_PATH)],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        # ユーザーがキャンセルした場合
        if result.returncode == 1:
            raise Exception("スクリーンショットがキャンセルされました")
        raise Exception(f"スクリーンショット取得失敗: {result.stderr}")

    # ファイルが作成されたか確認
    if not SCREENSHOT_PATH.exists():
        raise Exception("スクリーンショットファイルが作成されませんでした")

    print(f"✅ スクリーンショット保存: {SCREENSHOT_PATH}")

def extract_text_with_tesseract():
    """Tesseract OCRでテキストを抽出"""
    print()
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
    print()

    # パターン1: "Current session" の行から抽出
    pattern1 = r'Current\s+session[^\n]*?(\d+)%\s+used'
    match = re.search(pattern1, text, re.IGNORECASE | re.DOTALL)

    if match:
        percent = int(match.group(1))
        print(f"✅ 使用率を検出: {percent}% (パターン1)")
        return percent

    # パターン2: より柔軟なパターン
    pattern2 = r'session[^\n]*?(\d+)%'
    match = re.search(pattern2, text, re.IGNORECASE)

    if match:
        percent = int(match.group(1))
        print(f"✅ 使用率を検出: {percent}% (パターン2)")
        return percent

    # パターン3: 最もシンプルなパターン（最初に見つかった%）
    pattern3 = r'(\d+)\s*%\s*used'
    match = re.search(pattern3, text, re.IGNORECASE)

    if match:
        percent = int(match.group(1))
        print(f"✅ 使用率を検出: {percent}% (パターン3)")
        return percent

    # デバッグ: 抽出されたテキストを表示
    print("⚠️  使用率が見つかりませんでした")
    print()
    print("=" * 60)
    print("抽出されたテキスト:")
    print("=" * 60)
    print(text)
    print("=" * 60)

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

    print()
    print("=" * 60)
    print("💾 キャッシュに保存")
    print("=" * 60)
    print(f"ファイル: {CACHE_FILE}")
    print(f"使用率: {percent}%")
    print(f"更新日時: {timestamp}")

def main():
    try:
        print()
        print("=" * 60)
        print("  Claude Code 使用率取得スクリプト")
        print("  (インタラクティブ版)")
        print("=" * 60)
        print()

        # 1. スクリーンショット取得（インタラクティブ）
        capture_screenshot_interactive()

        # 2. OCRでテキスト抽出
        text = extract_text_with_tesseract()

        # 3. 使用率を抽出
        percent = extract_usage_percent(text)

        if percent is None:
            print()
            print("❌ エラー: 使用率を抽出できませんでした")
            print()
            print("考えられる原因:")
            print("  - /usage 画面がキャプチャされていない")
            print("  - OCRが正しくテキストを認識できなかった")
            print()
            print(f"スクリーンショット: {SCREENSHOT_PATH}")
            print("このファイルを確認して、/usage 画面が写っているか確認してください")
            return 1

        # 4. キャッシュに保存
        save_to_cache(percent)

        print()
        print("=" * 60)
        print("✅ 完了！")
        print("=" * 60)
        print()
        print("次のステップ:")
        print("  1. 新しいClaude Codeセッションを開始")
        print("  2. ステータスラインで使用率が表示されることを確認")
        print()

        return 0

    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ エラー: {e}")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    exit(main())
