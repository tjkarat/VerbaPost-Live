import requests
import json
import os
import streamlit as st
from secrets_manager import get_secret

# --- CONFIGURATION ---
# Use the correct endpoint for "Print & Mail" (Letters)
BASE_URL = "https://api.postgrid.com/print-mail/v1"

def _get_api_key():
    """Retrieve API Key from secrets or env vars."""
    key = get_secret("postgrid.api_key")
    if not key:
        st.error("❌ Configuration Error: PostGrid API Key missing.")
        return None
    return key

def _to_postgrid_addr(addr_dict):
    """
    CRITICAL FIX: Maps internal address keys to PostGrid's required format.
    Internal: street, city, state, zip
    PostGrid: addressLine1, city, provinceOrState, postalOrZip, countryCode
    """
    if not addr_dict:
        return {}

    # 1. Extract values safely using multiple possible keys
    line1 = (addr_dict.get("street") or 
             addr_dict.get("address_line1") or 
             addr_dict.get("line1") or 
             "").strip()
             
    line2 = (addr_dict.get("street2") or 
             addr_dict.get("address_line2") or 
             addr_dict.get("apt") or 
             "").strip()
             
    city = (addr_dict.get("city") or "").strip()
    
    state = (addr_dict.get("state") or 
             addr_dict.get("provinceOrState") or 
             "").strip()
             
    zip_code = (addr_dict.get("zip") or 
                addr_dict.get("postalOrZip") or 
                addr_dict.get("zip_code") or 
                "").strip()
    
    name = (addr_dict.get("name") or 
            addr_dict.get("full_name") or 
            "Valued Customer").strip()

    # 2. Return strictly formatted dictionary
    return {
        "firstName": name,  # PostGrid can take 'firstName' as full name line
        "addressLine1": line1,
        "addressLine2": line2,
        "city": city,
        "provinceOrState": state,
        "postalOrZip": zip_code,
        "countryCode": "US"  # Defaulting to US for safety
    }

def validate_address(address_dict):
    """
    Uses PostGrid's Verification API to check if an address is real.
    Returns: (is_valid: bool, suggestion: dict)
    """
    api_key = _get_api_key()
    if not api_key: 
        return False, None

    # Transform to PostGrid format first
    payload = {"address": _to_postgrid_addr(address_dict)}
    
    try:
        response = requests.post(
            f"{BASE_URL}/verifications/addresses",
            auth=(api_key, ""),
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            # "verified" status means it's deliverable
            if data.get("status") == "verified":
                return True, data.get("data")
            else:
                return False, data.get("data") # Return suggestion anyway
        else:
            print(f"PostGrid Verification Error: {response.text}")
            return True, None # Fail open (allow it) if API errors

    except Exception as e:
        print(f"Address Validation Exception: {e}")
        return True, None # Fail open

def send_letter(pdf_bytes, to_addr, from_addr, description="VerbaPost Letter"):
    """
    Uploads the PDF and creates the Letter order in one flow.
    """
    api_key = _get_api_key()
    if not api_key: return False

    # 1. Transform Addresses
    pg_to = _to_postgrid_addr(to_addr)
    pg_from = _to_postgrid_addr(from_addr)

    # Validate mandatory fields before sending
    if not pg_to.get("addressLine1") or not pg_to.get("postalOrZip"):
        print(f"❌ Aborting: Missing address fields. Data: {pg_to}")
        return False

    try:
        # 2. Create the Letter (using inline PDF upload if supported, or Create Contact first)
        # For simplicity and reliability, we send the contacts directly in the 'create' call.
        
        files = {
            'pdf': ('letter.pdf', pdf_bytes, 'application/pdf')
        }
        
        # We must pass the address data as JSON strings because we are using multipart/form-data
        data = {
            'to': json.dumps(pg_to),
            'from': json.dumps(pg_from),
            'description': description,
            'color': True,
            'express': True, # First Class
            'addressPlacement': 'top_first_page', # Ensures address shows in window
            'envelopeType': 'standard_double_window'
        }

        response = requests.post(
            f"{BASE_URL}/letters",
            auth=(api_key, ""),
            data=data,
            files=files,
            timeout=30
        )

        if response.status_code in [200, 201]:
            print(f"✅ Letter Sent! ID: {response.json().get('id')}")
            return True
        else:
            print(f"❌ PostGrid Error: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Mailer Exception: {e}")
        return False