"""Kokoro TTS HTTP Server with Web UI"""

import io
import os
import queue
import re
import subprocess
import tempfile
import threading
import time

import numpy as np
import sounddevice as sd
import soundfile as sf
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, Response
from mlx_audio.tts.utils import load_model
from pydantic import BaseModel

MODEL_ID = "mlx-community/Kokoro-82M-bf16"
SAMPLE_RATE = 24000

# Kokoro のサポートボイス
VOICES = {
    "Japanese": ["jf_alpha", "jm_kumo"],
    "American English": ["af_heart", "af_bella", "af_nova", "af_sky", "am_adam", "am_echo"],
    "British English": ["bf_alice", "bf_emma", "bm_daniel", "bm_george"],
    "Chinese": ["zf_xiaobei", "zm_yunxi"],
}

LANG_CODES = {
    "Japanese": "j",
    "American English": "a",
    "British English": "b",
    "Chinese": "z",
}

print(f"Loading model: {MODEL_ID}")
model = load_model(MODEL_ID)
print("Model loaded. Starting server...")

app = FastAPI()


class TTSRequest(BaseModel):
    text: str
    voice: str = "jf_alpha"
    language: str = "Japanese"
    speed: float = 1.0


def split_japanese_text(text, max_chars=100):
    """100文字程度で句読点で区切る"""
    chunks = []
    current = ""
    
    # 句読点で分割
    sentences = re.split(r'([。、！？\n])', text)
    
    for i in range(0, len(sentences), 2):
        sentence = sentences[i]
        delimiter = sentences[i+1] if i+1 < len(sentences) else ""
        
        if len(current) + len(sentence) + len(delimiter) > max_chars and current:
            chunks.append(current.strip())
            current = sentence + delimiter
        else:
            current += sentence + delimiter
    
    if current.strip():
        chunks.append(current.strip())
    
    return chunks if chunks else [text]


@app.post("/tts")
def generate_tts(req: TTSRequest):
    start = time.perf_counter()
    
    lang_code = LANG_CODES.get(req.language, "j")
    
    # 長文の場合は分割
    if len(req.text) > 120:
        chunks = split_japanese_text(req.text, max_chars=100)
        all_audio = []
        
        for chunk in chunks:
            results = list(model.generate(
                text=chunk,
                voice=req.voice,
                lang_code=lang_code,
                speed=req.speed,
                split_pattern="",
            ))
            all_audio.append(results[0].audio)
        
        audio = np.concatenate(all_audio)
    else:
        results = list(model.generate(
            text=req.text,
            voice=req.voice,
            lang_code=lang_code,
            speed=req.speed,
            split_pattern="",
        ))
        audio = results[0].audio
    
    elapsed = time.perf_counter() - start
    duration = len(audio) / SAMPLE_RATE

    buf = io.BytesIO()
    sf.write(buf, np.array(audio), SAMPLE_RATE, format="WAV")
    buf.seek(0)

    return Response(
        content=buf.read(),
        media_type="audio/wav",
        headers={
            "X-Generation-Time": f"{elapsed:.2f}",
            "X-Audio-Duration": f"{duration:.2f}",
            "X-RTF": f"{elapsed / duration:.3f}",
        },
    )


@app.post("/tts/stream-play")
def stream_play_tts(req: TTSRequest):
    """Generate and play audio on the server using afplay (supports media controls)."""
    start = time.perf_counter()
    
    lang_code = LANG_CODES.get(req.language, "j")
    
    # 長文の場合は分割
    if len(req.text) > 120:
        chunks = split_japanese_text(req.text, max_chars=100)
        chunk_count = len(chunks)
        all_chunks = []
        
        for chunk_text in chunks:
            results = list(model.generate(
                text=chunk_text,
                voice=req.voice,
                lang_code=lang_code,
                speed=req.speed,
                split_pattern="",
            ))
            audio = np.array(results[0].audio, dtype=np.float32)
            all_chunks.append(audio)
        
        combined = np.concatenate(all_chunks)
    else:
        results = list(model.generate(
            text=req.text,
            voice=req.voice,
            lang_code=lang_code,
            speed=req.speed,
            split_pattern="",
        ))
        combined = np.array(results[0].audio, dtype=np.float32)
        chunk_count = 1

    # 一時ファイルに保存してmpvで再生（メディアコントロール対応）
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
        tmp_path = tmp_file.name
        sf.write(tmp_path, combined, SAMPLE_RATE)
    
    try:
        # mpvで再生（AirPodsやキーボードのメディアキーで制御可能）
        subprocess.run(["mpv", "--no-video", "--really-quiet", tmp_path], check=True)
    finally:
        # 再生後に一時ファイル削除
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    elapsed = time.perf_counter() - start
    duration = len(combined) / SAMPLE_RATE

    return JSONResponse({
        "status": "ok",
        "chunks": chunk_count,
        "audio_duration": round(duration, 2),
        "generation_time": round(elapsed, 2),
        "rtf": round(elapsed / duration, 3),
    })


@app.get("/voices")
def get_voices():
    return {"voices": VOICES}


@app.get("/", response_class=HTMLResponse)
def index():
    return HTML_PAGE


