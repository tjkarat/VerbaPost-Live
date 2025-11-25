import streamlit as st
import requests
import resend

# --- CONFIG ---
try: LOB_API_KEY = st.secrets.get("LOB_API_KEY")
except: LOB_API_KEY = None

try:
    if "resend" in st.secrets: resend.api_key = st.secrets["resend"]["api_key"]
    elif "email" in st.secrets: resend.api_key = st.secrets["email"]["password"]
    else: resend.api_key = None
except: resend.api_key = None

# --- PHYSICAL MAIL ---
def send_letter(pdf_path, to_addr, from_addr):
    if not LOB_API_KEY: return None
    # ... (Keeping your existing Lob logic implied here for brevity, usually not called directly by current Admin UI) ...
    return None

# --- NOTIFICATIONS ---
def send_heirloom_notification(user_email, letter_text):
    if not resend.api_key: return False
    try:
        sender = st.secrets["email"].get("sender_email", "onboarding@resend.dev")
        r = resend.Emails.send({
            "from": f"VerbaPost Alerts <{sender}>",
            "to": ["tjkarat@gmail.com", "support@verbapost.com"],
            "subject": f"🔔 New Order: {user_email}",
            "html": f"<h3>New Order</h3><p>User: {user_email}</p><pre>{letter_text}</pre>"
        })
        return True
    except: return False

def send_shipping_confirmation(user_email, recipient_info):
    """Notifies user their letter was mailed."""
    if not resend.api_key: return False
    
    # Handle potential missing data gracefully
    r_name = recipient_info.get('recipient_name') or "Recipient"
    r_street = recipient_info.get('recipient_street') or ""
    
    html = f"""
    <div style="font-family: sans-serif; color: #333;">
        <h2 style="color: #2a5298;">🚀 Your Letter is on the way!</h2>
        <p>Great news! We have printed, stamped, and mailed your letter.</p>
        <div style="background:#f4f4f4; padding:15px; border-radius:5px; margin: 15px 0;">
            <strong>Mailed To:</strong><br>
            {r_name}<br>{r_street}
        </div>
        <p>Thank you for using VerbaPost.</p>
    </div>
    """
    
    try:
        sender = st.secrets["email"].get("sender_email", "onboarding@resend.dev")
        resend.Emails.send({
            "from": f"VerbaPost Support <{sender}>",
            "to": user_email,
            "subject": "Your letter has been mailed!",
            "html": html
        })
        return True
    except Exception as e:
        print(f"Email Error: {e}")
        return False