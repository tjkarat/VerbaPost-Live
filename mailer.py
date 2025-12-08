import streamlit as st
import requests
import resend
import secrets_manager
import hashlib
import json

def get_postgrid_key(): return secrets_manager.get_secret("postgrid.api_key")
def get_resend_key(): return secrets_manager.get_secret("email.password")

# --- ADDRESS VERIFICATION (NEW) ---
def verify_address_data(line1, line2, city, state, zip_code, country_code):
    """
    Calls PostGrid Address Verification API to standardize and validate input.
    Returns: (bool is_valid, dict data_or_error)
    """
    api_key = get_postgrid_key()
    if not api_key: return True, None # Skip if no key (Dev mode)

    url = "https://api.postgrid.com/v1/addver/verifications"
    
    payload = {
        "line1": line1,
        "line2": line2,
        "city": city,
        "provinceOrState": state,
        "postalOrZip": zip_code,
        "country": country_code
    }
    
    try:
        r = requests.post(url, headers={"x-api-key": api_key}, data=payload)
        
        if r.status_code == 200:
            res = r.json()
            
            # Case A: Success (Verified or Corrected)
            if res.get('status') in ['verified', 'corrected']:
                return True, {
                    "line1": res.get('line1'),
                    "line2": res.get('line2') or "",
                    "city": res.get('city'),
                    "state": res.get('provinceOrState'),
                    "zip": res.get('postalOrZip'),
                    "country": res.get('country')
                }
            # Case B: Failure (Invalid Address)
            else:
                errors = res.get('errors', {})
                msg = f"Address Invalid: {errors}" 
                return False, msg
        else:
            # API Error (Fail open so we don't block signups)
            print(f"PostGrid Verif Error: {r.text}")
            return True, None 

    except Exception as e:
        print(f"Verif Exception: {e}")
        return True, None

# --- NOTIFICATIONS ---
def send_confirmation_email(user_email, tier, recipient_name):
    key = get_resend_key()
    if not key or not user_email: return
    resend.api_key = key
    subject = f"📮 Letter Mailed: {tier} Edition"
    html = f"""<div style="font-family: sans-serif;"><h2>Letter Sent! ✈️</h2><p>Your <strong>{tier}</strong> letter to <strong>{recipient_name}</strong> has been processed.</p></div>"""
    try: resend.Emails.send({"from": "VerbaPost <updates@resend.dev>", "to": user_email, "subject": subject, "html": html})
    except: pass

def send_manual_completion_email(user_email, tier, recipient_name):
    key = get_resend_key()
    if not key or not user_email: return
    resend.api_key = key
    subject = f"📮 {tier} Letter Mailed"
    html = f"""<div style="font-family: sans-serif;"><h2>{tier} Letter Sent!</h2><p>Your letter to {recipient_name} has been mailed.</p></div>"""
    try: resend.Emails.send({"from": "VerbaPost <updates@resend.dev>", "to": user_email, "subject": subject, "html": html})
    except: pass

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

# --- CORE SENDING FUNCTION ---
def send_letter(pdf_path, to_address, from_address, certified=False):
    api_key = get_postgrid_key()
    if not api_key: return False, "Missing PostGrid API Key"

    try:
        url = "https://api.postgrid.com/print-mail/v1/letters"
        
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
            
            'addressStrictness': 'relaxed', 
            'color': 'false', 
            'addressPlacement': 'top_first_page'
        }

        if certified:
            data['express'] = 'true'; data['extraService'] = 'certified'
        else:
            data['express'] = 'false'

        # Idempotency Key Generation
        try:
            with open(pdf_path, 'rb') as f: pdf_bytes = f.read()
            fingerprint = json.dumps(data, sort_keys=True).encode() + pdf_bytes
            headers = { "x-api-key": api_key, "Idempotency-Key": hashlib.sha256(fingerprint).hexdigest() }
        except: headers = {"x-api-key": api_key}

        files = {'pdf': open(pdf_path, 'rb')}
        response = requests.post(url, headers=headers, data=data, files=files)
        files['pdf'].close()

        if response.status_code in [200, 201]:
            res = response.json()
            if certified and res.get('trackingNumber'): 
                send_tracking_email(from_address.get('email'), res.get('trackingNumber'), to_address.get('name'))
            
            send_confirmation_email(from_address.get('email'), "Standard", to_address.get('name'))
            return True, res
        else:
            return False, f"PostGrid Error {response.status_code}: {response.text}"

    except Exception as e: return False, f"Connection Error: {str(e)}"