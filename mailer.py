import streamlit as st
import requests
import resend
import secrets_manager
import hashlib
import json
import time
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_postgrid_key(): return secrets_manager.get_secret("postgrid.api_key") or secrets_manager.get_secret("POSTGRID_API_KEY")
def get_resend_key(): return secrets_manager.get_secret("email.password") or secrets_manager.get_secret("RESEND_API_KEY")

def verify_address_data(line1, line2, city, state, zip_code, country_code):
    api_key = get_postgrid_key()
    if not api_key: 
        logger.warning("⚠️ Address Verification Skipped: No API Key found.")
        return True, None 

    # Correct Endpoint for Address Verification
    url = "https://api.postgrid.com/v1/addver/verifications"
    payload = {
        "line1": line1, "line2": line2, "city": city,
        "provinceOrState": state, "postalOrZip": zip_code, "country": country_code
    }
    
    try:
        r = requests.post(url, headers={"x-api-key": api_key}, data=payload, timeout=5)
        if r.status_code == 200:
            res = r.json()
            if res.get('status') in ['verified', 'corrected']:
                data = res.get('data', {})
                return True, {
                    "line1": data.get('line1'), "line2": data.get('line2') or "",
                    "city": data.get('city'), "state": data.get('provinceOrState'),
                    "zip": data.get('postalOrZip'), "country": data.get('country')
                }
            return False, "Address not found or invalid."
        else:
            logger.error(f"Address Verify Error: {r.status_code} - {r.text}")
    except Exception as e:
        logger.error(f"Address Verify Fail: {e}")
    
    return True, None # Fail open if API down

def send_letter(pdf_path, to_addr, from_addr, certified=False):
    api_key = get_postgrid_key()
    
    # --- DEBUGGING: Check Key Presence ---
    if not api_key: 
        logger.error("❌ Send Letter Failed: Missing API Key.")
        return False, "Missing API Key"
    else:
        logger.info(f"✅ API Key found (starts with: {api_key[:4]}...)")

    # --- CRITICAL FIX: CORRECT PRINT & MAIL ENDPOINT ---
    url = "https://api.postgrid.com/print-mail/v1/letters"
    logger.info(f"📡 PostGrid Target URL: {url}")
    
    # Construct strictly validated payload
    data = {
        'to': json.dumps(to_addr),
        'from': json.dumps(from_addr),
        'express': 'true' if certified else 'false',
        'addressPlacement': 'top_first_page',
        'color': 'false'
    }
    
    if certified: data['extraService'] = 'certified'

    # Idempotency Header (Prevents double sends)
    try:
        with open(pdf_path, 'rb') as f: pdf_content = f.read()
        
        # Create hash of: Address Data + File Content
        payload_sig = json.dumps(data, sort_keys=True).encode() + pdf_content
        idempotency_key = hashlib.sha256(payload_sig).hexdigest()
        
        headers = {"x-api-key": api_key, "Idempotency-Key": idempotency_key}
    except Exception as e:
        logger.error(f"Idempotency Gen Failed: {e}")
        headers = {"x-api-key": api_key}

    try:
        # SAFE FILE OPENING
        with open(pdf_path, 'rb') as f_pdf:
            files = {'pdf': f_pdf}
            logger.info("📤 Sending request to PostGrid...")
            response = requests.post(url, headers=headers, data=data, files=files, timeout=30)
            
        if response.status_code in [200, 201]:
            res = response.json()
            logger.info(f"✅ Mail Sent! ID: {res.get('id')}")
            
            # Send Email Confirmations asynchronously
            try:
                if certified and res.get('trackingNumber'):
                    send_tracking_email(from_addr.get('email'), res.get('trackingNumber'))
            except: pass
            
            return True, res
        else:
            # --- DEBUGGING: Full Error Output ---
            logger.error(f"❌ PostGrid API Error: {response.status_code}")
            logger.error(f"❌ Response Body: {response.text}")
            return False, f"API Error: {response.status_code} - {response.text}"

    except Exception as e:
        logger.error(f"❌ Connection Error: {e}")
        return False, str(e)

def send_tracking_email(user_email, tracking):
    key = get_resend_key()
    if not key or not user_email: return
    
    resend.api_key = key
    try:
        resend.Emails.send({
            "from": "VerbaPost <notifications@verbapost.com>",
            "to": user_email,
            "subject": "📜 Your Certified Mail Tracking Number",
            "html": f"<p>Your letter has been mailed! Tracking Number: <strong>{tracking}</strong></p>"
        })
    except: pass

def send_admin_alert(user_email, content, tier):
    key = get_resend_key()
    admin_email = secrets_manager.get_secret("admin.email")
    if not key or not admin_email: return

    resend.api_key = key
    try:
        resend.Emails.send({
            "from": "VerbaPost Bot <alerts@verbapost.com>",
            "to": admin_email,
            "subject": f"🔔 New {tier} Order",
            "html": f"<p>User: {user_email}</p><p>Tier: {tier}</p><p>Length: {len(content)} chars</p>"
        })
    except: pass