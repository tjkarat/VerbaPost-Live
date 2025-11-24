import streamlit as st
import os
import re

# --- LAZY LOADER ---
@st.cache_resource
def load_model():
    """Loads the heavy AI model only when needed."""
    # 1. Import here so app doesn't crash on startup if missing
    import whisper 
    print("⬇️ Loading Whisper Model... (This happens once)")
    return whisper.load_model("base")

def polish_text(text):
    fillers = ["um", "uh", "ah", "like, you know", "you know"]
    polished = text
    for filler in fillers:
        pattern = re.compile(re.escape(filler), re.IGNORECASE)
        polished = pattern.sub("", polished)
    polished = " ".join(polished.split())
    return polished

def transcribe_audio(file_path):
    try:
        # 2. Load model logic
        model = load_model()
        
        print(f"🎧 Transcribing {file_path}...")
        result = model.transcribe(file_path)
        
        raw_text = result["text"]
        return polish_text(raw_text)
        
    except ImportError:
        return "❌ Error: 'openai-whisper' library not installed. Please add it to requirements.txt"
    except Exception as e:
        print(f"❌ Transcription Error: {e}")
        return f"Error: {e}"