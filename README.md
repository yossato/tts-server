# TTS HTTPサーバー

Qwen3-TTSモデルを常駐させ、ブラウザからテキスト入力→即座に音声生成・再生できるWebアプリ。
モデルは起動時に1回だけ読み込むため、2回目以降の生成は待ち時間なしで開始される。

## 動作要件

- **Apple Silicon Mac（M1/M2/M3/M4）専用**
- MLXフレームワークはApple Siliconのユニファイドメモリとニューラルエンジンを活用して推論を高速化するため、Intel MacやLinux/Windowsでは動作しません
- macOS 14 (Sonoma) 以降推奨
- Python 3.11以上

## セットアップ

```bash
# 追加パッケージ（初回のみ）
.venv/bin/pip install fastapi uvicorn

# サーバー起動
.venv/bin/python tts-server/tts_server.py
```

ブラウザで http://localhost:8000 を開く。

## Web UI

- テキスト入力エリア
- スピーカー選択（serena, vivian, uncle_fu, ryan, aiden, ono_anna, sohee, eric, dylan）
- 言語選択（Japanese / Chinese / English）
- 感情・話し方の指示入力
- 「生成」ボタン → 生成中ローディング表示 → 自動再生 + WAVダウンロード
- 生成時間・音声長・RTF を表示

## API

### POST `/tts`

```bash
curl -X POST http://localhost:8000/tts \
  -H "Content-Type: application/json" \
  -d '{"text":"こんにちは","speaker":"Aiden","language":"Japanese","instruct":"落ち着いた声で。"}' \
  -o output.wav
```

リクエストボディ:

| フィールド | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| `text` | string | (必須) | 読み上げるテキスト |
| `speaker` | string | `"Aiden"` | スピーカー名 |
| `language` | string | `"Japanese"` | 言語 |
| `instruct` | string | `"落ち着いた声で、はっきりとした発音。"` | 感情・話し方の指示 |

レスポンス: `audio/wav` バイナリ

レスポンスヘッダーに生成統計情報を含む:
- `X-Generation-Time` — 生成にかかった秒数
- `X-Audio-Duration` — 音声の長さ（秒）
- `X-RTF` — リアルタイムファクター

### GET `/speakers`

利用可能なスピーカー一覧を返す。

```bash
curl http://localhost:8000/speakers
```

## 使用モデル

`mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-bf16`（`tts_server.py`内の`MODEL_ID`で変更可能）
