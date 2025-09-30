#!/usr/bin/env python3
"""
Local STT Server with faster-whisper
Provides offline speech-to-text for the Live2D chatbot
"""

from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import tempfile
import subprocess
import os
import uuid
import contextlib
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Local STT Server", version="1.0.0")

# Enable CORS for all origins (adjust for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Whisper model
try:
    from faster_whisper import WhisperModel
    
    # Choose a model:
    #  - "tiny" (~39MB) fastest but less accurate
    #  - "base" (~140MB) good balance, recommended for start
    #  - "small" (~460MB) better accuracy
    #  - "medium" (~1.5GB) even better
    #  - "large-v3" (~3GB) best accuracy
    MODEL_SIZE = os.environ.get("WHISPER_MODEL", "base")
    
    logger.info(f"🎧 Loading Whisper model: {MODEL_SIZE}")
    model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")  # fully local
    logger.info(f"✅ Whisper model loaded: {MODEL_SIZE}")
    
except ImportError as e:
    logger.error("❌ faster-whisper not installed. Please run: pip install faster-whisper")
    model = None
except Exception as e:
    logger.error(f"❌ Error loading Whisper model: {e}")
    model = None

# Language mapping for Whisper
LANG_MAP = {
    "zh-HK": "zh",      # Cantonese -> Chinese (Whisper handles both)
    "zh-CN": "zh",      # Mandarin -> Chinese
    "en-US": "en",      # English
    "en": "en",         # English fallback
    "zh": "zh"          # Chinese fallback
}

def convert_to_wav16k(input_file):
    """Convert any audio file to 16kHz WAV using ffmpeg"""
    output_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
    
    try:
        # Convert with ffmpeg to 16kHz mono WAV
        cmd = [
            "ffmpeg", "-y", "-i", input_file,
            "-ac", "1",          # mono
            "-ar", "16000",      # 16kHz sample rate
            "-acodec", "pcm_s16le",  # 16-bit PCM
            output_file
        ]
        
        result = subprocess.run(
            cmd, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL, 
            check=True
        )
        
        return output_file
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ FFmpeg conversion failed: {e}")
        raise Exception("Audio conversion failed. Make sure ffmpeg is installed.")
    except FileNotFoundError:
        logger.error("❌ FFmpeg not found. Please install ffmpeg.")
        raise Exception("FFmpeg not found. Please install ffmpeg and ensure it's in PATH.")

@app.get("/health")
def health_check():
    """Health check endpoint"""
    whisper_status = "available" if model else "not_available"
    
    return JSONResponse({
        "status": "healthy",
        "whisper_model": MODEL_SIZE if model else None,
        "whisper_status": whisper_status,
        "message": f"Local STT Server running with {MODEL_SIZE} model" if model else "Whisper model not loaded"
    })

@app.post("/stt/stream")
async def transcribe_audio_stream(audio: UploadFile, lang: str = Form("en-US")):
    """
    Transcribe audio chunk from the browser
    Accepts: WebM, MP3, WAV, M4A, etc.
    Returns: JSON with transcribed text
    """
    if not model:
        return JSONResponse(
            {"error": "Whisper model not available"}, 
            status_code=503
        )
    
    # Get file extension from filename or default to webm
    file_extension = ".webm"
    if audio.filename:
        _, ext = os.path.splitext(audio.filename)
        if ext:
            file_extension = ext
    
    # Save uploaded audio chunk
    temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=file_extension).name
    
    try:
        # Save uploaded data
        audio_data = await audio.read()
        if not audio_data:
            return JSONResponse({"text": ""})
            
        with open(temp_input, "wb") as f:
            f.write(audio_data)
        
        # Convert to WAV
        temp_wav = convert_to_wav16k(temp_input)
        
        # Map language
        whisper_lang = LANG_MAP.get(lang, "en")
        
        # Transcribe with Whisper
        logger.info(f"🎧 Transcribing {len(audio_data)} bytes, language: {whisper_lang}")
        
        segments, info = model.transcribe(
            temp_wav,
            language=whisper_lang,
            vad_filter=True,  # Voice Activity Detection
            vad_parameters=dict(min_silence_duration_ms=200),
            beam_size=1,      # Fast inference
            best_of=1,        # Fast inference  
            patience=0,       # Fast inference
            temperature=0     # Deterministic
        )
        
        # Extract text from segments
        text = "".join(segment.text for segment in segments).strip()
        
        logger.info(f"🎧 Transcribed: '{text[:50]}{'...' if len(text) > 50 else ''}'")
        
        return JSONResponse({"text": text})
        
    except Exception as e:
        logger.error(f"❌ Transcription error: {e}")
        return JSONResponse({"text": "", "error": str(e)})
        
    finally:
        # Cleanup temporary files
        with contextlib.suppress(Exception):
            if 'temp_input' in locals():
                os.remove(temp_input)
        with contextlib.suppress(Exception):
            if 'temp_wav' in locals():
                os.remove(temp_wav)

@app.post("/stt/file")
async def transcribe_audio_file(audio: UploadFile, lang: str = Form("en-US")):
    """
    Transcribe a complete audio file (for testing)
    """
    if not model:
        return JSONResponse(
            {"error": "Whisper model not available"}, 
            status_code=503
        )
    
    # Similar to stream but with full file processing
    # ... (implementation similar to stream endpoint)
    return await transcribe_audio_stream(audio, lang)

if __name__ == "__main__":
    import uvicorn
    
    print("🎧 Starting Local STT Server...")
    print(f"🎯 Whisper Model: {MODEL_SIZE}")
    print(f"🌐 Server will run on: http://localhost:8790")
    print("📝 Install dependencies:")
    print("   pip install fastapi uvicorn faster-whisper python-multipart")
    print("   # Also need ffmpeg installed and in PATH")
    print("\n🚀 Starting server...")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8790, 
        log_level="info"
    )
