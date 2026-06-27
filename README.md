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

### かんたん起動（推奨）

`start.bat` をダブルクリックするだけ。**Python や uv を事前にインストールする必要はない。**

初回起動時に以下を自動で取得する（ネットワーク接続が必要）:

1. **uv**（環境マネージャ、約30MB）— 無ければ `./.uv/` に自動ダウンロード
2. **Python 3.12 + PyTorch(CUDA12.4) ほか依存**（約2.5GB）— uv が `./.venv/` に構築
3. **emotion2vec モデル**（初回推論時、数百MB）

2回目以降はそのまま起動する。初回のみ合計数GBのDLがあるため時間がかかる。

### 手動 / 開発者向け

uv を導入済みなら直接操作できる:

```bash
uv sync        # 依存環境を構築（または setup.bat）
uv run vea     # 起動（または start.bat）
```

uv 自体のインストール:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
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

エディタツールを Unity プロジェクトに導入する方法は2通り。

**A. unitypackage で導入（推奨）**

[Releases](https://github.com/narusenia/VoiceEmotionAvatar/releases) から `VEA-vX.Y.Z.unitypackage` をダウンロードし、Unity にドラッグ＆ドロップでインポートする。`Assets/VEA/Editor/` に展開される。

> 利用には VRChat SDK3 (Avatars) と [Modular Avatar](https://modular-avatar.nadena.dev/) がプロジェクトに導入済みであること。

**B. ソースから手動コピー**

`unity/Assets/VEA/Editor/` の中身を Unity プロジェクトの `Assets/VEA/Editor/` にコピーする。

導入後、以下のメニューが使えるようになる:

- **Tools → VEA → Setup with Modular Avatar** (推奨): MA Merge Animator で非破壊セットアップ。Face-Emo 等と干渉しない
- **Tools → VEA → Setup Avatar**: Expression Parameters と FX レイヤーの直接セットアップ（MA未使用時）
- **Tools → VEA → BlendShape Editor**: 各感情のアニメーションクリップを GUI で編集
- **Tools → VEA → Debug Test**: BlendShape 直接テスト、テスト用 FX への差し替え

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

### Instant Mode

チェックを入れると、最も確率の高い感情が閾値を超えた場合にその感情を 1.0、他を 0.0 にする即時切替モードになる。チェックを外すと Smooth Mode（後述）で動作する。

| パラメータ | 範囲 | デフォルト | 説明 |
|---|---|---|---|
| Instant Threshold | 0.1〜0.9 | 0.4 | この確率を超えた感情に切り替わる。低いと敏感に反応、高いとはっきり喋らないと切り替わらない |
| Smoothing | 0.0〜1.0 | 0.5 | 切替時のフェード量。0=パッと即座に切替、1=ゆっくりフェードして切替 |

### Settings (Smooth Mode)

Instant Mode が OFF の時に使われる設定。全感情の確率をそのまま Lerp 補間してブレンドするモード。

| パラメータ | 範囲 | デフォルト | 説明 |
|---|---|---|---|
| Lerp Speed | 0.01〜1.0 | 0.15 | 毎フレームの補間率。高いほど目標値に速く追従する。0.01だと非常にゆっくり、1.0だと即座に追従 |
| Hysteresis | 0.0〜0.5 | 0.10 | 感情の切替に必要な確率差。現在の感情より新しい感情がこの値以上高くないと切り替わらない。チャタリング（表情がパタパタ切り替わる現象）を防ぐ |
| Silence Threshold | 0.001〜0.1 | 0.01 | 入力音量（RMS）がこの値未満のとき無音と判定し、ニュートラルにフォールバックする。環境ノイズが多い場合は上げる |

### Input

| パラメータ | 範囲 | デフォルト | 説明 |
|---|---|---|---|
| Input Gain | 0.1〜10.0 | 1.0 | マイク入力の増幅倍率。マイクの音量が小さい場合に上げる。大きくしすぎるとクリッピングする |

### Advanced Settings

| パラメータ | デフォルト | 説明 |
|---|---|---|
| OSC IP | 127.0.0.1 | VRChat の OSC 受信アドレス。通常は変更不要 |
| OSC Port | 9000 | VRChat の OSC 受信ポート。通常は変更不要 |

## 設定ファイル

`~/.vea/config.yaml` に自動保存される。GUI で変更した値は即座に反映・保存される。

```yaml
audio:
  channels: 1
  device: null        # null = システムデフォルトマイク
  input_gain: 1.0
  sample_rate: 16000
emotion:
  analysis_interval_ms: 250
  hysteresis_threshold: 0.1
  lerp_speed: 0.15
  parameter_prefix: VEA
  silence_threshold: 0.01
osc:
  ip: 127.0.0.1
  port: 9000
```

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
├── unity/Assets/VEA/Editor/    # Unity プロジェクト構造でミラー（.meta 付き）
│   ├── VeaSetupWindow.cs      # Expression Parameters / FX レイヤー自動セットアップ
│   ├── VeaMaSetup.cs          # Modular Avatar 非破壊セットアップ
│   ├── VeaBlendShapeEditor.cs # 感情アニメーション BlendShape 編集 GUI
│   └── VeaDebugTest.cs        # BlendShape 直接テスト / テスト用 FX 差し替え
├── scripts/
│   ├── build_unitypackage.py  # .unitypackage ビルド（Unity 不要）
│   └── ensure_uv.bat     # uv を解決（無ければ自動DL）
├── .github/workflows/
│   └── release.yml       # tag push で .unitypackage を Release に添付
├── docs/
│   ├── requirements.md   # 要件定義書
│   └── implementation-plan.md  # 実装計画書
├── .python-version       # 使用 Python バージョン (3.12)
├── setup.bat             # 依存環境の事前準備（任意）
├── start.bat             # ワンクリック起動（uv→Python→依存を自動準備）
├── build_unitypackage.bat # unitypackage ビルド用バッチファイル
└── pyproject.toml        # uv / Python プロジェクト設定
```

## unitypackage のビルド

Unity をインストールしていなくても `.unitypackage` を生成できる（中身は gzip + tar のため、コミット済みの `.meta`/GUID からスクリプトで構築する）。

```bash
# いずれか
python scripts/build_unitypackage.py   # → dist/VEA.unitypackage
mise run package
# Windows: build_unitypackage.bat をダブルクリック
```

### リリース（CI）

`v` で始まるタグを push すると GitHub Actions が `.unitypackage` をビルドし、GitHub Release に自動添付する。

```bash
git tag v0.1.0
git push origin v0.1.0
```

手動実行（Actions タブの "Build & Release unitypackage" → Run workflow）の場合は Release は作らず、ワークフローの artifact としてダウンロードできる。

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
