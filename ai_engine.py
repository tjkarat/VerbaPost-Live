import os
import logging
import openai
import requests
import time
from datetime import datetime

# --- IMPORTS ---
try: import secrets_manager
except ImportError: secrets_manager = None

logger = logging.getLogger(__name__)

# --- CONFIG ---
def get_secret(key):
    if secrets_manager: return secrets_manager.get_secret(key)
    val = os.environ.get(key)
    if not val: val = os.environ.get(key.upper())
    return val

def get_openai_client():
    api_key = get_secret("openai.api_key")
    if not api_key: return None
    return openai.OpenAI(api_key=api_key)

# ==========================================
# 📞 B2B TELEPHONY
# ==========================================

def trigger_outbound_call(to_phone, advisor_name, firm_name, project_id, question_text=None):
    """
    Triggers a Twilio call with a dynamic B2B script.
    """
    sid = get_secret("twilio.account_sid")
    token = get_secret("twilio.auth_token")
    from_number = get_secret("twilio.from_number") or "+16156567667"

    if not sid or not token:
        logger.error("Twilio Credentials Missing")
        return None, "Missing Credentials"

    if not question_text:
        question_text = "Please share a favorite memory from your childhood."

    safe_advisor = advisor_name or "your financial advisor"

    twiml = f"""
    <Response>
        <Pause length="1"/>
        <Say voice="Polly.Joanna-Neural">
            Hello. This is the VerbaPost personal biographer calling for a scheduled interview sponsored by {safe_advisor}.
        </Say>
        <Pause length="1"/>
        <Say voice="Polly.Joanna-Neural">
            I am here to capture a specific story for your family archive. Here is your question:
        </Say>
        <Pause length="1"/>
        <Say voice="Polly.Joanna-Neural">
            {question_text}
        </Say>
        <Pause length="2"/>
        <Say voice="Polly.Joanna-Neural">
            Please take a moment to think. Then, record your answer after the beep.
        </Say>
        <Pause length="1"/>
        <Record maxLength="600" finishOnKey="#" playBeep="true" />
        <Say voice="Polly.Joanna-Neural">Thank you. Goodbye.</Say>
    </Response>
    """

    try:
        from twilio.rest import Client
        client = Client(sid, token)
        call = client.calls.create(
            twiml=twiml,
            to=to_phone,
            from_=from_number
        )
        return call.sid, None
    except Exception as e:
        logger.error(f"Twilio Error: {e}")
        return None, str(e)

def find_and_transcribe_recording(call_sid):
    """
    Connects to Twilio, checks if a recording exists for the SID,
    downloads it, and transcribes it.
    """
    sid = get_secret("twilio.account_sid")
    token = get_secret("twilio.auth_token")
    
    if not sid or not token: return None, None
    
    try:
        from twilio.rest import Client
        client = Client(sid, token)
        
        # 1. Fetch Recordings for this Call
        recordings = client.recordings.list(call_sid=call_sid, limit=1)
        
        if not recordings:
            return None, None
            
        rec = recordings[0]
        # Construct MP3 URL (Twilio usually returns .json by default in uri)
        # We strip .json and add .mp3
        base_uri = rec.uri.replace(".json", "")
        audio_url = f"https://api.twilio.com{base_uri}.mp3"
        
        # 2. Download Audio to Temp File
        # We need to authenticate the download request manually
        response = requests.get(audio_url, auth=(sid, token))
        
        if response.status_code == 200:
            filename = f"temp_{call_sid}.mp3"
            with open(filename, 'wb') as f:
                f.write(response.content)
            
            # 3. Transcribe
            transcript_text = transcribe_audio(filename)
            
            # 4. Cleanup
            try:
                os.remove(filename)
            except: pass
            
            # Return Text and the Public URL (or Twilio URL)
            return transcript_text, audio_url
            
        return None, None

    except Exception as e:
        logger.error(f"Find/Transcribe Error: {e}")
        return None, None

def transcribe_audio(file_path):
    client = get_openai_client()
    if not client: return None
    try:
        with open(file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
        return transcript.text
    except Exception as e:
        logger.error(f"Transcription Error: {e}")
        return "Audio recorded (Transcription failed)."

def refine_text(text):
    client = get_openai_client()
    if not client: return text
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful transcriber. Lightly edit this text only to fix grammar and remove filler words like 'um' or 'uh'. Do not change the meaning."},
                {"role": "user", "content": text}
            ]
        )
        polished_text = response.choices[0].message.content
        return polished_text
    except Exception as e:
        return text

def get_all_twilio_recordings(limit=50):
    """
    Fetches recent calls for the Admin Ghost Scanner.
    """
    sid = get_secret("twilio.account_sid")
    token = get_secret("twilio.auth_token")
    if not sid or not token: return []
    
    try:
        from twilio.rest import Client
        client = Client(sid, token)
        recordings = client.recordings.list(limit=limit)
        
        results = []
        for r in recordings:
            results.append({
                "sid": r.call_sid,
                "date_created": r.date_created,
                "duration": r.duration,
                "uri": r.uri.replace(".json", ".mp3")
            })
        return results
    except Exception as e:
        logger.error(f"Twilio Fetch Error: {e}")
        return []