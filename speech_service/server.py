"""
speech_service/server.py

Lightweight FastAPI service for:
  POST /transcribe  — audio file → text (Whisper, NPU-accelerated)
  POST /synthesize  — text → audio (Edge TTS)

Run with:
    cd speech_service
    uvicorn server:app --port 8002 --reload
"""

import io
import tempfile
import os
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from loguru import logger

app = FastAPI(title="NeuroLens Speech Service")

# ── Whisper STT ───────────────────────────────────────────────────────────────
# Using faster-whisper which supports CTranslate2 backend
# Export steps for NPU:
#   1. ct2-opus-mt-en-LANG-converter --model whisper-small --output_dir ./models/whisper_ct2
#   2. Use WhisperModel with device="cuda" or device="cpu" + compute_type="int8"
# For NPU on Ryzen AI: set device="directml" when onnxruntime-directml is installed

_whisper_model = None

def get_whisper():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        # "small" model: good accuracy, fast enough on NPU
        # For better accuracy: "medium" (slower, ~2x)
        # For max speed: "tiny" (less accurate)
        _whisper_model = WhisperModel(
            "small",
            device="cpu",          # Change to "cuda" or "directml" when available
            compute_type="int8",   # int8 = ~2x faster, minimal accuracy loss
            download_root="./models/whisper",
        )
        logger.success("Whisper model loaded")
    return _whisper_model


class TranscribeResponse(BaseModel):
    text: str
    language: str
    duration_s: float
    segments: list[dict]


@app.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(audio: UploadFile = File(...)):
    """
    Transcribe audio to text using Whisper.
    Accepts: webm, mp3, wav, m4a, ogg
    Returns: transcribed text + detected language
    """
    allowed = {
        "audio/webm", "audio/mpeg", "audio/wav",
        "audio/mp4", "audio/ogg", "audio/x-wav",
    }
    if audio.content_type not in allowed:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported audio format: {audio.content_type}"
        )

    content = await audio.read()

    # Write to temp file (faster-whisper needs a file path)
    suffix = Path(audio.filename or "audio.webm").suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        model = get_whisper()
        segments_gen, info = model.transcribe(
            tmp_path,
            beam_size=5,
            language=None,          # Auto-detect: supports Hindi + English
            task="transcribe",
            vad_filter=True,        # Filter silence (faster)
            vad_parameters={"min_silence_duration_ms": 500},
        )

        segments = []
        full_text_parts = []
        for seg in segments_gen:
            segments.append({
                "start": round(seg.start, 2),
                "end": round(seg.end, 2),
                "text": seg.text.strip(),
            })
            full_text_parts.append(seg.text.strip())

        full_text = " ".join(full_text_parts).strip()
        logger.info(f"Transcribed {info.duration:.1f}s → '{full_text[:80]}...'")

        return TranscribeResponse(
            text=full_text,
            language=info.language,
            duration_s=round(info.duration, 2),
            segments=segments,
        )
    finally:
        os.unlink(tmp_path)


# ── Edge TTS ──────────────────────────────────────────────────────────────────

class SynthesizeRequest(BaseModel):
    text: str
    voice: str = "en-IN-NeerjaNeural"   # Indian English — great for demo
    rate: str = "+0%"
    pitch: str = "+0Hz"


@app.post("/synthesize")
async def synthesize(request: SynthesizeRequest):
    """
    Convert text to speech using Edge TTS (Microsoft, free, no API key).
    Returns: audio/mpeg stream

    Good voices for demos:
      en-IN-NeerjaNeural   — Indian English female
      en-IN-PrabhatNeural  — Indian English male
      en-US-AriaNeural     — US English female
      hi-IN-SwaraNeural    — Hindi female
    """
    try:
        import edge_tts
        communicate = edge_tts.Communicate(
            text=request.text,
            voice=request.voice,
            rate=request.rate,
            pitch=request.pitch,
        )
        audio_buffer = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_buffer.write(chunk["data"])
        audio_buffer.seek(0)

        return StreamingResponse(
            audio_buffer,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "attachment; filename=speech.mp3"},
        )
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="edge-tts not installed. Run: pip install edge-tts"
        )


@app.get("/voices")
async def list_voices():
    """List available TTS voices — useful for the frontend voice selector."""
    try:
        import edge_tts
        voices = await edge_tts.list_voices()
        # Filter to English + Hindi voices
        filtered = [
            v for v in voices
            if v["Locale"].startswith(("en-IN", "en-US", "hi-IN"))
        ]
        return {"voices": filtered}
    except ImportError:
        return {"voices": [], "error": "edge-tts not installed"}


@app.get("/health")
def health():
    return {"status": "ok", "service": "NeuroLens Speech Service"}
