# Optional Streamlit: the FastAPI backend runs without it.
try:
    import streamlit as st
except ImportError:
    class _StreamlitStub:
        secrets = {}
        def __getattr__(self, _name):
            def _noop(*args, **kwargs):
                return None
            return _noop
    st = _StreamlitStub()

import logging
import os
import requests
import json
from html import escape as _esc  # HTML-escape user/advisor values before interpolating into email bodies

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- SECRETS & CONFIG ---
def get_api_key():
    """Retrieves the API key from Env Vars or Secrets."""
    # 1. Check Env Vars (GCP/Prod)
    key = os.environ.get("RESEND_API_KEY") or os.environ.get("email_password")
    if key: return key
    
    # 2. Check Streamlit Secrets (Local/QA)
    try:
        if "resend" in st.secrets: return st.secrets["resend"]["api_key"]
        if "email" in st.secrets: return st.secrets["email"]["password"]
    except: pass
    return None

def get_admin_email():
    """Retrieves the Admin Email for notifications."""
    # 1. Check Env Vars
    env_admin = os.environ.get("ADMIN_EMAIL")
    if env_admin: return env_admin
    
    # 2. Check Secrets
    try:
        if "admin" in st.secrets:
            return st.secrets["admin"]["email"]
    except: pass
    return None

def get_sender_address():
    """
    Returns the configured sender. 
    Prioritizes Env Vars > Secrets > Resend Sandbox.
    """
    # 1. GCP / Production Environment Variable
    env_sender = os.environ.get("EMAIL_SENDER")
    if env_sender: return env_sender

    # 2. Streamlit Secrets (Local / Cloud)
    try:
        if "email" in st.secrets and "sender" in st.secrets["email"]:
            return st.secrets["email"]["sender"]
    except: pass
    
    # 3. Fallback (Only use if config is missing)
    logger.warning("⚠️ No EMAIL_SENDER configured. Using Resend Sandbox.")
    return "VerbaPost Archives <onboarding@resend.dev>"

# --- CORE SEND FUNCTION ---
def send_email(to_email, subject, html_content):
    """
    Generic wrapper to send emails via Resend.
    """
    api_key = get_api_key()
    sender = get_sender_address()
    
    if not api_key:
        logger.error("❌ Email Failed: API Key missing.")
        return False

    if not to_email or "@" not in to_email:
        logger.warning(f"⚠️ Invalid email: {to_email}")
        return False

    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "from": sender, 
        "to": [to_email],
        "subject": subject,
        "html": html_content
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        if response.status_code in [200, 201, 202]:
            logger.info(f"✅ Email Sent to {to_email} from {sender}")
            return True
        else:
            logger.error(f"❌ Resend API Error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Email Exception: {e}")
        return False

# --- INTERVIEW PREP EMAIL ---
def send_interview_prep_email(to_email, advisor_name, question_text):
    """
    Sends a prep email to the interviewee so they know what to say.
    """
    # Subject carries the actual question so the storyteller can start
    # thinking about their answer from the inbox itself.
    _q = (question_text or "").strip().rstrip(".?!")
    subject = f'Your upcoming interview: "{_q[:70]}"' if _q else "Prep for your upcoming legacy interview"

    # 🔒 Escape user/advisor-controlled values before they enter the HTML body.
    advisor_name = _esc(advisor_name or "")
    question_text = _esc(question_text or "")

    # Simple, elegant HTML styling
    html_content = f"""
    <div style="font-family: 'Times New Roman', serif; color: #333; max-width: 600px; padding: 20px; border: 1px solid #eee;">
        <h2 style="color: #2c3e50; text-align: center; border-bottom: 1px solid #ccc; padding-bottom: 10px;">THE FAMILY LEGACY ARCHIVE</h2>
        <p>Hello,</p>
        <p><strong>{advisor_name}</strong> has sponsored a legacy preservation session to capture your story.</p>
        <p>You will receive a phone call shortly from <strong>(615) 656-7667</strong>. When you answer, our automated biographer will ask you to record your answer to the following question:</p>
        
        <div style="background-color: #f8f9fa; padding: 20px; border-left: 5px solid #d4af37; margin: 25px 0;">
            <h3 style="margin-top: 0; color: #d4af37; font-family: sans-serif; font-size: 14px; text-transform: uppercase;">Your Interview Question</h3>
            <p style="font-size: 20px; font-style: italic; margin-bottom: 0;">"{question_text}"</p>
        </div>
        
        <p>Please take a moment to collect your thoughts. There is no time limit, but we recommend a story length of about <strong>3 to 5 minutes</strong>.</p>
        <p style="margin-top: 30px;">Warmly,<br>The VerbaPost Archives</p>
    </div>
    """
    
    return send_email(to_email, subject, html_content)

