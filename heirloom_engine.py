import logging
import requests
import io
import streamlit as st
import os
from twilio.rest import Client

# --- ROBUST SECRETS IMPORT ---
try: import secrets_manager
except ImportError: secrets_manager = None

# --- IMPORTS ---
try: import ai_engine
except ImportError: ai_engine = None
try: import storage_engine
except ImportError: storage_engine = None

logger = logging.getLogger(__name__)

def _get_twilio_client():
    """
    Robust Client Loader.
    Checks Secrets Manager first (Prod/GCP), then st.secrets (Local/QA).
    """
    sid = None
    token = None

    # 1. Try Secrets Manager (Production/GCP Priority)
    if secrets_manager:
        sid = secrets_manager.get_secret("twilio.account_sid")
        token = secrets_manager.get_secret("twilio.auth_token")

    # 2. Fallback: Direct Streamlit Secrets (QA/Local)
    if not sid and hasattr(st, "secrets") and "twilio" in st.secrets:
        try:
            sid = st.secrets["twilio"]["account_sid"]
            token = st.secrets["twilio"]["auth_token"]
        except KeyError: pass

    # 3. Last Resort: Raw Environment Variables
    if not sid:
        sid = os.environ.get("TWILIO_ACCOUNT_SID")
        token = os.environ.get("TWILIO_AUTH_TOKEN")

    if sid and token:
        try:
            return Client(sid, token)
        except Exception as e:
            logger.error(f"Twilio Client Init Error: {e}")
            return None
            
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
    if not client: return None, None, "Twilio Config Missing (Check Secrets)"
    
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
                    uri = recs[0].uri.replace(".json", "")
                    # Construct valid MP3 URL
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