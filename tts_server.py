"""Qwen3-TTS HTTP Server with Web UI"""

import io
import time

import numpy as np
import soundfile as sf
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response
from mlx_audio.tts.utils import load_model
from pydantic import BaseModel

MODEL_ID = "mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-bf16"
SAMPLE_RATE = 24000

print(f"Loading model: {MODEL_ID}")
model = load_model(MODEL_ID)
speakers = model.get_supported_speakers()
print(f"Available speakers: {speakers}")
print("Model loaded. Starting server...")

app = FastAPI()


class TTSRequest(BaseModel):
    text: str
    speaker: str = "Aiden"
    instruct: str = "落ち着いた声で、はっきりとした発音。"
    language: str = "Japanese"


@app.post("/tts")
def generate_tts(req: TTSRequest):
    start = time.perf_counter()
    results = list(model.generate_custom_voice(
        text=req.text,
        speaker=req.speaker,
        language=req.language,
        instruct=req.instruct,
    ))
    elapsed = time.perf_counter() - start

    audio = results[0].audio
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


@app.get("/speakers")
def get_speakers():
    return {"speakers": speakers}


@app.get("/", response_class=HTMLResponse)
def index():
    return HTML_PAGE


HTML_PAGE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Qwen3-TTS Server</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f5f5f7; color: #1d1d1f; padding: 2rem; }
  .container { max-width: 640px; margin: 0 auto; }
  h1 { font-size: 1.5rem; margin-bottom: 1.5rem; }
  label { display: block; font-size: 0.85rem; font-weight: 600; margin-bottom: 0.3rem; color: #666; }
  textarea, select, input[type="text"] {
    width: 100%; padding: 0.6rem; border: 1px solid #ccc; border-radius: 8px;
    font-size: 1rem; font-family: inherit; margin-bottom: 1rem; background: #fff;
  }
  textarea { height: 120px; resize: vertical; }
  .row { display: flex; gap: 1rem; }
  .row > div { flex: 1; }
  button {
    width: 100%; padding: 0.8rem; font-size: 1rem; font-weight: 600;
    background: #007aff; color: #fff; border: none; border-radius: 8px; cursor: pointer;
  }
  button:hover { background: #0066d6; }
  button:disabled { background: #999; cursor: not-allowed; }
  .result { margin-top: 1.5rem; padding: 1rem; background: #fff; border-radius: 8px; display: none; }
  .result audio { width: 100%; margin: 0.5rem 0; }
  .stats { font-size: 0.85rem; color: #666; }
  .loading { display: none; text-align: center; margin-top: 1rem; color: #666; }
  .loading.active { display: block; }
  a { color: #007aff; }
</style>
</head>
<body>
<div class="container">
  <h1>Qwen3-TTS Server</h1>

  <label for="text">テキスト</label>
  <textarea id="text" placeholder="読み上げたいテキストを入力...">人工知能は私たちの生活を大きく変えています。</textarea>

  <div class="row">
    <div>
      <label for="speaker">スピーカー</label>
      <select id="speaker"></select>
    </div>
    <div>
      <label for="language">言語</label>
      <select id="language">
        <option value="Japanese">Japanese</option>
        <option value="Chinese">Chinese</option>
        <option value="English">English</option>
      </select>
    </div>
  </div>

  <label for="instruct">指示（感情・話し方）</label>
  <input type="text" id="instruct" value="落ち着いた声で、はっきりとした発音。">

  <button id="btn" onclick="generate()">生成</button>

  <div class="loading" id="loading">生成中...</div>

  <div class="result" id="result">
    <audio id="audio" controls autoplay></audio>
    <div class="stats" id="stats"></div>
    <a id="download" href="#" download="tts_output.wav">WAVをダウンロード</a>
  </div>
</div>

<script>
async function loadSpeakers() {
  const res = await fetch('/speakers');
  const data = await res.json();
  const sel = document.getElementById('speaker');
  data.speakers.forEach(s => {
    const opt = document.createElement('option');
    opt.value = s;
    opt.textContent = s;
    if (s === 'Aiden') opt.selected = true;
    sel.appendChild(opt);
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
    speaker: document.getElementById('speaker').value,
    instruct: document.getElementById('instruct').value,
    language: document.getElementById('language').value,
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

loadSpeakers();
</script>
</body>
</html>"""

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
