import streamlit as st
import logging
import os
import tempfile
import secrets_manager
import subprocess
import gc
import traceback
import sys
import shutil

# Configure Logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# --- CACHED MODEL LOADER ---
@st.cache_resource(show_spinner=False)
def load_whisper_model_cached():
    """Loads the model ONCE and keeps it in memory."""
    try:
        import whisper
        logger.info("[CACHE] Loading Whisper 'tiny' model...")
        return whisper.load_model("tiny")
    except Exception as e:
        logger.error(f"[CACHE] Failed to load model: {e}")
        return None

def load_and_transcribe(audio_path_or_file):
    try:
        logger.info("[TRANSCRIBE] Step 1: GC")
        gc.collect()
        
        # Check FFmpeg
        if not shutil.which("ffmpeg"):
             return False, "Error: 'ffmpeg' command not found."

        logger.info("[TRANSCRIBE] Step 2: Fetch Model")
        model = load_whisper_model_cached()
        if not model: return False, "Error: Failed to load AI model."

        logger.info("[TRANSCRIBE] Step 3: Transcribing...")
        result = model.transcribe(audio_path_or_file, fp16=False)
        
        text = result.get("text", "").strip()
        
        # FIX: Explicit feedback for silent audio
        if not text:
            return True, "[Audio processed but no speech detected. Please try recording again.]"
        
        return True, text

    except Exception as e:
        logger.error(f"[TRANSCRIBE] ERROR: {e}")
        return False, f"Error: {str(e)}"
    finally:
        gc.collect()

def transcribe_audio(audio_input):
    logger.info("="*60)
    logger.info("[TRANSCRIBE REQUEST]")
    
    tmp_path = None
    try:
        suffix = ".wav"
        if hasattr(audio_input, "name") and audio_input.name:
            if audio_input.name.endswith(".mp3"): suffix = ".mp3"
            elif audio_input.name.endswith(".m4a"): suffix = ".m4a"
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, mode='wb') as tmp:
            tmp.write(audio_input.getvalue())
            tmp_path = tmp.name
        
        success, result = load_and_transcribe(tmp_path)
        return result if success else f"Failed: {result}"

    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except: pass

def refine_text(text, style="Professional"):
    try:
        import openai
        api_key = secrets_manager.get_secret("openai.api_key") or secrets_manager.get_secret("OPENAI_API_KEY")
        if not api_key: return text 
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"Rewrite to be {style}. Preserve meaning."},
                {"role": "user", "content": text}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except: return text