import streamlit as st
import requests
import json
import resend

# --- CONFIGURATION ---
# Load Lob Key (For Physical Mail)
try:
    LOB_API_KEY = st.secrets["LOB_API_KEY"]
except Exception:
    LOB_API_KEY = None

# Load Resend Key (For Admin Notifications)
try:
    if "resend" in st.secrets:
        resend.api_key = st.secrets["resend"]["api_key"]
    else:
        resend.api_key = None
except:
    resend.api_key = None

# --- FUNCTION 1: SEND PHYSICAL MAIL (LOB) ---
def send_letter(pdf_path, to_address, from_address):
    """
    Sends a PDF letter via Lob using direct REST API.
    """
    if not LOB_API_KEY:
        print("❌ Error: Lob API Key missing.")
        # Fail silently or log to console to not break app flow if key is missing
        return None

    try:
        url = "https://api.lob.com/v1/letters"
        auth = (LOB_API_KEY, '')

        files = {
            'file': open(pdf_path, 'rb')
        }
        
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

# --- FUNCTION 2: SEND HEIRLOOM NOTIFICATION (RESEND) ---
def send_heirloom_notification(user_email, letter_text):
    """
    Sends an email alert to Admins via Resend when an Heirloom order is placed.
    """
    if not resend.api_key:
        print("❌ Resend API Key missing")
        return False

    subject = f"🔔 New Heirloom Order from {user_email}"
    
    html_content = f"""
    <div style="font-family: sans-serif; padding: 20px; color: #333;">
        <h2 style="color: #2a5298;">🏺 New Heirloom Order Received</h2>
        <p>A new Heirloom letter has been finalized and paid for. Please fulfill immediately.</p>
        
        <div style="background: #f0f2f6; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <p><strong>User Email:</strong> {user_email}</p>
            <p><strong>Tier:</strong> Heirloom ($5.99)</p>
            <p><strong>Status:</strong> Paid & Ready to Print</p>
        </div>

        <h3>📄 Letter Content to Print:</h3>
        <pre style="background: #fff; border: 1px solid #ddd; padding: 15px; white-space: pre-wrap; font-family: 'Courier New', Courier, monospace;">
{letter_text}
        </pre>
        
        <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="font-size: 12px; color: #888;">Sent via VerbaPost Automation</p>
    </div>
    """

    try:
        # Sends to both Tarak and Support
        r = resend.Emails.send({
            "from": "VerbaPost Orders <onboarding@resend.dev>", 
            "to": ["tjkarat@gmail.com", "support@verbapost.com"],
            "subject": subject,
            "html": html_content
        })
        print(f"✅ Admin Notification Sent: {r}")
        return True
    except Exception as e:
        print(f"❌ Email Failed: {e}")
        return False