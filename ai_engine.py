import streamlit as st
import logging
import os
import tempfile
import secrets_manager
import subprocess
import gc 

# Configure Logging
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
        # 1. Force Garbage Collection to clear RAM before we start
        gc.collect()
        
        # 2. Lazy Import (Prevents App Crash on Startup)
        import whisper
        
        # 3. Load TINY model (Safe for Cloud)
        # 'base' uses too much RAM and causes the "refresh loop"
        logger.info("🧠 Loading Whisper AI model (tiny)...")
        model = whisper.load_model("tiny")
        
        # 4. Transcribe
        logger.info(f"🎧 Transcribing: {audio_path_or_file}")
        result = model.transcribe(audio_path_or_file)
        text = result["text"].strip()
        
        return text

    except Exception as e:
        logger.error(f"Transcription Failed: {e}")
        return f"Error: {str(e)}"
        
    finally:
        # 5. AGGRESSIVE CLEANUP
        # Delete the model from memory so the app doesn't crash later
        if model:
            del model
        gc.collect()

def transcribe_audio(audio_input):
    """
    Main entry point called by UI. Handles file management.
    """
    # Check for FFmpeg first
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except:
        return "Error: Server missing FFmpeg. Add 'ffmpeg' to packages.txt."

    tmp_path = None
    try:
        # Handle file upload vs filepath
        if isinstance(audio_input, str):
            return load_and_transcribe(audio_input)
        else:
            # Create temp file for the uploaded binary
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(audio_input.getvalue())
                tmp_path = tmp.name
            
            return load_and_transcribe(tmp_path)

    except Exception as e:
        return f"Error processing file: {e}"
    
    finally:
        # Clean up the temp file
        if tmp_path and os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except: pass

# --- 2. OPENAI SETUP (Refining) ---
def refine_text(text, style="Professional"):
    # (Kept simple to save space - this part was working)
    try:
        import openai
        api_key = secrets_manager.get_secret("openai.api_key") or secrets_manager.get_secret("OPENAI_API_KEY")
        
        # Fallback to direct secrets
        if not api_key:
            try: api_key = st.secrets["openai"]["api_key"]
            except: pass
            
        if not api_key: return text # Return original if no key

        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": f"Rewrite this text to be {style}."},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content.strip()
    except:
        return text