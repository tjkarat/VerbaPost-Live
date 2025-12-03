import streamlit as st
import requests
import resend
import secrets_manager

# --- CONFIGURATION ---
def get_postgrid_key():
    return secrets_manager.get_secret("postgrid.api_key")

def get_resend_key():
    return secrets_manager.get_secret("email.password")

# --- FUNCTION 1: SEND PHYSICAL MAIL (POSTGRID) ---
def send_letter(pdf_path, to_address, from_address, certified=False):
    """
    Returns: (bool: success, str: error_message_or_data)
    """
    api_key = get_postgrid_key()
    if not api_key: return False, "Missing PostGrid API Key"

    try:
        url = "https://api.postgrid.com/print-mail/v1/letters"
        headers = {"x-api-key": api_key}
        files = {'pdf': open(pdf_path, 'rb')}
        
        data = {
            'description': f"VerbaPost to {to_address.get('name')}",
            'to[firstName]': to_address.get('name'), 
            'to[addressLine1]': to_address.get('address_line1'),
            'to[city]': to_address.get('address_city'),
            'to[provinceOrState]': to_address.get('address_state'),
            'to[postalOrZip]': to_address.get('address_zip'),
            'to[countryCode]': to_address.get('country_code', 'US'), 
            'from[firstName]': from_address.get('name'),
            'from[addressLine1]': from_address.get('address_line1'),
            'from[city]': from_address.get('address_city'),
            'from[provinceOrState]': from_address.get('address_state'),
            'from[postalOrZip]': from_address.get('address_zip'),
            'from[countryCode]': from_address.get('country', 'US'), 
            'color': 'false', 
            'addressPlacement': 'top_first_page'
        }

        if certified:
            data['express'] = 'true'
            data['extraService'] = 'certified'

        response = requests.post(url, headers=headers, data=data, files=files)
        files['pdf'].close()

        if response.status_code in [200, 201]:
            res_json = response.json()
            print(f"✅ PostGrid SUCCESS. ID: {res_json.get('id')}")
            
            # Handle Tracking Email
            tracking_num = res_json.get('trackingNumber')
            if certified and not tracking_num and "test" in api_key:
                 tracking_num = "TEST_TRACKING_12345" # Fallback for testing

            if certified and tracking_num:
                send_tracking_email(from_address.get('email'), tracking_num, to_address.get('name'))
                res_json['trackingNumber'] = tracking_num # Ensure it passes back
            
            return True, res_json
        else:
            # RETURN THE ACTUAL ERROR FROM POSTGRID
            error_msg = f"PostGrid Error {response.status_code}: {response.text}"
            print(f"❌ {error_msg}")
            return False, error_msg

    except Exception as e:
        return False, f"Connection Error: {str(e)}"

# --- NEW: SEND TRACKING RECEIPT ---
def send_tracking_email(user_email, tracking_num, recipient_name):
    key = get_resend_key()
    if not key or not user_email: return
    
    resend.api_key = key
    html = f"""
    <div style="font-family: sans-serif;">
        <h2>⚖️ Certified Mail Receipt</h2>
        <p>Your letter to <strong>{recipient_name}</strong> has been mailed.</p>
        <p><strong>Tracking:</strong> <a href="https://tools.usps.com/go/TrackConfirmAction?tLabels={tracking_num}">{tracking_num}</a></p>
    </div>
    """
    try:
        resend.Emails.send({
            "from": "VerbaPost Legal <onboarding@resend.dev>",
            "to": user_email,
            "subject": f"Certified Mail Receipt: {tracking_num}",
            "html": html
        })
    except: pass

def send_admin_alert(user_email, letter_text, tier):
    key = get_resend_key()
    if not key: return False
    resend.api_key = key
    admin_email = secrets_manager.get_secret("admin.email") or "tjkarat@gmail.com"
    subject = f"🔔 New {tier} Order"
    html = f"<div><h2>New Order</h2><p>User: {user_email}</p><pre>{letter_text}</pre></div>"
    try:
        resend.Emails.send({"from": "VerbaPost <onboarding@resend.dev>", "to": [admin_email], "subject": subject, "html": html})
        return True
    except: return False