# --- ADMIN ALERTS ---
def send_admin_alert(trigger_event, details_html):
    """
    Sends an alert to the Admin when a manual action is needed.
    """
    admin_email = get_admin_email()
    if not admin_email: return False

    # details_html is trusted (built internally); trigger_event may carry input.
    trigger_event = _esc(trigger_event or "")
    subject = f"🔔 ACTION REQUIRED: {trigger_event}"
    html = f"""
    <div style="font-family:sans-serif; border:1px solid #d93025; padding:20px;">
        <h2 style="color:#d93025; margin-top:0;">Manual Fulfillment Required</h2>
        <p><strong>Event:</strong> {trigger_event}</p>
        <hr>
        {details_html}
        <hr>
        <p>Login to Admin Console to print.</p>
    </div>
    """
    return send_email(admin_email, subject, html)

# --- HEIR WELCOME EMAIL (THE TRIGGER) ---
def send_heir_welcome_email(to_email, advisor_firm, advisor_name, heir_name=None):
    """
    Notifies the Heir that their Advisor has commissioned a legacy archive.
    Tone: engraved invitation — formal, restrained, private-bank register.
    """
    base_url = os.environ.get("BASE_URL", "https://app.verbapost.com").rstrip("/")

    # Subject is a plain-text header — use the raw firm name here.
    subject = f"{advisor_firm or ''} — An Invitation to Your Family Legacy Archive"

    # 🔒 Escape user/advisor-controlled values before they enter the HTML body.
    advisor_firm = _esc(advisor_firm or "")
    advisor_name = _esc(advisor_name or "")
    heir_name = _esc(heir_name) if heir_name else None

    salutation = f"Dear {heir_name}," if heir_name else "Dear Recipient,"

    html_content = f"""
    <div style="background-color:#f4f2ee; padding:40px 16px; font-family: Georgia, 'Times New Roman', serif;">
      <div style="max-width:560px; margin:0 auto; background:#ffffff; border:1px solid #d9d4c9;">
        <div style="border-bottom:3px double #0f172a; padding:36px 48px 28px; text-align:center;">
          <div style="font-size:11px; letter-spacing:4px; color:#8a7a5c; font-family: Helvetica, Arial, sans-serif; margin-bottom:14px;">BY PRIVATE ARRANGEMENT</div>
          <div style="font-size:22px; letter-spacing:3px; color:#0f172a; font-weight:bold;">THE FAMILY LEGACY ARCHIVE</div>
        </div>

        <div style="padding:40px 48px; color:#1a2332; font-size:16px; line-height:1.8;">
          <p style="margin:0 0 24px;">{salutation}</p>

          <p style="margin:0 0 24px;">On behalf of <strong>{advisor_firm}</strong>, we are honored to inform you
          that <strong>{advisor_name}</strong> has commissioned a private legacy archive for your family.</p>

          <p style="margin:0 0 24px;">Our biographers will record your family's most important stories in their
          teller's own voice — then transcribe, typeset, and preserve them as a keepsake letter, composed on
          archival linen and delivered by post.</p>

          <p style="margin:0 0 32px;">Your archive has been reserved under this email address.</p>

          <div style="text-align:center; margin:0 0 32px;">
            <a href="{base_url}/login"
               style="display:inline-block; background-color:#0f172a; color:#ffffff; padding:16px 44px;
                      text-decoration:none; font-family: Helvetica, Arial, sans-serif; font-size:12px;
                      letter-spacing:3px;">ENTER THE ARCHIVE</a>
          </div>

          <p style="margin:0 0 6px;">We remain at your service,</p>
          <p style="margin:0; font-style:italic;">The VerbaPost Archives</p>
        </div>

        <div style="border-top:1px solid #d9d4c9; padding:20px 48px; text-align:center;">
          <div style="font-size:11px; letter-spacing:2px; color:#8a7a5c; font-family: Helvetica, Arial, sans-serif;">
            PRESENTED IN PARTNERSHIP WITH {advisor_firm.upper()}
          </div>
          <div style="font-size:10px; color:#a39a88; font-family: Helvetica, Arial, sans-serif; margin-top:8px;">
            VerbaPost Inc. &nbsp;·&nbsp; Nashville, Tennessee
          </div>
        </div>
      </div>
    </div>
    """
    return send_email(to_email, subject, html_content)

