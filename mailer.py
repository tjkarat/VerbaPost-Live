import streamlit as st
import requests
import resend
import secrets_manager
import hashlib
import json
import time
import logging
import os
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CIRCUIT BREAKER ---
class AddressVerificationCircuitBreaker:
    def __init__(self):
        self.failure_count = 0
        self.last_failure = None
        self.threshold = 3
        self.timeout = timedelta(minutes=5)

    def is_open(self):
        if self.last_failure and datetime.now() - self.last_failure < self.timeout:
            return self.failure_count >= self.threshold
        self.failure_count = 0  # Reset after timeout
        return False

circuit_breaker = AddressVerificationCircuitBreaker()

def get_postgrid_key(): return secrets_manager.get_secret("postgrid.api_key") or secrets_manager.get_secret("POSTGRID_API_KEY")
def get_resend_key(): return secrets_manager.get_secret("email.password") or secrets_manager.get_secret("RESEND_API_KEY")

def verify_address_data(line1, line2, city, state, zip_code, country_code):
    api_key = get_postgrid_key()
    if not api_key: return True, None 

    if circuit_breaker.is_open():
        logger.error("Circuit breaker open - PostGrid unavailable")
        return False, "Address verification temporarily unavailable. Please try again later."

    url = "https://api.postgrid.com/v1/addver/verifications"
    payload = {
        "line1": line1, "line2": line2, "city": city,
        "provinceOrState": state, "postalOrZip": zip_code, "country": country_code
    }
    
    try:
        r = requests.post(url, headers={"x-api-key": api_key}, data=payload, timeout=5)
        
        if r.status_code == 200:
            circuit_breaker.failure_count = 0
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
            circuit_breaker.failure_count += 1
            circuit_breaker.last_failure = datetime.now()
            logger.error(f"PostGrid API Error: {r.status_code} - {r.text}")
            return False, f"Address verification failed (API Error)"

    except Exception as e:
        circuit_breaker.failure_count += 1
        circuit_breaker.last_failure = datetime.now()
        logger.error(f"Address Verify Fail: {e}")
        return False, "Address verification system error"

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((requests.Timeout, requests.ConnectionError)),
    reraise=True
)
def send_letter(pdf_path, to_addr, from_addr, certified=False):
    api_key = get_postgrid_key()
    if not api_key: return False, "Missing API Key"

    url = "https://api.postgrid.com/print-mail/v1/letters"
    
    data = {
        'to': json.dumps(to_addr),
        'from': json.dumps(from_addr),
        'express': 'true' if certified else 'false',
        'addressPlacement': 'top_first_page',
        'color': 'false'
    }
    
    if certified: data['extraService'] = 'certified'

    try:
        with open(pdf_path, 'rb') as f: pdf_content = f.read()
        payload_sig = json.dumps(data, sort_keys=True).encode() + pdf_content
        idempotency_key = hashlib.sha256(payload_sig).hexdigest()
        headers = {"x-api-key": api_key, "Idempotency-Key": idempotency_key}
    except Exception as e:
        logger.error(f"Idempotency Gen Failed: {e}")
        headers = {"x-api-key": api_key}

    try:
        with open(pdf_path, 'rb') as f_pdf:
            files = {'pdf': f_pdf}
            response = requests.post(url, headers=headers, data=data, files=files, timeout=30)
            
        if response.status_code in [200, 201]:
            res = response.json()
            logger.info(f"Mail Sent! ID: {res.get('id')}")
            try:
                if certified and res.get('trackingNumber'):
                    send_tracking_email(from_addr.get('email'), res.get('trackingNumber'))
            except: pass
            return True, res
        else:
            logger.error(f"PostGrid Error: {response.text}")
            return False, f"API Error: {response.status_code}"

    except Exception as e:
        logger.error(f"Connection Error: {e}")
        raise # Allow tenacity to retry