import streamlit as st
import os
import re
import tempfile

@st.cache_resource
def load_model():
    import whisper 
    print("⬇️ Loading Whisper Model...")
    return whisper.load_model("base")

def polish_text(text):
    fillers = ["um", "uh", "ah", "like, you know", "you know"]
    polished = text
    for filler in fillers:
        pattern = re.compile(re.escape(filler), re.IGNORECASE)
        polished = pattern.sub("", polished)
    polished = " ".join(polished.split())
    return polished

def transcribe_audio(uploaded_file):
    try:
        model = load_model()
        
        # Save temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        
        # CRITICAL FIX: fp16=False prevents the CPU crash/warning
        result = model.transcribe(tmp_path, fp16=False)
        
        os.remove(tmp_path)
        
        raw_text = result["text"]
        return polish_text(raw_text)
        
    except ImportError:
        return "Error: Libraries missing."
    except Exception as e:
        return f"Error: {e}"