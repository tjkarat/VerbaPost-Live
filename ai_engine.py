import os
import logging
import requests
import tempfile
from openai import OpenAI
from twilio.rest import Client

# --- LOGGING SETUP ---
logger = logging.getLogger(__name__)

# --- SECRETS & CONFIG ---
try: import secrets_manager
except ImportError: secrets_manager = None

def get_secret(key):
    if secrets_manager: return secrets_manager.get_secret(key)
    return os.environ.get(key) or os.environ.get(key.upper())

# --- 1. TELEPHONY (The Call) ---
def trigger_outbound_call(to_phone, advisor_name, firm_name, prompt_text=None):
    """
    Triggers a Twilio call with the SPECIFIC question from the database.
    """
    sid = get_secret("twilio.account_sid")
    token = get_secret("twilio.auth_token")
    from_number = get_secret("twilio.from_number") or "+16156567667" # Fallback

    if not sid or not token:
        return None, "Twilio Credentials Missing"

    # DEFAULT FALLBACK (Only used if database is empty)
    if not prompt_text:
        prompt_text = "Please share a favorite memory from your life that you want your family to remember."

    # TwiML Script (Latency Fix: Removed <Pause> tags)
    twiml = f"""
    <Response>
        <Say voice="Polly.Joanna-Neural">
            Hello. This is the family historian for {firm_name}.
        </Say>
        <Say voice="Polly.Joanna-Neural">
            {advisor_name} has sponsored this interview. Here is your question:
        </Say>
        <Say voice="Polly.Joanna-Neural">
            {prompt_text}
        </Say>
        <Record maxLength="600" timeout="10" playBeep="true" trim="trim-silence" />
        <Say voice="Polly.Joanna-Neural">Thank you. Your story has been saved.</Say>
    </Response>
    """

    try:
        client = Client(sid, token)
        call = client.calls.create(
            twiml=twiml,
            to=to_phone,
            from_=from_number,
            machine_detection='DetectMessageEnd'
        )
        return call.sid, None
    except Exception as e:
        logger.error(f"Twilio Error: {e}")
        return None, str(e)

# --- 2. TRANSCRIPTION (The Fetch) ---
def fetch_and_transcribe(call_sid):
    """
    1. Asks Twilio for the recording URL.
    2. Downloads the MP3.
    3. Sends to OpenAI Whisper.
    4. Returns text + audio_url.
    """
    sid = get_secret("twilio.account_sid")
    token = get_secret("twilio.auth_token")
    openai_key = get_secret("openai.api_key")
    
    if not sid or not token or not openai_key:
        return None, None, "Missing API Keys"

    try:
        client = Client(sid, token)
        
        # 1. Find Recording
        recordings = client.recordings.list(call_sid=call_sid, limit=1)
        if not recordings:
            return None, None, "No recording found yet (Call might be active)."
            
        rec = recordings[0]
        # Construct MP3 URL (Twilio creates .json by default in API, we force .mp3)
        # We assume the standard Twilio pattern: https://api.twilio.com/2010-04-01/Accounts/{AccountSid}/Recordings/{RecordingSid}.mp3
        # But grabbing it from the URI is safer if we strip the extension
        base_uri = f"https://api.twilio.com{rec.uri[:-5]}.mp3" 
        
        # 2. Download Audio
        resp = requests.get(base_uri)
        if resp.status_code != 200:
            return None, None, "Failed to download audio from Twilio."
            
        # 3. Transcribe with OpenAI
        transcript_text = ""
        openai_client = OpenAI(api_key=openai_key)
        
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp.write(resp.content)
            tmp.close()
            
            with open(tmp.name, "rb") as audio_file:
                transcript = openai_client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file
                )
                transcript_text = transcript.text
            
            os.unlink(tmp.name)

        return transcript_text, base_uri, None

    except Exception as e:
        logger.error(f"Transcribe Error: {e}")
        return None, None, str(e)

# --- 3. POLISHING (The AI Edit) ---
def refine_text(text):
    """
    GPT-4o Polish.
    """
    key = get_secret("openai.api_key")
    if not key: return text
    
    try:
        client = OpenAI(api_key=key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a professional editor. Clean up this spoken transcript. Remove 'ums', 'ahs', and stutters. Fix punctuation. Keep the tone warm and personal. Do not summarize; keep the original story intact."},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Refine Error: {e}")
        return text