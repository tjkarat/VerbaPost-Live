import streamlit as st
import resend
import logging

logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
API_KEY = None
try:
    # Check all possible secret locations
    if "resend" in st.secrets:
        API_KEY = st.secrets["resend"]["api_key"]
    elif "email" in st.secrets:
        API_KEY = st.secrets["email"]["password"]
        
    if API_KEY:
        resend.api_key = API_KEY
    else:
        print("⚠️ WARNING: No 'resend.api_key' found in secrets.toml")
except Exception as e:
    logger.error(f"Resend Config Error: {e}")

def send_confirmation(to_email, tracking_number, tier="Standard", order_id=None):
    """
    Sends a transaction receipt with tracking.
    """
    if not API_KEY:
        print("❌ Email Failed: API Key missing")
        return False

    subject = f"VerbaPost: {tier} Letter Dispatched"
    
    # Tracking Block
    track_block = ""
    if tracking_number:
        track_block = f"""
        <div style="background:#f4f4f4; padding:15px; margin:20px 0;">
            <strong>Tracking Number:</strong><br>
            <span style="font-family:monospace; color:#d93025; font-size:16px;">{tracking_number}</span>
        </div>"""
    else:
        track_block = f"<p>Order ID: {order_id}</p>"

    html = f"""
    <div style="font-family:sans-serif; color:#333;">
        <h2>Letter Sent! 📮</h2>
        <p>Your <strong>{tier}</strong> letter is on its way.</p>
        {track_block}
        <p><small>Thank you for using VerbaPost.</small></p>
    </div>
    """

    try:
        r = resend.Emails.send({
            "from": "VerbaPost <onboarding@resend.dev>", # DEFAULT TEST SENDER
            "to": to_email,
            "subject": subject,
            "html": html
        })
        print(f"✅ Email Sent to {to_email}: {r}")
        return True
    except Exception as e:
        # This will show up in your Streamlit logs now
        print(f"❌ Email API Error: {e}")
        return False