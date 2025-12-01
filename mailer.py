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
    api_key = get_postgrid_key()
    if not api_key: return None

    try:
        url = "https://api.postgrid.com/print-mail/v1/letters"
        headers = {"x-api-key": api_key}
        files = {'pdf': open(pdf_path, 'rb')}
        
        # Map fields with International Support
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
            'addressPlacement': 'top_first_page'
        }

        # --- CERTIFIED MAIL LOGIC ---
        if certified:
            data['express'] = 'true' # PostGrid often maps express to tracking
            data['extraService'] = 'certified' # Explicit request
            print("DEBUG: Sending CERTIFIED mail.")
        else:
            data['express'] = 'false'

        response = requests.post(url, headers=headers, data=data, files=files)
        files['pdf'].close()

        if response.status_code in [200, 201]:
            res_json = response.json()
            print(f"✅ PostGrid SUCCESS. ID: {res_json.get('id')}")
            
            # --- UPDATE: Handle Tracking ---
            tracking_num = res_json.get('trackingNumber')
            
            # FALLBACK FOR TEST MODE: If certified but no tracking returned, fake it so we can test email
            if certified and not tracking_num and "test" in api_key:
                 tracking_num = "TEST_TRACKING_12345"

            if certified and tracking_num:
                send_tracking_email(from_address.get('email'), tracking_num, to_address.get('name'))
            
            # Return the modified json so UI sees the fake number too
            res_json['trackingNumber'] = tracking_num
            return res_json
        else:
            print(f"❌ PostGrid Error: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return None

# --- NEW: SEND TRACKING RECEIPT ---
def send_tracking_email(user_email, tracking_num, recipient_name):
    key = get_resend_key()
    if not key or not user_email: return
    
    resend.api_key = key
    
    html = f"""
    <div style="font-family: sans-serif;">
        <h2>⚖️ Certified Mail Receipt</h2>
        <p>Your legal letter to <strong>{recipient_name}</strong> has been mailed.</p>
        <div style="background:#f4f4f4; padding:15px; margin:20px 0;">
            <strong>USPS Tracking Number:</strong><br>
            <a href="https://tools.usps.com/go/TrackConfirmAction?tLabels={tracking_num}">{tracking_num}</a>
        </div>
        <p>Save this email. This link is your proof of mailing.</p>
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

# --- FUNCTION 2: SEND ADMIN ALERT (HEIRLOOM/SANTA) ---
def send_admin_alert(user_email, letter_text, tier):
    """
    Sends an instant email to the Admin when a manual order (Santa/Heirloom) is placed.
    """
    key = get_resend_key()
    if not key: 
        print("❌ Resend Key Missing")
        return False
    
    resend.api_key = key
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
        # Use 'onboarding@resend.dev' to guarantee delivery until domain is verified
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