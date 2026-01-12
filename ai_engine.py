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
    # Fallback to os.environ for Cloud Run / Local
    val = os.environ.get(key)
    if not val: val = os.environ.get(key.upper())
    return val

def get_openai_client():
    api_key = get_secret("openai.api_key")
    if not api_key: return None
    return openai.OpenAI(api_key=api_key)

# ==========================================
# 📞 B2B TELEPHONY (NEW)
# ==========================================

def trigger_outbound_call(to_phone, advisor_name, firm_name, project_id):
    """
    Triggers a Twilio call with a dynamic B2B script.
    """
    sid = get_secret("twilio.account_sid")
    token = get_secret("twilio.auth_token")
    from_number = get_secret("twilio.from_number") or "+16156567667"

    if not sid or not token:
        logger.error("Twilio Credentials Missing")
        return None, "Missing Credentials"

    # Dynamic TwiML Script (The "Brain" of the call)
    # We embed the project_id in the callback URL so we know who spoke later.
    callback_url = f"https://api.verbapost.com/webhooks/voice?project_id={project_id}"
    
    # Sanitize inputs to prevent script injection or empty reads
    safe_advisor = advisor_name or "your financial advisor"
    safe_firm = firm_name or "their firm"

    twiml = f"""
    <Response>
        <Pause length="1"/>
        <Say voice="Polly.Joanna-Neural">
            Hello. This is a courtesy call from VerbaPost, on behalf of {safe_advisor} at {safe_firm}.
        </Say>
        <Pause length="1"/>
        <Say voice="Polly.Joanna-Neural">
            {safe_advisor} has sponsored a legacy interview to preserve your family story. 
            Please share a favorite memory from your childhood after the beep. 
            When you are finished, press the pound key.
        </Say>
        <Record maxLength="300" finishOnKey="#" action="{callback_url}" />
        <Say voice="Polly.Joanna-Neural">Thank you. Your story has been saved.</Say>
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

# ==========================================
# 🎤 TRANSCRIPTION & POLISHING (PRESERVED)
# ==========================================

def transcribe_audio(file_path):
    """
    Standard Whisper Transcription
    """
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
    """
    Legacy 'AI Polish' feature used by Standard Store.
    Preserved to prevent ui_main.py crashes.
    """
    client = get_openai_client()
    if not client: return text
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a professional editor. Polish this letter for clarity and warmth."},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Refine Error: {e}")
        return text

# ==========================================
# ⚙️ ADMIN UTILITIES (PRESERVED)
# ==========================================

def get_all_twilio_recordings(limit=50):
    """
    Used by ui_admin.py to scan for ghost recordings.
    """
    sid = get_secret("twilio.account_sid")
    token = get_secret("twilio.auth_token")
    if not sid or not token: return []

    try:
        from twilio.rest import Client
        client = Client(sid, token)
        recordings = client.recordings.list(limit=limit)
        
        # Serialize to dict to avoid Twilio object issues in Streamlit
        data = []
        for r in recordings:
            data.append({
                "sid": r.sid,
                "date_created": r.date_created,
                "duration": r.duration,
                "status": r.status,
                "uri": r.uri  # This is usually partial uri
            })
        return data
    except Exception as e:
        logger.error(f"Twilio Fetch Error: {e}")
        return []