# --- ADVISOR ALERT: HEIR STARTED STORY ---
def send_advisor_heir_started_alert(advisor_email, heir_name, client_name):
    """
    Notifies the Advisor that their client has logged in and started a story.
    """
    # 🔒 Escape user-controlled values before they enter the HTML body.
    heir_name = _esc(heir_name or "")
    client_name = _esc(client_name or "")
    subject = f"🔔 Activity Alert: {heir_name} started a story"
    html_content = f"""
    <div style="font-family: sans-serif; color: #333; max-width: 600px; padding: 20px; border: 1px solid #e2e8f0;">
        <h3 style="color: #166534;">Client Activity Detected</h3>
        <p>Great news! The legacy project for the <strong>{client_name}</strong> family is active.</p>
        <p><strong>{heir_name}</strong> just initiated an interview call to record a new story.</p>
        <p>You will be notified again when the audio is ready for your review.</p>
        <hr>
        <p style="font-size: 12px; color: #64748b;">VerbaPost Advisor Notifications</p>
    </div>
    """
    return send_email(advisor_email, subject, html_content)

# --- ADMIN ALERT: STORY READY TO PRINT ---
def send_admin_print_ready_alert(user_email, draft_id, content_preview, mailing_list=None):
    """
    Notifies Admin that a story has been created/approved and is ready to print.
    mailing_list: list of dicts {name, street, city, state, zip_code} —
    every address that should receive a printed copy (heir + extras).
    """
    admin_email = get_admin_email()
    if not admin_email: return False

    # 🔒 Escape user-controlled values before they enter the HTML body.
    user_email = _esc(user_email or "")
    content_preview = _esc(content_preview or "")

    addresses_html = ""
    if mailing_list:
        rows = "".join(
            f"<li><strong>{_esc(a.get('name','') or '')}</strong> — {_esc(a.get('street','') or '')}, "
            f"{_esc(a.get('city','') or '')}, {_esc(a.get('state','') or '')} {_esc(a.get('zip_code','') or '')}</li>"
            for a in mailing_list)
        addresses_html = f"""
        <p><strong>Print &amp; mail {len(mailing_list)} cop{'ies' if len(mailing_list) != 1 else 'y'}:</strong></p>
        <ol style="background:#fffbeb; border:1px solid #fde68a; padding:14px 14px 14px 34px;">{rows}</ol>
        """

    subject = f"PRINT JOB: Draft #{draft_id} — {len(mailing_list or []) or 1} letter(s)"
    html_content = f"""
    <div style="font-family: sans-serif; border: 2px solid #0f172a; padding: 20px;">
        <h2 style="margin-top:0;">New Print Job Submitted</h2>
        <p><strong>User:</strong> {user_email}</p>
        <p><strong>Draft ID:</strong> {draft_id}</p>
        {addresses_html}
        <div style="background: #f1f5f9; padding: 10px; margin: 10px 0; font-style: italic;">
            "{content_preview[:300]}..."
        </div>
        <p>See the Admin Console for the full transcript.</p>
    </div>
    """
    return send_email(admin_email, subject, html_content)