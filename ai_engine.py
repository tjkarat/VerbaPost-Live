import streamlit as st
import logging
import os
import tempfile
import secrets_manager
import subprocess
import gc
import traceback

# Configure Logging (Clean format, no emojis)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_whisper_model():
    """
    Loads the local Whisper model into memory.
    """
    # 1. Force Garbage Collection
    gc.collect()
    
    # 2. Check for FFmpeg
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except Exception:
        logger.error("FFmpeg is missing. Please add ffmpeg to packages.txt")
        return None

    # 3. Import Whisper locally (Prevents startup crash)
    try:
        import whisper
        logger.info("Loading Whisper AI model (tiny)...")
        return whisper.load_model("tiny")
    except ImportError:
        logger.error("openai-whisper python package is missing.")
        return None
    except Exception as e:
        logger.error(f"Model load failed: {e}")
        return None

def transcribe_audio(audio_input):
    """
    Transcribes audio using the local CPU/GPU model.
    """
    model = None
    tmp_path = None
    
    try:
        logger.info("Starting transcription process...")
        
        # Load model
        model = load_whisper_model()
        if model is None:
            return "Error: Transcription engine failed to load. Check logs."

        # Handle file
        if isinstance(audio_input, str):
            tmp_path = audio_input
            delete_file = False
        else:
            # Create temp file
            delete_file = True
            suffix = ".wav"
            if hasattr(audio_input, "name"):
                suffix = f".{audio_input.name.split('.')[-1]}"
                
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(audio_input.getvalue())
                tmp_path = tmp.name
            
        logger.info(f"Transcribing file: {tmp_path}")
        
        # Transcribe
        result = model.transcribe(tmp_path, fp16=False) # fp16=False fixes CPU warnings
        text = result["text"].strip()
        
        logger.info("Transcription success.")
        return text

    except Exception as e:
        logger.error(f"Transcription Critical Failure: {e}")
        logger.error(traceback.format_exc())
        return f"Error: {str(e)}"
    
    finally:
        # Cleanup
        if tmp_path and delete_file and os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except: pass
        
        if model:
            del model
        gc.collect()

# --- TEXT REFINEMENT ---
def refine_text(text, style="Professional"):
    try:
        import openai
        # Try multiple key locations
        api_key = None
        if secrets_manager:
            api_key = secrets_manager.get_secret("openai.api_key") or secrets_manager.get_secret("OPENAI_API_KEY")
        
        if not api_key:
            try: api_key = st.secrets["openai"]["api_key"]
            except: pass
            
        if not api_key: 
            return text 

        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": f"Rewrite this text to be {style}."},
                {"role": "user", "content": text}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Refine Error: {e}")
        return text