import streamlit as st
import requests
import resend
import secrets_manager
import hashlib # <--- NEW IMPORT
import json    # <--- NEW IMPORT

def get_postgrid_key(): return secrets_manager.get_secret("postgrid.api_key")
def get_resend_key(): return secrets_manager.get_secret("email.password")

def send_letter(pdf_path, to_address, from_address, certified=False):
    api_key = get_postgrid_key()
    if not api_key: return False, "Missing PostGrid API Key"

    try:
        url = "https://api.postgrid.com/print-mail/v1/letters"
        
        # --- 1. PREPARE DATA PAYLOAD ---
        data = {
            'description': f"VerbaPost to {to_address.get('name')}",
            'to[firstName]': to_address.get('name'), 
            'to[addressLine1]': to_address.get('address_line1'),
            'to[addressLine2]': to_address.get('address_line2', ''),
            'to[city]': to_address.get('address_city'),
            'to[provinceOrState]': to_address.get('address_state'),
            'to[postalOrZip]': to_address.get('address_zip'),
            'to[countryCode]': to_address.get('country_code', 'US'), 
            
            'from[firstName]': from_address.get('name'),
            'from[addressLine1]': from_address.get('address_line1'),
            'from[addressLine2]': from_address.get('address_line2', ''),
            'from[city]': from_address.get('address_city'),
            'from[provinceOrState]': from_address.get('address_state'),
            'from[postalOrZip]': from_address.get('address_zip'),
            'from[countryCode]': from_address.get('country_code', 'US'), 
            
            'color': 'false', 
            'addressPlacement': 'top_first_page'
        }

        if certified:
            data['express'] = 'true'
            data['extraService'] = 'certified'
        else:
            data['express'] = 'false'

        # --- 2. GENERATE IDEMPOTENCY KEY (THE FIX) ---
        # We hash the Data Dict + The PDF Bytes to create a unique fingerprint.
        # If the address OR the file content changes, it's a new letter.
        # If nothing changes, it's a retry, and PostGrid will deduplicate it.
        try:
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
            
            # Combine Data string + PDF content
            fingerprint_source = json.dumps(data, sort_keys=True).encode() + pdf_bytes
            idempotency_key = hashlib.sha256(fingerprint_source).hexdigest()
            
            # Add to Headers
            headers = {
                "x-api-key": api_key,
                "Idempotency-Key": idempotency_key 
            }
        except Exception as e:
            print(f"⚠️ Idempotency Gen Failed: {e}")
            headers = {"x-api-key": api_key} # Fallback if hashing fails
            pdf_bytes = None # Reset to ensure we re-open file below

        # --- 3. SEND REQUEST ---
        # Re-open file for the actual request (cursor is at end from reading bytes above)
        files = {'pdf': open(pdf_path, 'rb')}
        
        response = requests.post(url, headers=headers, data=data, files=files)
        files['pdf'].close()

        if response.status_code in [200, 201]:
            res_json = response.json()
            print(f"✅ PostGrid SUCCESS. ID: {res_json.get('id')}")
            
            tracking_num = res_json.get('trackingNumber')
            if certified and not tracking_num and "test" in api_key:
                 tracking_num = "TEST_TRACKING_12345"

            if certified and tracking_num:
                send_tracking_email(from_address.get('email'), tracking_num, to_address.get('name'))
                res_json['trackingNumber'] = tracking_num
            
            return True, res_json
        else:
            return False, f"PostGrid Error {response.status_code}: {response.text}"

    except Exception as e:
        return False, f"Connection Error: {str(e)}"

def send_tracking_email(user_email, tracking_num, recipient_name):
    key = get_resend_key()
    if not key or not user_email: return
    resend.api_key = key
    html = f"""<div style="font-family: sans-serif;"><h2>⚖️ Certified Mail Receipt</h2><p>Your letter to <strong>{recipient_name}</strong> has been mailed.</p><p><strong>Tracking:</strong> <a href="https://tools.usps.com/go/TrackConfirmAction?tLabels={tracking_num}">{tracking_num}</a></p></div>"""
    try: resend.Emails.send({"from": "VerbaPost Legal <onboarding@resend.dev>", "to": user_email, "subject": f"Certified Mail Receipt: {tracking_num}", "html": html})
    except: pass

def send_admin_alert(user_email, letter_text, tier):
    key = get_resend_key()
    if not key: return False
    resend.api_key = key
    admin_email = secrets_manager.get_secret("admin.email") or "tjkarat@gmail.com"
    subject = f"🔔 New {tier} Order"
    html = f"<div><h2>New Order</h2><p>User: {user_email}</p><pre>{letter_text}</pre></div>"
    try: resend.Emails.send({"from": "VerbaPost <onboarding@resend.dev>", "to": [admin_email], "subject": subject, "html": html})
    except: return False