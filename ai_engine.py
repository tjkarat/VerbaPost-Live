import streamlit as st
import whisper
import os
import re

# --- LAZY LOADER (Prevents App Crash on Startup) ---
@st.cache_resource
def load_model():
    """Loads the heavy AI model only when needed."""
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
        # Load model HERE, not at top level
        model = load_model()
        
        print(f"🎧 Transcribing {file_path}...")
        result = model.transcribe(file_path)
        
        raw_text = result["text"]
        return polish_text(raw_text)
        
    except Exception as e:
        print(f"❌ Transcription Error: {e}")
        return f"Error: {e}"