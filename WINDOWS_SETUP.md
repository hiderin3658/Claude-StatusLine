# Claude Code メッセージ使用率監視システム - Windows セットアップガイド

このガイドは、Windows環境で Claude Code のメッセージ使用率監視システムをセットアップする手順を説明します。

## 前提条件

以下のソフトウェアがインストールされている必要があります：

1. **Node.js** (v14以降)
   - https://nodejs.org/ からダウンロード・インストール
   - インストール後、コマンドプロンプトで `node --version` を実行して確認

2. **Python 3** (v3.7以降)
   - https://www.python.org/downloads/ からダウンロード・インストール
   - **重要**: インストール時に「Add Python to PATH」にチェックを入れる
   - インストール後、コマンドプロンプトで `python --version` を実行して確認

3. **Git** (オプション: Gitブランチ表示を使う場合)
   - https://git-scm.com/download/win からダウンロード・インストール

## セットアップ手順

### 1. ファイルのコピー

以下のファイルを `%USERPROFILE%\.claude\` ディレクトリにコピーします：

```
C:\Users\<ユーザー名>\.claude\
├── get-message-usage.py          # メッセージカウントスクリプト
├── ccusage-daemon.mjs            # バックグラウンド監視daemon
├── status-line.ps1               # ステータスライン表示（PowerShell）
├── on-startup.ps1                # 起動フック（PowerShell）
└── usage-config.json             # プラン設定
```

**コピー方法（PowerShell）:**

```powershell
# .claude ディレクトリを作成
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.claude"

# Mac/Linux からファイルをコピー（例: USBメモリ経由）
# または、各ファイルの内容を手動でコピー＆ペースト
```

### 2. プラン設定

`%USERPROFILE%\.claude\usage-config.json` を編集して、使用しているプランを設定します：

```json
{
  "plan": "max-100"
}
```

**利用可能なプラン:**
- `"free"` - Free プラン（15メッセージ/5h）
- `"pro"` - Pro プラン（45メッセージ/5h）
- `"max-100"` - MAX $100 プラン（225メッセージ/5h）
- `"max-200"` - MAX $200 プラン（900メッセージ/5h）

### 3. Claude Code 設定ファイルの編集

Claude Code の設定ファイルを編集して、PowerShell スクリプトを使用するように設定します。

**設定ファイルの場所:**
```
%APPDATA%\Claude\config.json
```

**編集内容:**

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

**注意:** 既に他の設定がある場合は、`statusLine` と `hooks` セクションのみを追加してください。

### 4. PowerShell 実行ポリシーの確認

PowerShell スクリプトを実行するために、実行ポリシーを確認します。

**管理者権限で PowerShell を開き、以下を実行:**

```powershell
# 現在の実行ポリシーを確認
Get-ExecutionPolicy

# RemoteSigned または Unrestricted でない場合、以下を実行
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 5. 動作テスト

#### 5.1 Python スクリプトのテスト

```powershell
# PowerShell を開いて実行
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
  "windowStart": "2025-12-31T07:30:00.000000+00:00",
  "calculatedAt": "2025-12-31T12:30:00.000000+00:00"
}
```

#### 5.2 ステータスライン表示のテスト

```powershell
# テスト用JSONを作成して表示
@'
{
  "model": {
    "display_name": "Claude Sonnet 4.5"
  },
  "workspace": {
    "current_dir": "C:\\Users\\YourName\\Projects\\MyProject"
  },
  "context_window": {
    "context_window_size": 200000,
    "current_usage": {
      "input_tokens": 50000,
      "output_tokens": 8000,
      "cache_creation_input_tokens": 0,
      "cache_read_input_tokens": 0
    }
  }
}
'@ | powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.claude\status-line.ps1"
```

**期待される出力:**
```
[Claude Sonnet 4.5] 📁 MyProject | Ctx:29% | 5h:12%
```

#### 5.3 Daemon 起動テスト

