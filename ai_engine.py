import os
import logging
import openai
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
# 📞 B2B TELEPHONY (UPDATED)
# ==========================================

def trigger_outbound_call(to_phone, advisor_name, firm_name, project_id, question_text=None):
    """
    Triggers a Twilio call with a dynamic B2B script.
    NOW SUPPORTS: Custom Question Text & Neural Voice.
    """
    sid = get_secret("twilio.account_sid")
    token = get_secret("twilio.auth_token")
    from_number = get_secret("twilio.from_number") or "+16156567667"

    if not sid or not token:
        logger.error("Twilio Credentials Missing")
        return None, "Missing Credentials"

    # Default fallback if no question provided
    if not question_text:
        question_text = "Please share a favorite memory from your childhood."

    # Sanitize inputs
    safe_advisor = advisor_name or "your financial advisor"
    safe_firm = firm_name or "their firm"

    # --- FIX 1: NATURAL SCRIPT (NO REPETITION + BEEP PAUSE) ---
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
            Please take a moment to think. Then, record your answer after the beep. When you are finished, simply hang up or press the pound key.
        </Say>
        <Pause length="1"/>
        <Record maxLength="600" finishOnKey="#" playBeep="true" />
        <Say voice="Polly.Joanna-Neural">Thank you. Your story has been saved to the archive. Goodbye.</Say>
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

# --- NEW: SYNC LOGIC (POLLING) ---

def find_and_transcribe_recording(call_sid):
    """
    Looks for a completed recording for the given SID.
    If found, transcribes it and returns the text and URL.
    """
    sid = get_secret("twilio.account_sid")
    token = get_secret("twilio.auth_token")
    if not sid or not token: return None, None

    try:
        from twilio.rest import Client
        client = Client(sid, token)
        
        # 1. Fetch recordings for this Call SID
        recordings = client.recordings.list(call_sid=call_sid, limit=1)
        
        if not recordings:
            return None, None
            
        rec = recordings[0]
        # Twilio URIs are usually .json, strip to get base
        # Construct .mp3 URL
        mp3_url = f"https://api.twilio.com{rec.uri[:-5]}.mp3"
        
        # 2. Transcribe (if we haven't already - assuming we call this only when needed)
        # Note: We need to download the bytes to send to OpenAI
        import requests
        import tempfile
        
        # Download Audio
        resp = requests.get(mp3_url)
        if resp.status_code != 200: return None, None
        
        transcript_text = "Transcription Failed."
        
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp.write(resp.content)
            tmp.flush()
            
            # Send to Whisper
            ai_client = get_openai_client()
            if ai_client:
                try:
                    with open(tmp.name, "rb") as audio_file:
                        res = ai_client.audio.transcriptions.create(model="whisper-1", file=audio_file)
                        transcript_text = res.text
                except Exception as e:
                    logger.error(f"Whisper Error: {e}")
            
            os.unlink(tmp.name)
            
        return transcript_text, mp3_url

    except Exception as e:
        logger.error(f"Sync Logic Error: {e}")
        return None, None

# ==========================================
# 📝 TRANSCRIPTION & POLISH
# ==========================================

def transcribe_audio(file_path):
    client = get_openai_client()
    if not client: return None
    try:
        with open(file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )
        return transcript.text
    except Exception as e:
        logger.error(f"Transcription Error: {e}")
        return None

def refine_text(text):
    client = get_openai_client()
    if not client: return text
    
    # 1. GPT-4 Light Polish
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a helpful transcriber. Lightly edit this text only to fix grammar and remove filler words (ums, ahs). Do not change the speaker's tone or vocabulary."
                },
                {"role": "user", "content": text}
            ]
        )
        polished_text = response.choices[0].message.content
    except Exception as e:
        logger.error(f"Refine Error: {e}")
        polished_text = text

    # 2. Hardcoded Corrections (The Safety Net)
    # This catches the Whisper errors that GPT-4 might miss.
    replacements = {
        "Lubana": "Robbana",
        "lubana": "Robbana",
        "Lubana and Associates": "Robbana and Associates",
    }
    
    for wrong, right in replacements.items():
        polished_text = polished_text.replace(wrong, right)
        
    return polished_text

def get_all_twilio_recordings(limit=50):
    sid = get_secret("twilio.account_sid")
    token = get_secret("twilio.auth_token")
    if not sid or not token: return []

    try:
        from twilio.rest import Client
        client = Client(sid, token)
        recordings = client.recordings.list(limit=limit)
        data = []
        for r in recordings:
            data.append({
                "sid": r.sid,
                "date_created": r.date_created,
                "duration": r.duration,
                "status": r.status,
                "uri": r.uri 
            })
        return data
    except Exception as e:
        logger.error(f"Twilio Fetch Error: {e}")
        return []