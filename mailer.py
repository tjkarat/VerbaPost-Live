import requests
import json
import os
import streamlit as st
import logging

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
# PostGrid Address Verification API
POSTGRID_VERIFY_URL = "https://api.postgrid.com/v1/add_ver/verifications"
# PostGrid Print & Mail API (for sending letters later)
POSTGRID_PRINT_URL = "https://api.postgrid.com/print-mail/v1/letters"

def get_api_key():
    """Retrieves PostGrid API Key from secrets."""
    # Check secrets.toml first
    if hasattr(st, "secrets") and "postgrid" in st.secrets:
        return st.secrets["postgrid"].get("api_key")
    # Fallback to environment variable
    return os.environ.get("POSTGRID_API_KEY")

def validate_address(address_dict):
    """
    Validates address via PostGrid Verification API.
    Docs: https://postgrid.readme.io/reference/verify-an-address
    """
    api_key = get_api_key()
    if not api_key: 
        logger.warning("PostGrid Key missing. Skipping validation (Soft Pass).")
        return True, "Dev Mode: Validation Skipped"

    # Construct Payload expected by PostGrid
    payload = {
        "address": {
            "line1": address_dict.get('street') or address_dict.get('address_line1'),
            "city": address_dict.get('city'),
            "provinceOrState": address_dict.get('state'),
            "postalOrZip": address_dict.get('zip_code') or address_dict.get('zip'),
            "country": address_dict.get('country', "US")
        }
    }

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(POSTGRID_VERIFY_URL, json=payload, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            
            # PostGrid returns a 'status' field in the 'result' object
            # Statuses: 'verified', 'corrected', 'active'
            result = data.get('data', {})
            status = result.get('status')
            
            if status == 'verified':
                # Perfect match
                return True, result
            elif status == 'corrected':
                # It fixed a typo (e.g. "St" -> "Street"), we accept this
                logger.info(f"Address Auto-Corrected: {result.get('summary')}")
                return True, result
            else:
                # Failed (e.g. 'unverified', 'ambiguous')
                errors = result.get('errors', {})
                error_msg = f"Invalid Address: {errors}" if errors else "Address could not be verified."
                return False, error_msg
                
        elif response.status_code == 401:
            return False, "System Error: Invalid PostGrid API Key"
        else:
            logger.error(f"PostGrid Error {response.status_code}: {response.text}")
            # In production, we might want to fail open if the API is down
            # For now, we return the error to the user
            return False, f"Verification Service unavailable ({response.status_code})"

    except Exception as e:
        logger.error(f"Validation Exception: {e}")
        # Fail Open (Allow signup if our validator crashes) to prevent blocking users
        return True, "Validation Service Offline (Soft Pass)"

def send_letter(pdf_bytes, to_addr, from_addr, description="VerbaPost Letter"):
    """
    Sends PDF via PostGrid Print & Mail API.
    Docs: https://postgrid.readme.io/reference/create-letter
    """
    api_key = get_api_key()
    if not api_key: return None

    # Prepare Multipart Upload
    # PostGrid accepts the PDF file directly in the request
    files = {
        'pdf': ('letter.pdf', pdf_bytes, 'application/pdf')
    }

    data = {
        "to": {
            "firstName": to_addr.get('name'),
            "addressLine1": to_addr.get('street'),
            "city": to_addr.get('city'),
            "provinceOrState": to_addr.get('state'),
            "postalOrZip": to_addr.get('zip'),
            "countryCode": "US"
        },
        "from": {
            "firstName": from_addr.get('name'),
            "addressLine1": from_addr.get('street'),
            "city": from_addr.get('city'),
            "provinceOrState": from_addr.get('state'),
            "postalOrZip": from_addr.get('zip'),
            "countryCode": "US"
        },
        "description": description,
        "color": True,
        "express": False # Standard Class Mail
    }

    # Note: PostGrid Send API uses form-data style when sending files
    # We need to flatten the nested dicts or use their SDK. 
    # For raw requests, passing JSON as a string field often works, 
    # but PostGrid prefers individual form fields.
    
    # SIMPLIFIED APPROACH: Use JSON + URL for PDF if you host it. 
    # Since we have bytes, we must use multipart/form-data.
    # We will flatten the 'to' and 'from' fields for the form-data logic.
    
    form_data = {
        "to[firstName]": to_addr.get('name'),
        "to[addressLine1]": to_addr.get('street'),
        "to[city]": to_addr.get('city'),
        "to[provinceOrState]": to_addr.get('state'),
        "to[postalOrZip]": to_addr.get('zip'),
        "to[countryCode]": "US",
        
        "from[firstName]": from_addr.get('name'),
        "from[addressLine1]": from_addr.get('street'),
        "from[city]": from_addr.get('city'),
        "from[provinceOrState]": from_addr.get('state'),
        "from[postalOrZip]": from_addr.get('zip'),
        "from[countryCode]": "US",
        
        "description": description,
        "color": "true"
    }

    try:
        response = requests.post(
            POSTGRID_PRINT_URL,
            headers={"x-api-key": api_key},
            files=files,
            data=form_data
        )

        if response.status_code in [200, 201]:
            return response.json().get('id')
        else:
            logger.error(f"PostGrid Send Failed: {response.text}")
            return None
    except Exception as e:
        logger.error(f"PostGrid Exception: {e}")
        return None