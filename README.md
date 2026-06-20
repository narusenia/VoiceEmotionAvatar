# VoiceEmotionAvatar (VEA)

VRChatでリアルタイムに音声の感情をAIで判別し、アバターの表情パラメータをOSCで操作するツール。

## セットアップ

```bash
uv sync
```

## 起動

```bash
uv run vea
```

## VRChat側の設定

アバターのExpression Parametersに以下のFloatパラメータを追加:

| パラメータ名 | 型 | 説明 |
|---|---|---|
| `VEA_Joy` | Float | 喜び (0.0〜1.0) |
| `VEA_Anger` | Float | 怒り (0.0〜1.0) |
| `VEA_Sadness` | Float | 悲しみ (0.0〜1.0) |
| `VEA_Surprise` | Float | 驚き (0.0〜1.0) |
| `VEA_Neutral` | Float | ニュートラル (0.0〜1.0) |

VRChatのOSC機能を有効にしてください（Action Menu → Options → OSC → Enabled）。
