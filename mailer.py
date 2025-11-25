import streamlit as st
import requests
import json
import resend

# --- CONFIGURATION ---
# 1. Load Lob Key (Physical Mail)
try:
    LOB_API_KEY = st.secrets.get("LOB_API_KEY")
except:
    LOB_API_KEY = None

# 2. Load Resend Key (Email) - FIXED FOR YOUR SECRETS
try:
    # Option A: Standard structure
    if "resend" in st.secrets:
        resend.api_key = st.secrets["resend"]["api_key"]
    # Option B: Your SMTP structure
    elif "email" in st.secrets:
        # In SMTP config, the 'password' IS the API Key
        resend.api_key = st.secrets["email"]["password"]
    else:
        resend.api_key = None
except:
    resend.api_key = None

# --- FUNCTION 1: SEND PHYSICAL MAIL (LOB) ---
def send_letter(pdf_path, to_address, from_address):
    """Sends a PDF letter via Lob."""
    if not LOB_API_KEY:
        print("❌ Error: Lob API Key missing.")
        return None

    try:
        url = "https://api.lob.com/v1/letters"
        auth = (LOB_API_KEY, '')
        files = {'file': open(pdf_path, 'rb')}
        
        data = {
            'description': f"VerbaPost to {to_address.get('name')}",
            'to[name]': to_address.get('name'),
            'to[address_line1]': to_address.get('address_line1'),
            'to[address_city]': to_address.get('address_city'),
            'to[address_state]': to_address.get('address_state'),
            'to[address_zip]': to_address.get('address_zip'),
            'from[name]': from_address.get('name'),
            'from[address_line1]': from_address.get('address_line1'),
            'from[address_city]': from_address.get('address_city'),
            'from[address_state]': from_address.get('address_state'),
            'from[address_zip]': from_address.get('address_zip'),
            'color': 'false',
            'double_sided': 'true'
        }

        response = requests.post(url, auth=auth, data=data, files=files)
        files['file'].close()

        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Lob Error: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return None

# --- FUNCTION 2: SEND NOTIFICATION (RESEND) ---
def send_heirloom_notification(user_email, letter_text):
    """Sends email alert using the 'password' from [email] secrets."""
    if not resend.api_key:
        print("❌ Resend API Key missing")
        return False

    subject = f"🔔 New Heirloom Order from {user_email}"
    
    html_content = f"""
    <div style="font-family: sans-serif; padding: 20px; color: #333;">
        <h2 style="color: #2a5298;">🏺 New Heirloom Order</h2>
        <p><strong>User:</strong> {user_email}</p>
        <hr>
        <pre style="background: #eee; padding: 15px;">{letter_text}</pre>
    </div>
    """

    try:
        # Note: We use the 'sender_email' from secrets if available, else default
        sender = st.secrets["email"].get("sender_email", "onboarding@resend.dev")
        
        r = resend.Emails.send({
            "from": f"VerbaPost System <{sender}>",
            "to": ["tjkarat@gmail.com", "support@verbapost.com"],
            "subject": subject,
            "html": html_content
        })
        print(f"✅ Email Sent: {r}")
        return True
    except Exception as e:
        print(f"❌ Email Failed: {e}")
        return False