```powershell
# Daemon を起動
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.claude\on-startup.ps1"

# 起動確認（2-3秒待ってから）
Get-Process | Where-Object { $_.ProcessName -eq "node" -and $_.CommandLine -like "*ccusage-daemon*" }

# キャッシュファイルが生成されたか確認
Get-Content "$env:TEMP\ccusage-cache.json"
```

### 6. トラブルシューティング

#### 問題: Python が見つからない

```powershell
# Python のパスを確認
where.exe python

# パスが表示されない場合、環境変数 PATH に Python を追加
```

#### 問題: Node.js が見つからない

```powershell
# Node.js のパスを確認
where.exe node

# パスが表示されない場合、Node.js を再インストール
```

#### 問題: PowerShell スクリプトが実行できない

```powershell
# 実行ポリシーを確認
Get-ExecutionPolicy

# RemoteSigned に変更
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### 問題: daemon が起動しない

```powershell
# ログファイルを確認
Get-Content "$env:TEMP\ccusage-daemon-startup.log"
Get-Content "$env:TEMP\ccusage-daemon.log"

# 手動で daemon を起動してエラーを確認
node "$env:USERPROFILE\.claude\ccusage-daemon.mjs"
```

#### 問題: メッセージカウントが0のまま

```powershell
# ログディレクトリが存在するか確認（優先順位で検索）
# 1. 新バージョン（推奨）
Test-Path "$env:USERPROFILE\.claude\projects"

# 2. 旧バージョン
Test-Path "$env:APPDATA\Claude\projects"

# ログファイルが存在するか確認
Get-ChildItem "$env:USERPROFILE\.claude\projects" -Recurse -Filter "*.jsonl" -ErrorAction SilentlyContinue
Get-ChildItem "$env:APPDATA\Claude\projects" -Recurse -Filter "*.jsonl" -ErrorAction SilentlyContinue
```

## 使用方法

### プラン変更

```powershell
# MAX $200 プランに変更する場合
@'
{
  "plan": "max-200"
}
'@ | Out-File -FilePath "$env:USERPROFILE\.claude\usage-config.json" -Encoding utf8

# daemon を再起動（変更を反映）
Stop-Process -Name "node" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
powershell -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\.claude\on-startup.ps1"
```

### 手動でキャッシュを更新

```powershell
python "$env:USERPROFILE\.claude\get-message-usage.py" | Out-File -FilePath "$env:TEMP\ccusage-cache.json" -Encoding utf8
```

### daemon の停止

```powershell
# daemon プロセスを停止
Stop-Process -Name "node" -Force -ErrorAction SilentlyContinue

# PIDファイルを削除
Remove-Item "$env:TEMP\ccusage-daemon.pid" -ErrorAction SilentlyContinue
```

## ファイル配置場所

| ファイル | Windows パス |
|---------|-------------|
| スクリプト類 | `%USERPROFILE%\.claude\` |
| キャッシュ | `%TEMP%\ccusage-cache.json` |
| daemon ログ | `%TEMP%\ccusage-daemon.log` |
| PIDファイル | `%TEMP%\ccusage-daemon.pid` |
| Claude ログ（新） | `%USERPROFILE%\.claude\projects\` |
| Claude ログ（旧） | `%APPDATA%\Claude\projects\` |

## 注意事項

1. **PowerShell のバージョン**: Windows PowerShell 5.1 以降を推奨
2. **文字コード**: ファイル保存時は UTF-8 BOM なし を推奨
3. **パス**: スペースを含むパスは正しく動作します
4. **daemon の自動起動**: Claude Code 起動時に自動で daemon が起動します
5. **複数ウィンドウ**: 複数の Claude Code ウィンドウで同じ使用率が表示されます

## サポート

問題が解決しない場合は、以下の情報を含めて報告してください：

1. Windows のバージョン (`winver` で確認)
2. PowerShell のバージョン (`$PSVersionTable.PSVersion`)
3. Python のバージョン (`python --version`)
4. Node.js のバージョン (`node --version`)
5. エラーメッセージとログファイルの内容
