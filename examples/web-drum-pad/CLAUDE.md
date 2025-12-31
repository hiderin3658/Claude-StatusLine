# プロジェクト AI ガイド（Web Drum Pad）

> このファイルは、**Web Drum Pad 専用の AI 向けルール集**です。
> 共通ルール（`~/.claude/AI_COMMON_RULES.md`）に加えて、このプロジェクト固有の前提・例外・開発規約を定義します。

---

## 1. プロジェクト概要

- **プロジェクト名**: Web Drum Pad
- **概要**:
  - ブラウザ上で動作する音楽パッドコントローラー
  - 16パッド（4×4グリッド）で最大8音同時発音
  - 16ステップシーケンサー機能付き
  - MP3録音・ダウンロード機能
- **想定ユーザー**:
  - PC、タブレット、スマートフォンのユーザー
  - 音楽制作やビートメイキングに興味のある一般ユーザー
- **対象ブラウザ**:
  - Chrome、Safari、Edge、Firefox（最新版）
- **デプロイ先**: Vercel

---

## 2. 技術スタック（このプロジェクト専用）

### 2.1 フレームワーク・言語
- **React**: 18.x（UIフレームワーク）
- **Vite**: ビルドツール（高速な開発環境）
- **JavaScript/JSX**: メイン言語（TypeScriptはオプション）

### 2.2 スタイリング
- **Tailwind CSS**: レスポンシブ対応が容易

### 2.3 音声処理
- **Tone.js**: Web Audio APIのラッパー（音声再生・シーケンサー）
- **lamejs**: ブラウザ内でのMP3エンコード

### 2.4 データ保存
- **localStorage**: ユーザー設定・パターン保存

### 2.5 開発ツール
- **ESLint**: コード品質チェック
- **Prettier**: コードフォーマット

> AI への指示例：
> 「このプロジェクトでは React 18 と Vite を使用します。
> 音声処理は Tone.js で実装し、スタイリングは Tailwind CSS を使用してください。」

---

## 3. ディレクトリ構成ルール

```text
web-drum-pad/
├── public/
│   ├── sounds/               # 音源ファイル
│   │   ├── drums/            # ドラムキット（20音）
│   │   ├── synth/            # シンセ・ベース（12音）
│   │   └── fx/               # パーカッション・FX（8音）
│   └── favicon.ico
├── src/
│   ├── components/           # UIコンポーネント
│   │   ├── Pad.jsx           # 個別パッドコンポーネント
│   │   ├── PadGrid.jsx       # 4×4パッドグリッド
│   │   ├── Sequencer.jsx     # 16ステップシーケンサー
│   │   ├── Controls.jsx      # 再生・停止・BPMコントロール
│   │   ├── Settings.jsx      # 設定画面
│   │   └── Recorder.jsx      # 録音機能
│   ├── hooks/                # カスタムフック
│   │   ├── useAudio.js       # 音声再生フック
│   │   ├── useSequencer.js   # シーケンサーフック
│   │   ├── useRecorder.js    # 録音フック
│   │   └── useLocalStorage.js # localStorage操作フック
│   ├── utils/                # ユーティリティ
│   │   ├── soundData.js      # 音源定義データ
│   │   └── constants.js      # 定数定義
│   ├── styles/               # スタイル
│   │   └── index.css         # Tailwind CSS エントリーポイント
│   ├── App.jsx               # メインアプリケーション
│   └── main.jsx              # エントリーポイント
├── docs/                     # ドキュメント
│   ├── web-drum-pad-specification.md  # 仕様書
│   └── web-drum-pad-sound-sources.md  # 音源リスト
├── .gitignore
├── index.html
├── package.json
├── tailwind.config.js
├── vite.config.js
└── README.md
```

### ディレクトリに関するルール

- `src/components/`: 再利用可能なUIコンポーネントを配置
- `src/hooks/`: React カスタムフックを配置（ロジックの分離）
- `src/utils/`: 純粋関数・定数・データ定義を配置
- `public/sounds/`: 音源ファイルをカテゴリ別に配置

> AI への指示例：
> 「新しい機能を追加する場合は、UIロジックは components/、
> 状態管理やビジネスロジックは hooks/ に分離してください。」

---

## 4. コーディング規約（このプロジェクト専用）

### 4.1 React コンポーネント

```jsx
// ✅ 良い例：関数コンポーネント + カスタムフック
import { useState, useCallback } from 'react';
import { useAudio } from '../hooks/useAudio';

export const Pad = ({ soundId, color, volume }) => {
  const [isActive, setIsActive] = useState(false);
  const { playSound } = useAudio();

  const handleTap = useCallback(() => {
    setIsActive(true);
    playSound(soundId, volume);
    setTimeout(() => setIsActive(false), 100);
  }, [soundId, volume, playSound]);

  return (
    <button
      onClick={handleTap}
      className={`pad ${isActive ? 'active' : ''}`}
      style={{ backgroundColor: color }}
    >
      {soundId}
    </button>
  );
};
```

