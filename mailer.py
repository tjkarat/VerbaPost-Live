import streamlit as st
import requests
import resend
import secrets_manager

# --- CONFIGURATION ---
def get_postgrid_key():
    key = secrets_manager.get_secret("postgrid.api_key")
    if not key:
        print("❌ ERROR: PostGrid API Key is MISSING.")
    return key

def get_resend_key():
    return secrets_manager.get_secret("email.password")

# --- FUNCTION 1: SEND PHYSICAL MAIL (POSTGRID) ---
def send_letter(pdf_path, to_address, from_address):
    api_key = get_postgrid_key()
    if not api_key: return None

    try:
        url = "https://api.postgrid.com/print-mail/v1/letters"
        headers = {"x-api-key": api_key}
        files = {'pdf': open(pdf_path, 'rb')}
        
        print(f"DEBUG: Sending to PostGrid. To: {to_address.get('country_code')} From: {from_address.get('country_code')}")

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
            'from[countryCode]': from_address.get('country_code', 'US'), 
            'color': 'false', 
            'express': 'false', 
            'addressPlacement': 'top_first_page'
        }

        response = requests.post(url, headers=headers, data=data, files=files)
        files['pdf'].close()

        if response.status_code in [200, 201]:
            print(f"✅ PostGrid SUCCESS. ID: {response.json().get('id')}")
            return response.json()
        else:
            print(f"❌ PostGrid REJECTION: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return None

# --- FUNCTION 2: SEND ADMIN ALERT (UPDATED) ---
def send_admin_alert(user_email, letter_text, tier):
    """
    Sends an instant email to the Admin when a manual order (Santa/Heirloom) is placed.
    """
    key = get_resend_key()
    if not key: 
        print("❌ Resend Key Missing")
        return False
    
    resend.api_key = key
    # Defaults to your email if secret is missing
    admin_email = secrets_manager.get_secret("admin.email") or "tjkarat@gmail.com"

    subject = f"🔔 New {tier} Order to Fulfill"
    
    html = f"""
    <div style="font-family: sans-serif; padding: 20px; color: #333; border: 1px solid #ddd; border-radius: 8px;">
        <h2 style="color: #2a5298;">📮 New {tier} Order</h2>
        <p><strong>Customer:</strong> {user_email}</p>
        <p><strong>Action Required:</strong> Log in to Admin Console > {tier} Tab > Generate PDF.</p>
        <hr>
        <p><strong>Content Preview:</strong></p>
        <pre style="background: #f4f4f4; padding: 15px; white-space: pre-wrap; border-radius: 5px;">{letter_text}</pre>
    </div>
    """

    try:
        r = resend.Emails.send({
            "from": "VerbaPost System <onboarding@resend.dev>",
            "to": [admin_email],
            "subject": subject,
            "html": html
        })
        print(f"✅ Admin Alert Sent! ID: {r.get('id')}")
        return True
    except Exception as e:
        print(f"❌ Admin Alert Failed: {e}")
        return False

# --- FUNCTION 3: SHIPPING CONFIRMATION ---
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
        r = resend.Emails.send({
            "from": "VerbaPost Support <onboarding@resend.dev>",
            "to": user_email,
            "subject": "Your letter has been mailed!",
            "html": html
        })
        return True, f"ID: {r.get('id')}"
    except Exception as e:
        return False, str(e)