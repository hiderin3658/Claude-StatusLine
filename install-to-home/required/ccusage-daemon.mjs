#!/usr/bin/env node

/**
 * ccusage バックグラウンドデーモン
 *
 * 機能:
 * - 5分ごとに ccusage blocks --json を実行してキャッシュ更新
 * - Claude Code プロセス監視（プロセスがなくなったら自己終了）
 * - PIDファイルで重複起動防止
 */

import { execSync } from 'child_process';
import { writeFileSync, readFileSync, unlinkSync, existsSync, mkdirSync, statSync } from 'fs';
import { platform } from 'os';
import { join } from 'path';

// タイムアウト定数
const SCRIPT_TIMEOUT = 5000; // 5秒（プロセス検出スクリプト）
const PYTHON_TIMEOUT = 10000; // 10秒（Python スクリプト）
const MAIN_LOOP_INTERVAL = 10000; // 10秒（メインループ待機時間）
const UPDATE_INTERVAL = 5 * 60 * 1000; // 5分（キャッシュ更新間隔）
const PROCESS_CHECK_INTERVAL = 60 * 1000; // 1分（プロセスチェック間隔）
const MAX_LOG_SIZE = 5 * 1024 * 1024; // 5MB（ログファイル最大サイズ）

// ログレベル
const LOG_LEVELS = {
  DEBUG: 'DEBUG',
  INFO: 'INFO',
  WARNING: 'WARNING',
  ERROR: 'ERROR'
};

// ディレクトリ設定（セキュアなユーザーホームディレクトリ配下を使用）
const HOME_DIR = process.env.HOME || process.env.USERPROFILE;
const CACHE_DIR = join(HOME_DIR, '.claude', 'cache');

// キャッシュディレクトリが存在しない場合は作成
if (!existsSync(CACHE_DIR)) {
  mkdirSync(CACHE_DIR, { recursive: true });
}

const CACHE_FILE = join(CACHE_DIR, 'ccusage-cache.json');
const PID_FILE = join(CACHE_DIR, 'ccusage-daemon.pid');
const LOG_FILE = join(CACHE_DIR, 'ccusage-daemon.log');

// ログローテーション（5MBを超えたら古いログを削除）
function rotateLogIfNeeded() {
  try {
    if (existsSync(LOG_FILE)) {
      const stats = statSync(LOG_FILE);
      if (stats.size > MAX_LOG_SIZE) {
        const backupFile = `${LOG_FILE}.old`;
        if (existsSync(backupFile)) {
          unlinkSync(backupFile);
        }
        // 現在のログファイルをバックアップにリネーム
        writeFileSync(backupFile, readFileSync(LOG_FILE));
        unlinkSync(LOG_FILE);
      }
    }
  } catch (error) {
    // ローテーション失敗時は続行（ログが書けなくなるよりはマシ）
    console.error('Log rotation failed:', error);
  }
}

// ログ出力（ログレベル対応）
function log(message, level = LOG_LEVELS.INFO) {
  const timestamp = new Date().toISOString();
  const logMessage = `[${timestamp}] [${level}] ${message}\n`;
  try {
    rotateLogIfNeeded();
    writeFileSync(LOG_FILE, logMessage, { flag: 'a' });
  } catch (error) {
    console.error('Failed to write log:', error);
  }
}

// PIDファイルチェック（重複起動防止）
function checkPidFile() {
  if (existsSync(PID_FILE)) {
    try {
      const pidStr = readFileSync(PID_FILE, 'utf8').trim();
      const oldPid = parseInt(pidStr, 10);

      // PID値の妥当性チェック
      if (isNaN(oldPid) || oldPid <= 0) {
        log(`Invalid PID in PID file: ${pidStr}`, LOG_LEVELS.WARNING);
        unlinkSync(PID_FILE);
        return true; // 起動可能
      }

      // プロセスが実際に動いているか確認
      try {
        process.kill(oldPid, 0); // シグナル0で存在確認
        log(`Daemon already running (PID: ${oldPid})`, LOG_LEVELS.INFO);
        return false; // 既に動いている
      } catch (e) {
        // プロセスが存在しない（古いPIDファイル）
        log(`Removing stale PID file (PID: ${oldPid})`, LOG_LEVELS.INFO);
        unlinkSync(PID_FILE);
      }
    } catch (error) {
      log(`Error reading PID file: ${error.message}`, LOG_LEVELS.ERROR);
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
      log('PID file removed', LOG_LEVELS.INFO);
    }
  } catch (error) {
    log(`Failed to remove PID file: ${error.message}`, LOG_LEVELS.ERROR);
  }
}

// パス構築ヘルパー関数（クロスプラットフォーム対応）
function getClaudeScriptPath(filename) {
  return join(HOME_DIR, '.claude', filename);
}

