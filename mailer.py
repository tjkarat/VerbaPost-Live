import requests
import json
import os
import streamlit as st
from secrets_manager import get_secret

# --- CONFIGURATION ---
# We use the Print & Mail API for EVERYTHING (Sending & Verifying)
BASE_URL = "https://api.postgrid.com/print-mail/v1"

def _get_api_key():
    """Retrieve API Key from secrets or env vars."""
    # This grabs 'postgrid.api_key' which will be the TEST key in QA and LIVE key in Prod
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
    Uses PostGrid's Print & Mail Verification Endpoint.
    """
    api_key = _get_api_key()
    if not api_key: return False, {"error": "API Key Missing"}

    pg_addr = _to_postgrid_addr(address_dict)
    if not pg_addr:
        return False, {"error": "Missing critical fields (Street, City, State, Zip)"}

    try:
        # FIX: The correct endpoint for Print & Mail verification is /verifications
        # We removed "/address" from the end.
        response = requests.post(
            url = f"{BASE_URL}/verifications", 
            auth=(api_key, ""),
            json={"address": pg_addr},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success") or data.get("status") in ["verified", "corrected"]: 
                # PostGrid Print & Mail API typically returns the verified address in 'data'
                return True, data.get("data", data) 
            else:
                return False, data.get("error", "Address not found or invalid.")
        else:
            return False, f"API Error {response.status_code}: {response.text}"

    except Exception as e:
        return False, f"Exception: {str(e)}"

def send_letter(pdf_bytes, to_addr, from_addr, description="VerbaPost Letter", extra_service=None):
    """
    Uploads the PDF and creates the Letter order.
    """
    api_key = _get_api_key()
    if not api_key: return False

    pg_to = _to_postgrid_addr(to_addr)
    pg_from = _to_postgrid_addr(from_addr)

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