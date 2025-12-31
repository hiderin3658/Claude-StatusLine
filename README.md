# Claude Code メッセージ使用率監視システム

Claude Code のメッセージ使用率をステータスラインに表示するためのツール群です。5時間ローリングウィンドウでのメッセージ数を正確にカウントし、リアルタイムで使用状況を監視できます。

## ✨ 機能

- 📊 **5時間ローリングウィンドウ**でのメッセージ使用率を正確に計算
- 🎯 **プラン別制限設定**（Free / Pro / MAX-100 / MAX-200）
- 🔄 **複数ウィンドウ対応**（全Claude Codeウィンドウで同じ値を表示）
- 🌍 **クロスプラットフォーム**（Windows / macOS / Linux）
- 🎨 **色分け表示**（使用率に応じて緑/黄/赤で視覚化）
- 🚀 **バックグラウンド監視**（5分ごとに自動更新）
- 🔍 **正確なカウント**（サブエージェントや内部イベントを除外）

## 📸 スクリーンショット

```
[Claude Sonnet 4.5] 📁 my-project | main | Ctx:34% | 5h:12%
                                             ^^^^     ^^^^^
                                    コンテキスト  メッセージ使用率
```

- **緑** (< 50%): 安全
- **黄** (50-80%): 注意
- **赤** (≥ 80%): 警告

## 🚀 クイックスタート

### 必要なソフトウェア

- **Node.js** v14以降
- **Python 3** v3.7以降
- **Git**（オプション: ブランチ表示用）

### インストール（macOS / Linux）

```bash
# 1. ファイルをダウンロード
git clone https://github.com/hiderin3658/Claude-StatusLine.git
cd Claude-StatusLine

# 2. ~/.claude/ ディレクトリにコピー
cp get-message-usage.py ~/.claude/
cp ccusage-daemon.mjs ~/.claude/
cp status-line.sh ~/.claude/
cp on-startup.sh ~/.claude/
cp usage-config.json ~/.claude/

# 3. 実行権限を付与
chmod +x ~/.claude/get-message-usage.py
chmod +x ~/.claude/ccusage-daemon.mjs
chmod +x ~/.claude/status-line.sh
chmod +x ~/.claude/on-startup.sh

# 4. Claude Code 設定ファイルを編集
# ~/.config/claude/config.json または ~/.claude/settings.json
```

**config.json の設定例:**

```json
{
  "statusLine": {
    "command": "~/.claude/status-line.sh"
  },
  "hooks": {
    "on-startup": "~/.claude/on-startup.sh"
  }
}
```

### インストール（Windows）

詳細な手順は [WINDOWS_SETUP.md](./WINDOWS_SETUP.md) をご覧ください。

```powershell
# 1. ファイルをコピー
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.claude"
# ファイルを %USERPROFILE%\.claude\ に配置

# 2. Claude Code 設定ファイルを編集
# %APPDATA%\Claude\config.json
```

**config.json の設定例（Windows）:**

```json
{
  "statusLine": {
    "command": "powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"%USERPROFILE%\\.claude\\status-line.ps1\""
  },
  "hooks": {
    "on-startup": "powershell.exe -NoProfile -ExecutionPolicy Bypass -File \"%USERPROFILE%\\.claude\\on-startup.ps1\""
  }
}
```

## ⚙️ プラン設定

`~/.claude/usage-config.json` を編集して、使用しているプランを設定します：

```json
{
  "plan": "max-100"
}
```

### 利用可能なプラン

| プラン設定 | 月額料金 | メッセージ制限 | 説明 |
|-----------|---------|---------------|------|
| `free` | 無料 | 15メッセージ/5h | Freeプラン（推定） |
| `pro` | $20 | 45メッセージ/5h | Proプラン |
| `max-100` | $100 | 225メッセージ/5h | MAX（Proの5倍） |
| `max-200` | $200 | 900メッセージ/5h | MAX（Proの20倍） |

**プラン変更後は daemon を再起動してください：**

```bash
# macOS / Linux
pkill -f ccusage-daemon
~/.claude/on-startup.sh

# Windows
Stop-Process -Name "node" -Force
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.claude\on-startup.ps1"
```

## 📁 ファイル構成

### 必須ファイル（メッセージ使用率監視）

| ファイル | 説明 | 対応OS |
|---------|------|--------|
| `get-message-usage.py` | メッセージカウントスクリプト | 全OS |
| `ccusage-daemon.mjs` | バックグラウンド監視daemon | 全OS |
| `status-line.sh` | ステータスライン表示 | macOS/Linux |
| `status-line.ps1` | ステータスライン表示 | Windows |
| `on-startup.sh` | 起動フック | macOS/Linux |
| `on-startup.ps1` | 起動フック | Windows |
| `usage-config.json` | プラン設定 | 全OS |