### 4.2 カスタムフックのパターン

```jsx
// ✅ 良い例：Tone.js を使った音声フック
import { useRef, useCallback, useEffect } from 'react';
import * as Tone from 'tone';

export const useAudio = () => {
  const playersRef = useRef({});

  // 音源のプリロード
  useEffect(() => {
    const loadSounds = async () => {
      // 音源ファイルをロード
    };
    loadSounds();

    return () => {
      // クリーンアップ
      Object.values(playersRef.current).forEach(player => player.dispose());
    };
  }, []);

  const playSound = useCallback((soundId, volume = 1.0) => {
    const player = playersRef.current[soundId];
    if (player && player.loaded) {
      player.volume.value = Tone.gainToDb(volume);
      player.start();
    }
  }, []);

  return { playSound };
};
```

### 4.3 Tailwind CSS スタイリング

```jsx
// ✅ 良い例：レスポンシブ対応
<div className="grid grid-cols-4 gap-2 p-4">
  {/* PC: 100px, タブレット: 80px, スマホ: 70px */}
  <button className="
    w-[70px] h-[70px]
    md:w-[80px] md:h-[80px]
    lg:w-[100px] lg:h-[100px]
    rounded-lg
    bg-gray-800
    hover:bg-gray-700
    active:scale-95
    transition-all
  ">
    Pad
  </button>
</div>
```

### 4.4 エラーハンドリング

```jsx
// ✅ 良い例：Web Audio API のエラーハンドリング
const initAudio = async () => {
  try {
    // ユーザー操作後に AudioContext を開始
    await Tone.start();
    console.log('Audio context started');
  } catch (error) {
    console.error('Failed to start audio context:', error);
    // ユーザーにフィードバックを表示
    setAudioError('音声の初期化に失敗しました');
  }
};
```

---

## 5. 機能仕様

### 5.1 パッドコントローラー

| 項目 | 仕様 |
|------|------|
| パッド数 | 16個（4×4グリッド） |
| 操作方法 | タップ / クリック / キーボードショートカット |
| 同時発音 | 最大8音（ポリフォニック） |
| ビジュアルフィードバック | タップ時にパッドが光る |

### 5.2 シーケンサー

| 項目 | 仕様 |
|------|------|
| ステップ数 | 16ステップ（1小節） |
| BPM設定 | 60〜200 BPM（可変） |
| ループ再生 | ON/OFF切り替え |
| メトロノーム | ON/OFF切り替え |
| パターン保存 | 最大8パターン |

### 5.3 録音機能

| 項目 | 仕様 |
|------|------|
| 録音形式 | MP3（lamejsでエンコード） |
| 最大録音時間 | 5分 |
| ダウンロード | ボタン1クリックで保存 |

---

## 6. キーボードショートカット

### パッド操作

```
┌───┬───┬───┬───┐
│ 1 │ 2 │ 3 │ 4 │  ← パッド 1-4
├───┼───┼───┼───┤
│ Q │ W │ E │ R │  ← パッド 5-8
├───┼───┼───┼───┤
│ A │ S │ D │ F │  ← パッド 9-12
├───┼───┼───┼───┤
│ Z │ X │ C │ V │  ← パッド 13-16
└───┴───┴───┴───┘
```

### コントロール

| キー | 機能 |
|------|------|
| `Space` | 再生 / 停止 |
| `Enter` | 録音開始 / 停止 |
| `←` / `→` | BPM -1 / +1 |
| `↑` / `↓` | BPM -10 / +10 |
| `M` | メトロノーム ON/OFF |
| `L` | ループ ON/OFF |

---

## 7. 音源リスト（40音）

### ドラムキット（20音）

| # | 音名 | ファイル名 |
|---|------|-----------|
| 1 | Kick Deep | `drums/kick-deep.mp3` |
| 2 | Kick Tight | `drums/kick-tight.mp3` |
| 3 | Kick 808 | `drums/kick-808.mp3` |
| 4 | Snare Acoustic | `drums/snare-acoustic.mp3` |
| 5 | Snare Electronic | `drums/snare-electronic.mp3` |
| 6 | Snare Rim | `drums/snare-rim.mp3` |
| 7 | Clap | `drums/clap.mp3` |
| 8 | Hi-Hat Closed | `drums/hihat-closed.mp3` |
| 9 | Hi-Hat Open | `drums/hihat-open.mp3` |
| 10 | Hi-Hat Pedal | `drums/hihat-pedal.mp3` |
| 11 | Crash | `drums/crash.mp3` |
| 12 | Ride | `drums/ride.mp3` |
| 13 | Tom High | `drums/tom-high.mp3` |
| 14 | Tom Mid | `drums/tom-mid.mp3` |
| 15 | Tom Low | `drums/tom-low.mp3` |
| 16 | Floor Tom | `drums/floor-tom.mp3` |
| 17 | Cowbell | `drums/cowbell.mp3` |
| 18 | Tambourine | `drums/tambourine.mp3` |
| 19 | Shaker | `drums/shaker.mp3` |
| 20 | Cross Stick | `drums/cross-stick.mp3` |

