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

def get_postgrid_key(): 
    key = secrets_manager.get_secret("postgrid.api_key") or secrets_manager.get_secret("POSTGRID_API_KEY")
    return key.strip() if key else None

def get_resend_key(): 
    key = secrets_manager.get_secret("email.password") or secrets_manager.get_secret("RESEND_API_KEY")
    return key.strip() if key else None

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
            return False, f"Address verification failed ({r.status_code})"

    except Exception as e:
        circuit_breaker.failure_count += 1
        circuit_breaker.last_failure = datetime.now()
        logger.error(f"Address Verify Fail: {e}")
        return False, "Address verification system error"

def flatten_contact(prefix, data):
    """
    Converts internal snake_case dict to PostGrid camelCase bracket syntax.
    Example: {'address_line1': '123 Main'} -> {'to[addressLine1]': '123 Main'}
    """
    # Map internal keys to PostGrid API keys
    key_map = {
        'name': 'firstName', # PostGrid requires firstName/lastName or companyName. Mapping full name to firstName is usually safe.
        'address_line1': 'addressLine1',
        'address_line2': 'addressLine2',
        'address_city': 'city',
        'address_state': 'provinceOrState',
        'address_zip': 'postalOrZip',
        'country_code': 'countryCode'
    }
    
    flat = {}
    for k, v in data.items():
        pg_key = key_map.get(k, k) # Use mapped key or fallback to original
        flat[f"{prefix}[{pg_key}]"] = v
    return flat

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
    
    # Base Options
    data = {
        'express': 'true' if certified else 'false',
        'addressPlacement': 'top_first_page',
        'color': 'false',
        'doubleSided': 'true' # Often a good default
    }
    
    if certified: data['extraService'] = 'certified'

    # --- CRITICAL FIX: FLATTEN CONTACT OBJECTS ---
    # We merge the flattened dictionaries into the main data payload
    data.update(flatten_contact("to", to_addr))
    data.update(flatten_contact("from", from_addr))

    # Idempotency
    try:
        with open(pdf_path, 'rb') as f: pdf_content = f.read()
        # Sort keys to ensure consistent signature
        payload_sig = json.dumps(data, sort_keys=True).encode() + pdf_content
        idempotency_key = hashlib.sha256(payload_sig).hexdigest()
        headers = {"x-api-key": api_key, "Idempotency-Key": idempotency_key}
    except Exception as e:
        logger.error(f"Idempotency Gen Failed: {e}")
        headers = {"x-api-key": api_key}

    try:
        with open(pdf_path, 'rb') as f_pdf:
            files = {'pdf': f_pdf}
            # Sending as multipart/form-data
            response = requests.post(url, headers=headers, data=data, files=files, timeout=30)
            
        if response.status_code in [200, 201]:
            res = response.json()
            logger.info(f"Mail Sent! ID: {res.get('id')}")
            return True, res
        else:
            err_msg = response.text
            logger.error(f"PostGrid Error: {err_msg}")
            return False, f"API Error {response.status_code}: {err_msg}"

    except Exception as e:
        logger.error(f"Connection Error: {e}")
        raise