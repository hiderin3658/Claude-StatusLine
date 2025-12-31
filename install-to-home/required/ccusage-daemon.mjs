#!/usr/bin/env node

/**
 * ccusage バックグラウンドデーモン
 *
 * 機能:
 * - 5分ごとに ccusage blocks --json を実行してキャッシュ更新
 * - Claude Code プロセス監視（プロセスがなくなったら自己終了）
 * - PIDファイルで重複起動防止
 */

import { execSync, spawn } from 'child_process';
import { writeFileSync, readFileSync, unlinkSync, existsSync } from 'fs';
import { platform } from 'os';

// 設定（クロスプラットフォーム対応）
// macOS/Linux: /tmp, Windows: %TEMP%
const TEMP_DIR = platform() === 'win32' ? process.env.TEMP : '/tmp';
const CACHE_FILE = `${TEMP_DIR}/ccusage-cache.json`;
const PID_FILE = `${TEMP_DIR}/ccusage-daemon.pid`;
const LOG_FILE = `${TEMP_DIR}/ccusage-daemon.log`;
const UPDATE_INTERVAL = 5 * 60 * 1000; // 5分
const PROCESS_CHECK_INTERVAL = 60 * 1000; // 1分

// ログ出力
function log(message) {
  const timestamp = new Date().toISOString();
  const logMessage = `[${timestamp}] ${message}\n`;
  try {
    writeFileSync(LOG_FILE, logMessage, { flag: 'a' });
  } catch (error) {
    console.error('Failed to write log:', error);
  }
}

// PIDファイルチェック（重複起動防止）
function checkPidFile() {
  if (existsSync(PID_FILE)) {
    try {
      const oldPid = readFileSync(PID_FILE, 'utf8').trim();
      // プロセスが実際に動いているか確認
      try {
        process.kill(oldPid, 0); // シグナル0で存在確認
        log(`Daemon already running (PID: ${oldPid})`);
        return false; // 既に動いている
      } catch (e) {
        // プロセスが存在しない（古いPIDファイル）
        log(`Removing stale PID file (PID: ${oldPid})`);
        unlinkSync(PID_FILE);
      }
    } catch (error) {
      log(`Error reading PID file: ${error.message}`);
    }
  }
  return true; // 起動可能
}

// PIDファイル作成
function writePidFile() {
  try {
    writeFileSync(PID_FILE, `${process.pid}`);
    log(`Daemon started (PID: ${process.pid})`);
  } catch (error) {
    log(`Failed to write PID file: ${error.message}`);
    process.exit(1);
  }
}

// PIDファイル削除
function removePidFile() {
  try {
    if (existsSync(PID_FILE)) {
      unlinkSync(PID_FILE);
      log('PID file removed');
    }
  } catch (error) {
    log(`Failed to remove PID file: ${error.message}`);
  }
}

// Claude Code プロセス数を取得
function getClaudeProcessCount() {
  try {
    let command;
    if (platform() === 'win32') {
      // Windows: node.exe プロセスで claude-code を含むものを検索
      command = 'tasklist /FI "IMAGENAME eq node.exe" /V';
    } else {
      // macOS / Linux: claude-code/cli.js を含むプロセスを検索
      command = 'pgrep -fl "claude-code/cli.js"';
    }

    const output = execSync(command, { encoding: 'utf8', stdio: ['pipe', 'pipe', 'ignore'] });

    if (platform() === 'win32') {
      // Windows: claude-code を含む行をカウント
      const lines = output.split('\n').filter(line => line.toLowerCase().includes('claude-code'));
      return lines.length;
    } else {
      // macOS/Linux: pgrep の出力行数をカウント
      const lines = output.split('\n').filter(line => line.trim() !== '');
      return lines.length;
    }
  } catch (error) {
    // pgrep がプロセスを見つけられなかった場合（exit code 1）
    return 0;
  }
}

// Python コマンドを取得（クロスプラットフォーム対応）
function getPythonCommand() {
  if (platform() === 'win32') {
    // Windows: 複数のパスを試行
    const pythonPaths = [
      `${process.env.LOCALAPPDATA}\\Programs\\Python\\Python312-arm64\\python.exe`,
      `${process.env.LOCALAPPDATA}\\Programs\\Python\\Python312\\python.exe`,
      `${process.env.LOCALAPPDATA}\\Programs\\Python\\Python311\\python.exe`,
      'python'
    ];
    for (const pythonPath of pythonPaths) {
      try {
        execSync(`"${pythonPath}" --version`, { stdio: 'pipe' });
        return `"${pythonPath}"`;
      } catch (e) {
        continue;
      }
    }
    return 'python';
  }
  return 'python3';
}

