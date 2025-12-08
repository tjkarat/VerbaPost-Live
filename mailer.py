import streamlit as st
import requests
import resend
import secrets_manager
import hashlib
import json
import time
import logging
from address_standard import StandardAddress

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_postgrid_key(): return secrets_manager.get_secret("postgrid.api_key")
def get_resend_key(): return secrets_manager.get_secret("email.password")

def verify_address_data(line1, line2, city, state, zip_code, country_code):
    api_key = get_postgrid_key()
    if not api_key: return True, None 

    url = "https://api.postgrid.com/v1/addver/verifications"
    payload = {
        "line1": line1, "line2": line2, "city": city,
        "provinceOrState": state, "postalOrZip": zip_code, "country": country_code
    }
    
    try:
        r = requests.post(url, headers={"x-api-key": api_key}, data=payload)
        if r.status_code == 200:
            res = r.json()
            if res.get('status') in ['verified', 'corrected']:
                return True, {
                    "line1": res.get('line1'), "line2": res.get('line2') or "",
                    "city": res.get('city'), "state": res.get('provinceOrState'),
                    "zip": res.get('postalOrZip'), "country": res.get('country')
                }
            else: return False, f"Address Invalid: {res.get('errors', {})}"
        else: return True, None 
    except Exception as e:
        logger.error(f"Verif Exception: {e}")
        return True, None

def send_confirmation_email(user_email, tier, recipient_name):
    key = get_resend_key()
    if not key or not user_email: return
    resend.api_key = key
    subject = f"📮 Letter Mailed: {tier} Edition"
    html = f"""<div style="font-family: sans-serif;"><h2>Letter Sent! ✈️</h2><p>Your <strong>{tier}</strong> letter to <strong>{recipient_name}</strong> has been processed.</p></div>"""
    try: resend.Emails.send({"from": "VerbaPost <updates@verbapost.com>", "to": user_email, "subject": subject, "html": html})
    except: pass

def send_tracking_email(user_email, tracking_num, recipient_name):
    key = get_resend_key()
    if not key or not user_email: return
    resend.api_key = key
    html = f"""<div style="font-family: sans-serif;"><h2>⚖️ Certified Mail Receipt</h2><p>Your letter to <strong>{recipient_name}</strong> has been mailed.</p><p><strong>Tracking:</strong> <a href="https://tools.usps.com/go/TrackConfirmAction?tLabels={tracking_num}">{tracking_num}</a></p></div>"""
    try: resend.Emails.send({"from": "VerbaPost Legal <support@verbapost.com>", "to": user_email, "subject": f"Certified Mail Receipt: {tracking_num}", "html": html})
    except: pass

def send_admin_alert(user_email, letter_text, tier):
    key = get_resend_key()
    if not key: return False
    resend.api_key = key
    admin_email = secrets_manager.get_secret("admin.email") or "tjkarat@gmail.com"
    subject = f"🔔 New {tier} Order"
    html = f"<div><h2>New Order</h2><p>User: {user_email}</p><pre>{letter_text}</pre></div>"
    try: resend.Emails.send({"from": "VerbaPost Ops <support@verbapost.com>", "to": [admin_email], "subject": subject, "html": html})
    except: return False

def send_letter(pdf_path, to_address, from_address, certified=False):
    api_key = get_postgrid_key()
    if not api_key: 
        logger.error("Missing PostGrid API Key")
        return False, "Missing PostGrid API Key"

    try:
        url = "https://api.postgrid.com/print-mail/v1/letters"
        
        # FIX: Robust parsing via StandardAddress
        to_std = StandardAddress.from_dict(to_address)
        from_std = StandardAddress.from_dict(from_address)
        
        to_p = to_std.to_postgrid_payload()
        from_p = from_std.to_postgrid_payload()
        
        data = {
            'description': f"VerbaPost to {to_std.name}",
            'to[firstName]': to_p['name'],
            'to[addressLine1]': to_p['address_line1'],
            'to[addressLine2]': to_p['address_line2'],
            'to[city]': to_p['address_city'],
            'to[provinceOrState]': to_p['address_state'],
            'to[postalOrZip]': to_p['address_zip'],
            'to[countryCode]': to_p['country_code'],
            
            'from[firstName]': from_p['name'],
            'from[addressLine1]': from_p['address_line1'],
            'from[addressLine2]': from_p['address_line2'],
            'from[city]': from_p['address_city'],
            'from[provinceOrState]': from_p['address_state'],
            'from[postalOrZip]': from_p['address_zip'],
            'from[countryCode]': from_p['country_code'],
            
            'addressStrictness': 'relaxed', 
            'color': 'false',
            'addressPlacement': 'top_first_page'
        }

        if certified:
            data['express'] = 'true'; data['extraService'] = 'certified'
        else:
            data['express'] = 'false'

        # Idempotency with Time Salt
        try:
            with open(pdf_path, 'rb') as f: pdf_bytes = f.read()
            salt = str(time.time()).encode()
            fingerprint = json.dumps(data, sort_keys=True).encode() + pdf_bytes + salt
            headers = { "x-api-key": api_key, "Idempotency-Key": hashlib.sha256(fingerprint).hexdigest() }
        except: headers = {"x-api-key": api_key}

        # FIX: Safe file handling
        with open(pdf_path, 'rb') as f_pdf:
            files = {'pdf': f_pdf}
            response = requests.post(url, headers=headers, data=data, files=files)

        if response.status_code in [200, 201]:
            res = response.json()
            if certified and res.get('trackingNumber'): 
                send_tracking_email(from_std.name, res.get('trackingNumber'), to_std.name)
            
            send_confirmation_email(from_address.get('email'), "Standard", to_std.name)
            return True, res
        else:
            logger.error(f"PostGrid Error: {response.text}")
            return False, f"PostGrid Error {response.status_code}: {response.text}"

    except Exception as e:
        logger.exception("Mailer Exception")
        return False, f"Connection Error: {str(e)}"