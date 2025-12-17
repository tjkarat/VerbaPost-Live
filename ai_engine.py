import openai
import streamlit as st
from twilio.rest import Client
import requests
import os
import tempfile
import time
import logging

# --- IMPORT SECRETS MANAGER ---
try:
    import secrets_manager
except ImportError:
    secrets_manager = None

logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
def get_openai_client():
    """Retreives OpenAI Client using Secrets Manager logic."""
    api_key = None
    
    if secrets_manager:
        api_key = secrets_manager.get_secret("openai.api_key")
    
    # Fallback for QA if secrets_manager fails
    if not api_key and "openai" in st.secrets:
        api_key = st.secrets["openai"]["api_key"]
        
    if not api_key:
        logger.error("OpenAI API Key missing.")
        return None
        
    return openai.OpenAI(api_key=api_key)

# --- PHASE 1: MANUAL UPLOAD TRANSCRIPTION ---

def transcribe_audio(audio_file_obj):
    """
    Transcribes audio. Handles both direct file objects AND string file paths.
    """
    client = get_openai_client()
    if not client:
        return "Error: Client not configured."

    try:
        # CASE A: Input is a file path (String)
        if isinstance(audio_file_obj, str):
            if not os.path.exists(audio_file_obj):
                return "Error: Temporary audio file not found."
            with open(audio_file_obj, "rb") as f:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=f,
                    response_format="text"
                )
            return transcript

        # CASE B: Input is already an open file / BytesIO
        else:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file_obj,
                response_format="text"
            )
            return transcript

    except Exception as e:
        return f"Transcription Error: {e}"

# --- PHASE 2: TWILIO INTEGRATION ---

def _get_twilio_client():
    """Helper to get authenticated Twilio client."""
    account_sid = None
    auth_token = None

    if secrets_manager:
        account_sid = secrets_manager.get_secret("twilio.account_sid")
        auth_token = secrets_manager.get_secret("twilio.auth_token")
    
    if not account_sid and "twilio" in st.secrets:
        account_sid = st.secrets["twilio"]["account_sid"]
        auth_token = st.secrets["twilio"]["auth_token"]

    if not account_sid or not auth_token:
        return None
    
    try:
        return Client(account_sid, auth_token)
    except Exception as e:
        logger.error(f"Twilio Client Error: {e}")
        return None

def fetch_and_transcribe_latest_call(parent_phone):
    """
    Finds the last call from a specific number, downloads, and transcribes.
    """
    client = _get_twilio_client()
    if not client: return None, "Twilio Config Missing"

    try:
        # Clean phone number
        clean_phone = "".join(filter(lambda x: x.isdigit() or x == '+', str(parent_phone)))
        calls = client.calls.list(from_=clean_phone, limit=5)
    except Exception as e:
        return None, f"Twilio List Error: {e}"
    
    if not calls:
        return None, "No recent calls found from this number."

    # Look for recording
    target_recording_url = None
    for call in calls:
        try:
            recordings = call.recordings.list()
            if recordings:
                rec = recordings[0]
                base_uri = rec.uri.replace(".json", "")
                target_recording_url = f"https://api.twilio.com{base_uri}.mp3"
                break
        except Exception:
            continue
            
    if not target_recording_url:
        return None, "Found calls, but no recordings found."

    # Download & Transcribe
    try:
        account_sid = client.username
        auth_token = client.password
        response = requests.get(target_recording_url, auth=(account_sid, auth_token))
        
        if response.status_code != 200:
            return None, f"Download failed: {response.status_code}"
            
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f"temp_story_{int(time.time())}.mp3")
        
        with open(temp_path, "wb") as f:
            f.write(response.content)

        client_ai = get_openai_client()
        if not client_ai: return None, "OpenAI Failed"

        with open(temp_path, "rb") as audio_file:
            transcript = client_ai.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file,
                response_format="text"
            )
        
        if os.path.exists(temp_path): os.remove(temp_path)
        return transcript, None

    except Exception as e:
        return None, f"Process failed: {e}"

def get_recent_call_logs(limit=20):
    """
    ADMIN TOOL: Fetches raw call log metadata to find 'Ghost Calls'.
    """
    client = _get_twilio_client()
    if not client: return []

    try:
        calls = client.calls.list(limit=limit)
        data = []
        for c in calls:
            data.append({
                "from": c.from_,
                "to": c.to,
                "status": c.status,
                "duration": c.duration,
                "date": c.date_created,
                "sid": c.sid
            })
        return data
    except Exception as e:
        logger.error(f"Log Fetch Error: {e}")
        return []