// メッセージ使用率を取得（Pythonスクリプト経由）
function getMessageUsage() {
  try {
    const scriptPath = platform() === 'win32'
      ? `${process.env.USERPROFILE}\\.claude\\get-message-usage.py`
      : `${process.env.HOME}/.claude/get-message-usage.py`;

    const pythonCmd = getPythonCommand();
    const output = execSync(`${pythonCmd} "${scriptPath}"`, {
      encoding: 'utf8',
      stdio: ['pipe', 'pipe', 'pipe'],
      timeout: 10000 // 10秒タイムアウト
    });

    return JSON.parse(output);
  } catch (error) {
    // Pythonスクリプトは使用率が80%以上の場合 exit code 1 を返すが、
    // stdout には有効なJSONが含まれている
    if (error.stdout) {
      try {
        return JSON.parse(error.stdout);
      } catch (parseError) {
        log(`Failed to parse message usage JSON: ${parseError.message}`);
      }
    }

    log(`Failed to get message usage: ${error.message}`);
    return {
      messageCount: 0,
      messageLimit: 250,
      messagePercent: 0,
      error: error.message
    };
  }
}

// キャッシュ更新（メッセージベース）
async function updateCache() {
  log('Updating usage cache...');

  try {
    // メッセージ使用率を取得
    const messageUsage = getMessageUsage();

    const cacheData = {
      timestamp: new Date().toISOString(),
      // メッセージベースの情報（優先表示）
      messageCount: messageUsage.messageCount || 0,
      messageLimit: messageUsage.messageLimit || 250,
      messagePercent: messageUsage.messagePercent || 0,
      remainingMessages: messageUsage.remainingMessages || 0
    };

    writeFileSync(CACHE_FILE, JSON.stringify(cacheData, null, 2));
    log(`Cache updated: ${cacheData.messagePercent}% (${cacheData.messageCount}/${cacheData.messageLimit} messages)`);
  } catch (error) {
    log(`Failed to update cache: ${error.message}`);
    // エラー時も空のキャッシュを書き込む
    writeFileSync(CACHE_FILE, JSON.stringify({
      timestamp: new Date().toISOString(),
      messageCount: 0,
      messageLimit: 250,
      messagePercent: 0,
      error: error.message
    }, null, 2));
  }
}

// メインループ
async function mainLoop(initialLastUpdate = 0, initialLastProcessCheck = 0) {
  let lastUpdate = initialLastUpdate;
  let lastProcessCheck = initialLastProcessCheck;

  while (true) {
    const now = Date.now();

    // プロセスチェック（1分ごと）
    if (now - lastProcessCheck >= PROCESS_CHECK_INTERVAL) {
      const processCount = getClaudeProcessCount();
      log(`Claude Code processes: ${processCount}`);

      if (processCount === 0) {
        log('No Claude Code processes found. Shutting down...');
        break;
      }

      lastProcessCheck = now;
    }

    // キャッシュ更新（5分ごと）
    if (now - lastUpdate >= UPDATE_INTERVAL) {
      await updateCache();
      lastUpdate = now;
    }

    // 10秒待機
    await new Promise(resolve => setTimeout(resolve, 10000));
  }

  // 終了処理
  removePidFile();
  log('Daemon stopped');
  process.exit(0);
}

// シグナルハンドラ
function setupSignalHandlers() {
  const shutdown = () => {
    log('Received shutdown signal');
    removePidFile();
    process.exit(0);
  };

  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);
}

// メイン処理
async function main() {
  // 重複起動チェック
  if (!checkPidFile()) {
    process.exit(0);
  }

  // PIDファイル作成
  writePidFile();

  // シグナルハンドラ設定
  setupSignalHandlers();

  // 初回キャッシュ更新
  await updateCache();

  // メインループ開始（初回更新済みなので lastUpdate を設定）
  await mainLoop(Date.now(), Date.now());
}

// 実行
main().catch(error => {
  log(`Fatal error: ${error.message}`);
  removePidFile();
  process.exit(1);
});
