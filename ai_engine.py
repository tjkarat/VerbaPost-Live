import streamlit as st
import logging
import os
import tempfile
import secrets_manager
import subprocess

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 1. LOCAL WHISPER SETUP (Transcription) ---
@st.cache_resource
def load_whisper_model():
    """
    Loads the local Whisper model into memory.
    """
    # CRITICAL: Check for FFmpeg first to prevent hard crashes
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        logger.error("❌ FFmpeg is missing. Please add 'ffmpeg' to packages.txt.")
        return None

    import whisper
    logger.info("🧠 Loading Whisper AI model (tiny)...")
    return whisper.load_model("tiny")

def transcribe_audio(audio_input):
    """
    Transcribes audio using the local CPU/GPU model.
    """
    try:
        model = load_whisper_model()
        if model is None:
            return "Error: Server missing audio tools (FFmpeg). Please contact support."
    except Exception as e:
        return f"Error loading Whisper: {e}"

    tmp_path = None
    try:
        # Handle file-like object (microphone/upload) vs file path
        if isinstance(audio_input, str):
            result = model.transcribe(audio_input)
        else:
            # Microphone (BytesIO) -> Temp File
            # We explicitly allow "wb" (write binary) to prevent encoding errors
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(audio_input.getvalue())
                tmp_path = tmp.name
            
            logger.info("🎧 Transcribing microphone input...")
            result = model.transcribe(tmp_path)

        text = result["text"].strip()
        logger.info("✅ Transcription successful.")
        
        return text if text else "Silence detected (Please try recording again)"

    except Exception as e:
        logger.error(f"Local Transcription Failed: {e}")
        return f"Error: {str(e)}"
    
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except: pass

# --- 2. OPENAI SETUP (Only for Text Refinement) ---
def get_openai_client():
    try:
        import openai
        api_key = secrets_manager.get_secret("openai.api_key") or secrets_manager.get_secret("OPENAI_API_KEY")
        
        # Fallback to direct secrets
        if not api_key:
            try: api_key = st.secrets["openai"]["api_key"]
            except: pass

        if not api_key: return None
        return openai.OpenAI(api_key=api_key)
    except ImportError:
        return None

def refine_text(text, style="Professional"):
    """
    Uses OpenAI GPT-4o ONLY for rewriting text.
    """
    if not text or len(text) < 5: return text

    client = get_openai_client()
    if not client: return text

    prompts = {
        "Grammar": "Fix grammar, spelling, and punctuation. Do not change the tone.",
        "Professional": "Rewrite this to be professional and business-appropriate.",
        "Friendly": "Rewrite this to be warm and friendly.",
        "Concise": "Rewrite this to be brief and remove fluff.",
    }

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": f"You are a helpful editor. {prompts.get(style, '')} Return ONLY the rewritten body text."},
                {"role": "user", "content": text}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Refine Text Error: {e}")
        return text