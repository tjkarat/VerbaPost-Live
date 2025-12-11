import streamlit as st
import logging
import os
import tempfile
import secrets_manager
import subprocess
import gc
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
    try:
        import whisper
        import torch
        logger.info("[CACHE] Loading Whisper 'tiny' model...")
        
        # CRITICAL FIX 1: Force CPU to prevent GPU/CUDA crashes in cloud
        device = "cpu" 
        
        # CRITICAL FIX 2: download_root="/tmp" for Read-Only filesystems
        return whisper.load_model("tiny", device=device, download_root="/tmp")
    except Exception as e:
        logger.error(f"[CACHE] Failed to load model: {e}")
        return None

# --- TRANSCRIPTION ENGINE ---
def load_and_transcribe(audio_path_or_file):
    try:
        logger.info("[TRANSCRIBE] Step 1: GC & System Check")
        gc.collect()
        
        if not shutil.which("ffmpeg"):
             return False, "Error: 'ffmpeg' missing. Add to packages.txt."

        logger.info("[TRANSCRIBE] Step 2: Fetching Model")
        model = load_whisper_model_cached()
        
        if not model:
            return False, "Error: AI Model failed to load."

        logger.info(f"[TRANSCRIBE] Step 3: Transcribing {audio_path_or_file}...")
        
        # CRITICAL FIX 3: fp16=False prevents CPU errors
        # CRITICAL FIX 4: language='en' speeds up processing significantly
        result = model.transcribe(
            audio_path_or_file,
            fp16=False,
            language='en'
        )
        
        text = result.get("text", "").strip()
        logger.info(f"[TRANSCRIBE] Finished. Text length: {len(text)}")
        
        if not text:
            # If silence, return a placeholder so user knows it ran
            return True, "[Silence detected. Please try recording again.]" 
        
        return True, text

    except Exception as e:
        logger.error(f"[TRANSCRIBE] ERROR: {e}")
        return False, f"Error processing audio: {str(e)}"
        
    finally:
        gc.collect()

def transcribe_audio(audio_input):
    logger.info("="*60)
    logger.info("[TRANSCRIBE REQUEST]")
    
    tmp_path = None
    try:
        # 1. Determine Extension
        suffix = ".wav"
        if hasattr(audio_input, "name") and audio_input.name:
            if audio_input.name.endswith(".mp3"): suffix = ".mp3"
            elif audio_input.name.endswith(".m4a"): suffix = ".m4a"
            
        # 2. Write Temp File (Safely)
        # delete=False is required so we can close it before Whisper reads it (Windows/Linux compat)
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, mode='wb') as tmp:
            tmp.write(audio_input.getvalue())
            tmp_path = tmp.name
        
        # 3. Validation
        if os.path.getsize(tmp_path) < 100:
            return "Error: Audio file is empty or too small."
            
        # 4. Transcribe
        success, result = load_and_transcribe(tmp_path)
        return result if success else f"Error: {result}"

    except Exception as e:
        logger.error(f"[TRANSCRIBE AUDIO] ERROR: {e}")
        return f"Error: {str(e)}"
    
    finally:
        # 5. Cleanup
        if tmp_path and os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except: pass

# --- TEXT REFINEMENT ---
def refine_text(text, style="Professional"):
    try:
        import openai
        api_key = secrets_manager.get_secret("openai.api_key") or secrets_manager.get_secret("OPENAI_API_KEY")
        if not api_key: return text 

        client = openai.OpenAI(api_key=api_key)
        
        prompt_map = {
            "Grammar": "Fix grammar/spelling.",
            "Professional": "Make formal/professional.",
            "Friendly": "Make warm/friendly.",
            "Concise": "Shorten significantly."
        }
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"{prompt_map.get(style, '')} Keep meaning. No chat preamble."},
                {"role": "user", "content": text}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"[REFINE] Error: {e}")
        return text