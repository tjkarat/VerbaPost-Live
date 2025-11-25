import streamlit as st
import requests
import resend

# --- HELPER: GET KEY SAFELY ---
def get_api_key():
    """Retrieves API Key from secrets at runtime."""
    try:
        if "resend" in st.secrets:
            return st.secrets["resend"]["api_key"]
        elif "email" in st.secrets:
            return st.secrets["email"]["password"]
    except:
        return None
    return None

# --- FUNCTION 1: SEND PHYSICAL MAIL (LOB) ---
def send_letter(pdf_path, to_address, from_address):
    try:
        LOB_API_KEY = st.secrets.get("LOB_API_KEY")
        if not LOB_API_KEY: return None
        
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

        if response.status_code == 200: return response.json()
        else: return None
    except: return None

# --- FUNCTION 2: SEND ADMIN ALERT (New Order) ---
def send_heirloom_notification(user_email, letter_text):
    key = get_api_key()
    if not key: return False
    resend.api_key = key

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
        sender = st.secrets["email"].get("sender_email", "onboarding@resend.dev")
        resend.Emails.send({
            "from": f"VerbaPost Admin <{sender}>",
            "to": ["tjkarat@gmail.com", "support@verbapost.com"],
            "subject": subject,
            "html": html_content
        })
        return True
    except: return False

# --- FUNCTION 3: SEND SHIPPING CONFIRMATION (User) ---
def send_shipping_confirmation(user_email, recipient_info):
    """
    Notifies the user that their letter has been mailed.
    Returns: (bool_success, str_message)
    """
    key = get_api_key()
    if not key: 
        return False, "Missing API Key in Secrets"
    
    resend.api_key = key
    
    # Safely handle potential None values
    r_name = recipient_info.get('recipient_name') or "Recipient"
    r_street = recipient_info.get('recipient_street') or ""
    
    html = f"""
    <div style="font-family: sans-serif; padding: 20px; color: #333; max-width: 600px;">
        <h2 style="color: #2a5298;">🚀 Your Letter is on the way!</h2>
        <p>Great news! We have printed, stamped, and handed off your letter to the USPS.</p>
        
        <div style="background: #f8f9fa; border-left: 4px solid #2a5298; padding: 15px; margin: 20px 0;">
            <p style="margin: 0; color: #666; font-size: 12px;">MAILED TO:</p>
            <p style="margin: 5px 0 0 0; font-weight: bold; font-size: 16px;">
                {r_name}<br>{r_street}
            </p>
        </div>
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
        return True, f"Sent ID: {r.get('id')}"
    except Exception as e:
        # Return the actual error message so Admin can see it
        return False, str(e)