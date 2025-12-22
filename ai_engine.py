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
    
    if not api_key and "openai" in st.secrets:
        api_key = st.secrets["openai"]["api_key"]
        
    if not api_key:
        logger.error("OpenAI API Key missing.")
        return None
        
    return openai.OpenAI(api_key=api_key)

# --- PHASE 1: AUDIO TRANSCRIPTION ---

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

# --- PHASE 2: TEXT REFINEMENT ---

def refine_text(text, style="Professional"):
    """
    Uses GPT-4o to polish the letter text.
    """
    client = get_openai_client()
    if not client: return text

    prompt_map = {
        "Professional": "Rewrite the following letter to be more professional, clear, and concise, but keep the original meaning.",
        "Grammar": "Fix all grammar, spelling, and punctuation errors in the following text. Do not change the tone.",
        "Warm": "Rewrite the following letter to sound warmer, friendlier, and more affectionate."
    }
    
    system_prompt = prompt_map.get(style, prompt_map["Professional"])

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Refine Error: {e}")
        return text

def enhance_transcription_for_seniors(text):
    """
    Lightly edits transcriptions to remove 'ums', 'ahs', and repetitive stammers.
    """
    client = get_openai_client()
    if not client: return text

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful editor. Clean up the following speech-to-text transcript. Remove filler words (um, uh, like, you know) and fix stuttering. Keep the tone natural and conversational. Do not summarize."},
                {"role": "user", "content": text}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return text

# --- PHASE 3: TWILIO INTEGRATION ---

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
def get_all_twilio_recordings(limit=50):
    """Fetches list of all recordings from Twilio."""
    # Initialization of Twilio Client using secrets_manager
    try:
        recordings = client.recordings.list(limit=limit)
        return [{
            'sid': r.sid,
            'date_created': r.date_created.strftime("%Y-%m-%d %H:%M"),
            'duration': r.duration,
            'uri': f"https://api.twilio.com{r.uri.replace('.json', '.mp3')}",
            'call_sid': r.call_sid
        } for r in recordings]
    except: return []

def delete_twilio_recording(recording_sid):
    """Permanently deletes a recording from Twilio."""
    try:
        client.recordings(recording_sid).delete()
        return True
    except: return False
    
# --- FIXED: NORMALIZATION HELPER ---
def _normalize_phone(phone_str):
    """
    Aggressively cleans phone number to E.164 format.
    Ex: (615) 555-1234 -> +16155551234
    """
    if not phone_str: return ""
    
    # Remove all non-digits
    digits = "".join(filter(str.isdigit, str(phone_str)))
    
    if not digits: return ""

    # Assuming US numbers for now if no country code
    if len(digits) == 10:
        return f"+1{digits}"
    elif len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    elif len(digits) > 11:
        # International likely already has code
        return f"+{digits}"
        
    return f"+{digits}" # Fallback

def trigger_outbound_call(to_number, from_number, parent_name="there", topic="your day"):
    """
    Triggers an outbound call with a DYNAMIC script.
    UPDATED: Uses Neural Voice (Polly.Joanna) for human sound and explicit pauses for the beep.
    """
    client = _get_twilio_client()
    if not client:
        return None, "Twilio Client Config Error"

    # FIX: Normalize numbers before calling
    clean_to = _normalize_phone(to_number)

    # UPDATED TwiML:
    # 1. voice="Polly.Joanna-Neural" is much more human.
    # 2. Explicit <Pause> before <Record> ensures the beep isn't stepped on.
    twiml_script = f"""
    <Response>
        <Pause length="1"/>
        <Say voice="Polly.Joanna-Neural">Hello! This is the Verba Post family archivist calling for {parent_name}.</Say>
        <Pause length="1"/>
        <Say voice="Polly.Joanna-Neural">Your family would like to save a new story. Here is their question.</Say>
        <Pause length="1"/>
        <Say voice="Polly.Joanna-Neural">{topic}</Say>
        <Pause length="1"/>
        <Say voice="Polly.Joanna-Neural">Please tell your story after the tone. When you are finished, press the pound key or simply hang up.</Say>
        <Pause length="1"/>
        <Record maxLength="600" finishOnKey="#" playBeep="true" trim="trim-silence"/>
        <Say voice="Polly.Joanna-Neural">Thank you. Your story has been saved safe and sound. Goodbye!</Say>
    </Response>
    """

    try:
        call = client.calls.create(
            to=clean_to,
            from_=from_number,
            twiml=twiml_script
        )
        return call.sid, None
    except Exception as e:
        return None, f"Dialing Error: {e}"

def fetch_and_transcribe_latest_call(parent_phone):
    """
    Finds the last call (Inbound OR Outbound) for a specific number.
    FIX: Now uses robust normalization and checks BOTH 'from' and 'to'.
    """
    client = _get_twilio_client()
    if not client: return None, "Twilio Config Missing"

    try:
        # FIX: Normalize user input to ensure it matches Twilio's E.164 log
        clean_phone = _normalize_phone(parent_phone)
        logger.info(f"Scanning logs for: {clean_phone}")
        
        # 1. Check calls FROM parent (Inbound to us)
        calls_in = client.calls.list(from_=clean_phone, limit=20)
        # 2. Check calls TO parent (Outbound from us)
        calls_out = client.calls.list(to=clean_phone, limit=20)
        
        # Combine and sort by date (newest first)
        all_calls = calls_in + calls_out
        all_calls.sort(key=lambda c: c.date_created, reverse=True)
        
    except Exception as e:
        return None, f"Twilio List Error: {e}"
    
    if not all_calls:
        return None, f"No calls found for {clean_phone}"

    target_recording_url = None
    
    # Iterate to find the first COMPLETED one with a recording
    for call in all_calls:
        # Skip failed/busy/no-answer calls immediately
        if call.status not in ['completed']:
            continue

        try:
            recordings = call.recordings.list()
            if recordings:
                rec = recordings[0]
                base_uri = rec.uri.replace(".json", "")
                target_recording_url = f"https://api.twilio.com{base_uri}.mp3"
                logger.info(f"Found recording at: {target_recording_url}")
                break
        except Exception:
            continue
            
    if not target_recording_url:
        return None, "Found calls, but no audio recordings."

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
    ADMIN TOOL: Fetches raw call log metadata.
    """
    client = _get_twilio_client()
    if not client: return []

    try:
        calls = client.calls.list(limit=limit)
        data = []
        for c in calls:
            from_num = getattr(c, 'from_', 'Unknown')
            to_num = getattr(c, 'to', 'Unknown')
            
            data.append({
                "from": from_num,
                "to": to_num,
                "status": c.status,
                "duration": c.duration,
                "date": c.date_created,
                "sid": c.sid
            })
        return data
    except Exception as e:
        logger.error(f"Log Fetch Error: {e}")
        return []