HTML_PAGE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Kokoro TTS Server</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f5f5f7; color: #1d1d1f; padding: 2rem; }
  .container { max-width: 640px; margin: 0 auto; }
  h1 { font-size: 1.5rem; margin-bottom: 1.5rem; }
  label { display: block; font-size: 0.85rem; font-weight: 600; margin-bottom: 0.3rem; color: #666; }
  textarea, select {
    width: 100%; padding: 0.6rem; border: 1px solid #ccc; border-radius: 8px;
    font-size: 1rem; font-family: inherit; margin-bottom: 1rem; background: #fff;
  }
  textarea { height: 120px; resize: vertical; }
  .row { display: flex; gap: 1rem; }
  .row > div { flex: 1; }
  button {
    width: 100%; padding: 0.8rem; font-size: 1rem; font-weight: 600;
    background: #007aff; color: #fff; border: none; border-radius: 8px; cursor: pointer;
    margin-bottom: 0.5rem;
  }
  button:hover { background: #0066d6; }
  button:disabled { background: #999; cursor: not-allowed; }
  .result { margin-top: 1.5rem; padding: 1rem; background: #fff; border-radius: 8px; display: none; }
  .result audio { width: 100%; margin: 0.5rem 0; }
  .stats { font-size: 0.85rem; color: #666; }
  .loading { display: none; text-align: center; margin-top: 1rem; color: #666; }
  .loading.active { display: block; }
  a { color: #007aff; }
  .info { background: #e8f4ff; padding: 1rem; border-radius: 8px; margin-bottom: 1rem; font-size: 0.85rem; color: #333; }
</style>
</head>
<body>
<div class="container">
  <h1>🎙️ Kokoro TTS Server</h1>

  <div class="info">
    <strong>Kokoro-82M</strong> - 超高速・多言語TTS (RTF ~0.1)<br>
    長文対応: 100文字ごとに自動分割
  </div>

  <label for="text">テキスト</label>
  <textarea id="text" placeholder="読み上げたいテキストを入力...">こんにちは。これはKokoroの音声合成システムのテストです。</textarea>

  <div class="row">
    <div>
      <label for="language">言語</label>
      <select id="language" onchange="updateVoices()">
        <option value="Japanese">Japanese</option>
        <option value="American English">American English</option>
        <option value="British English">British English</option>
        <option value="Chinese">Chinese</option>
      </select>
    </div>
    <div>
      <label for="voice">音声</label>
      <select id="voice"></select>
    </div>
  </div>

  <label for="speed">速度 (<span id="speed-value">1.0</span>x)</label>
  <input type="range" id="speed" min="0.5" max="2.0" step="0.1" value="1.0" oninput="document.getElementById('speed-value').textContent = this.value" style="width: 100%; margin-bottom: 1rem;">

  <button id="btn" onclick="generate()">生成</button>
  <button id="btn-play" onclick="streamPlay()" style="background: #34c759;">サーバーで再生</button>

  <div class="loading" id="loading">生成中...</div>

  <div class="result" id="result">
    <audio id="audio" controls autoplay></audio>
    <div class="stats" id="stats"></div>
    <a id="download" href="#" download="kokoro_output.wav">WAVをダウンロード</a>
  </div>
</div>

<script>
const VOICES = {
  "Japanese": ["jf_alpha", "jm_kumo"],
  "American English": ["af_heart", "af_bella", "af_nova", "af_sky", "am_adam", "am_echo"],
  "British English": ["bf_alice", "bf_emma", "bm_daniel", "bm_george"],
  "Chinese": ["zf_xiaobei", "zm_yunxi"]
};

function updateVoices() {
  const language = document.getElementById('language').value;
  const voiceSel = document.getElementById('voice');
  voiceSel.innerHTML = '';
  
  VOICES[language].forEach(v => {
    const opt = document.createElement('option');
    opt.value = v;
    opt.textContent = v;
    voiceSel.appendChild(opt);
  });
}

async function generate() {
  const btn = document.getElementById('btn');
  const loading = document.getElementById('loading');
  const result = document.getElementById('result');

  btn.disabled = true;
  loading.classList.add('active');
  result.style.display = 'none';

  const body = {
    text: document.getElementById('text').value,
    voice: document.getElementById('voice').value,
    language: document.getElementById('language').value,
    speed: parseFloat(document.getElementById('speed').value),
  };

  try {
    const res = await fetch('/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);

    const genTime = res.headers.get('X-Generation-Time');
    const audioDur = res.headers.get('X-Audio-Duration');
    const rtf = res.headers.get('X-RTF');

    document.getElementById('audio').src = url;
    document.getElementById('download').href = url;
    document.getElementById('stats').textContent =
      `生成時間: ${genTime}s / 音声長: ${audioDur}s / RTF: ${rtf}`;
    result.style.display = 'block';
  } catch (e) {
    alert('エラー: ' + e.message);
  } finally {
    btn.disabled = false;
    loading.classList.remove('active');
  }
}

async function streamPlay() {
  const btn = document.getElementById('btn-play');
  const loading = document.getElementById('loading');

  btn.disabled = true;
  loading.classList.add('active');

  const body = {
    text: document.getElementById('text').value,
    voice: document.getElementById('voice').value,
    language: document.getElementById('language').value,
    speed: parseFloat(document.getElementById('speed').value),
  };

  try {
    const res = await fetch('/tts/stream-play', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    const data = await res.json();
    alert(`再生完了！\\n生成: ${data.generation_time}s / 長さ: ${data.audio_duration}s / RTF: ${data.rtf}`);
  } catch (e) {
    alert('エラー: ' + e.message);
  } finally {
    btn.disabled = false;
    loading.classList.remove('active');
  }
}

// Initialize
updateVoices();
</script>
</body>
</html>"""

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
