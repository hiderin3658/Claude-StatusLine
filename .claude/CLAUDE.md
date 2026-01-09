# プロジェクト AI ガイド（Claude-StatusLine）

> 共通ルール（`~/.claude/CLAUDE.md`）に加えて、このプロジェクト固有のルールを定義します。

---

## 1. プロジェクト概要

| 項目 | 内容 |
|-----|------|
| **名前** | Claude-StatusLine |
| **概要** | Claude Code のメッセージ使用率をステータスラインに表示するツール群 |
| **機能** | 5時間ローリングウィンドウでの使用率計算、プラン別制限、色分け表示 |
| **対応OS** | Windows、macOS、Linux |
| **配布物** | AIルールファイル、監視スクリプト、テンプレート |

---

## 2. 技術スタック

| カテゴリ | 技術 |
|---------|------|
| **スクリプト言語** | Python 3.7+、Node.js 14+、Bash、PowerShell |
| **データ形式** | JSON、JSONL |
| **対象ツール** | Claude Code CLI |

---

## 3. ディレクトリ構成

```
Claude-StatusLine/
├── .claude/
│   └── CLAUDE.md              # このファイル（プロジェクト固有ルール）
├── install-to-home/
│   ├── required/              # ~/.claude/ にインストールする必須ファイル
│   │   ├── CLAUDE.md          # 配布用AIルール
│   │   ├── templates/         # テンプレートファイル
│   │   ├── references/        # 参照ファイル
│   │   ├── get-message-usage.py
│   │   ├── ccusage-daemon.mjs
│   │   ├── status-line.sh / .ps1
│   │   ├── on-startup.sh / .ps1
│   │   └── usage-config.json
│   └── optional/              # オプションツール
├── project-template/          # プロジェクト固有設定テンプレート
│   └── CLAUDE.md
├── README.md
├── WINDOWS_SETUP.md
└── CLAUDE.md                  # 参照用（旧バージョン）
```

---

## 4. コーディング規約

### 4.1 クロスプラットフォーム対応

| OS | シェル | ファイル拡張子 |
|----|--------|--------------|
| macOS/Linux | Bash | `.sh` |
| Windows | PowerShell | `.ps1` |
| 共通 | Python/Node.js | `.py`, `.mjs` |

**重要ルール**:
- 同一機能は必ず両プラットフォーム版を用意
- パス区切りはOSに応じて処理（Python: `pathlib`、Node.js: `path`）
- 環境変数参照: `$HOME` (Unix) / `$env:USERPROFILE` (Windows)

### 4.2 Python スクリプト

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""スクリプトの説明"""

import sys
from pathlib import Path

def main():
    # クロスプラットフォームパス処理
    home = Path.home()
    claude_dir = home / ".claude"
```

### 4.3 Node.js スクリプト

```javascript
#!/usr/bin/env node
import { homedir } from 'os';
import { join } from 'path';

const claudeDir = join(homedir(), '.claude');
```

### 4.4 シェルスクリプト（Bash）

```bash
#!/bin/bash
# 説明コメント

CLAUDE_DIR="${HOME}/.claude"
```

### 4.5 PowerShell スクリプト

```powershell
# 説明コメント

$ClaudeDir = "$env:USERPROFILE\.claude"
```

---

## 5. 配布ファイル管理

### 5.1 ルールファイルの同期

| ファイル | 役割 |
|---------|------|
| `~/.claude/CLAUDE.md` | ユーザーの実際のルールファイル |
| `install-to-home/required/CLAUDE.md` | 配布用（最新版を維持） |
| `/CLAUDE.md`（ルート） | 参照用（削除または最新版に更新） |

**更新時の注意**:
- `~/.claude/CLAUDE.md` を更新したら `install-to-home/required/CLAUDE.md` も同期
- 外部ファイル（templates/, references/）も同様に同期

### 5.2 バージョン管理

更新履歴は各ファイルの末尾に記録する。

---

## 6. テスト方針

### 6.1 手動テスト項目

| 項目 | コマンド |
|------|---------|
| Python スクリプト | `python3 ~/.claude/get-message-usage.py` |
| Node.js daemon | `node ~/.claude/ccusage-daemon.mjs` |
| ステータスライン | `~/.claude/status-line.sh` (Unix) / `.ps1` (Windows) |

### 6.2 期待される出力

```json
{
  "plan": "max-100",
  "messageCount": 28,
  "messageLimit": 225,
  "messagePercent": 12
}
```

---

## 7. セキュリティ考慮事項

- ログファイルのパスは固定（`~/.claude/projects/`）
- 外部サービスへの通信は行わない
- ユーザーデータは読み取りのみ（書き込みはキャッシュファイルのみ）

---

## 8. 更新ポリシー

- ルートの `~/.claude/CLAUDE.md` 更新時は配布ファイルも同期
- 新機能追加時は両プラットフォーム版を同時に実装
- README.md のファイル構成セクションも更新

### 更新履歴

- 2026-01-09: 初版作成
  - プロジェクト固有ルールを `.claude/CLAUDE.md` として分離
  - 配布用ファイルをスリム化バージョンに更新
  - 外部ファイル（templates/, references/）を追加
