# VoiceEmotionAvatar (VEA) 要件定義書

## 概要

VRChatでリアルタイムに音声の感情をAIで判別し、アバターの表情パラメータをOSCで操作するツール。

## システム構成

```
[マイク] → [音声キャプチャ] → [emotion2vec] → [スムージング] → [OSC送信] → [VRChat]
                                      ↓
                              [Dear PyGui GUI]
```

## 機能要件

### 1. 音声入力

- 物理マイク（VRChatで使用中のマイクデバイス）から音声を取得
- デバイス選択はGUIから変更可能
- マイク切断時は自動リトライで復帰を試みる

### 2. 感情認識

- モデル: emotion2vec (FunAudioLLM)
- 対応感情: 5種
  - Joy（喜び）
  - Anger（怒り）
  - Sadness（悲しみ）
  - Surprise（驚き）
  - Neutral（ニュートラル）
- 分析間隔: 250ms（4fps）
- 各感情の確率（0.0〜1.0）を出力

### 3. スムージング（表情遷移）

- ヒステリシス付きスムーズ補間（Lerp）
- 一定の確信度閾値を超えないと感情が切り替わらない（チャタリング防止）
- 現在の表情から次の表情へ滑らかにフェード

### 4. OSC送信

- プロトコル: OSC (Open Sound Control)
- 送信先デフォルト: `127.0.0.1:9000`
- 送信先はGUIの高度な設定から変更可能
- パラメータ形式: 感情ごとに独立したFloat（0.0〜1.0）
- パラメータ名:
  - `/avatar/parameters/VEA_Joy`
  - `/avatar/parameters/VEA_Anger`
  - `/avatar/parameters/VEA_Sadness`
  - `/avatar/parameters/VEA_Surprise`
  - `/avatar/parameters/VEA_Neutral`

### 5. GUI

- フレームワーク: Dear PyGui
- 簡素なデザイン
- 必須画面要素:
  - マイクデバイス選択
  - 感情リアルタイムモニター（各感情の確率をバー表示）
  - 感度・閾値調整
  - 開始/停止ボタン
  - 高度な設定（OSC送信先IP・ポート変更）
- エラー時はGUI上にポップアップ通知

### 6. エラーハンドリング

- 一時的エラー（マイク切断等）: GUI通知 + 自動リトライ
- 致命的エラー（モデルロード失敗等）: GUI通知 + 手動対応

## 非機能要件

### 動作環境

- OS: Windows 11
- GPU: NVIDIA RTX3080（CUDA対応）
- Python環境: uv

### パフォーマンス

- 推論レイテンシ: 250ms以内
- 表情遷移: スムーズ（体感遅延なし）
- GPU使用率: VRChatと共存できる範囲

### 起動・終了

- 手動起動・手動終了
- VRChatとの連動なし（将来拡張候補）

## 配置

- プロジェクトパス: `I:\vrc\projects\VoiceEmotionAvatar\`
- Unityプロジェクトとは独立

## 配布形態

- 初期: Pythonスクリプト（`uv run`で起動）
- 将来: exe化（PyInstaller / Nuitka）を検討
