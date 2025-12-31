# ~/.claude/ インストール用ファイル

このディレクトリには、`~/.claude/` にインストールするファイルが含まれています。

## フォルダ構成

```
install-to-home/
├── required/          # 必須ファイル（メッセージ使用率監視に必要）
│   ├── get-message-usage.py
│   ├── ccusage-daemon.mjs
│   ├── status-line.sh
│   ├── status-line.ps1
│   ├── on-startup.sh
│   ├── on-startup.ps1
│   ├── usage-config.json
│   └── CLAUDE.md
└── optional/          # オプションツール（必要に応じて使用）
    ├── status-line-cost.sh
    ├── status-line-with-usage.sh
    ├── capture-usage.py
    ├── capture-usage-window.sh
    ├── capture-usage-interactive.py
    └── save-usage.sh
```

## インストール方法

### macOS / Linux

```bash
# 必須ファイルをインストール
cp required/* ~/.claude/
chmod +x ~/.claude/*.sh
chmod +x ~/.claude/*.py
chmod +x ~/.claude/*.mjs

# （オプション）追加ツールをインストール
cp optional/* ~/.claude/
chmod +x ~/.claude/optional/*.sh
chmod +x ~/.claude/optional/*.py
```

### Windows

```powershell
# 必須ファイルをインストール
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.claude"
Copy-Item -Path "required\*" -Destination "$env:USERPROFILE\.claude\" -Force

# （オプション）追加ツールをインストール
Copy-Item -Path "optional\*" -Destination "$env:USERPROFILE\.claude\" -Force
```

## ファイルの説明

### required/ - 必須ファイル

| ファイル | 説明 | 対応OS |
|---------|------|--------|
| `get-message-usage.py` | メッセージカウントスクリプト | 全OS |
| `ccusage-daemon.mjs` | バックグラウンド監視daemon | 全OS |
| `status-line.sh` | ステータスライン表示 | macOS/Linux |
| `status-line.ps1` | ステータスライン表示 | Windows |
| `on-startup.sh` | 起動フック | macOS/Linux |
| `on-startup.ps1` | 起動フック | Windows |
| `usage-config.json` | プラン設定 | 全OS |
| `CLAUDE.md` | AI共通コーディングルール | 全OS |

### optional/ - オプションツール

| ファイル | 説明 |
|---------|------|
| `status-line-cost.sh` | コスト表示版ステータスライン |
| `status-line-with-usage.sh` | 使用量表示版ステータスライン |
| `capture-usage.py` | 使用量キャプチャスクリプト |
| `capture-usage-window.sh` | ウィンドウキャプチャスクリプト |
| `capture-usage-interactive.py` | インタラクティブキャプチャ |
| `save-usage.sh` | 使用量保存スクリプト |

## 次のステップ

インストール後は、Claude Code 設定ファイルを編集してください：

- macOS/Linux: `~/.config/claude/config.json`
- Windows: `%APPDATA%\Claude\config.json`

詳細な設定方法は、プロジェクトルートの README.md を参照してください。
