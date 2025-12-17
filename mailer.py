import requests
import json
import os
import streamlit as st
from secrets_manager import get_secret

# --- CONFIGURATION ---
# We use the Print & Mail API for EVERYTHING
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
    """
    if not addr_dict:
        return None

    line1 = (addr_dict.get("street") or addr_dict.get("address_line1") or "").strip()
    line2 = (addr_dict.get("street2") or addr_dict.get("address_line2") or addr_dict.get("apt") or "").strip()
    city = (addr_dict.get("city") or "").strip()
    state = (addr_dict.get("state") or addr_dict.get("provinceOrState") or "").strip()
    zip_code = (addr_dict.get("zip") or addr_dict.get("postalOrZip") or addr_dict.get("zip_code") or "").strip()
    name = (addr_dict.get("name") or addr_dict.get("full_name") or "Valued Customer").strip()

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
    WORKAROUND: Verifies address by creating a temporary 'Contact' 
    using the Print & Mail API key.
    """
    api_key = _get_api_key()
    if not api_key: return False, {"error": "API Key Missing"}

    pg_addr = _to_postgrid_addr(address_dict)
    if not pg_addr:
        return False, {"error": "Missing critical fields"}

    try:
        # Use /contacts to validate address syntax
        response = requests.post(
            url = f"{BASE_URL}/contacts", 
            auth=(api_key, ""),
            json=pg_addr,
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            standardized_data = {
                "address_line1": data.get("addressLine1"),
                "address_line2": data.get("addressLine2"),
                "city": data.get("city"),
                "state": data.get("provinceOrState"),
                "zip": data.get("postalOrZip"),
                "country": data.get("countryCode")
            }
            return True, standardized_data
            
        elif response.status_code == 400:
            err_msg = response.json().get("error", {}).get("message", "Invalid Address")
            return False, {"error": err_msg}
            
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

    if not pg_to or not pg_from:
        return False

    try:
        # 1. Create Contacts First (Recommended by PostGrid Best Practices)
        # This ensures we get valid IDs before trying to send the letter
        
        # Create To Contact
        r_to = requests.post(f"{BASE_URL}/contacts", auth=(api_key, ""), json=pg_to)
        if r_to.status_code not in [200, 201]:
            print(f"❌ Recipient Error: {r_to.text}")
            return False
        to_id = r_to.json().get("id")
        
        # Create From Contact
        r_from = requests.post(f"{BASE_URL}/contacts", auth=(api_key, ""), json=pg_from)
        if r_from.status_code not in [200, 201]:
            print(f"❌ Sender Error: {r_from.text}")
            return False
        from_id = r_from.json().get("id")

        # 2. Upload PDF & Create Letter
        # We use multipart/form-data for the PDF file
        files = { 'pdf': ('letter.pdf', pdf_bytes, 'application/pdf') }
        
        data = {
            'to': to_id,     # Use ID reference
            'from': from_id, # Use ID reference
            'description': description,
            'color': 'true',
            'express': 'true',
            'addressPlacement': 'top_first_page',
            'envelopeType': 'standard_double_window'
        }

        if extra_service:
            data['extraService'] = extra_service

        # The endpoint MUST be /letters in the print-mail/v1 namespace
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
            print(f"❌ PostGrid Letter Error: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Mailer Exception: {e}")
        return False