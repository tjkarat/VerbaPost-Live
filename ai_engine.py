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
    """Transcribes an uploaded audio file object."""
    client = get_openai_client()
    if not client:
        return "Error: Client not configured."

    try:
        transcript = client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio_file_obj,
            response_format="text"
        )
        return transcript
    except Exception as e:
        return f"Transcription Error: {e}"

# --- PHASE 2: TWILIO FETCH & TRANSCRIBE ---

def fetch_and_transcribe_latest_call(parent_phone):
    """
    Connects to Twilio, finds the last call, downloads audio, and transcribes it.
    """
    # 1. Setup Twilio Credentials safely
    account_sid = None
    auth_token = None

    if secrets_manager:
        account_sid = secrets_manager.get_secret("twilio.account_sid")
        auth_token = secrets_manager.get_secret("twilio.auth_token")
    
    # QA Fallback
    if not account_sid and "twilio" in st.secrets:
        account_sid = st.secrets["twilio"]["account_sid"]
        auth_token = st.secrets["twilio"]["auth_token"]

    if not account_sid or not auth_token:
        return None, "Twilio credentials missing. Check secrets/env vars."

    try:
        client = Client(account_sid, auth_token)
    except Exception as e:
        return None, f"Twilio Connection Error: {e}"

    # 2. Find calls from this specific phone number
    try:
        # Clean phone number just in case (remove spaces/dashes)
        clean_phone = "".join(filter(lambda x: x.isdigit() or x == '+', str(parent_phone)))
        calls = client.calls.list(from_=clean_phone, limit=5)
    except Exception as e:
        return None, f"Twilio List Error: {e}"
    
    if not calls:
        return None, "No recent calls found from this number."

    # 3. Look for a call with a recording
    target_recording_url = None
    
    for call in calls:
        try:
            recordings = call.recordings.list()
            if recordings:
                # FIX: Build the URL manually using the relative URI.
                # 'media_url' attribute is unreliable in some library versions.
                rec = recordings[0]
                # Construct: https://api.twilio.com + uri + .mp3
                # rec.uri typically looks like "/2010-04-01/Accounts/AC.../Recordings/RE..."
                base_uri = rec.uri.replace(".json", "") # Ensure we don't double extension
                target_recording_url = f"https://api.twilio.com{base_uri}.mp3"
                break
        except Exception:
            continue
            
    if not target_recording_url:
        return None, "Found calls, but no recordings found."

    # 4. Download the Audio
    try:
        # We must authorize the download request itself
        response = requests.get(target_recording_url, auth=(account_sid, auth_token))
        if response.status_code != 200:
            return None, f"Failed to download audio. Status: {response.status_code}"
    except Exception as e:
        return None, f"Download Exception: {e}"

    # 5. Save to a temporary file for OpenAI
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"temp_story_{int(time.time())}.mp3")
    
    try:
        with open(temp_path, "wb") as f:
            f.write(response.content)

        # 6. Transcribe
        client_ai = get_openai_client()
        if not client_ai:
             return None, "OpenAI Client failed."

        with open(temp_path, "rb") as audio_file:
            transcript = client_ai.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file,
                response_format="text"
            )
        
        return transcript, None

    except Exception as e:
        return None, f"Transcription failed: {e}"
        
    finally:
        # Cleanup temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)