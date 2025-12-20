import streamlit as st
import requests
import base64
import logging

# --- CONFIGURATION ---
logger = logging.getLogger(__name__)

try: import secrets_manager
except ImportError: secrets_manager = None

def get_postgrid_key():
    if secrets_manager:
        return secrets_manager.get_secret("postgrid.api_key")
    if "postgrid" in st.secrets:
        return st.secrets["postgrid"]["api_key"]
    return None

def validate_address(address_dict):
    """
    Validates an address using PostGrid's verification API.
    """
    api_key = get_postgrid_key()
    if not api_key:
        return False, {"error": "API Key Missing"}

    url = "https://api.postgrid.com/print-mail/v1/add_verifications"
    payload = {
        "addressLine1": address_dict.get("street", ""),
        "city": address_dict.get("city", ""),
        "stateOrProvinceCode": address_dict.get("state", ""),
        "postalOrZipCode": address_dict.get("zip_code", ""),
        "countryCode": "US"
    }
    
    try:
        response = requests.post(url, auth=(api_key, ""), data=payload)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "verified":
                # Return standardized dict
                return True, {
                    "street": data["addressLine1"],
                    "city": data["city"],
                    "state": data["stateOrProvinceCode"],
                    "zip_code": data["postalOrZipCode"],
                    "country": "US"
                }
            else:
                return False, {"error": "Address not verifiable"}
        else:
            return False, {"error": f"API Error: {response.status_code}"}
    except Exception as e:
        return False, {"error": str(e)}

def send_letter(pdf_bytes, addr_to, addr_from, description="VerbaPost Letter"):
    """
    Sends a PDF letter via PostGrid.
    Returns: Letter ID (str) on success, None on failure.
    """
    api_key = get_postgrid_key()
    if not api_key:
        logger.error("PostGrid API Key missing")
        return None

    url = "https://api.postgrid.com/print-mail/v1/letters"
    
    # Create the contact for the recipient
    to_payload = {
        "firstName": addr_to.name,
        "addressLine1": addr_to.street,
        "city": addr_to.city,
        "stateOrProvinceCode": addr_to.state,
        "postalOrZipCode": addr_to.zip_code,
        "countryCode": "US"
    }

    # Create the contact for the sender
    from_payload = {
        "firstName": addr_from.name,
        "addressLine1": addr_from.street,
        "city": addr_from.city,
        "stateOrProvinceCode": addr_from.state,
        "postalOrZipCode": addr_from.zip_code,
        "countryCode": "US"
    }

    # Prepare file
    # For PostGrid, we typically upload the file first or send as base64/multipart.
    # Simple approach: Multipart upload
    files = {
        'pdf': ('letter.pdf', pdf_bytes, 'application/pdf')
    }
    
    data = {
        "to": to_payload,
        "from": from_payload,
        "description": description,
        "color": True,
        "express": False
    }

    try:
        # Note: PostGrid Python requests usually handle dicts for 'to'/'from' if creating contacts inline
        # But robust way is creating contacts first. For simplicity here, assuming API accepts inline object.
        # If not, we'd adjust to create_contact -> get ID -> send letter.
        
        # NOTE: requests.post with 'files' and 'data' sends multipart/form-data.
        # Nested dicts in 'data' might need JSON stringifying if API expects JSON body vs Form data.
        # PostGrid expects JSON if sending links, or Form if sending files.
        # Let's try sending as PDF upload.
        
        response = requests.post(url, auth=(api_key, ""), files=files, data=data)
        
        if response.status_code in [200, 201]:
            res_json = response.json()
            return res_json.get("id")
        else:
            logger.error(f"PostGrid Error {response.status_code}: {response.text}")
            return None

    except Exception as e:
        logger.error(f"Mailer Exception: {e}")
        return None