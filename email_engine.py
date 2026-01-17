import streamlit as st
import logging
import os
import requests
import json

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
    subject = f"Upcoming Legacy Interview: Prep for your call"
    
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
def send_heir_welcome_email(to_email, advisor_firm, advisor_name):
    """
    Notifies the Heir that their Advisor has sponsored a legacy project.
    """
    subject = f"Gift from {advisor_name}: The Family Legacy Project"
    
    html_content = f"""
    <div style="font-family: 'Times New Roman', serif; color: #333; max-width: 600px; padding: 20px; border: 1px solid #eee;">
        <h2 style="color: #0f172a; text-align: center; border-bottom: 1px solid #ccc; padding-bottom: 10px;">THE FAMILY LEGACY ARCHIVE</h2>
        
        <p>Hello,</p>
        
        <p><strong>{advisor_name}</strong> (from {advisor_firm}) has sponsored a private legacy archive for your family.</p>
        
        <p>This secure vault allows you to capture, preserve, and print your family's most important stories before they are lost to time.</p>
        
        <div style="background-color: #f8f9fa; padding: 15px; text-align: center; margin: 25px 0; border: 1px solid #ddd;">
            <p style="margin: 0 0 10px 0;">To access your vault, please log in below using this email address:</p>
            <a href="https://app.verbapost.com?nav=login" style="background-color: #0f172a; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; font-family: sans-serif;">Access Family Vault</a>
        </div>
        
        <p><strong>Next Step:</strong> Log in and schedule your first interview call.</p>
        
        <p style="margin-top: 30px;">Warmly,<br>The VerbaPost Archives</p>
    </div>
    """
    return send_email(to_email, subject, html_content)

# --- ADVISOR ALERT: HEIR STARTED STORY ---
def send_advisor_heir_started_alert(advisor_email, heir_name, client_name):
    """
    Notifies the Advisor that their client has logged in and started a story.
    """
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
def send_admin_print_ready_alert(user_email, draft_id, content_preview):
    """
    Notifies Admin that a story has been created/approved and is ready to print.
    """
    admin_email = get_admin_email()
    if not admin_email: return False
    
    subject = f"🖨️ PRINT JOB: Draft #{draft_id} Ready"
    html_content = f"""
    <div style="font-family: sans-serif; border: 2px solid #0f172a; padding: 20px;">
        <h2 style="margin-top:0;">New Print Job Submitted</h2>
        <p><strong>User:</strong> {user_email}</p>
        <p><strong>Draft ID:</strong> {draft_id}</p>
        <div style="background: #f1f5f9; padding: 10px; margin: 10px 0; font-style: italic;">
            "{content_preview[:100]}..."
        </div>
        <p><a href="https://app.verbapost.com?nav=login" style="font-weight: bold;">Login to Admin Console</a> to generate PDF and Envelope.</p>
    </div>
    """
    return send_email(admin_email, subject, html_content)