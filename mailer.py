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
    Used for both sending mail AND validating addresses.
    """
    api_key = get_api_key()
    if not api_key:
        logger.error("Mailer Error: Missing API Key")
        return None

    # --- DEBUG START ---
    print(f"[DEBUG] Creating Contact for: {contact_data.get('name')}")
    # -------------------

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

    # --- DEBUG PAYLOAD ---
    print(f"[DEBUG] Payload: {json.dumps(payload)}")
    # ---------------------

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }

    try:
        url = "https://api.postgrid.com/print-mail/v1/contacts"
        resp = requests.post(url, json=payload, headers=headers)
        
        if resp.status_code in [200, 201]:
            cid = resp.json().get('id')
            print(f"[DEBUG] Contact Created: {cid}")
            return cid
        else:
            # Log the specific rejection reason (e.g., "Invalid Zip")
            logger.error(f"Contact Creation Failed: {resp.status_code} - {resp.text}")
            print(f"[DEBUG] Contact Failed: {resp.text}")
            return None

    except Exception as e:
        logger.error(f"Contact Exception: {e}")
        return None

def validate_address(address_dict):
    """
    Validates an address by attempting to create a Contact.
    This bypasses the need for a separate Address Verification subscription.
    """
    print(f"[VALIDATION] Testing address via Contact Creation...")
    
    # We attempt to create the contact.
    # If successful, PostGrid has accepted the address as valid (or valid enough to mail).
    contact_id = _create_contact(address_dict)
    
    if contact_id:
        # Success! The address is valid.
        # We return the original address_dict because _create_contact doesn't return normalized data,
        # but the ID proves it is safe to use.
        return True, address_dict
    else:
        # Failure. PostGrid rejected it (likely Error 400 - Invalid Address).
        return False, {"error": "Address Rejected by Post Office. Please check Street and Zip Code."}

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