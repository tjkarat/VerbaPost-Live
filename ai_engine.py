import os
import logging
import openai
import requests
import time
from datetime import datetime
from xml.sax.saxutils import escape as _xml_escape

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
    if not api_key: 
        logger.warning("⚠️ OpenAI API Key is missing. Transcription will be skipped.")
        return None
    return openai.OpenAI(api_key=api_key)

# ==========================================
# 📞 B2B TELEPHONY
# ==========================================

# ============================================================
# In-call review ("press 1 to send, press 2 to record again")
# ============================================================
# Both call scripts record with <Record action=...>. When the recording ends
# Twilio POSTs that URL and CONTINUES the call with whatever TwiML we return —
# that is the hook we use to play the take back and offer a redo.
#
# Note the recordingStatusCallback carries mode=safety. Every take fires that
# callback, including discarded ones, so it must not process anything; it only
# logs the recording for admin recovery. The action callback is the single
# place that decides which take becomes the letter.

VOICE = "Polly.Joanna-Neural"
MAX_TAKES = 3                    # first take + up to two redos

# Spoken once in the intro so the option is known BEFORE they start talking.
REDO_PROMISE = ("When you are finished, press the pound key. "
                "You will then hear your story back, and you can record it "
                "again if you would like to.")


def callback_base():
    return (get_secret("WEBHOOK_BASE_URL") or get_secret("BASE_URL")
            or "https://app.verbapost.com").rstrip("/")


def record_block(kind, ref_id, take=1, max_seconds=600):
    """The <Record> verb, wired to the review endpoint. Shared by the initial
    call scripts and by the redo TwiML returned mid-call."""
    base = callback_base()
    # &amp; — these land inside XML attributes, where a bare & is a parse error
    # and Twilio rejects the whole document.
    action = (f"{base}/webhooks/twilio/review"
              f"?kind={kind}&amp;ref={ref_id}&amp;take={take}&amp;max={max_seconds}")
    safety = f"{base}/webhooks/twilio/recording?mode=safety"
    return (f'<Record maxLength="{max_seconds}" finishOnKey="#" playBeep="true" '
            f'action="{action}" method="POST" '
            f'recordingStatusCallback="{safety}" recordingStatusCallbackMethod="POST" />')


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

    # 🔒 XML-escape every value interpolated into the TwiML below. These come
    # from user input (the heir's interview question) and must never be able to
    # inject TwiML verbs like <Dial> — otherwise an attacker could redirect the
    # call or dial premium/international numbers billed to our Twilio account.
    question_text = _xml_escape(question_text)
    safe_advisor = _xml_escape(advisor_name or "your financial advisor")

    # NEW (Phase 1): tell Twilio to POST to our webhook the moment the
    # recording is ready, instead of us polling "Check for New Stories".
    # WEBHOOK_BASE_URL points at the FastAPI service (staging/new stack);
    # falls back to BASE_URL, then prod domain.
    callback_base = (get_secret("WEBHOOK_BASE_URL") or get_secret("BASE_URL")
                     or "https://app.verbapost.com").rstrip("/")
    recording_callback = f"{callback_base}/webhooks/twilio/recording"
    record_verb = record_block("heirloom", project_id, take=1, max_seconds=600)

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
            {REDO_PROMISE}
        </Say>
        <Pause length="1"/>
        {record_verb}
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
        base_uri = rec.uri.replace(".json", "")
        audio_url = f"https://api.twilio.com{base_uri}.mp3"
        
        # 2. Download Audio to Temp File
        response = requests.get(audio_url, auth=(sid, token))
        
        transcript_text = "[Audio captured. Transcription unavailable.]"

        if response.status_code == 200:
            filename = f"temp_{call_sid}.mp3"
            with open(filename, 'wb') as f:
                f.write(response.content)
            
            # 3. Transcribe (Robust)
            try:
                result = transcribe_audio(filename)
                if result:
                    transcript_text = result
            except Exception as e:
                logger.error(f"Transcription Failed (but audio saved): {e}")

            # 4. Cleanup
            try:
                os.remove(filename)
            except: pass
            
            # Return Text (even if placeholder) and the URL
            return transcript_text, audio_url
            
        return None, None

    except Exception as e:
        logger.error(f"Find/Transcribe Error: {e}")
        return None, None

