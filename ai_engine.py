import os
import logging
import tempfile
import shutil

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai_engine")

# --- IMPORTS ---
try:
    import whisper
except ImportError:
    logger.error("Whisper not installed. Run: pip install openai-whisper")
    whisper = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

import streamlit as st

# --- CONFIGURATION ---
# CRITICAL: Force CPU to prevent Cloud Run memory crashes
DEVICE = "cpu"
WHISPER_MODEL_SIZE = "tiny"  # 'tiny', 'base', 'small', 'medium', 'large'

# --- MODEL CACHING ---
@st.cache_resource
def load_whisper_model():
    """
    Loads and caches the Whisper model to avoid reloading on every run.
    """
    if not whisper:
        return None
    try:
        logger.info(f"Loading Whisper model ({WHISPER_MODEL_SIZE}) on {DEVICE}...")
        return whisper.load_model(WHISPER_MODEL_SIZE, device=DEVICE)
    except Exception as e:
        logger.error(f"Failed to load Whisper: {e}")
        return None

# --- TRANSCRIPTION FUNCTIONS ---
def transcribe_audio(audio_source):
    """
    Robust transcription that handles BOTH file paths (str) and Streamlit UploadedFiles.
    """
    model = load_whisper_model()
    if not model:
        return "Error: AI Transcription model is not available."

    temp_path = None
    path_to_transcribe = ""

    try:
        # --- SCENARIO A: Input is a File Path (String) ---
        if isinstance(audio_source, str):
            if os.path.exists(audio_source):
                path_to_transcribe = audio_source
            else:
                return f"Error: File path not found: {audio_source}"

        # --- SCENARIO B: Input is a Streamlit UploadedFile/BytesIO ---
        elif hasattr(audio_source, 'getvalue') or hasattr(audio_source, 'read'):
            # Create a temp file to store the bytes
            suffix = ".wav"
            if hasattr(audio_source, 'name'):
                suffix = f".{audio_source.name.split('.')[-1]}"
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                # Handle 'getvalue' (Streamlit) vs 'read' (Standard Python)
                if hasattr(audio_source, 'getvalue'):
                    tmp_file.write(audio_source.getvalue())
                else:
                    tmp_file.write(audio_source.read())
                
                path_to_transcribe = tmp_file.name
                temp_path = tmp_file.name
        else:
            return "Error: Unsupported audio input format."

        # --- PERFORM TRANSCRIPTION ---
        logger.info(f"Transcribing file: {path_to_transcribe}")
        result = model.transcribe(path_to_transcribe)
        transcribed_text = result.get("text", "").strip()
        
        return transcribed_text

    except Exception as e:
        logger.error(f"Transcription Failed: {e}")
        return f"Error during transcription: {str(e)}"
    
    finally:
        # Cleanup temp file if we created one
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

# --- TEXT REFINEMENT (GPT-4o) ---
def refine_text(text, style="Professional"):
    """
    Uses OpenAI API (GPT-4o) to rewrite the text.
    Styles: Grammar, Professional, Friendly, Concise
    """
    api_key = st.secrets.get("openai", {}).get("api_key")
    if not api_key:
        return text  # Fail gracefully if no key

    if not OpenAI:
        return text

    client = OpenAI(api_key=api_key)
    
    prompts = {
        "Grammar": "Fix grammar and punctuation only. Keep the original tone.",
        "Professional": "Rewrite this to be professional, polite, and clear. Suitable for business.",
        "Friendly": "Rewrite this to be warm, personal, and engaging. Suitable for family.",
        "Concise": "Summarize this. Remove fluff, keep the key points, make it brief."
    }
    
    system_prompt = prompts.get(style, prompts["Grammar"])
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": f"You are an expert editor. {system_prompt}"},
                {"role": "user", "content": text}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Refinement Error: {e}")
        return text  # Return original if API fails