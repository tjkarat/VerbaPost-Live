import streamlit as st
import os
import tempfile
import secrets_manager

# --- CONFIGURATION ---
# CRITICAL: Do NOT import 'whisper' here. It loads 2GB of Torch/NVIDIA libraries.
# Loading it at the top level causes Streamlit Cloud (QA) to crash immediately (White Screen).

def load_model():
    """
    Lazy loader for the local Whisper model.
    Only runs if we actually try to use local transcription.
    """
    import whisper 
    print("⬇️ STARTING LOCAL MODEL LOAD...")
    model = whisper.load_model("tiny")
    print("✅ MODEL LOADED SUCCESSFULLY")
    return model

def transcribe_audio(audio_file):
    """
    Robust Transcriber:
    1. Tries Local Whisper (Free, but heavy memory usage).
    2. Falls back to OpenAI API (Reliable, requires Key).
    """
    # 1. Setup Temp File
    prefix = "audio"
    suffix = ".wav"
    # Handle both file-like objects and Streamlit UploadedFile
    if hasattr(audio_file, 'name'):
        suffix = f".{audio_file.name.split('.')[-1]}"
        
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(audio_file.getvalue())
        tmp_path = tmp.name

    try:
        # --- ATTEMPT 1: LOCAL WHISPER ---
        # We wrap this in a broad try/except because it frequently crashes on small cloud instances
        try:
            # Check if we should skip local to save memory (optional env var)
            if os.environ.get("SKIP_LOCAL_WHISPER"):
                raise ImportError("Skipping local whisper by config")

            import whisper
            print("🎤 Attempting Local Whisper...")
            model = load_model()
            result = model.transcribe(tmp_path, fp16=False)
            return result["text"]
            
        except (ImportError, Exception, RuntimeError) as e:
            print(f"⚠️ Local Whisper unavailable ({e}). Switching to OpenAI API...")

        # --- ATTEMPT 2: OPENAI API (Fallback) ---
        import openai
        api_key = secrets_manager.get_secret("openai.api_key") or secrets_manager.get_secret("OPENAI_API_KEY")
        
        if not api_key:
            return "⚠️ Error: Transcription failed. No API Key found and Local AI crashed."
            
        client = openai.OpenAI(api_key=api_key)
        
        with open(tmp_path, "rb") as audio_file_obj:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file_obj
            )
        return transcript.text

    except Exception as e:
        return f"❌ Transcription Critical Error: {str(e)}"
        
    finally:
        # Cleanup temp file
        if os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except: pass

def refine_text(text, style):
    """
    Sends text to OpenAI to be rewritten in a specific style.
    """
    try:
        import openai
        
        # Get Key Safely
        api_key = secrets_manager.get_secret("openai.api_key") or secrets_manager.get_secret("OPENAI_API_KEY")
        
        if not api_key:
            print("❌ AI Editor: Missing OPENAI_API_KEY")
            return text 
        
        client = openai.OpenAI(api_key=api_key)
        
        prompts = {
            "Grammar": "Fix grammar and spelling errors. Keep the tone natural.",
            "Professional": "Rewrite this to be formal, polite, and professional.",
            "Friendly": "Rewrite this to be warm, personal, and friendly.",
            "Concise": "Rewrite this to be concise and to the point. Remove fluff."
        }
        
        instruction = prompts.get(style, "Fix grammar.")
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", 
            messages=[
                {"role": "system", "content": f"You are an expert editor. {instruction}"},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"AI Edit Error: {e}")
        return text