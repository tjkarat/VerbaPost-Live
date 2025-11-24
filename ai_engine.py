import streamlit as st
import os
import re
import tempfile

# --- LAZY LOADER ---
@st.cache_resource
def load_model():
    """Loads the heavy AI model only when needed."""
    import whisper 
    print("⬇️ Loading Whisper Model... (This happens once)")
    return whisper.load_model("base")

def polish_text(text):
    """Cleans up 'um', 'uh', and stutters"""
    fillers = ["um", "uh", "ah", "like, you know", "you know"]
    polished = text
    for filler in fillers:
        pattern = re.compile(re.escape(filler), re.IGNORECASE)
        polished = pattern.sub("", polished)
    polished = " ".join(polished.split())
    return polished

def transcribe_audio(uploaded_file):
    """
    Handles the transcription process.
    Input: Streamlit UploadedFile object
    Output: Transcribed String
    """
    try:
        # 1. Load Model
        model = load_model()
        
        # 2. Save the in-memory file to a temporary file on disk
        # Whisper requires a file path on the actual disk to read from
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        
        print(f"🎧 Transcribing temporary file: {tmp_path}...")
        
        # 3. Transcribe using the file path
        result = model.transcribe(tmp_path)
        
        # 4. Clean up (Delete the temp file)
        os.remove(tmp_path)
        
        raw_text = result["text"]
        return polish_text(raw_text)
        
    except ImportError:
        return "❌ Error: 'openai-whisper' library not installed. Please add it to requirements.txt"
    except Exception as e:
        print(f"❌ Transcription Error: {e}")
        return f"Error: {e}"