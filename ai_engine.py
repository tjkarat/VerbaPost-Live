import streamlit as st
import os
import tempfile

@st.cache_resource
def load_model():
    """Loads the lightweight AI model."""
    import whisper 
    print("⬇️ STARTING MODEL LOAD...")
    # 'tiny' is 75MB. 'base' is 150MB. Tiny is safest for cloud.
    model = whisper.load_model("tiny")
    print("✅ MODEL LOADED SUCCESSFULLY")
    return model

def transcribe_audio(uploaded_file):
    try:
        # 1. Load the model
        model = load_model()
        
        # 2. Save temp file (Standard Streamlit Pattern)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        
        print(f"🎧 Transcribing file: {tmp_path}")
        
        # 3. Transcribe with CPU settings
        # fp16=False is MANDATORY for CPU servers
        result = model.transcribe(tmp_path, fp16=False)
        
        # 4. Cleanup
        os.remove(tmp_path)
        
        print("✅ Transcription success")
        return result["text"]
        
    except ImportError:
        return "❌ Error: 'openai-whisper' library not installed."
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return f"Error: {e}"