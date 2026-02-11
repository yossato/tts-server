# Kokoro TTS Server

超高速・多言語対応TTSサーバー（Kokoro-82M）

## 特徴

- **超高速**: RTF 0.08-0.14（Qwen3-TTSの約10倍速い）
- **多言語**: 日本語、英語（米英・英英）、中国語
- **長文対応**: 100文字ごとに自動分割して連続生成・再生
- **読み間違いなし**: 複雑な文章も正確に読める
- **軽量**: 82Mパラメータ

## 利用可能な音声

- **日本語**: `jf_alpha` (女性), `jm_kumo` (男性)
- **アメリカ英語**: `af_heart`, `af_bella`, `af_nova`, `af_sky`, `am_adam`, `am_echo`
- **イギリス英語**: `bf_alice`, `bf_emma`, `bm_daniel`, `bm_george`
- **中国語**: `zf_xiaobei` (女性), `zm_yunxi` (男性)

## HTTPサーバー

### 起動

```bash
python tts-server/kokoro_tts_server.py
```

ポート: `8001`

### Web UI

ブラウザで http://localhost:8001 にアクセス

### API

#### POST /tts

音声ファイル生成

```bash
curl -X POST http://localhost:8001/tts \
  -H "Content-Type: application/json" \
  -d '{
    "text": "こんにちは。これはKokoroのテストです。",
    "voice": "jf_alpha",
    "language": "Japanese"
  }' \
  --output output.wav
```

#### POST /tts/stream-play

サーバーで再生

```bash
curl -X POST http://localhost:8001/tts/stream-play \
  -H "Content-Type: application/json" \
  -d '{
    "text": "こんにちは",
    "voice": "jf_alpha",
    "language": "Japanese"
  }'
```

## MCPサーバー

### 起動

```bash
python tts-mcp-server/kokoro_mcp_server.py
```

### グローバル設定

`~/Library/Application Support/Code/User/mcp.json` に追加:

```json
{
  "mcpServers": {
    "kokoro-tts": {
      "command": "/Users/yoshiaki/Projects/tts100/.venv/bin/python",
      "args": ["/Users/yoshiaki/Projects/tts100/tts-mcp-server/kokoro_mcp_server.py"],
      "env": {
        "KOKORO_TTS_SERVER_URL": "http://localhost:8001"
      }
    }
  }
}
```

### MCPツール

- `speak(text, voice, language)` - 音声生成・再生
- `get_voices()` - 利用可能な音声一覧
- `notify_completion(message, voice)` - タスク完了通知

## 性能比較

| モデル | RTF | 速度 | 読み間違い | 日本語品質 |
|--------|-----|------|-----------|-----------|
| Kokoro-82M | 0.09 | ⭐⭐⭐⭐⭐ | なし | ⭐⭐⭐⭐ |
| Qwen3-TTS-8bit | 1.05 | ⭐⭐⭐ | 少ない | ⭐⭐⭐⭐⭐ |

## 依存パッケージ

```bash
pip install mlx-audio fastapi uvicorn sounddevice soundfile misaki[ja] num2words phonemizer spacy
pip install https://github.com/explosion/spacy-models/releases/download/ja_core_news_sm-3.8.0/ja_core_news_sm-3.8.0-py3-none-any.whl
brew install espeak-ng
```
