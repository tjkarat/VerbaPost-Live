import streamlit as st
import logging
import os
import tempfile
import secrets_manager
import shutil
import gc
import sys

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CACHED MODEL LOADER (Local Fallback) ---
@st.cache_resource(show_spinner=False)
def load_whisper_model_cached():
    """
    Loads the Whisper model ONCE and keeps it in memory.
    Forces download to /tmp to avoid "Read-only file system" errors.
    """
    try:
        import whisper
        logger.info("[CACHE] Downloading/Loading Whisper 'tiny' model to /tmp...")
        # Force CPU to prevent Cloud Run crashes
        return whisper.load_model("tiny", device="cpu", download_root="/tmp")
    except Exception as e:
        logger.error(f"[CACHE] Failed to load model: {e}")
        return None

# --- LOCAL TRANSCRIPTION ---
def _transcribe_local(audio_path):
    try:
        logger.info("[TRANSCRIBE] Step 1: Garbage collection")
        gc.collect()
        
        if not shutil.which("ffmpeg"):
             return False, "Error: 'ffmpeg' command not found. Please ensure it is installed in packages.txt."

        logger.info("[TRANSCRIBE] Step 2: Fetching Cached Model")
        model = load_whisper_model_cached()
        
        if not model:
            return False, "Error: AI Model failed to initialize. Check logs."

        logger.info("[TRANSCRIBE] Step 3: Transcribing...")
        
        result = model.transcribe(
            audio_path,
            fp16=False,
            language='en' 
        )
        
        text = result.get("text", "").strip()
        logger.info(f"[TRANSCRIBE] Finished. Text length: {len(text)}")
        
        if not text:
            return True, "[Error: No speech detected. Please speak closer to the microphone.]" 
        
        return True, text

    except Exception as e:
        logger.error(f"[TRANSCRIBE] ERROR: {e}")
        return False, f"Error: {str(e)}"
    finally:
        gc.collect()

# --- MAIN TRANSCRIPTION FUNCTION ---
def transcribe_audio(audio_input):
    """
    Main entry point. 
    1. Checks for OpenAI API Key -> Uses Cloud (Fast, Stable).
    2. Fallback -> Uses Local CPU (Free, but memory intensive).
    """
    logger.info("="*60)
    logger.info("[TRANSCRIBE REQUEST]")
    
    tmp_path = None
    try:
        # 1. Handle file input
        suffix = ".wav"
        if hasattr(audio_input, "name") and audio_input.name:
            if audio_input.name.endswith(".mp3"): suffix = ".mp3"
            elif audio_input.name.endswith(".m4a"): suffix = ".m4a"
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, mode='wb') as tmp:
            tmp.write(audio_input.getvalue())
            tmp_path = tmp.name
        
        # 2. Check File Size
        if os.path.getsize(tmp_path) < 100:
            return "Error: Audio file is empty or too small."

        # 3. Hybrid Logic: Try API First
        api_key = secrets_manager.get_secret("openai.api_key") or secrets_manager.get_secret("OPENAI_API_KEY")
        
        if api_key:
            try:
                import openai
                client = openai.OpenAI(api_key=api_key)
                logger.info("[TRANSCRIBE] Attempting OpenAI API...")
                
                with open(tmp_path, "rb") as audio_file:
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1", 
                        file=audio_file,
                        response_format="text"
                    )
                return transcript.strip()
            except Exception as e:
                logger.warning(f"[TRANSCRIBE] API failed, failing over to local: {e}")

        # 4. Fallback to Local
        success, result = _transcribe_local(tmp_path)
        return result if success else f"Error: {result}"

    except Exception as e:
        logger.error(f"[TRANSCRIBE AUDIO] ERROR: {e}")
        return f"Error: File processing failed - {str(e)}"
    
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
        
    except Exception:
        return text