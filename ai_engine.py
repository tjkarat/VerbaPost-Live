import streamlit as st
import os
import tempfile
import secrets_manager  # <--- Ensure this is imported at the top

@st.cache_resource
def load_model():
    """Loads the lightweight AI model."""
    import whisper 
    print("⬇️ STARTING MODEL LOAD...")
    model = whisper.load_model("tiny")
    print("✅ MODEL LOADED SUCCESSFULLY")
    return model

def transcribe_audio(uploaded_file):
    try:
        model = load_model()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        
        print(f"🎧 Transcribing file: {tmp_path}")
        result = model.transcribe(tmp_path, fp16=False)
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
    """
    try:
        import openai
        
        # 1. Get Key Safely (Checks both Secrets file AND Cloud Env Vars)
        api_key = secrets_manager.get_secret("OPENAI_API_KEY")
        
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