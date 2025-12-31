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
    Now with DEBUG LOGGING.
    """
    api_key = get_api_key()
    if not api_key:
        logger.error("Mailer Error: Missing API Key")
        return None

    # --- DEBUG: PRINT THE EXACT DATA ---
    logger.info(f"--------------------------------------------------")
    logger.info(f"[DEBUG] Creating Contact for: {contact_data.get('name')}")
    logger.info(f"[DEBUG] Raw Data: {contact_data}")
    # -----------------------------------

    # PostGrid requires CamelCase for keys (addressLine1, firstName)
    # We must map our snake_case keys manually.
    
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

    # --- DEBUG: PRINT THE API PAYLOAD ---
    logger.info(f"[DEBUG] JSON Payload to PostGrid: {json.dumps(payload, indent=2)}")
    # ------------------------------------

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json" # CRITICAL: Must be JSON
    }

    try:
        # Use the /contacts endpoint
        url = "https://api.postgrid.com/print-mail/v1/contacts"
        
        resp = requests.post(url, json=payload, headers=headers)
        
        # --- DEBUG: PRINT RESPONSE ---
        logger.info(f"[DEBUG] PostGrid Response Code: {resp.status_code}")
        logger.info(f"[DEBUG] PostGrid Response Body: {resp.text}")
        logger.info(f"--------------------------------------------------")
        # -----------------------------

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
    """
    api_key = get_api_key()
    if not api_key: return False, {"error": "Configuration Error"}

    # Map to Verification format (standard 'line1', etc.)
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
        # Note: Verification endpoint is different
        url = "https://api.postgrid.com/print-mail/v1/addver/verifications"
        resp = requests.post(url, json=payload, headers=headers)
        
        if resp.status_code == 200:
            data = resp.json()
            if data.get('status') == 'verified':
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
                # Return the specific error from PostGrid
                return False, {"error": f"Address Invalid: {data.get('summary', 'Unknown Issue')}"}
        else:
            return False, {"error": f"API Error {resp.status_code}"}
            
    except Exception as e:
        return False, {"error": str(e)}

def send_letter(pdf_bytes, to_addr, from_addr, description="VerbaPost Letter"):
    """
    Sends a letter via PostGrid using the 2-step contact creation method.
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
        
        # We send data as multipart/form-data because we are uploading a file
        files = {
            'pdf': ('letter.pdf', pdf_bytes, 'application/pdf')
        }
        
        data = {
            'to': to_id,
            'from': from_id,
            'description': description,
            'color': 'true', # Force color for Vintage/Logos
            'express': 'false',
            'addressPlacement': 'top_first_page' # CRITICAL for window envelopes
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