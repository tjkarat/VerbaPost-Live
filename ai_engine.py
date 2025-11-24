import whisper
import sys
import re
import os
import streamlit as st

# Load model once (Cached)
@st.cache_resource
def load_whisper_model():
    print("⬇️ Loading Whisper Model (Base)...")
    return whisper.load_model("base")

try:
    model = load_whisper_model()
except Exception as e:
    print(f"Model loading error: {e}")
    model = None

def transcribe_audio(filename):
    if model is None:
        return "Error: AI Model not loaded (Check logs)."
        
    print(f"🎧 Transcribing {filename}...")
    try:
        result = model.transcribe(filename)
        text = result["text"]
        return polish_text(text)
    except Exception as e:
        return f"Transcription Error: {e}"

def polish_text(text):
    fillers = ["um", "uh", "ah", "like, you know", "you know"]
    polished = text
    for filler in fillers:
        pattern = re.compile(re.escape(filler), re.IGNORECASE)
        polished = pattern.sub("", polished)
    polished = " ".join(polished.split())
    return polished