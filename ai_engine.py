from openai import OpenAI, APIConnectionError, APITimeoutError
import os
import tempfile
import shutil
import contextlib
import logging
import secrets_manager
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# --- CONFIGURATION ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_client():
    """Safely creates OpenAI Client"""
    key = secrets_manager.get_secret("openai.api_key") or secrets_manager.get_secret("OPENAI_API_KEY")
    if key:
        return OpenAI(api_key=key)
    return None

# --- 1. SAFE TEMP FILE CONTEXT MANAGER ---
@contextlib.contextmanager
def safe_temp_file(file_obj, suffix=".wav"):
    """
    Context manager for safe temp file handling.
    1. Checks for available disk space (prevents filling the disk).
    2. Writes the file.
    3. Yields the path.
    4. GUARANTEES deletion in the 'finally' block.
    """
    # Safety Check: Require at least 50MB free space
    try:
        if shutil.disk_usage('/tmp').free < 50 * 1024 * 1024:
            logger.error("Insufficient disk space for processing audio.")
            raise RuntimeError("Server busy (storage full). Please try again later.")
    except Exception:
        pass # If disk check fails (e.g. windows/permissions), proceed with caution

    tmp_path = None
    try:
        # Create temp file, delete=False so we can close it and let other libs open it by path
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=tempfile.gettempdir()) as tmp:
            tmp.write(file_obj.getvalue())
            tmp_path = tmp.name
        
        yield tmp_path

    finally:
        # Cleanup guarantees
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
                logger.info(f"Cleaned up temp file: {tmp_path}")
            except OSError as e:
                logger.error(f"Failed to cleanup temp file {tmp_path}: {e}")

# --- 2. TRANSCRIPTION (v1.0 Syntax) ---
def transcribe_audio(file_obj):
    """
    Transcribes audio using OpenAI Whisper (v1.0 Syntax).
    """
    client = get_client()
    if not client:
        return "[Error: OpenAI API Key missing]"

    # Determine suffix from name if available, else default to .wav
    suffix = f".{file_obj.name.split('.')[-1]}" if hasattr(file_obj, 'name') else '.wav'
    
    try:
        with safe_temp_file(file_obj, suffix) as tmp_path:
            with open(tmp_path, "rb") as audio_file:
                # Updated v1.0 Call
                transcript = client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file
                )
            
            # v1.0 returns an object, access via .text
            text = transcript.text
            logger.info("Transcription successful.")
            return text

    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        return f"[Error processing audio: {str(e)}]"

# --- 3. TEXT REFINEMENT (v1.0 Syntax) ---
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((APIConnectionError, APITimeoutError)),
    reraise=False 
)
def refine_text(text, style="Professional"):
    """
    Refines text using GPT-3.5/4 (v1.0 Syntax).
    """
    if not text or len(text.strip()) < 5:
        return text

    client = get_client()
    if not client:
        return text

    # Prompt Engineering
    prompts = {
        "Grammar": "Correct the grammar and spelling of the following text. Do not change the tone or content, just fix errors.",
        "Professional": "Rewrite the following text to be professional, polite, and formal suitable for business correspondence.",
        "Friendly": "Rewrite the following text to be warm, personal, and friendly.",
        "Concise": "Rewrite the following text to be concise and to the point, removing unnecessary fluff."
    }

    system_instruction = prompts.get(style, prompts["Professional"])

    try:
        # Updated v1.0 Call
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"You are an expert editor. {system_instruction}"},
                {"role": "user", "content": f"Text to rewrite:\n{text}"}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        # v1.0 Object Access
        refined = response.choices[0].message.content.strip()
        return refined

    except Exception as e:
        logger.error(f"AI Refinement Failed: {e}")
        # Fail safe: Return original text if AI fails
        return text