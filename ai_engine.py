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
def refine_text(text, style):
    """
    Sends text to OpenAI to be rewritten in a specific style.
    Styles: 'Grammar Fix', 'Professional', 'Warm & Friendly', 'Concise'
    """
    import os  # <--- CHANGED: Import os instead of secrets_manager
    import openai
    
    # 1. Get Key from Environment Variable
    # Cloud Run automatically injects the secret here if you "mounted" it
    api_key = os.getenv("OPENAI_API_KEY") 
    
    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment variables.")
        return text # Fail safe: return original text if key is missing
    
    # 2. Initialize Client
    client = openai.OpenAI(api_key=api_key)
    
    # 2. Define Prompts
    prompts = {
        "Fix Grammar": "Fix the grammar and spelling of this text, but keep the tone exactly the same.",
        "Professional": "Rewrite this text to be more formal and professional.",
        "Friendly": "Rewrite this text to be warmer, friendlier, and more personal.",
        "Concise": "Rewrite this text to be more concise and to the point.",
        "Pirate": "Rewrite this text like a pirate (Arr!)." # Fun easter egg for Santa letters?
    }
    
    system_instruction = prompts.get(style, "Fix grammar.")
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", # Cheap and fast
            messages=[
                {"role": "system", "content": f"You are a helpful editor. {system_instruction}"},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"AI Edit Error: {e}")
        return text