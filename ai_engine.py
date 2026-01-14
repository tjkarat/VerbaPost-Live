import os
import logging
import openai
import streamlit as st # Added for GUI Toast
from datetime import datetime

# ==========================================
# 🚨 BOOT VERIFICATION SIGNAL 🚨
# ==========================================
print("\n" + "="*50)
print("👉 AI ENGINE V999 (DEBUG) IS LOADING ... 👈")
print("="*50 + "\n")

# Try to verify imports immediately on boot
try:
    import twilio
    print(f"✅ BOOT CHECK: Twilio is installed. Version: {twilio.__version__}")
except ImportError as e:
    print(f"❌ BOOT CHECK: Twilio is MISSING. Error: {e}")

# ==========================================

# --- IMPORTS ---
try: import secrets_manager
except ImportError: secrets_manager = None

logger = logging.getLogger(__name__)

# --- CONFIG ---
def get_secret(key):
    """
    Retrieves secret from secrets_manager or environment variables.
    """
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
# 📞 B2B TELEPHONY (LOUD DEBUGGER)
# ==========================================

def send_prep_sms(to_phone, advisor_name):
    """
    Sends a 'Warm Up' SMS.
    """
    sid = get_secret("twilio.account_sid")
    token = get_secret("twilio.auth_token")
    from_number = get_secret("twilio.from_number") or "+16156567667"

    if not sid or not token: return False, "Missing Credentials"
    
    msg_body = f"Hello. This is the automated interview service for {advisor_name or 'your advisor'}. We will call you in about 2 minutes to record your family story. Please pick up!"

    try:
        from twilio.rest import Client
        client = Client(sid, token)
        message = client.messages.create(
            body=msg_body,
            from_=from_number,
            to=to_phone
        )
        return True, message.sid
    except ImportError:
        logger.error("Twilio Module Missing (ImportError)")
        return False, "ERROR 999: Import Failed in SMS"
    except Exception as e:
        logger.error(f"SMS Error: {e}")
        return False, str(e)

def trigger_outbound_call(to_phone, advisor_name, firm_name, project_id=None):
    """
    DEBUG VERSION: If you don't see "ERROR 999" in the UI, 
    this code is NOT running.
    """
    logger.info(f"📞 DEBUG: Starting call to {to_phone}")

    # 1. Config
    sid = get_secret("twilio.account_sid")
    token = get_secret("twilio.auth_token")
    from_number = get_secret("twilio.from_number") or "+16156567667"

    if not sid or not token:
        return None, "ERROR 999: Missing Credentials"

    # 2. TwiML
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
        <Record maxLength="300" finishOnKey="#" playBeep="true" />
        <Say voice="Polly.Joanna-Neural">Thank you. Your story has been saved. Goodbye.</Say>
    </Response>
    """

    # 3. Import & Execute (The Failure Point)
    try:
        # Check if library exists
        import importlib.util
        twilio_spec = importlib.util.find_spec("twilio")
        if twilio_spec is None:
             return None, "ERROR 999: Twilio Package NOT FOUND on Server"
        
        # Check if submodule exists
        from twilio.rest import Client
        
        # Attempt Call
        client = Client(sid, token)
        call = client.calls.create(
            twiml=twiml,
            to=to_phone,
            from_=from_number,
            # --- RED TEAM: ANSWERING MACHINE DETECTION ---
            machine_detection='DetectMessageEnd', 
        )
        return call.sid, None

    except ImportError as e:
        # THIS IS THE KEY: We print the real error 'e'
        logger.error(f"Import Failed: {e}")
        return None, f"ERROR 999: Import Failed -> {e}"
        
    except Exception as e:
        logger.error(f"API Error: {e}")
        return None, f"ERROR 999: API Error -> {e}"

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
    Legacy 'AI Polish' feature.
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
# ⚙️ ADMIN UTILITIES
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