### シンセ・ベース（12音）

| # | 音名 | ファイル名 |
|---|------|-----------|
| 21 | Bass 808 | `synth/bass-808.mp3` |
| 22 | Bass Sub | `synth/bass-sub.mp3` |
| 23 | Bass Wobble | `synth/bass-wobble.mp3` |
| 24 | Synth Lead | `synth/synth-lead.mp3` |
| 25 | Synth Pluck | `synth/synth-pluck.mp3` |
| 26 | Synth Stab | `synth/synth-stab.mp3` |
| 27 | Synth Pad | `synth/synth-pad.mp3` |
| 28 | Synth Arp | `synth/synth-arp.mp3` |
| 29 | Piano Hit | `synth/piano-hit.mp3` |
| 30 | Organ Stab | `synth/organ-stab.mp3` |
| 31 | Brass Hit | `synth/brass-hit.mp3` |
| 32 | String Hit | `synth/string-hit.mp3` |

### パーカッション・FX（8音）

| # | 音名 | ファイル名 |
|---|------|-----------|
| 33 | Conga High | `fx/conga-high.mp3` |
| 34 | Conga Low | `fx/conga-low.mp3` |
| 35 | Bongo | `fx/bongo.mp3` |
| 36 | Djembe | `fx/djembe.mp3` |
| 37 | FX Rise | `fx/fx-rise.mp3` |
| 38 | FX Down | `fx/fx-down.mp3` |
| 39 | FX Noise | `fx/fx-noise.mp3` |
| 40 | FX Laser | `fx/fx-laser.mp3` |

---

## 8. データ構造

### localStorage保存形式

```json
{
  "webDrumPad": {
    "version": "1.0.0",
    "settings": {
      "bpm": 120,
      "volume": 0.8,
      "metronome": false,
      "loop": true
    },
    "pads": [
      {
        "id": 1,
        "soundId": "kick-deep",
        "volume": 1.0,
        "color": "#FF5733"
      }
    ],
    "patterns": [
      {
        "id": 1,
        "name": "Pattern 1",
        "steps": {
          "1": [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0],
          "2": [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0]
        }
      }
    ],
    "currentPattern": 1
  }
}
```

---

## 9. レスポンシブ対応

| デバイス | 画面幅 | パッドサイズ | レイアウト |
|----------|--------|-------------|-----------|
| PC | 1024px以上 | 100px × 100px | 横並び（パッド + コントロール） |
| タブレット | 768px〜1023px | 80px × 80px | 横並び（コンパクト） |
| スマートフォン | 767px以下 | 70px × 70px | 縦並び |

---

## 10. 開発フェーズ

| Phase | 内容 | 詳細 |
|-------|------|------|
| Phase 1 | プロジェクトセットアップ | Vite + React + Tailwind初期設定 |
| Phase 2 | パッドUI + 音再生 | 16パッドの表示、Tone.jsで音再生 |
| Phase 3 | 音源選択 + 設定画面 | 40音源の選択UI、パッド設定 |
| Phase 4 | localStorage保存 | 設定の保存・読み込み |
| Phase 5 | シーケンサー機能 | 16ステップシーケンサー、パターン保存 |
| Phase 6 | 録音機能 | MP3録音・ダウンロード |
| Phase 7 | キーボードショートカット | PC用ショートカット実装 |
| Phase 8 | レスポンシブ対応 | スマホ・タブレット最適化 |
| Phase 9 | テスト + バグ修正 | 各デバイスでの動作確認 |
| Phase 10 | Vercelデプロイ | 本番環境デプロイ |

---

## 11. Tone.js 使用パターン

### 11.1 音源のロード

```jsx
import * as Tone from 'tone';

// Playerを使った音源ロード
const player = new Tone.Player('/sounds/drums/kick-deep.mp3').toDestination();

// 複数音源を一括ロード
const players = new Tone.Players({
  'kick': '/sounds/drums/kick-deep.mp3',
  'snare': '/sounds/drums/snare-acoustic.mp3',
  'hihat': '/sounds/drums/hihat-closed.mp3',
}).toDestination();
```

### 11.2 シーケンサーの実装

