import streamlit as st
import logging
import os
import tempfile
import secrets_manager
import subprocess
import gc
import traceback

# Configure Logging to show in the Streamlit Console
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 1. ROBUST TRANSCRIPTION ENGINE ---
def load_and_transcribe(audio_path_or_file):
    """
    Self-contained transcription function.
    Loads Whisper, processes audio, and dumps memory immediately.
    """
    model = None
    try:
        logger.info("[AI DEBUG] 🧹 Starting Garbage Collection...")
        gc.collect()
        
        logger.info("[AI DEBUG] 📦 Importing Whisper locally...")
        import whisper
        
        # Load TINY model (Safe for Cloud)
        logger.info("[AI DEBUG] 🧠 Loading Whisper model 'tiny'...")
        model = whisper.load_model("tiny")
        
        # Transcribe
        logger.info(f"[AI DEBUG] 🎧 Transcribing file: {audio_path_or_file}")
        result = model.transcribe(audio_path_or_file)
        text = result["text"].strip()
        
        logger.info(f"[AI DEBUG] ✅ Success! Text length: {len(text)}")
        return text

    except Exception as e:
        # CAPTURE THE EXACT CRASH REASON
        error_msg = f"Transcription Failed: {str(e)}"
        logger.error(f"❌ [AI CRASH] {error_msg}")
        logger.error(traceback.format_exc()) # Prints the full error trace to console
        return f"Error: {str(e)}"
        
    finally:
        # AGGRESSIVE CLEANUP
        logger.info("[AI DEBUG] 🧹 Cleaning up memory...")
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
            # We use delete=False because Windows/Streamlit sometimes locks files if we don't close them first
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
                logger.info(f"[AI DEBUG] 🗑️ Deleted temp file: {tmp_path}")
            except:
                pass

# --- 2. OPENAI SETUP (Refining) ---
def refine_text(text, style="Professional"):
    try:
        import openai
        api_key = secrets_manager.get_secret("openai.api_key") or secrets_manager.get_secret("OPENAI_API_KEY")
        
        # Fallback to direct secrets
        if not api_key:
            try: api_key = st.secrets["openai"]["api_key"]
            except: pass
            
        if not api_key: 
            logger.warning("[AI DEBUG] No OpenAI Key found. Skipping refinement.")
            return text 

        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": f"Rewrite this text to be {style}."},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"[AI DEBUG] Refine Error: {e}")
        return text