import requests
import json
import os
import streamlit as st
from secrets_manager import get_secret

# --- CONFIGURATION ---
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
    Maps internal address keys to PostGrid's required format.
    Returns None if critical fields are missing.
    """
    if not addr_dict:
        return None

    # Handle various key names safely
    line1 = (addr_dict.get("street") or addr_dict.get("address_line1") or "").strip()
    line2 = (addr_dict.get("street2") or addr_dict.get("address_line2") or addr_dict.get("apt") or "").strip()
    city = (addr_dict.get("city") or "").strip()
    state = (addr_dict.get("state") or addr_dict.get("provinceOrState") or "").strip()
    zip_code = (addr_dict.get("zip") or addr_dict.get("postalOrZip") or addr_dict.get("zip_code") or "").strip()
    name = (addr_dict.get("name") or addr_dict.get("full_name") or "Valued Customer").strip()

    # CRITICAL VALIDATION
    if not line1 or not city or not state or not zip_code:
        return None

    return {
        "firstName": name,
        "addressLine1": line1,
        "addressLine2": line2,
        "city": city,
        "provinceOrState": state,
        "postalOrZip": zip_code,
        "countryCode": "US" 
    }

def validate_address(address_dict):
    """
    Uses PostGrid's Verification API.
    Returns: (bool is_valid, dict details)
    """
    api_key = _get_api_key()
    if not api_key: return False, {"error": "API Key Missing"}

    pg_addr = _to_postgrid_addr(address_dict)
    if not pg_addr:
        return False, {"error": "Missing critical fields (Street, City, State, Zip)"}

    try:
        response = requests.post(
            f"{BASE_URL}/verifications/addresses",
            auth=(api_key, ""),
            json={"address": pg_addr},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "verified":
                return True, data.get("data")
            else:
                # Return the error message from PostGrid if available
                return False, data.get("error", "Address not found or invalid.")
        else:
            return False, f"API Error: {response.text}"

    except Exception as e:
        return False, f"Exception: {str(e)}"

def send_letter(pdf_bytes, to_addr, from_addr, description="VerbaPost Letter", extra_service=None):
    """
    Uploads the PDF and creates the Letter order.
    """
    api_key = _get_api_key()
    if not api_key: return False

    # 1. Convert and Validate Addresses
    pg_to = _to_postgrid_addr(to_addr)
    pg_from = _to_postgrid_addr(from_addr)

    # 2. CIRCUIT BREAKER
    if not pg_to:
        print(f"❌ Aborting Send: Invalid TO address. Data received: {to_addr}")
        return False
    if not pg_from:
        print(f"❌ Aborting Send: Invalid FROM address. Data received: {from_addr}")
        return False

    try:
        files = { 'pdf': ('letter.pdf', pdf_bytes, 'application/pdf') }
        
        data = {
            'to': json.dumps(pg_to),
            'from': json.dumps(pg_from),
            'description': description,
            'color': True,
            'express': True,
            'addressPlacement': 'top_first_page',
            'envelopeType': 'standard_double_window'
        }

        if extra_service:
            data['extraService'] = extra_service

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