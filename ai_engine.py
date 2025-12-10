import streamlit as st
import logging
import os
import tempfile
import secrets_manager

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 1. LOCAL WHISPER SETUP (Transcription) ---
# We use a try/except import so the app doesn't crash if whisper isn't installed yet
try:
    import whisper
except ImportError:
    whisper = None

@st.cache_resource
def load_whisper_model():
    """
    Loads the local Whisper model into memory.
    Cached so it only loads once per session (preventing slowness).
    """
    if not whisper:
        logger.error("Whisper module not found. Please add 'openai-whisper' to requirements.txt")
        return None
    
    logger.info("Loading local Whisper model (base)...")
    # 'base' is the best trade-off for speed vs accuracy on a standard server.
    return whisper.load_model("base")

def transcribe_audio(audio_input):
    """
    Transcribes audio using the local CPU/GPU model.
    Does NOT use OpenAI API.
    """
    model = load_whisper_model()
    if not model:
        return "[Error: Whisper library not installed.]"

    tmp_path = None
    try:
        # Handle file-like object (microphone/upload) vs file path
        if isinstance(audio_input, str):
            # It's a file path (from upload temp file)
            logger.info(f"Transcribing file path: {audio_input}")
            result = model.transcribe(audio_input)
        else:
            # It's a BytesIO object (from microphone)
            # We must write it to a temp file because local Whisper needs a file on disk
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(audio_input.getvalue())
                tmp_path = tmp.name
            
            logger.info("Transcribing microphone input...")
            result = model.transcribe(tmp_path)

        text = result["text"].strip()
        return text if text else "[Silence detected]"

    except Exception as e:
        logger.error(f"Local Transcription Failed: {e}")
        return f"[Error: Transcription failed - {str(e)}]"
    
    finally:
        # cleanup temp file if we created one
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except:
                pass

# --- 2. OPENAI SETUP (Only for Text Refinement) ---
# This was the code "missing" from the short version.
# It handles the "Professional", "Grammar", "Friendly" buttons.

def get_openai_client():
    try:
        import openai
        api_key = secrets_manager.get_secret("openai.api_key") or secrets_manager.get_secret("OPENAI_API_KEY")
        if not api_key:
            return None
        return openai.OpenAI(api_key=api_key)
    except ImportError:
        logger.warning("OpenAI library not found. Refinement features disabled.")
        return None

def refine_text(text, style="Professional"):
    """
    Uses OpenAI GPT-4o ONLY for rewriting text (Grammar, Professional, etc).
    If OpenAI API key is missing or fails, it simply returns the original text.
    """
    if not text or len(text) < 5:
        return text

    client = get_openai_client()
    if not client:
        # If API is down/missing, we just return original text so user loses nothing.
        logger.warning("Cannot refine text: OpenAI client missing.")
        return text

    prompts = {
        "Grammar": "Fix grammar, spelling, and punctuation. Do not change the tone.",
        "Professional": "Rewrite this text to be professional, polite, and business-appropriate. Keep the core message.",
        "Friendly": "Rewrite this text to be warm, friendly, and casual.",
        "Concise": "Rewrite this text to be brief and to the point. Remove fluff.",
    }

    system_instruction = prompts.get(style, "Fix grammar.")

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": f"You are a helpful editor. {system_instruction} Return ONLY the rewritten body text."},
                {"role": "user", "content": text}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Refine Text Error: {e}")
        return text