### その他のStatusLine関連ツール

| ファイル | 説明 |
|---------|------|
| `status-line-cost.sh` | コスト表示版ステータスライン |
| `status-line-with-usage.sh` | 使用量表示版ステータスライン |
| `capture-usage.py` | 使用量キャプチャスクリプト |
| `capture-usage-window.sh` | ウィンドウキャプチャスクリプト |
| `capture-usage-interactive.py` | インタラクティブキャプチャ |
| `save-usage.sh` | 使用量保存スクリプト |

### ドキュメント

| ファイル | 説明 |
|---------|------|
| `WINDOWS_SETUP.md` | Windows詳細セットアップガイド |
| `CLAUDE.md` | AI共通コーディングルール |
| `examples/` | プロジェクト別設定例 |

## 🔧 動作確認

### Python スクリプトのテスト

```bash
# macOS / Linux
python3 ~/.claude/get-message-usage.py

# Windows
python "$env:USERPROFILE\.claude\get-message-usage.py"
```

**正常な出力例:**

```json
{
  "plan": "max-100",
  "messageCount": 28,
  "messageLimit": 225,
  "messagePercent": 12,
  "remainingMessages": 197,
  "windowHours": 5,
  "windowStart": "2025-12-31T07:30:00+00:00",
  "calculatedAt": "2025-12-31T12:30:00+00:00"
}
```

### ステータスライン表示のテスト

```bash
# macOS / Linux
echo '{
  "model": {"display_name": "Claude Sonnet 4.5"},
  "workspace": {"current_dir": "/path/to/project"},
  "context_window": {
    "context_window_size": 200000,
    "current_usage": {
      "input_tokens": 50000,
      "output_tokens": 8000,
      "cache_creation_input_tokens": 0,
      "cache_read_input_tokens": 0
    }
  }
}' | ~/.claude/status-line.sh
```

**期待される出力:**

```
[Claude Sonnet 4.5] 📁 project | main | Ctx:29% | 5h:12%
```

## 📊 仕組み

### 5時間ローリングウィンドウ

```
現在時刻: 12:30
         ↓
┌────────────────────────────────┐
│ 5時間ウィンドウ               │
│ 07:30 ～ 12:30                 │
│                                │
│ メッセージ数: 28/225 (12%)    │
└────────────────────────────────┘
         ↑
    最古メッセージ: 07:30
    → リセット時刻: 12:30 (5時間後)
```

### カウント方法

1. **全プロジェクトのログを集計**
   - `~/.claude/projects/*/*.jsonl` を走査
   - 複数ウィンドウの使用量を合算

2. **正確なフィルタリング**
   - ✅ ユーザーメッセージのみカウント
   - ❌ サブエージェント（Task tool等）を除外
   - ❌ ツール実行結果を除外
   - ❌ 内部イベントを除外

3. **5分ごとに自動更新**
   - daemon がバックグラウンドで監視
   - キャッシュファイル (`/tmp/ccusage-cache.json`) を更新

## 🛠️ トラブルシューティング

### メッセージカウントが0のまま

```bash
# ログディレクトリを確認
ls ~/.claude/projects/

# Python スクリプトを手動実行してエラーを確認
python3 ~/.claude/get-message-usage.py
```

### daemon が起動しない

```bash
# ログファイルを確認
cat /tmp/ccusage-daemon.log

# 手動で daemon を起動してエラーを確認
node ~/.claude/ccusage-daemon.mjs
```

### 使用率が実際と異なる

```bash
# キャッシュファイルを確認
cat /tmp/ccusage-cache.json

# daemon を再起動
pkill -f ccusage-daemon
~/.claude/on-startup.sh
```

### Windows で PowerShell スクリプトが実行できない

```powershell
# 実行ポリシーを確認
Get-ExecutionPolicy

# RemoteSigned に変更
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## 📝 ライセンス

MIT License

## 🤝 コントリビューション

Issue や Pull Request を歓迎します！

## 📚 参考資料

- [Claude Pro Plan Usage](https://support.claude.com/en/articles/8324991-about-claude-s-pro-plan-usage)
- [Claude Code Limits](https://portkey.ai/blog/claude-code-limits/)
- [Understanding Usage and Length Limits](https://support.claude.com/en/articles/11647753-understanding-usage-and-length-limits)

---

🤖 Built with [Claude Code](https://claude.com/claude-code)
