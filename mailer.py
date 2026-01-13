import requests
import json
import os
import streamlit as st
import logging

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
# Base URL for PCM Integrations V3
PCM_BASE_URL = "https://api.pcmintegrations.com/v3" 

def get_api_key():
    """Retrieves PCM Integrations API Key from secrets."""
    key = None
    if hasattr(st, "secrets") and "pcm" in st.secrets:
        key = st.secrets["pcm"].get("api_key")
    if not key:
        key = os.environ.get("PCM_API_KEY")
    return str(key).strip().replace("'", "").replace('"', "") if key else None

def validate_address(address_dict):
    """
    Validates address via PCM Integrations.
    Docs: https://docs.pcmintegrations.com/docs/directmail-api/84aca6606cef4-direct-mail-api-v3
    """
    api_key = get_api_key()
    if not api_key: return False, "Missing PCM API Key"

    # NOTE: Check if your endpoint requires a specific path like /address/verify
    # We use /recipient/verify based on typical V3 patterns, but check docs if 404 persists.
    url = f"{PCM_BASE_URL}/recipient/verify"
    
    payload = {
        "address1": address_dict.get('street') or address_dict.get('address_line1'),
        "address2": address_dict.get('street2') or address_dict.get('address_line2', ""),
        "city": address_dict.get('city'),
        "state": address_dict.get('state'),
        "zip": address_dict.get('zip_code') or address_dict.get('zip'),
        "country": address_dict.get('country', "US")
    }

    try:
        # Bearer Token Auth (Strict Adherence)
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        resp = requests.post(url, json=payload, headers=headers)
        
        if resp.status_code == 200:
            data = resp.json()
            if data.get('isValid') or data.get('status') == 'verified':
                return True, address_dict
            else:
                return False, "Address rejected by carrier (USPS)."
        else:
            logger.error(f"PCM Error {resp.status_code} at {url}: {resp.text}")
            return False, f"Verification Service Error: {resp.status_code}"
            
    except Exception as e:
        logger.error(f"Validation Exception: {e}")
        return False, "Validation Service Unavailable"

def send_letter(pdf_bytes, to_addr, from_addr):
    """
    Sends PDF via PCM Integrations V3.
    """
    api_key = get_api_key()
    if not api_key: return None

    url = f"{PCM_BASE_URL}/orders/create" 

    files = {
        'file': ('letter.pdf', pdf_bytes, 'application/pdf')
    }
    
    metadata = {
        "recipient": {
            "name": to_addr.get('name'),
            "address1": to_addr.get('street'),
            "city": to_addr.get('city'),
            "state": to_addr.get('state'),
            "zip": to_addr.get('zip')
        },
        "sender": {
            "name": from_addr.get('name'),
            "address1": from_addr.get('street'),
            "city": from_addr.get('city'),
            "state": from_addr.get('state'),
            "zip": from_addr.get('zip')
        },
        "options": {
            "printColor": True,
            "envelopeType": "standard_double_window"
        }
    }

    try:
        resp = requests.post(
            url, 
            headers={"Authorization": f"Bearer {api_key}"},
            files=files,
            data={"order_data": json.dumps(metadata)} 
        )

        if resp.status_code in [200, 201]:
            return resp.json().get('id')
        else:
            logger.error(f"PCM Send Failed: {resp.text}")
            return None
    except Exception as e:
        logger.error(f"PCM Exception: {e}")
        return None