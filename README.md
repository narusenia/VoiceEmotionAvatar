# VoiceEmotionAvatar (VEA)

VRChatでリアルタイムに音声の感情をAIで判別し、アバターの表情パラメータをOSCで操作するツール。
笑えば笑顔に、怒れば怒り顔に、声の感情がそのままアバターの表情に反映される。

## 仕組み

```
マイク → 音声キャプチャ(1.5s窓) → emotion2vec(GPU推論) → スムージング → OSC → VRChat
                                                              ↓
                                                        Dear PyGui GUI
```

- **感情認識**: [emotion2vec](https://github.com/ddlBoJack/emotion2vec) (FunASR) によるローカルAI推論
- **対応感情**: 喜び / 怒り / 悲しみ / 驚き / ニュートラル の5種
- **出力**: 各感情の確率を Float (0.0〜1.0) で OSC 送信
- **推論**: 250msごと、OSC/GUI出力は毎フレーム（~60fps）Lerp補間

## 動作環境

- Windows 10/11
- Python 3.10〜3.12
- NVIDIA GPU (CUDA対応、RTX3060以上推奨)
- [uv](https://docs.astral.sh/uv/) パッケージマネージャ

## セットアップ

### 1. uv のインストール

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. 依存パッケージのインストール

`setup.bat` をダブルクリック、または:

```bash
uv sync --python 3.12
```

初回は PyTorch (~2.5GB) と emotion2vec モデルのダウンロードがあるため時間がかかる。

### 3. 起動

`start.bat` をダブルクリック、または:

```bash
uv run vea
```

## VRChat側の設定

### Expression Parameters

アバターの Expression Parameters に以下の Float パラメータを追加する:

| パラメータ名 | 型 | Default | Saved |
|---|---|---|---|
| `VEA_Joy` | Float | 0 | false |
| `VEA_Anger` | Float | 0 | false |
| `VEA_Sadness` | Float | 0 | false |
| `VEA_Surprise` | Float | 0 | false |
| `VEA_Neutral` | Float | 1 | false |

### FX Animator

FX Animator Controller に `VEA_Emotions` レイヤーを追加し、Direct Blend Tree で各感情のアニメーションクリップを紐づける。レイヤーは **一番最後** に配置すること（他のレイヤーに上書きされるのを防ぐ）。

### Unity Editor スクリプト

`unity/Editor/` にエディタツールが同梱されている。Unity プロジェクトの `Assets/VEA/Editor/` にコピーして使う。

- **Tools → VEA → Setup Avatar**: Expression Parameters と FX レイヤーの自動セットアップ
- **Tools → VEA → BlendShape Editor**: 各感情のアニメーションクリップを GUI で編集
- **Tools → VEA → Debug Test**: Animator を経由せず BlendShape を直接テスト、テスト用 FX への差し替え

### OSC 有効化

VRChat 内で Action Menu → Options → OSC → Enabled。
初回有効化時はアバターを着替えて戻し、OSC パラメータファイルを再生成する。

## GUI の使い方

### 基本操作

1. **Microphone**: 使用するマイクデバイスを選択
2. **Input Gain**: マイク入力の増幅（音が小さい場合に上げる）
3. **Level**: 現在の入力音量メーター
4. **Start / Stop**: パイプラインの開始・停止
5. **Emotion Monitor**: 5感情の確率をリアルタイム表示

### モード

- **Smooth Mode** (デフォルト): Lerp + ヒステリシスで滑らかに表情遷移
  - Lerp Speed: 遷移の速さ
  - Hysteresis: 感情切替の閾値（チャタリング防止）
- **Instant Mode**: 閾値を超えた感情に即座に切替
  - Instant Threshold: 切替に必要な確率の閾値
  - Smoothing: 0=キレキレ（即座）、1=なめらか（ゆっくりフェード）

### Advanced Settings

- OSC 送信先 IP / Port の変更（デフォルト: 127.0.0.1:9000）

## 設定ファイル

`~/.vea/config.yaml` に自動保存される。GUI で変更した値は即座に反映・保存される。

## プロジェクト構成

```
VoiceEmotionAvatar/
├── src/vea/
│   ├── main.py          # エントリーポイント、アプリケーション統合
│   ├── audio.py          # マイク音声キャプチャ（1.5sスライディングウィンドウ）
│   ├── emotion.py        # emotion2vec による感情認識
│   ├── smoother.py       # ヒステリシス付き Lerp / Instant Mode
│   ├── osc_sender.py     # VRChat への OSC パラメータ送信
│   ├── gui.py            # Dear PyGui による GUI
│   └── config.py         # YAML 設定管理
├── unity/Editor/
│   ├── VeaSetupWindow.cs      # Expression Parameters / FX レイヤー自動セットアップ
│   ├── VeaBlendShapeEditor.cs # 感情アニメーション BlendShape 編集 GUI
│   └── VeaDebugTest.cs        # BlendShape 直接テスト / テスト用 FX 差し替え
├── docs/
│   ├── requirements.md   # 要件定義書
│   └── implementation-plan.md  # 実装計画書
├── setup.bat             # 環境構築用バッチファイル
├── start.bat             # 起動用バッチファイル
└── pyproject.toml        # uv / Python プロジェクト設定
```

## 依存ライブラリ

| ライブラリ | 用途 |
|---|---|
| torch + CUDA | emotion2vec の推論エンジン |
| funasr | emotion2vec モデルのロード・推論 |
| sounddevice | マイク音声キャプチャ |
| numpy | 音声データ処理 |
| python-osc | OSC プロトコル送信 |
| dearpygui | GUI |
| pyyaml | 設定ファイル |

## ライセンス

Private