def transcribe_audio(file_path):
    """
    Sends audio file to OpenAI Whisper.
    Returns None if client is missing (handled by caller).
    """
    client = get_openai_client()
    if not client: 
        return None # Caller will use fallback text

    try:
        with open(file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
        return transcript.text
    except Exception as e:
        logger.error(f"OpenAI API Error: {e}")
        return None

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
            # Normalize URI to .mp3 for display
            clean_uri = r.uri.replace(".json", "") + ".mp3"
            results.append({
                "sid": r.call_sid,
                "date_created": r.date_created,
                "duration": r.duration,
                "uri": clean_uri 
            })
        return results
    except Exception as e:
        logger.error(f"Twilio Fetch Error: {e}")
        return []

def fetch_recording_audio(partial_uri):
    """
    NEW: Downloads the raw audio bytes from Twilio using backend secrets.
    This prevents the browser from prompting the user for a login.
    """
    sid = get_secret("twilio.account_sid")
    token = get_secret("twilio.auth_token")
    
    if not sid or not token: 
        return None

    # Construct clean URL
    # partial_uri usually looks like: /2010-04-01/Accounts/.../Recordings/....mp3
    if not partial_uri.endswith(".mp3"):
        partial_uri = partial_uri.replace(".json", "") + ".mp3"
        
    url = f"https://api.twilio.com{partial_uri}"
    
    try:
        # Perform authenticated request on the SERVER side
        response = requests.get(url, auth=(sid, token))
        if response.status_code == 200:
            return response.content
    except Exception as e:
        logger.error(f"Audio Fetch Error: {e}")
        
    return None

def delete_recording(recording_url):
    """Delete a recording at Twilio. Used by the retention job — clearing our
    own pointer leaves the media sitting in the Twilio account, which is not
    what the Terms promise. Returns True on success (or if it is already gone).
    """
    sid = get_secret("twilio.account_sid")
    token = get_secret("twilio.auth_token")
    if not sid or not token:
        logger.error("Cannot delete recording: Twilio credentials missing")
        return False

    from urllib.parse import urlparse
    path = urlparse(recording_url or "").path
    for suffix in (".mp3", ".wav", ".json"):
        if path.endswith(suffix):
            path = path[: -len(suffix)]
    if "/Recordings/" not in path:
        logger.error(f"Not a recording URL, refusing to delete: {recording_url}")
        return False

    try:
        resp = requests.delete(f"https://api.twilio.com{path}", auth=(sid, token), timeout=30)
        if resp.status_code in (204, 404):        # 404: already deleted
            return True
        logger.error(f"Twilio delete failed ({resp.status_code}) for {path}")
    except Exception:
        logger.exception(f"Twilio delete error for {path}")
    return False


# ==========================================
# 📞 PROSPECT ACQUISITION CALL (advisor-branded free letter)
# ==========================================

PROSPECT_CALL_TIMEOUT_SECONDS = 20   # stop ringing before most voicemails pick up
PROSPECT_MAX_RECORD_SECONDS = 600


def trigger_prospect_call(to_phone, prospect_name, advisor_name, firm_name,
                          recipient_name, question_text=None, letter_id=None):
    """
    Outbound call to a PROSPECT who asked (with express written consent) to
    record a story for someone they named. Same Twilio plumbing as
    trigger_outbound_call; different script — the prospect is the storyteller,
    the call is a gift from the advisor, and recording is disclosed up front.
    Returns (call_sid, None) or (None, error).
    """
    sid = get_secret("twilio.account_sid")
    token = get_secret("twilio.auth_token")
    from_number = get_secret("twilio.from_number") or "+16156567667"

    if not sid or not token:
        logger.error("Twilio Credentials Missing")
        return None, "Missing Credentials"

    if not question_text:
        question_text = (f"Tell {recipient_name} about a memory you hope they will "
                         "carry with them for the rest of their life.")

    # 🔒 XML-escape everything interpolated into TwiML (prospect-supplied
    # names could otherwise inject <Dial> or <Redirect>).
    safe_q = _xml_escape(question_text)
    safe_prospect = _xml_escape((prospect_name or "").split(" ")[0] or "there")
    safe_advisor = _xml_escape(advisor_name or "your financial advisor")
    safe_firm = _xml_escape(firm_name or "")
    safe_recipient = _xml_escape(recipient_name or "your loved one")
    firm_clause = f" at {safe_firm}" if safe_firm else ""

    callback_base = (get_secret("WEBHOOK_BASE_URL") or get_secret("BASE_URL")
                     or "https://app.verbapost.com").rstrip("/")
    recording_callback = f"{callback_base}/webhooks/twilio/recording"
    record_verb = record_block("prospect", letter_id or 0, take=1,
                               max_seconds=PROSPECT_MAX_RECORD_SECONDS)

    twiml = f"""
    <Response>
        <Pause length="1"/>
        <Say voice="Polly.Joanna-Neural">
            Hello {safe_prospect}. This is the VerbaPost biographer, calling because you asked us to,
            on behalf of {safe_advisor}{firm_clause}.
        </Say>
        <Pause length="1"/>
        <Say voice="Polly.Joanna-Neural">
            This call is being recorded, so that your story can be printed as a letter and mailed to {safe_recipient}.
            If you would rather not continue, simply hang up now.
        </Say>
        <Pause length="1"/>
        <Say voice="Polly.Joanna-Neural">
            Here is your question: {safe_q}
        </Say>
        <Pause length="2"/>
        <Say voice="Polly.Joanna-Neural">
            Take a moment to think. Then speak after the beep. You have up to ten minutes.
            {REDO_PROMISE}
        </Say>
        <Pause length="1"/>
        {record_verb}
        <Say voice="Polly.Joanna-Neural">
            Thank you. Your letter for {safe_recipient} will be printed and mailed, with the compliments of {safe_advisor}. Goodbye.
        </Say>
    </Response>
    """

    try:
        from twilio.rest import Client
        client = Client(sid, token)
        call = client.calls.create(
            twiml=twiml,
            to=to_phone,
            from_=from_number,
            timeout=PROSPECT_CALL_TIMEOUT_SECONDS,
        )
        return call.sid, None
    except Exception as e:
        logger.error(f"Twilio Error (prospect): {e}")
        return None, str(e)
