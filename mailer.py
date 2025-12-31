import requests
import json
import os
import streamlit as st
import logging

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_api_key():
    """
    Retrieves the PostGrid API Key safely.
    """
    key = None
    # 1. Check Secrets
    if hasattr(st, "secrets") and "postgrid" in st.secrets:
        key = st.secrets["postgrid"].get("api_key")
    
    # 2. Check Environment
    if not key:
        key = os.environ.get("POSTGRID_API_KEY")
        
    if key:
        # Sanitize: Remove quotes or whitespace that might have been copied
        return str(key).strip().replace("'", "").replace('"', "")
    return None

def _create_contact(contact_data):
    """
    Internal helper to create a contact in PostGrid and get an ID.
    """
    api_key = get_api_key()
    if not api_key:
        logger.error("Mailer Error: Missing API Key")
        return None

    # Split Name if possible
    full_name = str(contact_data.get('name', ''))
    first_name = full_name
    last_name = ""
    if " " in full_name:
        parts = full_name.split(" ", 1)
        first_name = parts[0]
        last_name = parts[1]

    # Map Fields
    payload = {
        "firstName": first_name,
        "lastName": last_name,
        "addressLine1": str(contact_data.get('address_line1') or contact_data.get('street') or ""),
        "addressLine2": str(contact_data.get('address_line2') or ""),
        "city": str(contact_data.get('city') or ""),
        "provinceOrState": str(contact_data.get('state') or ""),
        "postalOrZip": str(contact_data.get('zip_code') or contact_data.get('zip') or ""),
        "countryCode": "US"
    }

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }

    try:
        url = "https://api.postgrid.com/print-mail/v1/contacts"
        resp = requests.post(url, json=payload, headers=headers)
        
        if resp.status_code in [200, 201]:
            return resp.json().get('id')
        else:
            logger.error(f"Contact Creation Failed: {resp.status_code} - {resp.text}")
            return None

    except Exception as e:
        logger.error(f"Contact Exception: {e}")
        return None

def validate_address(address_dict):
    """
    Validates an address using PostGrid's verification endpoint.
    FIXED: Uses the correct Print & Mail verification URL to avoid 404s.
    """
    api_key = get_api_key()
    if not api_key: return False, {"error": "Configuration Error"}

    # Map to Verification format
    payload = {
        "address": {
            "line1": str(address_dict.get('street') or address_dict.get('address_line1') or ""),
            "city": str(address_dict.get('city') or ""),
            "provinceOrState": str(address_dict.get('state') or ""),
            "postalOrZip": str(address_dict.get('zip_code') or address_dict.get('zip') or ""),
            "countryCode": "US"
        }
    }

    headers = {"x-api-key": api_key, "Content-Type": "application/json"}
    
    try:
        # --- CRITICAL FIX: Correct Endpoint for Print & Mail ---
        url = "https://api.postgrid.com/print-mail/v1/verifications"
        resp = requests.post(url, json=payload, headers=headers)
        
        if resp.status_code == 200:
            data = resp.json()
            # PostGrid returns 'status': 'verified' or 'corrected' or 'failed'
            if data.get('status') in ['verified', 'corrected']:
                # Return the cleaned, standardized address
                verified_addr = data.get('data', {})
                clean_data = {
                    "street": verified_addr.get('line1'),
                    "city": verified_addr.get('city'),
                    "state": verified_addr.get('provinceOrState'),
                    "zip_code": verified_addr.get('postalOrZip'),
                    "name": address_dict.get('name')
                }
                return True, clean_data
            else:
                return False, {"error": f"Address Invalid: {data.get('summary', 'Unknown Issue')}"}
        else:
            return False, {"error": f"API Error {resp.status_code}"}
            
    except Exception as e:
        return False, {"error": str(e)}

def send_letter(pdf_bytes, to_addr, from_addr, description="VerbaPost Letter"):
    """
    Sends a letter via PostGrid.
    """
    api_key = get_api_key()
    if not api_key: 
        logger.error("Missing API Key")
        return None

    # 1. Create Contacts First
    to_id = _create_contact(to_addr)
    from_id = _create_contact(from_addr)

    if not to_id or not from_id:
        logger.error("Failed to create contacts. Aborting.")
        return None

    # 2. Create Letter
    try:
        url = "https://api.postgrid.com/print-mail/v1/letters"
        
        files = {
            'pdf': ('letter.pdf', pdf_bytes, 'application/pdf')
        }
        
        data = {
            'to': to_id,
            'from': from_id,
            'description': description,
            'color': 'true', 
            'express': 'false',
            'addressPlacement': 'top_first_page'
        }

        resp = requests.post(url, headers={"x-api-key": api_key}, files=files, data=data)
        
        if resp.status_code in [200, 201]:
            letter_id = resp.json().get('id')
            logger.info(f"Letter Sent! ID: {letter_id}")
            return letter_id
        else:
            logger.error(f"Letter Failed: {resp.status_code} - {resp.text}")
            return None

    except Exception as e:
        logger.error(f"Mailing Exception: {e}")
        return None