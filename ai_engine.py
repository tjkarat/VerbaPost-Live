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
# 📞 B2B TELEPHONY (HARDENED & DEBUGGED)
# ==========================================

def send_prep_sms(to_phone, advisor_name):
    """
    Sends a 'Warm Up' SMS so the user knows the call is coming.
    Prevents 'Spam Risk' rejection.
    """
    sid = get_secret("twilio.account_sid")
    token = get_secret("twilio.auth_token")
    # Use the verified number from your screenshot or secret
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
        return False, "Telephony module missing (ImportError)"
    except Exception as e:
        logger.error(f"SMS Error: {e}")
        return False, str(e)

def trigger_outbound_call(to_phone, advisor_name, firm_name, project_id=None):
    """
    Triggers a Twilio call with Answering Machine Detection (AMD).
    Includes Verbose Debugging for Cloud Run.
    """
    print(f"📞 DEBUG: Attempting call to {to_phone}")

    # 1. Credential Check
    sid = get_secret("twilio.account_sid")
    token = get_secret("twilio.auth_token")
    # Default matches your screenshot: +16156567667
    from_number = get_secret("twilio.from_number") or "+16156567667"

    print(f"📞 DEBUG: Credentials found? SID={bool(sid)}, Token={bool(token)}")
    print(f"📞 DEBUG: Using From Number: {from_number}")

    if not sid or not token:
        logger.error("Twilio Credentials Missing")
        print("❌ DEBUG: Missing Credentials")
        return None, "Missing Credentials"

    # 2. TwiML Generation (The "Brain" of the call)
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

    # 3. Execution & Import
    try:
        print("📞 DEBUG: Importing Twilio Client...")
        from twilio.rest import Client
        
        print("📞 DEBUG: Initializing Client...")
        client = Client(sid, token)

        print("📞 DEBUG: Sending API Request...")
        call = client.calls.create(
            twiml=twiml,
            to=to_phone,
            from_=from_number,
            # --- RED TEAM: ANSWERING MACHINE DETECTION ---
            machine_detection='DetectMessageEnd', 
            # If a machine answers, Twilio handles it (status will be 'completed' but 'AnsweredBy' machine)
        )
        print(f"✅ DEBUG: Call Success! SID: {call.sid}")
        return call.sid, None

    except ImportError:
        print("❌ DEBUG: Twilio Library NOT installed in environment.")
        return None, "Telephony module missing (ImportError)"
    except Exception as e:
        print(f"❌ DEBUG: Twilio API Failure: {e}")
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