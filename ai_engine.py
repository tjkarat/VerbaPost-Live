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

# Configure Logging - CRITICAL: Use stdout for Streamlit visibility
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# --- NEW: CACHED MODEL LOADER ---
@st.cache_resource(show_spinner=False)
def load_whisper_model_cached():
    """
    Loads the Whisper model ONCE and keeps it in memory.
    This prevents the app from crashing due to repeated loading/unloading.
    """
    logger.info("[CACHE] Loading Whisper 'tiny' model into memory...")
    import whisper
    return whisper.load_model("tiny")

# --- 1. ROBUST TRANSCRIPTION ENGINE ---
def load_and_transcribe(audio_path_or_file):
    """
    Self-contained transcription function.
    Uses cached model for stability.
    """
    # model = None  <-- REMOVED: We don't manage model variable manually anymore
    # whisper = None
    
    try:
        logger.info("[TRANSCRIBE] Step 1: Garbage collection")
        gc.collect()
        
        # Check FFmpeg explicitly
        if not shutil.which("ffmpeg"):
             logger.error("FFmpeg not found in system path")
             return False, "Error: 'ffmpeg' command not found. Please ensure it is installed."

        logger.info("[TRANSCRIBE] Step 2: Fetching Cached Model")
        try:
            # USE THE CACHED LOADER
            model = load_whisper_model_cached()
            logger.info("[TRANSCRIBE] Model retrieved from cache")
        except Exception as model_err:
            logger.error(f"[TRANSCRIBE] Model load FAILED: {model_err}")
            return False, f"Error: Failed to load Whisper model - {str(model_err)}"
        
        # Transcribe
        logger.info(f"[TRANSCRIBE] Step 3: Transcribing audio file: {audio_path_or_file}")
        try:
            # fp16=False is crucial for CPU stability
            result = model.transcribe(
                audio_path_or_file,
                fp16=False,
                language=None, 
                task='transcribe'
            )
            logger.info("[TRANSCRIBE] Transcription completed")
        except Exception as trans_err:
            logger.error(f"[TRANSCRIBE] Transcription FAILED: {trans_err}")
            
            error_str = str(trans_err).lower()
            if "ffmpeg" in error_str:
                return False, "Error: FFmpeg error - audio format may be unsupported"
            elif "memory" in error_str:
                return False, "Error: Out of memory - try a shorter audio file"
            else:
                return False, f"Error: Transcription failed - {str(trans_err)}"
        
        text = result.get("text", "").strip()
        
        if not text:
            return False, "Error: No speech detected in audio (empty transcription)"
        
        return True, text

    except Exception as e:
        logger.error(f"[TRANSCRIBE] UNEXPECTED ERROR: {str(e)}")
        return False, f"Error: Unexpected transcription failure - {str(e)}"
        
    finally:
        # AGGRESSIVE CLEANUP (Modified)
        # We do NOT delete the model anymore because it is cached.
        # We ONLY clean up general garbage.
        gc.collect()
        logger.info("[TRANSCRIBE] Memory cleanup complete (Model preserved in cache)")


def transcribe_audio(audio_input):
    """
    Main entry point called by UI. Handles file management.
    """
    logger.info("="*60)
    logger.info("[TRANSCRIBE AUDIO] NEW TRANSCRIPTION REQUEST")
    
    # 1. FFmpeg Check
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except:
        return "Error: FFmpeg not installed. Add 'ffmpeg' to packages.txt"

    tmp_path = None
    try:
        # Handle file upload vs filepath
        if isinstance(audio_input, str):
            success, result = load_and_transcribe(audio_input)
            return result if success else f"Failed: {result}"
        
        else:
            # Streamlit UploadedFile object
            suffix = ".wav"
            if hasattr(audio_input, "name") and audio_input.name:
                if audio_input.name.endswith(".mp3"): suffix = ".mp3"
                elif audio_input.name.endswith(".m4a"): suffix = ".m4a"
            
            # Create temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, mode='wb') as tmp:
                tmp.write(audio_input.getvalue())
                tmp_path = tmp.name
            
            # Transcribe
            success, result = load_and_transcribe(tmp_path)
            
            return result if success else f"Failed: {result}"

    except Exception as e:
        logger.error(f"[TRANSCRIBE AUDIO] ERROR: {e}")
        return f"Error: File processing failed - {str(e)}"
    
    finally:
        # Clean up the temp file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except: pass

# --- 2. TEXT REFINEMENT ---
def refine_text(text, style="Professional"):
    try:
        import openai
        api_key = secrets_manager.get_secret("openai.api_key") or secrets_manager.get_secret("OPENAI_API_KEY")
        if not api_key: return text 

        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"Rewrite to be {style}. Preserve meaning. No preamble."},
                {"role": "user", "content": text}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"[REFINE] Error: {e}")
        return text