# 破壊的コマンド拒否リスト（詳細版）

> このファイルは `~/.claude/CLAUDE.md` から参照される詳細リストです。
> 日常的に読み込む必要はなく、確認が必要な時のみ参照してください。

---

## 1. システムファイル・ディレクトリ削除

### Mac/Linux

```bash
# 絶対に実行禁止
rm -rf /
rm -rf /*
rm -rf /etc
rm -rf /usr
rm -rf /bin
rm -rf /sbin
rm -rf /var
rm -rf /System              # macOS
rm -rf /Library             # macOS（システムライブラリ）
rm -rf /Applications        # macOS（全アプリケーション削除）
rm -rf ~                    # ホームディレクトリ全体
rm -rf ~/*                  # ホームディレクトリ内全削除
rm -rf .                    # カレントディレクトリ全削除（危険）
```

### Windows

```bash
# 絶対に実行禁止
rmdir /s /q C:\
rmdir /s /q C:\Windows
rmdir /s /q C:\Program Files
rmdir /s /q C:\Users
del /f /s /q C:\*
rd /s /q C:\
```

---

## 2. sudo/管理者権限の制限

```bash
# sudo は削除以外のすべての操作で禁止
sudo chmod ...              # 権限変更禁止
sudo chown ...              # 所有者変更禁止
sudo mv /etc/...            # システムファイル移動禁止
sudo cp ... /etc/...        # システムファイルコピー禁止
sudo apt remove ...         # パッケージ削除禁止
sudo yum remove ...         # パッケージ削除禁止
sudo brew services ...      # サービス操作禁止
sudo systemctl ...          # サービス操作禁止
sudo launchctl ...          # macOS サービス操作禁止

# sudo で許可される操作（削除のみ、確認後）
sudo rm <file>              # 単一ファイル削除
sudo rm -rf <directory>     # ディレクトリ削除
```

---

## 3. ディスク・パーティション操作

### Mac/Linux

```bash
# 絶対に実行禁止
dd if=/dev/zero of=/dev/...   # ディスク消去
mkfs.*                        # フォーマット
fdisk                         # パーティション操作
diskutil erase                # macOS ディスク消去
diskutil partitionDisk        # macOS パーティション操作
```

### Windows

```bash
# 絶対に実行禁止
format C:                     # ドライブフォーマット
diskpart                      # パーティション操作
```

---

## 4. 権限変更

```bash
# 絶対に実行禁止
chmod -R 777 /
chmod -R 000 /
chown -R root:root /
icacls C:\ /grant Everyone:F  # Windows 権限変更
```

---

## 5. Git 破壊的操作（main/master ブランチ）

```bash
# main/master ブランチで実行禁止
git reset --hard origin/main
git reset --hard origin/master
git push --force origin main
git push --force origin master
git push -f origin main
git push -f origin master
git clean -fdx                # 追跡されていないファイル全削除
```

---

## 6. データベース全削除

```sql
-- 絶対に実行禁止
DROP DATABASE *;
DROP DATABASE production;
DELETE FROM users;            -- WHERE句なしの全削除
DELETE FROM * WHERE 1=1;      -- 全削除系
TRUNCATE TABLE *;             -- 全テーブル削除
```

---

## 更新履歴

- 2026-01-09: 初版作成（CLAUDE.md から分離）
