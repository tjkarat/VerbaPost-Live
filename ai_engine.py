import os
import tempfile
import shutil
import contextlib
import logging
import streamlit as st
from openai import OpenAI

# Try to import whisper (Local AI)
try: 
    import whisper
except ImportError:
    whisper = None

# Try to import secrets
try: import secrets_manager
except ImportError: secrets_manager = None

# --- CONFIGURATION ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 1. LOAD LOCAL WHISPER MODEL (Cached) ---
@st.cache_resource
def load_whisper_model():
    """
    Loads the local Whisper model once and caches it in memory.
    """
    if not whisper:
        logger.error("Whisper library not installed.")
        return None
        
    logger.info("🧠 Loading Whisper AI model (base)...")
    try:
        return whisper.load_model("base")
    except Exception as e:
        logger.error(f"Failed to load Whisper: {e}")
        return None

def get_openai_client():
    """Safely creates OpenAI Client for text refinement only"""
    if not secrets_manager: return None
    key = secrets_manager.get_secret("openai.api_key") or secrets_manager.get_secret("OPENAI_API_KEY")
    if key:
        return OpenAI(api_key=key)
    return None

# --- 2. SAFE TEMP FILE CONTEXT MANAGER ---
@contextlib.contextmanager
def safe_temp_file(file_obj, suffix=".wav"):
    """
    Context manager for safe temp file handling.
    Checks disk space and guarantees cleanup.
    """
    try:
        if shutil.disk_usage('/tmp').free < 50 * 1024 * 1024:
            logger.error("Insufficient disk space.")
            raise RuntimeError("Server storage full.")
    except Exception:
        pass 

    tmp_path = None
    try:
        # Create temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=tempfile.gettempdir()) as tmp:
            file_obj.seek(0)
            data = file_obj.getvalue()
            if len(data) == 0:
                raise ValueError("Audio file is empty.")
            tmp.write(data)
            tmp_path = tmp.name
        
        yield tmp_path

    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError as e:
                logger.error(f"Cleanup failed: {e}")

# --- 3. LOCAL TRANSCRIPTION ---
def transcribe_audio(file_obj):
    """
    Transcribes audio using the LOCAL Whisper model.
    """
    if not whisper:
        return "[Error: Whisper library missing on server.]"

    # Determine suffix
    suffix = f".{file_obj.name.split('.')[-1]}" if hasattr(file_obj, 'name') else '.wav'
    
    try:
        model = load_whisper_model()
        if not model:
            return "[Error: Could not load Whisper model.]"
        
        with safe_temp_file(file_obj, suffix) as tmp_path:
            logger.info(f"🎧 Transcribing {tmp_path} locally...")
            
            # Local Inference
            result = model.transcribe(tmp_path)
            text = result["text"]
            
            if not text or not text.strip():
                return "[No speech detected. Please try recording again.]"
            
            logger.info("✅ Transcription successful.")
            return text

    except Exception as e:
        logger.error(f"Local Transcription failed: {e}", exc_info=True)
        return f"[Error processing audio: {str(e)}]"

# --- 4. TEXT REFINEMENT (OpenAI GPT) ---
def refine_text(text, style="Professional"):
    """
    Refines text using GPT-3.5/4.
    """
    if not text or len(text.strip()) < 5:
        return text

    client = get_openai_client()
    if not client:
        return text 

    prompts = {
        "Grammar": "Correct the grammar and spelling.",
        "Professional": "Rewrite to be professional, polite, and formal.",
        "Friendly": "Rewrite to be warm and personal.",
        "Concise": "Rewrite to be concise and to the point."
    }

    system_instruction = prompts.get(style, prompts["Professional"])

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"You are an expert editor. {system_instruction}"},
                {"role": "user", "content": f"Text to rewrite:\n{text}"}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"Refinement Failed: {e}")
        return text