// Claude Code プロセス数を取得（クロスプラットフォーム対応）
function getClaudeProcessCount() {
  try {
    let command;

    if (platform() === 'win32') {
      // Windows: PowerShellスクリプトを使用してプロセスを検出
      const scriptPath = getClaudeScriptPath('check-claude-process.ps1');
      command = `powershell -NoProfile -ExecutionPolicy Bypass -File "${scriptPath}"`;
    } else {
      // macOS / Linux: シェルスクリプトを使用してプロセスを検出
      const scriptPath = getClaudeScriptPath('check-claude-process.sh');
      command = `bash "${scriptPath}"`;
    }

    const output = execSync(command, {
      encoding: 'utf8',
      stdio: ['pipe', 'pipe', 'pipe'],
      timeout: SCRIPT_TIMEOUT
    });

    // スクリプトから返されるプロセス数を解析
    const count = parseInt(output.trim(), 10);

    // デバッグログ: プロセス数を記録
    log(`Process detection: ${count} Claude Code processes found`, LOG_LEVELS.DEBUG);

    return isNaN(count) ? 0 : count;
  } catch (error) {
    // エラー時の詳細ログ
    if (error.code === 'ENOENT') {
      log(`Process detection failed: Script not found - ${error.message}`, LOG_LEVELS.ERROR);
    } else if (error.status === 1) {
      // exit code 1 = プロセスが見つからなかった（正常）
      log('Process detection: No Claude Code processes found (exit code 1)', LOG_LEVELS.DEBUG);
      return 0;
    } else {
      log(`Process detection error: ${error.message}`, LOG_LEVELS.ERROR);
    }
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
    const scriptPath = getClaudeScriptPath('get-message-usage.py');
    const pythonCmd = getPythonCommand();

    const output = execSync(`${pythonCmd} "${scriptPath}"`, {
      encoding: 'utf8',
      stdio: ['pipe', 'pipe', 'pipe'],
      timeout: PYTHON_TIMEOUT
    });

    return JSON.parse(output);
  } catch (error) {
    // Pythonスクリプトは使用率が80%以上の場合 exit code 1 を返すが、
    // stdout には有効なJSONが含まれている
    if (error.stdout) {
      try {
        return JSON.parse(error.stdout);
      } catch (parseError) {
        log(`Failed to parse message usage JSON: ${parseError.message}`, LOG_LEVELS.ERROR);
      }
    }

    log(`Failed to get message usage: ${error.message}`, LOG_LEVELS.ERROR);
    return {
      messageCount: 0,
      messageLimit: 250,
      messagePercent: 0,
      error: error.message
    };
  }
}

// キャッシュ更新（トークンベース）
function updateCache() {
  log('Updating usage cache...', LOG_LEVELS.INFO);

  try {
    // 使用率データを取得（get-message-usage.py から）
    const usageData = getMessageUsage();

    // トークンベースの使用率を優先（後方互換性のため messagePercent も保持）
    const cacheData = {
      timestamp: new Date().toISOString(),
      // トークンベースの使用率（メイン表示用）
      tokenPercent: usageData.tokenPercent || 0,
      tokenLimit: usageData.tokenLimit || 0,
      remainingTokens: usageData.remainingTokens || 0,
      // トークン詳細
      tokens: usageData.tokens || null,
      modelBreakdown: usageData.modelBreakdown || null,
      // 後方互換性のため messagePercent も保持（トークンベースの値）
      messagePercent: usageData.messagePercent || 0,
      // レガシー: メッセージベースの情報
      legacy: usageData.legacy || null,
      // プラン情報
      plan: usageData.plan || 'pro',
      // ウィンドウ情報（リセット機能対応）
      windowStart: usageData.windowStart || null,
      windowEnd: usageData.windowEnd || null,
      windowHours: usageData.windowHours || 5,
      timeUntilReset: usageData.timeUntilReset || 0,
      // リセット状態
      resetStatus: usageData.resetStatus || null
    };

    writeFileSync(CACHE_FILE, JSON.stringify(cacheData, null, 2));
    const resetMinutes = Math.floor(cacheData.timeUntilReset / 60);
    const tokenK = Math.round((usageData.tokens?.weighted?.total || 0) / 1000);
    const limitK = Math.round(cacheData.tokenLimit / 1000);
    log(`Cache updated: ${cacheData.tokenPercent}% (${tokenK}K/${limitK}K tokens, reset in ${resetMinutes}m)`, LOG_LEVELS.INFO);
  } catch (error) {
    log(`Failed to update cache: ${error.message}`, LOG_LEVELS.ERROR);
    // エラー時も空のキャッシュを書き込む
    writeFileSync(CACHE_FILE, JSON.stringify({
      timestamp: new Date().toISOString(),
      tokenPercent: 0,
      tokenLimit: 0,
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
      log(`Claude Code processes: ${processCount}`, LOG_LEVELS.INFO);

      if (processCount === 0) {
        log('No Claude Code processes found. Shutting down...', LOG_LEVELS.INFO);
        break;
      }

      lastProcessCheck = now;
    }

    // キャッシュ更新（5分ごと）
    if (now - lastUpdate >= UPDATE_INTERVAL) {
      updateCache();
      lastUpdate = now;
    }

    // 10秒待機
    await new Promise(resolve => setTimeout(resolve, MAIN_LOOP_INTERVAL));
  }

  // 終了処理
  removePidFile();
  log('Daemon stopped', LOG_LEVELS.INFO);
  process.exit(0);
}

// シグナルハンドラ
function setupSignalHandlers() {
  const shutdown = () => {
    log('Received shutdown signal', LOG_LEVELS.INFO);
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
  updateCache();

  // メインループ開始（初回更新済みなので lastUpdate を設定）
  await mainLoop(Date.now(), Date.now());
}

// 実行
main().catch(error => {
  log(`Fatal error: ${error.message}`, LOG_LEVELS.ERROR);
  removePidFile();
  process.exit(1);
});
