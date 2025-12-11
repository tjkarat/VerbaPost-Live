import streamlit as st
import logging
import os
import tempfile
import secrets_manager
import subprocess
import gc
import shutil

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CACHED MODEL LOADER (The Critical Fix) ---
@st.cache_resource(show_spinner=False)
def load_whisper_model_cached():
    try:
        import whisper
        # FIX: Force download to /tmp to prevent "Read-only file system" errors
        logger.info("[CACHE] Loading Whisper 'tiny' model to /tmp...")
        return whisper.load_model("tiny", download_root="/tmp")
    except Exception as e:
        logger.error(f"[CACHE] Failed to load model: {e}")
        return None

def transcribe_audio(audio_input):
    """
    Robust transcription that handles Streamlit Audio objects.
    """
    tmp_path = None
    try:
        # 1. FFmpeg Check
        if not shutil.which("ffmpeg"):
            return "Error: FFmpeg is missing. Please check packages.txt."

        # 2. Handle Input
        suffix = ".wav"
        if hasattr(audio_input, "name") and audio_input.name:
            if audio_input.name.endswith(".mp3"): suffix = ".mp3"
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, mode='wb') as tmp:
            tmp.write(audio_input.getvalue())
            tmp_path = tmp.name
        
        # 3. Load Model & Transcribe
        model = load_whisper_model_cached()
        if not model:
            return "Error: AI Model failed to load."
            
        result = model.transcribe(tmp_path, fp16=False)
        text = result.get("text", "").strip()
        
        if not text:
            return "Error: Audio processed, but no speech detected."
            
        return text

    except Exception as e:
        return f"Error: {str(e)}"
    
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except: pass

# Keep your existing refine_text function if you have one
def refine_text(text, style="Professional"):
    try:
        import openai
        api_key = secrets_manager.get_secret("openai.api_key")
        if not api_key: return text 
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": f"Rewrite to be {style}."},{"role": "user", "content": text}]
        )
        return response.choices[0].message.content.strip()
    except: return text