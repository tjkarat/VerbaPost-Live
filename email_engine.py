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
    key = os.environ.get("RESEND_API_KEY") or os.environ.get("email_password")
    if key: return key
    try:
        if "resend" in st.secrets: return st.secrets["resend"]["api_key"]
        if "email" in st.secrets: return st.secrets["email"]["password"]
    except: pass
    return None

def get_admin_email():
    """Retrieves the Admin Email for notifications."""
    try:
        # Check standard admin location
        if "admin" in st.secrets:
            return st.secrets["admin"]["email"]
    except: pass
    return os.environ.get("ADMIN_EMAIL")

def get_sender_address():
    """
    Returns the configured sender or the Resend default.
    Change 'VERIFIED_DOMAIN_EMAIL' in secrets to use your custom domain.
    """
    try:
        if "email" in st.secrets and "sender" in st.secrets["email"]:
            return st.secrets["email"]["sender"]
    except: pass
    
    # Fallback to Resend Test Domain if not configured (Ensures delivery)
    return "VerbaPost <onboarding@resend.dev>"

# --- CORE SEND FUNCTION ---
def send_email(to_email, subject, html_content):
    """
    Generic wrapper to send emails to Users.
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
            logger.info(f"✅ Email Sent to {to_email}")
            return True
        else:
            logger.error(f"❌ Resend API Error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Email Exception: {e}")
        return False

# --- NEW: ADMIN NOTIFICATION SYSTEM ---
def send_admin_alert(trigger_event, details_html):
    """
    Sends an alert to the Admin when a manual action is needed.
    """
    admin_email = get_admin_email()
    if not admin_email:
        logger.warning("⚠️ Cannot send Admin Alert: No Admin Email configured.")
        return False
        
    subject = f"🔔 ACTION REQUIRED: {trigger_event}"
    
    html = f"""
    <div style="font-family:sans-serif; border:1px solid #d93025; padding:20px;">
        <h2 style="color:#d93025; margin-top:0;">Manual Fulfillment Required</h2>
        <p><strong>Event:</strong> {trigger_event}</p>
        <hr>
        {details_html}
        <hr>
        <p>Login to <a href="https://verbapost.streamlit.app">VerbaPost Admin</a> to print.</p>
    </div>
    """
    
    return send_email(admin_email, subject, html)