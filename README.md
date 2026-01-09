# Claude Code メッセージ使用率監視システム

Claude Code のメッセージ使用率をステータスラインに表示するためのツール群です。5時間ローリングウィンドウでのトークンベース使用率を正確に計算し、リアルタイムで使用状況を監視できます。

## 📋 目次

- [機能](#-機能)
- [スクリーンショット](#-スクリーンショット)
- [クイックスタート](#-クイックスタート)
  - [必要なソフトウェア](#必要なソフトウェア)
  - [インストール（macOS / Linux）](#インストールmacos--linux)
  - [インストール（Windows）](#インストールwindows)
- [プラン設定](#️-プラン設定)
- [リポジトリ構成](#-リポジトリ構成)
- [インストール後の構成](#-インストール後の構成)
- [プロジェクト固有設定の使い方](#-プロジェクト固有設定の使い方オプション)
- [動作確認](#-動作確認)
- [仕組み](#-仕組み)
- [トラブルシューティング](#️-トラブルシューティング)
- [ライセンス](#-ライセンス)
- [参考資料](#-参考資料)

## ✨ 機能

- 📊 **トークンベース使用率計算**（5時間ローリングウィンドウ）
  - モデル別重み付け（Opus:Sonnet = 3:1）
  - コスト係数適用（キャッシュ、入力、出力）
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
                                    コンテキスト  トークン使用率
```

- **緑** (< 50%): 安全
- **黄** (50-80%): 注意
- **赤** (≥ 80%): 警告

## 🚀 クイックスタート

### 📦 ファイル構成について

このリポジトリは、**インストール先ごとにファイルが整理**されています：

- **`install-to-home/required/`** - `~/.claude/` にインストールする必須ファイル
- **`install-to-home/optional/`** - オプションの追加ツール
- **`project-template/`** - プロジェクト固有の AI ルールテンプレート

### 必要なソフトウェア

- **Node.js** v14以降
- **Python 3** v3.7以降
- **jq** - JSON パーサー（macOS/Linux のみ）
- **Git**（オプション: ブランチ表示用）

#### jq のインストール

```bash
# macOS
brew install jq

# Ubuntu/Debian
sudo apt-get install jq

# CentOS/RHEL
sudo yum install jq

# Windows（WSL使用時）
sudo apt-get install jq
```

### インストール（macOS / Linux）

```bash
# 1. ファイルをダウンロード
git clone https://github.com/hiderin3658/Claude-StatusLine.git
cd Claude-StatusLine

# 2. ~/.claude/ ディレクトリに必須ファイルをコピー
cp install-to-home/required/*.md ~/.claude/
cp install-to-home/required/*.py ~/.claude/
cp install-to-home/required/*.mjs ~/.claude/
cp install-to-home/required/*.sh ~/.claude/
cp install-to-home/required/*.json ~/.claude/
cp -r install-to-home/required/templates ~/.claude/
cp -r install-to-home/required/references ~/.claude/

# 3. 実行権限を付与
chmod +x ~/.claude/*.py
chmod +x ~/.claude/*.mjs
chmod +x ~/.claude/*.sh

# 4. （オプション）追加ツールをインストール
cp install-to-home/optional/* ~/.claude/

# 5. Claude Code 設定ファイルを編集
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
# 1. 必須ファイルをコピー
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.claude"
Copy-Item -Path "install-to-home\required\*.md" -Destination "$env:USERPROFILE\.claude\" -Force
Copy-Item -Path "install-to-home\required\*.py" -Destination "$env:USERPROFILE\.claude\" -Force
Copy-Item -Path "install-to-home\required\*.mjs" -Destination "$env:USERPROFILE\.claude\" -Force
Copy-Item -Path "install-to-home\required\*.ps1" -Destination "$env:USERPROFILE\.claude\" -Force
Copy-Item -Path "install-to-home\required\*.json" -Destination "$env:USERPROFILE\.claude\" -Force
Copy-Item -Path "install-to-home\required\templates" -Destination "$env:USERPROFILE\.claude\" -Recurse -Force
Copy-Item -Path "install-to-home\required\references" -Destination "$env:USERPROFILE\.claude\" -Recurse -Force

# 2. （オプション）追加ツールをコピー
Copy-Item -Path "install-to-home\optional\*" -Destination "$env:USERPROFILE\.claude\" -Force

# 3. Claude Code 設定ファイルを編集
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

| プラン設定 | 月額料金 | トークン制限（5時間） | 説明 |
|-----------|---------|---------------------|------|
| `free` | 無料 | 170,000 | Freeプラン（推定） |
| `pro` | $20 | 500,000 | Proプラン |
| `max-100` | $100 | 2,500,000 | MAX（Proの5倍） |
| `max-200` | $200 | 5,000,000 | MAX（Proの10倍） |

**プラン変更後は daemon を再起動してください：**

```bash
# macOS / Linux
pkill -f ccusage-daemon
~/.claude/on-startup.sh

# Windows
Stop-Process -Name "node" -Force
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.claude\on-startup.ps1"
```

## 📁 リポジトリ構成

このリポジトリは、**インストール先ごとにファイルが整理**されています。

```
Claude-StatusLine/
├── .claude/
│   └── CLAUDE.md             # このプロジェクト固有のAIルール
├── install-to-home/          # ~/.claude/ にインストールするファイル
│   ├── required/             # 必須ファイル（トークン使用率監視）
│   │   ├── CLAUDE.md         # AI共通コーディングルール
│   │   ├── templates/        # テンプレートファイル
│   │   │   ├── COMMIT_MESSAGE_TEMPLATE.md
│   │   │   └── PR_TEMPLATE.md
│   │   ├── references/       # 参照ファイル
│   │   │   └── DESTRUCTIVE_COMMANDS_BLOCKLIST.md
│   │   ├── get-message-usage.py
│   │   ├── ccusage-daemon.mjs
│   │   ├── status-line.sh / .ps1
│   │   ├── on-startup.sh / .ps1
│   │   └── usage-config.json
│   └── optional/             # オプションツール
├── project-template/         # プロジェクト固有設定テンプレート
│   └── CLAUDE.md             # プロジェクト固有AIルールのサンプル
├── README.md                 # このファイル
├── WINDOWS_SETUP.md          # Windows詳細セットアップガイド
└── CLAUDE.md                 # 参照用（配布用は install-to-home/required/）
```

### install-to-home/required/ - 必須ファイル

| ファイル | 説明 | 対応OS |
|---------|------|--------|
| `CLAUDE.md` | AI共通コーディングルール | 全OS |
| `templates/` | テンプレートファイル（コミット、PR） | 全OS |
| `references/` | 参照ファイル（破壊的コマンドリスト） | 全OS |
| `get-message-usage.py` | トークンカウントスクリプト | 全OS |
| `ccusage-daemon.mjs` | バックグラウンド監視daemon | 全OS |
| `status-line.sh` | ステータスライン表示 | macOS/Linux |
| `status-line.ps1` | ステータスライン表示 | Windows |
| `on-startup.sh` | 起動フック | macOS/Linux |
| `on-startup.ps1` | 起動フック | Windows |
| `usage-config.json` | プラン設定 | 全OS |

### install-to-home/optional/ - オプションツール

| ファイル | 説明 |
|---------|------|
| `capture-usage.py` | 使用量キャプチャスクリプト |
| `save-usage.sh` | 使用量保存スクリプト |

### project-template/ - プロジェクト固有設定

| ファイル | 説明 |
|---------|------|
| `CLAUDE.md` | プロジェクト固有AIルールのテンプレート |

## 📂 インストール後の構成

インストール後、以下のように配置されます：

```
~/.claude/                    # ホームディレクトリの .claude フォルダ
├── CLAUDE.md                 # AI共通コーディングルール
├── templates/                # テンプレートファイル
│   ├── COMMIT_MESSAGE_TEMPLATE.md
│   └── PR_TEMPLATE.md
├── references/               # 参照ファイル
│   └── DESTRUCTIVE_COMMANDS_BLOCKLIST.md
├── get-message-usage.py      # トークンカウントスクリプト
├── ccusage-daemon.mjs        # バックグラウンド監視daemon
├── status-line.sh            # ステータスライン表示（macOS/Linux）
├── status-line.ps1           # ステータスライン表示（Windows）
├── on-startup.sh             # 起動フック（macOS/Linux）
├── on-startup.ps1            # 起動フック（Windows）
├── usage-config.json         # プラン設定
└── usage-cache.json          # キャッシュファイル（自動生成）

~/your-project/               # あなたのプロジェクト（任意）
├── .claude/
│   └── CLAUDE.md             # プロジェクト固有AIルール（オプション）
├── src/
└── README.md
```

## 🎯 プロジェクト固有設定の使い方（オプション）

このツールは AI 共通コーディングルール（`CLAUDE.md`）も含まれています。プロジェクトごとに異なる AI ルールを設定したい場合は、以下の手順で設定できます。

### 1. プロジェクト固有の CLAUDE.md を作成

```bash
# プロジェクトルートまたは .claude/ にテンプレートをコピー
cp project-template/CLAUDE.md /path/to/your-project/.claude/CLAUDE.md
```

### 2. プロジェクト固有のルールを編集

`/path/to/your-project/.claude/CLAUDE.md` を開いて、以下を編集します：

- プロジェクト名
- 技術スタック（使用言語、フレームワーク）
- ディレクトリ構成ルール
- プロジェクト固有のコーディング規約

### 3. AI が自動的に参照

Claude Code は以下の優先順位で CLAUDE.md を参照します：

1. **プロジェクト固有の `.claude/CLAUDE.md`**（最優先）
2. **グローバルの `~/.claude/CLAUDE.md`**（全プロジェクト共通）

プロジェクト固有のルールが優先されますが、グローバルルールも同時に適用されます。

### ファイル配置の例

```
~/.claude/CLAUDE.md                    # 全プロジェクト共通のAIルール

~/projects/
├── web-app/                           # Webアプリプロジェクト
│   ├── .claude/
│   │   └── CLAUDE.md                  # React + TypeScript 固有ルール
│   └── src/
└── python-api/                        # Python APIプロジェクト
    ├── .claude/
    │   └── CLAUDE.md                  # FastAPI + Python 固有ルール
    └── app/
```

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
  "windowHours": 5,
  "windowStart": "2026-01-09T00:52:12.583000+00:00",
  "windowEnd": "2026-01-09T05:52:12.583000+00:00",
  "timeUntilReset": 5237,
  "calculatedAt": "2026-01-09T04:24:55.031448+00:00",
  "tokens": {
    "raw": {
      "input": 680,
      "output": 64987,
      "cache_creation": 227582,
      "cache_read": 3462780,
      "total": 3756029
    },
    "weighted": {
      "input": 1463835.7,
      "output": 734025.0,
      "total": 2197860.7
    }
  },
  "modelBreakdown": {
    "opus": {
      "requests": 18,
      "rawTokens": 2102695,
      "weightedTokens": 1862235.3
    },
    "sonnet": {
      "requests": 16,
      "rawTokens": 1653334,
      "weightedTokens": 335625.4
    }
  },
  "tokenLimit": 2500000,
  "tokenPercent": 88,
  "remainingTokens": 302139.3
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
[Claude Sonnet 4.5] 📁 project | main | Ctx:29% | 5h:88%
```

## 📊 仕組み

### トークンベース使用率計算

```
重み付けトークン数 = (
  入力トークン × 1.0 +
  キャッシュ作成 × 1.25 +
  キャッシュ読取 × 0.1 +
  出力トークン × 5.0
) × モデル重み

モデル重み:
- Opus: 3.0（Sonnet の 3倍）
- Sonnet: 1.0（基準）
- Haiku: 0.33（Sonnet の 1/3）
```

### 5時間ローリングウィンドウ

```
現在時刻: 12:30
         ↓
┌────────────────────────────────┐
│ 5時間ウィンドウ               │
│ 07:30 ～ 12:30                 │
│                                │
│ トークン数: 2.2M/2.5M (88%)   │
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
   - キャッシュファイル (`~/.claude/usage-cache.json`) を更新

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
cat ~/.claude/usage-cache.json

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

## 🎓 次のステップ

インストールと動作確認が完了したら、以下を試してみてください：

### 1. プラン設定の確認

`~/.claude/usage-config.json` を開いて、使用しているプランが正しく設定されているか確認してください。

### 2. プロジェクト固有の AI ルールを設定（オプション）

プロジェクトごとに異なる開発ルールを AI に適用したい場合：

```bash
# プロジェクトの .claude/ にテンプレートをコピー
mkdir -p /path/to/your-project/.claude
cp project-template/CLAUDE.md /path/to/your-project/.claude/CLAUDE.md
# CLAUDE.md を編集してプロジェクト固有のルールを設定
```

詳細は「[プロジェクト固有設定の使い方](#-プロジェクト固有設定の使い方オプション)」を参照してください。

### 3. オプションツールを試す

`install-to-home/optional/` には追加ツールが含まれています。必要に応じて `~/.claude/` にコピーして使用してください。

### 4. カスタマイズ

- ステータスラインの表示内容を変更したい場合は、`~/.claude/status-line.sh`（または `.ps1`）を編集
- daemon の更新間隔を変更したい場合は、`~/.claude/ccusage-daemon.mjs` を編集
- モデル重み付けを調整したい場合は、`~/.claude/get-message-usage.py` の `MODEL_WEIGHTS` を編集

## 📝 ライセンス

MIT License

## 🤝 コントリビューション

Issue や Pull Request を歓迎します！

改善提案や機能要望がありましたら、お気軽に Issue を作成してください。

## 📚 参考資料

- [Claude Pro Plan Usage](https://support.claude.com/en/articles/8324991-about-claude-s-pro-plan-usage)
- [Claude Code Limits](https://portkey.ai/blog/claude-code-limits/)
- [Understanding Usage and Length Limits](https://support.claude.com/en/articles/11647753-understanding-usage-and-length-limits)

## 🔗 関連リンク

- [Claude Code 公式サイト](https://claude.com/claude-code)
- [リポジトリ Issues](https://github.com/hiderin3658/Claude-StatusLine/issues)

---

🤖 Built with [Claude Code](https://claude.com/claude-code)
