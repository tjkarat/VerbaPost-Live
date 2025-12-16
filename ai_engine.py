import openai
import streamlit as st
from twilio.rest import Client
import requests
import os
import tempfile
import time

# --- CONFIGURATION ---
# We retrieve keys safely from secrets
def get_openai_client():
    try:
        api_key = st.secrets["openai"]["api_key"]
        return openai.OpenAI(api_key=api_key)
    except KeyError:
        st.error("OpenAI API Key missing in .streamlit/secrets.toml")
        return None

# --- PHASE 1: MANUAL UPLOAD TRANSCRIPTION ---

def transcribe_audio(audio_file_obj):
    """
    Transcribes an audio file object (from st.file_uploader).
    """
    client = get_openai_client()
    if not client:
        return "Error: Client not configured."

    try:
        # OpenAI requires a filename attribute to detect format (mp3/wav)
        # st.file_uploader objects have .name, but sometimes we need to be explicit.
        # We pass the file-like object directly.
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
    1. Connects to Twilio.
    2. Finds the last call from the Parent's phone number.
    3. Downloads the recording.
    4. Sends it to OpenAI.
    5. Returns the text.
    """
    # 1. Setup Twilio
    try:
        account_sid = st.secrets["twilio"]["account_sid"]
        auth_token = st.secrets["twilio"]["auth_token"]
        client = Client(account_sid, auth_token)
    except KeyError:
        return None, "Twilio secrets missing in .streamlit/secrets.toml"

    # 2. Find calls from this specific phone number
    try:
        # We look for calls 'from' the parent to our Twilio number
        # limit=5 ensures we check a few recent ones if the very last one had no recording
        calls = client.calls.list(from_=parent_phone, limit=5)
    except Exception as e:
        return None, f"Twilio Connection Error: {e}"
    
    if not calls:
        return None, "No recent calls found from this number."

    # Look for a call with a recording
    target_recording_url = None
    
    for call in calls:
        recordings = call.recordings.list()
        if recordings:
            # Twilio returns a generic JSON URL; append '.mp3' to get the raw audio file
            target_recording_url = recordings[0].media_url + ".mp3"
            break
            
    if not target_recording_url:
        return None, "Found calls, but no recordings (did she hang up too fast?)"

    # 3. Download the Audio
    try:
        response = requests.get(target_recording_url)
        if response.status_code != 200:
            return None, "Failed to download audio from Twilio."
    except Exception as e:
        return None, f"Download Error: {e}"

    # 4. Save to a temporary file 
    # (OpenAI requires a real file path or a named buffer for remote files)
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"temp_story_{int(time.time())}.mp3")
    
    with open(temp_path, "wb") as f:
        f.write(response.content)

    # 5. Transcribe
    try:
        client_ai = get_openai_client()
        if not client_ai:
             return None, "OpenAI Client failed."

        with open(temp_path, "rb") as audio_file:
            transcript = client_ai.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file,
                response_format="text"
            )
        
        # Cleanup temp file to keep server clean
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        return transcript, None

    except Exception as e:
        # Cleanup on error too
        if os.path.exists(temp_path):
            os.remove(temp_path)
        return None, f"Transcription failed: {e}"