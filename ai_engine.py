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
    """
    Loads the Whisper model ONCE and keeps it in memory.
    Forces download to /tmp to avoid "Read-only file system" errors.
    """
    try:
        import whisper
        logger.info("[CACHE] Downloading/Loading Whisper 'tiny' model to /tmp...")
        
        # CRITICAL FIX 1: Force CPU to prevent Cloud Run crashes
        device = "cpu"
        
        # CRITICAL FIX 2: download_root="/tmp" for Read-Only filesystems
        return whisper.load_model("tiny", device=device, download_root="/tmp")
    except Exception as e:
        logger.error(f"[CACHE] Failed to load model: {e}")
        return None

# --- TRANSCRIPTION ENGINE ---
def load_and_transcribe(audio_path_or_file):
    try:
        logger.info("[TRANSCRIBE] Step 1: Garbage collection")
        gc.collect()
        
        # CRITICAL FIX: Explicit check for FFmpeg dependency
        if not shutil.which("ffmpeg"):
             return False, "Error: 'ffmpeg' command not found. Please ensure it is installed in packages.txt."

        logger.info("[TRANSCRIBE] Step 2: Fetching Cached Model")
        model = load_whisper_model_cached()
        
        if not model:
            return False, "Error: AI Model failed to initialize. Check logs."

        logger.info("[TRANSCRIBE] Step 3: Transcribing...")
        
        # fp16=False is crucial for CPU stability
        # language='en' helps prevent silence hallucination
        result = model.transcribe(
            audio_path_or_file,
            fp16=False,
            language='en' 
        )
        
        text = result.get("text", "").strip()
        logger.info(f"[TRANSCRIBE] Finished. Text length: {len(text)}")
        
        if not text:
            # Return a visible error string if silence is detected, 
            # so the UI knows to warn the user instead of showing blank.
            return True, "[Error: No speech detected. Please speak closer to the microphone.]" 
        
        return True, text

    except Exception as e:
        logger.error(f"[TRANSCRIBE] ERROR: {e}")
        return False, f"Error: {str(e)}"
        
    finally:
        gc.collect()

def transcribe_audio(audio_input):
    """
    Main entry point. Handles Streamlit Audio objects.
    """
    logger.info("="*60)
    logger.info("[TRANSCRIBE REQUEST]")
    
    tmp_path = None
    try:
        # Handle file upload vs filepath
        if isinstance(audio_input, str):
            success, result = load_and_transcribe(audio_input)
            return result if success else f"Error: {result}"
        
        else:
            # Streamlit UploadedFile object
            suffix = ".wav"
            if hasattr(audio_input, "name") and audio_input.name:
                if audio_input.name.endswith(".mp3"): suffix = ".mp3"
                elif audio_input.name.endswith(".m4a"): suffix = ".m4a"
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, mode='wb') as tmp:
                tmp.write(audio_input.getvalue())
                tmp_path = tmp.name
            
            # Check for empty files
            if os.path.getsize(tmp_path) < 100:
                return "Error: Audio file is empty or too small."
            
            success, result = load_and_transcribe(tmp_path)
            
            # Standardize error return
            return result if success else f"Error: {result}"

    except Exception as e:
        logger.error(f"[TRANSCRIBE AUDIO] ERROR: {e}")
        return f"Error: File processing failed - {str(e)}"
    
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except: pass

# --- TEXT REFINEMENT ENGINE (Restored) ---
def refine_text(text, style="Professional"):
    """
    Uses OpenAI API to rewrite text styles (Grammar, Friendly, etc).
    Gracefully degrades if API key is missing.
    """
    try:
        # Lazy import to prevent startup crash if library missing
        import openai
        
        api_key = secrets_manager.get_secret("openai.api_key") or secrets_manager.get_secret("OPENAI_API_KEY")
        if not api_key: 
            logger.warning("[REFINE] No OpenAI API Key found. Returning original text.")
            return text 

        client = openai.OpenAI(api_key=api_key)
        
        prompt_map = {
            "Grammar": "Fix grammar and spelling only. Keep tone.",
            "Professional": "Rewrite to be formal and professional. Keep meaning.",
            "Friendly": "Rewrite to be warm and friendly. Keep meaning.",
            "Concise": "Summarize and shorten. Keep key points."
        }
        
        sys_prompt = prompt_map.get(style, "Rewrite this text.")

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"{sys_prompt} Do not add conversational filler."},
                {"role": "user", "content": text}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
        
    except ImportError:
        logger.error("[REFINE] openai library not installed.")
        return text
    except Exception as e:
        logger.error(f"[REFINE] Error: {e}")
        return text