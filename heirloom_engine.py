import logging
import requests
import io
import streamlit as st
from twilio.rest import Client

# --- IMPORTS ---
try: import ai_engine
except ImportError: ai_engine = None
try: import storage_engine
except ImportError: storage_engine = None

logger = logging.getLogger(__name__)

def _get_twilio_client():
    """Duplicated helper to avoid modifying ai_engine.py"""
    try:
        sid = st.secrets["twilio"]["account_sid"]
        token = st.secrets["twilio"]["auth_token"]
        return Client(sid, token)
    except Exception:
        return None

def process_latest_call(parent_phone, user_email):
    """
    1. Finds latest call from parent_phone
    2. Downloads Audio
    3. Uploads to Storage Vault (Permanent)
    4. Transcribes via AI
    Returns: (transcript_text, storage_path, error_message)
    """
    client = _get_twilio_client()
    if not client: return None, None, "Twilio Config Missing"
    
    # 1. FIND CALL
    try:
        # Simple normalization
        clean_phone = "".join(filter(str.isdigit, str(parent_phone)))
        if not clean_phone.startswith("+"): 
            if len(clean_phone) == 10: clean_phone = f"+1{clean_phone}"
            else: clean_phone = f"+{clean_phone}"

        # Search Inbound & Outbound
        calls_in = client.calls.list(from_=clean_phone, limit=5)
        calls_out = client.calls.list(to=clean_phone, limit=5)
        all_calls = sorted(calls_in + calls_out, key=lambda c: c.date_created, reverse=True)
        
        target_url = None
        for call in all_calls:
            if call.status == 'completed':
                recs = call.recordings.list()
                if recs:
                    # Remove .json if present
                    uri = recs[0].uri.replace(".json", "")
    
                    # Check if .mp3 is already there to prevent ".mp3.mp3"
                    if uri.endswith(".mp3"):
                        target_url = f"https://api.twilio.com{uri}"
                    else:
                        target_url = f"https://api.twilio.com{uri}.mp3"
                    break
        
        if not target_url: return None, None, "No recordings found."

    except Exception as e: return None, None, f"Twilio Search Error: {e}"

    # 2. DOWNLOAD AUDIO
    try:
        resp = requests.get(target_url, auth=(client.username, client.password))
        if resp.status_code != 200: return None, None, "Download Failed"
        
        audio_bytes = resp.content
    except Exception as e: return None, None, f"Download Error: {e}"

    # 3. UPLOAD TO VAULT
    storage_path = None
    if storage_engine:
        storage_path = storage_engine.upload_audio(user_email, audio_bytes)

    # 4. TRANSCRIBE
    transcript = ""
    if ai_engine:
        # Create a file-like object for Whisper
        with io.BytesIO(audio_bytes) as f:
            f.name = "story.mp3" # Whisper needs a filename hint
            transcript = ai_engine.transcribe_audio(f)
    
    return transcript, storage_path, None