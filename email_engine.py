import streamlit as st
import logging
import os

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- ROBUST IMPORT ---
try:
    import resend
except ImportError:
    resend = None
    logger.error("❌ CRITICAL: 'resend' library not found. Add it to requirements.txt")

try:
    from secrets_manager import get_secret
except ImportError:
    def get_secret(key):
        # Quick fallback if secrets_manager missing
        return os.environ.get(key.upper().replace('.', '_')) or st.secrets.get(key)

# --- CONFIGURATION ---
API_KEY = None
try:
    # 1. Try robust fetcher (Checks Env Vars first, then Secrets.toml)
    API_KEY = get_secret("email.password") or get_secret("RESEND_API_KEY")
    
    # 2. Hard fallback to Streamlit secrets
    if not API_KEY and "email" in st.secrets:
        API_KEY = st.secrets["email"]["password"]

    if API_KEY and resend:
        resend.api_key = API_KEY
        logger.info("✅ Email Engine Configured")
    else:
        logger.warning("⚠️ Email Engine Missing API Key or Library")

except Exception as e:
    logger.error(f"Resend Config Error: {e}")

def send_confirmation(to_email, tracking_number, tier="Standard", order_id=None):
    """
    Sends a transaction receipt with tracking.
    """
    if not resend:
        logger.error("❌ Cannot send email: 'resend' library missing.")
        return False

    if not API_KEY:
        logger.error("❌ Cannot send email: API Key missing.")
        return False

    if not to_email or "@" not in to_email:
        logger.warning(f"⚠️ Invalid email address: {to_email}")
        return False

    subject = f"VerbaPost: {tier} Letter Dispatched"
    
    # Tracking Block
    track_block = ""
    if tracking_number:
        track_block = f"""
        <div style="background:#f4f4f4; padding:15px; margin:20px 0; border-radius:5px;">
            <strong>Tracking Number:</strong><br>
            <span style="font-family:monospace; color:#d93025; font-size:16px; letter-spacing:1px;">{tracking_number}</span>
        </div>"""
    else:
        track_block = f"<p>Order ID: {order_id}</p>"

    html = f"""
    <div style="font-family:sans-serif; color:#333; max-width:600px; margin:0 auto;">
        <h2 style="color:#d93025;">Letter Sent! 📮</h2>
        <p>Your <strong>{tier}</strong> letter has been securely generated and is entering the mail stream.</p>
        {track_block}
        <p>If you have any questions, simply reply to this email.</p>
        <hr style="border:0; border-top:1px solid #eee; margin:20px 0;">
        <p style="color:#999; font-size:12px;">Thank you for using VerbaPost.</p>
    </div>
    """

    try:
        # NOTE: If you haven't verified a domain, you must send FROM 'onboarding@resend.dev'
        # and you can ONLY send TO the email address you signed up with.
        r = resend.Emails.send({
            "from": "VerbaPost <onboarding@resend.dev>", 
            "to": to_email,
            "subject": subject,
            "html": html
        })
        logger.info(f"✅ Email Sent to {to_email}: {r}")
        return True
    except Exception as e:
        logger.error(f"❌ Email API Error: {e}")
        return False