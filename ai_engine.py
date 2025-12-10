import streamlit as st
import logging
import os
import tempfile
import secrets_manager
import subprocess
import gc
import traceback

# Configure Logging
logging.basicConfig(level=logging.DEBUG) # DEBUG MODE ON
logger = logging.getLogger(__name__)

# --- 1. ROBUST TRANSCRIPTION ENGINE ---
def load_and_transcribe(audio_path_or_file):
    """
    Self-contained transcription function.
    Loads Whisper, processes audio, and dumps memory immediately.
    """
    model = None
    try:
        logger.debug("[AI DEBUG] 🧹 Starting Garbage Collection...")
        gc.collect()
        
        logger.debug("[AI DEBUG] 📦 Importing Whisper locally...")
        import whisper
        
        # Load TINY model (Safe for Cloud)
        logger.debug("[AI DEBUG] 🧠 Loading Whisper model 'tiny'...")
        model = whisper.load_model("tiny")
        
        # Transcribe
        logger.debug(f"[AI DEBUG] 🎧 Transcribing file: {audio_path_or_file}")
        result = model.transcribe(audio_path_or_file, fp16=False) # fp16=False is safer for CPU
        text = result["text"].strip()
        
        logger.debug(f"[AI DEBUG] ✅ Success! Text length: {len(text)}")
        return text

    except Exception as e:
        # CAPTURE THE EXACT CRASH REASON
        error_msg = f"Transcription Failed: {str(e)}"
        logger.error(f"❌ [AI CRASH] {error_msg}")
        logger.error(traceback.format_exc()) # Prints the full error trace to console
        return f"Error: {str(e)}"
        
    finally:
        # AGGRESSIVE CLEANUP
        logger.debug("[AI DEBUG] 🧹 Cleaning up memory...")
        if model:
            del model
        gc.collect()

def transcribe_audio(audio_input):
    """
    Main entry point called by UI. Handles file management.
    """
    # 1. FFmpeg Check
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except:
        logger.error("❌ [AI DEBUG] FFmpeg not found on server.")
        return "Error: Server missing FFmpeg. Please ensure packages.txt contains 'ffmpeg'."

    tmp_path = None
    try:
        # Handle file upload vs filepath
        if isinstance(audio_input, str):
            return load_and_transcribe(audio_input)
        else:
            # Create temp file
            suffix = ".wav"
            if hasattr(audio_input, "name"):
                suffix = f".{audio_input.name.split('.')[-1]}"
                
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(audio_input.getvalue())
                tmp_path = tmp.name
            
            return load_and_transcribe(tmp_path)

    except Exception as e:
        logger.error(f"❌ [AI DEBUG] File Handling Error: {e}")
        return f"Error processing file: {e}"
    
    finally:
        # Clean up the temp file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
                logger.debug(f"[AI DEBUG] 🗑️ Deleted temp file: {tmp_path}")
            except:
                pass

def refine_text(text, style="Professional"):
    # ... (Keep existing refinement logic if needed) ...
    return text