```jsx
// Tone.Sequence を使った16ステップシーケンサー
const sequence = new Tone.Sequence(
  (time, step) => {
    // 各ステップで発音するサウンドを再生
    if (pattern[step]) {
      player.start(time);
    }
  },
  [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
  '16n'
);

// BPM設定
Tone.Transport.bpm.value = 120;

// 再生開始
Tone.Transport.start();
sequence.start(0);
```

### 11.3 録音の実装

```jsx
// MediaRecorder + Tone.Destination を使った録音
const recorder = new Tone.Recorder();
Tone.Destination.connect(recorder);

// 録音開始
await recorder.start();

// 録音停止 & Blobを取得
const recording = await recorder.stop();

// ダウンロード
const url = URL.createObjectURL(recording);
const a = document.createElement('a');
a.href = url;
a.download = 'recording.webm';
a.click();
```

---

## 12. 実装後の品質チェックフロー（必須）

### 12.1 品質チェックの流れ

```
1. 実装完了
2. ビルドエラーチェック（npm run build）
3. ESLint チェック（npm run lint）
4. エラー修正
5. ブラウザ動作確認
6. レスポンシブ確認（PC、タブレット、スマホ）
7. 完了
```

### 12.2 ビルドエラーチェック

```bash
# 開発サーバー起動
npm run dev

# 本番ビルド
npm run build

# プレビュー
npm run preview
```

### 12.3 ESLint チェック

```bash
# リントチェック
npm run lint

# 自動修正
npm run lint -- --fix
```

### 12.4 動作確認チェックリスト

- [ ] 全16パッドが正常に発音するか
- [ ] キーボードショートカットが動作するか
- [ ] シーケンサーの再生・停止が動作するか
- [ ] BPM変更が反映されるか
- [ ] パターン保存・読み込みが動作するか
- [ ] 録音・ダウンロードが動作するか
- [ ] localStorageに設定が保存されるか
- [ ] レスポンシブ表示が正しいか

---

## 13. Vercel デプロイ

### 13.1 デプロイ設定

| 項目 | 設定値 |
|------|--------|
| Framework Preset | Vite |
| Build Command | `npm run build` |
| Output Directory | `dist` |
| Install Command | `npm install` |

### 13.2 デプロイ手順

1. GitHubリポジトリを作成
2. Vercelアカウント作成（GitHub連携）
3. リポジトリをインポート
4. ビルド設定（自動検出）
5. デプロイ完了

### 13.3 環境変数（必要に応じて）

```
VITE_APP_NAME=Web Drum Pad
VITE_APP_VERSION=1.0.0
```

---

## 14. 既知の制限・注意事項

### 14.1 Web Audio API の制限

- **自動再生禁止**: ユーザー操作（クリック等）後に AudioContext を開始する必要がある
- **モバイルでの挙動**: iOS Safari では追加の対応が必要な場合がある

```jsx
// ✅ 良い例：ユーザー操作後に初期化
const handleFirstInteraction = async () => {
  await Tone.start();
  console.log('Audio is ready');
};
```

### 14.2 音源ファイルの制限

- 推奨形式: MP3（128-320kbps）または WAV
- 推奨長さ: 0.1秒〜2秒
- ファイルサイズ: 1ファイル50KB〜500KB目安

### 14.3 localStorage の制限

- 容量制限: 約5MB
- パターンデータが大きくなりすぎないよう注意

---

## 15. AI への依頼テンプレート（このプロジェクト専用）

このプロジェクトで AI にコードを書いてもらうときの依頼例：

```text
あなたは React と Tone.js を使用した Web Drum Pad の
開発アシスタントです。

共通ルール（~/.claude/AI_COMMON_RULES.md）に加えて、
次のプロジェクト固有ルールを守ってください：
- React 18 の関数コンポーネントを使用
- 状態管理は useState/useReducer を使用
- 音声処理は Tone.js で実装
- スタイリングは Tailwind CSS を使用
- レスポンシブ対応（PC、タブレット、スマホ）

【依頼内容】
シーケンサーコンポーネントを実装してください。
- 16ステップのグリッド表示
- 各ステップのON/OFF切り替え
- 現在の再生位置をハイライト表示
- パターンの保存・読み込み機能

実装後は以下の流れで品質チェックを実施してください：
1. ビルドエラーチェック（npm run build）
2. ESLint チェック（npm run lint）
3. ブラウザ動作確認
```

---

## 16. 更新ポリシー

- この専用メモリは、**機能追加・仕様変更時に更新**する
- 大きな方針変更がある場合は、共通ルール側も確認する
- 更新履歴や改訂日を下に追記して管理する

---

### 更新履歴

- 2025-12-23: 初版作成（web-drum-pad-specification.md を基に作成）
