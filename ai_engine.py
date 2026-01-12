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
# 📞 HYBRID MODEL TELEPHONY (UPDATED FIX)
# ==========================================

def trigger_outbound_call(to_phone, from_number=None, advisor_name=None, firm_name=None, heir_name=None, strategic_prompt=None, project_id=None, parent_name="Client", topic="your favorite memories"):
    """
    Triggers a Twilio call focusing on the Strategic Endorsement first.
    B2B FIX: Signature now accepts 'parent_name' and 'topic' to match ui_heirloom.py.
    """
    sid = get_secret("twilio.account_sid")
    token = get_secret("twilio.auth_token")
    # Fallback logic for Caller ID
    caller_id = from_number or get_secret("twilio.from_number") or "+16156567667"

    if not sid or not token:
        logger.error("Twilio Credentials Missing")
        return None, "Missing Credentials"

    # Callback includes project_id for transcription mapping if provided
    callback_url = f"https://api.verbapost.com/webhooks/voice?project_id={project_id}" if project_id else ""
    
    # Sanitization for Advisor Mode
    safe_advisor = advisor_name or "your financial advisor"
    safe_firm = firm_name or "their firm"
    safe_heir = heir_name or "your family"
    
    # Logic: If advisor info is present, use B2B script. Otherwise, use Heirloom script.
    if advisor_name:
        safe_prompt = strategic_prompt or f"Why do you trust {safe_firm} for your family's future?"
        twiml = f"""
        <Response>
            <Pause length="1"/>
            <Say voice="Polly.Joanna-Neural">
                Hello {parent_name}. This is the Family Archive biographer, calling on behalf of {safe_advisor} at {safe_firm}.
            </Say>
            <Pause length="1"/>
            <Say voice="Polly.Joanna-Neural">
                {safe_advisor} has sponsored this session as a legacy gift for {safe_heir}. 
                Before we record your personal stories, {safe_advisor} asked us to start with this question:
            </Say>
            <Pause length="1"/>
            <Say voice="Polly.Joanna-Neural">
                {safe_prompt}
            </Say>
            <Record maxLength="300" finishOnKey="#" action="{callback_url}" />
            
            <Say voice="Polly.Joanna-Neural">
                Thank you. Now, please share a favorite memory from your childhood or a piece of advice for {safe_heir} after the beep.
            </Say>
            <Record maxLength="300" finishOnKey="#" action="{callback_url}" />
            <Say voice="Polly.Joanna-Neural">Thank you. Your legacy stories have been preserved.</Say>
        </Response>
        """
    else:
        # Standard Heirloom / Family Script
        twiml = f"""
        <Response>
            <Pause length="1"/>
            <Say voice="Polly.Joanna-Neural">
                Hello {parent_name}. This is VerbaPost calling to record a story for your family archive.
            </Say>
            <Pause length="1"/>
            <Say voice="Polly.Joanna-Neural">
                Today, we would love to hear about {topic}. 
                Please share your memory after the beep. 
                When you are finished, just hang up or press the pound key.
            </Say>
            <Record maxLength="300" finishOnKey="#" />
            <Say voice="Polly.Joanna-Neural">Thank you. Your story has been saved.</Say>
        </Response>
        """

    try:
        from twilio.rest import Client
        client = Client(sid, token)

        call = client.calls.create(
            twiml=twiml,
            to=to_phone,
            from_=caller_id
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
    Legacy 'AI Polish' feature preserved for ui_main.py stability.
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