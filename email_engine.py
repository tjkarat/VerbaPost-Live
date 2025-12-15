import streamlit as st
import logging
import os
import requests
import json

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- ROBUST SECRETS FETCHER ---
def get_api_key():
    """Retrieves the API key from Env Vars or Secrets."""
    # 1. Try Environment Variable (Prod)
    key = os.environ.get("RESEND_API_KEY") or os.environ.get("email_password")
    if key: return key
    
    # 2. Try Streamlit Secrets (QA)
    try:
        if "resend" in st.secrets:
            return st.secrets["resend"]["api_key"]
        if "email" in st.secrets:
            return st.secrets["email"]["password"]
    except:
        pass
    
    return None

def send_confirmation(to_email, tracking_number, tier="Standard", order_id=None):
    """
    Sends a transaction receipt using direct HTTP requests (No SDK required).
    """
    api_key = get_api_key()
    
    if not api_key:
        logger.error("❌ Email Failed: API Key missing in environment or secrets.")
        return False

    if not to_email or "@" not in to_email:
        logger.warning(f"⚠️ Invalid email address: {to_email}")
        return False

    # --- EMAIL CONTENT ---
    subject = f"VerbaPost: {tier} Letter Dispatched"
    
    track_block = ""
    if tracking_number:
        track_block = f"""
        <div style="background:#f4f4f4; padding:15px; margin:20px 0; border-radius:5px;">
            <strong>Tracking Number:</strong><br>
            <span style="font-family:monospace; color:#d93025; font-size:16px; letter-spacing:1px;">{tracking_number}</span>
        </div>"""
    else:
        track_block = f"<p>Order ID: {order_id}</p>"

    html_content = f"""
    <div style="font-family:sans-serif; color:#333; max-width:600px; margin:0 auto;">
        <h2 style="color:#d93025;">Letter Sent! 📮</h2>
        <p>Your <strong>{tier}</strong> letter has been securely generated and is entering the mail stream.</p>
        {track_block}
        <p>If you have any questions, simply reply to this email.</p>
        <hr style="border:0; border-top:1px solid #eee; margin:20px 0;">
        <p style="color:#999; font-size:12px;">Thank you for using VerbaPost.</p>
    </div>
    """

    # --- DIRECT API CALL ---
    url = "https://api.resend.com/emails"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "from": "VerbaPost <onboarding@resend.dev>",
        "to": [to_email],
        "subject": subject,
        "html": html_content
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        if response.status_code in [200, 201, 202]:
            logger.info(f"✅ Email Sent to {to_email}. ID: {response.json().get('id')}")
            return True
        else:
            logger.error(f"❌ Resend API Error {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Email Exception: {e}")
        return False