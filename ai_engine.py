import streamlit as st
import logging
import os
import tempfile
import secrets_manager
import subprocess
import gc
import traceback
import sys

# Configure Logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# --- 1. CORE TRANSCRIPTION LOGIC ---
def load_and_transcribe(audio_path_or_file):
    """
    Self-contained transcription function.
    Loads Whisper, processes audio, and dumps memory immediately.
    """
    model = None
    whisper = None
    
    try:
        logger.info("[TRANSCRIBE] Step 1: Garbage collection")
        gc.collect()
        
        try:
            import whisper as whisper_module
            whisper = whisper_module
        except ImportError as ie:
            return False, "Error: openai-whisper not installed. Run: pip install openai-whisper"
        
        # Load TINY model (Safe for Cloud)
        logger.info("[TRANSCRIBE] Step 2: Loading Whisper 'tiny' model")
        try:
            model = whisper.load_model("tiny")
        except Exception as model_err:
            return False, f"Error: Failed to load Whisper model - {str(model_err)}"
        
        # Transcribe
        logger.info(f"[TRANSCRIBE] Step 3: Transcribing")
        try:
            result = model.transcribe(
                audio_path_or_file,
                fp16=False,  # CPU-safe mode
                language=None,  # Auto-detect
                task='transcribe'
            )
        except Exception as trans_err:
            return False, f"Error: Transcription failed - {str(trans_err)}"
        
        text = result.get("text", "").strip()
        if not text:
            return False, "Error: No speech detected (empty result)"
        
        return True, text

    except Exception as e:
        return False, f"Error: Unexpected failure - {str(e)}"
        
    finally:
        # AGGRESSIVE CLEANUP
        if model: del model
        if whisper: 
             if hasattr(whisper, '_MODELS'): whisper._MODELS.clear()
        gc.collect()


def transcribe_audio(audio_input):
    """
    Main entry point called by UI. Handles file management.
    """
    logger.info("="*60)
    logger.info("[TRANSCRIBE AUDIO] NEW REQUEST")
    
    # 1. FFmpeg Check
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except:
        return "Error: FFmpeg not installed on server."

    tmp_path = None
    try:
        # Handle file upload vs filepath
        if isinstance(audio_input, str):
             # Direct path
            success, result = load_and_transcribe(audio_input)
            return result if success else f"Failed: {result}"
        
        else:
            # Streamlit UploadedFile / AudioInput object
            suffix = ".wav"
            if hasattr(audio_input, "name") and audio_input.name:
                if audio_input.name.endswith(".mp3"): suffix = ".mp3"
                elif audio_input.name.endswith(".m4a"): suffix = ".m4a"
            
            # Create temp file safely
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, mode='wb') as tmp:
                tmp.write(audio_input.getvalue())
                tmp_path = tmp.name
            
            # Transcribe
            success, result = load_and_transcribe(tmp_path)
            return result if success else f"Failed: {result}"

    except Exception as e:
        logger.error(f"[TRANSCRIBE ERROR] {e}")
        return f"Error processing file: {e}"
    
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except: pass


# --- 2. TEXT REFINEMENT (OPTIONAL) ---
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
    except:
        return text