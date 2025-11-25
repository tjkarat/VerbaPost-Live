import streamlit as st
import requests
import resend

# --- CONFIGURATION ---
def get_postgrid_key():
    try: return st.secrets["postgrid"]["api_key"]
    except: return None

def get_resend_key():
    try:
        if "resend" in st.secrets: return st.secrets["resend"]["api_key"]
        elif "email" in st.secrets: return st.secrets["email"]["password"]
    except: return None

# --- FUNCTION 1: SEND PHYSICAL MAIL (POSTGRID) ---
def send_letter(pdf_path, to_address, from_address):
    """
    Sends a PDF letter via PostGrid.
    """
    api_key = get_postgrid_key()
    if not api_key:
        print("❌ Error: PostGrid API Key missing.")
        return None

    try:
        url = "https://api.postgrid.com/print-mail/v1/letters"
        headers = {"x-api-key": api_key}
        
        # We open the file safely within the request logic
        files = {'pdf': open(pdf_path, 'rb')}
        
        # FIX: Map 'name' to 'firstName' to satisfy PostGrid requirements
        # We use the full name string in the firstName field, which PostGrid accepts.
        data = {
            'description': f"VerbaPost to {to_address.get('name')}",
            
            # Recipient
            'to[firstName]': to_address.get('name'), 
            'to[addressLine1]': to_address.get('address_line1'),
            'to[city]': to_address.get('address_city'),
            'to[provinceOrState]': to_address.get('address_state'),
            'to[postalOrZip]': to_address.get('address_zip'),
            'to[countryCode]': 'US',
            
            # Sender
            'from[firstName]': from_address.get('name'),
            'from[addressLine1]': from_address.get('address_line1'),
            'from[city]': from_address.get('address_city'),
            'from[provinceOrState]': from_address.get('address_state'),
            'from[postalOrZip]': from_address.get('address_zip'),
            'from[countryCode]': 'US',
            
            'color': 'false',
            'express': 'false',
            'addressPlacement': 'top_first_page'
        }

        response = requests.post(url, headers=headers, data=data, files=files)
        files['pdf'].close()

        if response.status_code in [200, 201]:
            return response.json()
        else:
            print(f"❌ PostGrid Error: {response.text}")
            # Return None so the UI knows it failed
            return None

    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return None

# --- NOTIFICATION FUNCTIONS ---
def send_heirloom_notification(user_email, letter_text):
    key = get_resend_key()
    if not key: return False
    resend.api_key = key

    subject = f"🔔 New Heirloom Order from {user_email}"
    html = f"""
    <div style="font-family: sans-serif; padding: 20px; color: #333;">
        <h2 style="color: #2a5298;">🏺 New Heirloom Order</h2>
        <p><strong>User:</strong> {user_email}</p>
        <pre style="background: #eee; padding: 15px;">{letter_text}</pre>
    </div>
    """
    try:
        sender = st.secrets["email"].get("sender_email", "onboarding@resend.dev")
        resend.Emails.send({
            "from": f"VerbaPost Admin <{sender}>",
            "to": ["tjkarat@gmail.com", "support@verbapost.com"],
            "subject": subject,
            "html": html
        })
        return True
    except: return False

def send_shipping_confirmation(user_email, recipient_info):
    key = get_resend_key()
    if not key: return False, "Missing Key"
    resend.api_key = key
    
    r_name = recipient_info.get('recipient_name') or "Recipient"
    html = f"""
    <div style="font-family: sans-serif; padding: 20px; color: #333;">
        <h2 style="color: #2a5298;">🚀 Your Letter is on the way!</h2>
        <p>Your letter to <strong>{r_name}</strong> has been mailed.</p>
        <p>Thank you for using VerbaPost.</p>
    </div>
    """
    try:
        sender = st.secrets["email"].get("sender_email", "onboarding@resend.dev")
        r = resend.Emails.send({
            "from": f"VerbaPost Support <{sender}>",
            "to": user_email,
            "subject": "Your letter has been mailed!",
            "html": html
        })
        return True, f"ID: {r.get('id')}"
    except Exception as e:
        return False, str(e)