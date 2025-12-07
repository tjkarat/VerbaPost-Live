import streamlit as st
import requests
import resend
import secrets_manager
import hashlib
import json

def get_postgrid_key(): return secrets_manager.get_secret("postgrid.api_key")
def get_resend_key(): return secrets_manager.get_secret("email.password")

# --- NEW: GENERIC CONFIRMATION EMAIL ---
def send_confirmation_email(user_email, tier, recipient_name):
    """Sends immediate confirmation for Standard/Civic orders."""
    key = get_resend_key()
    if not key or not user_email: return
    resend.api_key = key
    
    subject = f"📮 Letter Mailed: {tier} Edition"
    html = f"""
    <div style="font-family: sans-serif; color: #333;">
        <h2>Letter Sent! ✈️</h2>
        <p>Your <strong>{tier}</strong> letter to <strong>{recipient_name}</strong> has been processed and is on its way.</p>
        <p>Thank you for using VerbaPost.</p>
        <hr>
        <p style="font-size: 12px; color: #888;">If you need help, reply to this email.</p>
    </div>
    """
    try: resend.Emails.send({"from": "VerbaPost <updates@resend.dev>", "to": user_email, "subject": subject, "html": html})
    except: pass

# --- NEW: MANUAL FULFILLMENT EMAIL (Santa/Heirloom) ---
def send_manual_completion_email(user_email, tier, recipient_name):
    """Called by Admin Console when marking special orders as Complete."""
    key = get_resend_key()
    if not key or not user_email: return
    resend.api_key = key
    
    if "Santa" in tier:
        subject = "🎅 A Letter form the North Pole has Sent!"
        html = f"""
        <div style="font-family: sans-serif; color: #333;">
            <h2>Ho Ho Ho! 🎅</h2>
            <p>The letter to <strong>{recipient_name}</strong> has just left the North Pole via Reindeer Express.</p>
            <p>Keep an eye on the chimney (or mailbox)!</p>
        </div>
        """
    else:
        subject = f"🏺 Heirloom Letter Mailed"
        html = f"""
        <div style="font-family: sans-serif; color: #333;">
            <h2>Hand-Crafted & Mailed 🏺</h2>
            <p>Your Heirloom letter to <strong>{recipient_name}</strong> has been printed on archival stock, hand-addressed, and mailed.</p>
        </div>
        """
    
    try: resend.Emails.send({"from": "VerbaPost <updates@resend.dev>", "to": user_email, "subject": subject, "html": html})
    except: pass


def send_letter(pdf_path, to_address, from_address, certified=False):
    api_key = get_postgrid_key()
    if not api_key: return False, "Missing PostGrid API Key"

    try:
        url = "https://api.postgrid.com/print-mail/v1/letters"
        
        # --- 1. DATA PAYLOAD ---
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

        # --- 2. IDEMPOTENCY KEY ---
        try:
            with open(pdf_path, 'rb') as f:
                pdf_bytes = f.read()
            fingerprint_source = json.dumps(data, sort_keys=True).encode() + pdf_bytes
            idempotency_key = hashlib.sha256(fingerprint_source).hexdigest()
            headers = { "x-api-key": api_key, "Idempotency-Key": idempotency_key }
        except:
            headers = {"x-api-key": api_key}
            pdf_bytes = None

        # --- 3. SEND ---
        files = {'pdf': open(pdf_path, 'rb')}
        response = requests.post(url, headers=headers, data=data, files=files)
        files['pdf'].close()

        if response.status_code in [200, 201]:
            res_json = response.json()
            print(f"✅ PostGrid SUCCESS. ID: {res_json.get('id')}")
            
            # --- EMAIL TRIGGERS ---
            recip_name = to_address.get('name')
            user_email = from_address.get('email')
            
            # 1. Certified Tracking Email
            tracking_num = res_json.get('trackingNumber')
            if certified and not tracking_num and "test" in api_key: tracking_num = "TEST_TRACKING_12345"
            if certified and tracking_num:
                send_tracking_email(user_email, tracking_num, recip_name)
                res_json['trackingNumber'] = tracking_num
            
            # 2. Standard Success Email (New Request)
            send_confirmation_email(user_email, "Standard", recip_name)
            
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