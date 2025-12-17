import requests
import json
import os
import streamlit as st
try:
    from secrets_manager import get_secret
except ImportError:
    get_secret = lambda x: st.secrets.get(x.split('.')[0], {}).get(x.split('.')[1])

# --- CONFIGURATION ---
BASE_URL = "https://api.postgrid.com/print-mail/v1"

def _get_api_key():
    """Retrieve API Key from secrets or env vars."""
    key = get_secret("postgrid.api_key")
    if not key:
        # Fallback for direct env var
        key = os.environ.get("POSTGRID_API_KEY")
    if not key:
        st.error("❌ Configuration Error: PostGrid API Key missing.")
        return None
    return key

def _to_postgrid_addr(addr_dict):
    """Maps internal address keys to PostGrid's required format."""
    if not addr_dict: return None
    
    # Handle both object and dict access
    def get_val(obj, key_list):
        for k in key_list:
            if isinstance(obj, dict):
                if obj.get(k): return obj[k]
            else:
                if getattr(obj, k, None): return getattr(obj, k)
        return ""

    line1 = get_val(addr_dict, ["street", "address_line1", "address"])
    city = get_val(addr_dict, ["city", "address_city"])
    state = get_val(addr_dict, ["state", "address_state", "provinceOrState"])
    zip_code = get_val(addr_dict, ["zip", "zip_code", "postalOrZip", "address_zip"])
    name = get_val(addr_dict, ["name", "full_name"]) or "Valued Customer"
    
    # Clean strings
    line1 = str(line1).strip()
    city = str(city).strip()
    state = str(state).strip()
    zip_code = str(zip_code).strip()

    if not line1 or not city or not state or not zip_code:
        return None

    payload = {
        "firstName": name,
        "addressLine1": line1,
        "city": city,
        "provinceOrState": state,
        "postalOrZip": zip_code,
        "countryCode": "US" 
    }
    
    # Optional Line 2
    line2 = get_val(addr_dict, ["street2", "address_line2", "apt", "suite"])
    if line2: payload["addressLine2"] = str(line2).strip()
        
    return payload

def validate_address(address_dict):
    """Verifies address using PostGrid /contacts endpoint."""
    api_key = _get_api_key()
    if not api_key: return False, {"error": "API Key Missing"}

    pg_addr = _to_postgrid_addr(address_dict)
    if not pg_addr: return False, {"error": "Missing critical fields"}

    try:
        response = requests.post(f"{BASE_URL}/contacts", auth=(api_key, ""), json=pg_addr, timeout=10)
        if response.status_code in [200, 201]:
            data = response.json()
            return True, {
                "address_line1": data.get("addressLine1"),
                "address_line2": data.get("addressLine2"),
                "city": data.get("city"),
                "state": data.get("provinceOrState"),
                "zip": data.get("postalOrZip"),
                "country": data.get("countryCode")
            }
        elif response.status_code == 400:
            return False, {"error": response.json().get("error", {}).get("message", "Invalid Address")}
        else:
            return False, f"API Error {response.status_code}"
    except Exception as e:
        return False, f"Exception: {str(e)}"

def send_letter(pdf_bytes, to_addr, from_addr, description="VerbaPost Letter", extra_service=None):
    """
    Uploads the PDF and creates the Letter order.
    CRITICAL FIX: Uses 'insert_blank_page' to prevent overlap errors.
    """
    api_key = _get_api_key()
    if not api_key: return None

    pg_to = _to_postgrid_addr(to_addr)
    pg_from = _to_postgrid_addr(from_addr)

    if not pg_to or not pg_from:
        print("❌ Missing address data")
        return None

    try:
        # 1. Create Contacts
        r_to = requests.post(f"{BASE_URL}/contacts", auth=(api_key, ""), json=pg_to)
        to_id = r_to.json().get("id") if r_to.status_code in [200, 201] else None
        
        r_from = requests.post(f"{BASE_URL}/contacts", auth=(api_key, ""), json=pg_from)
        from_id = r_from.json().get("id") if r_from.status_code in [200, 201] else None

        if not to_id or not from_id:
            print("❌ Contact Creation Failed")
            return None

        # 2. Upload PDF & Create Letter
        files = { 'pdf': ('letter.pdf', pdf_bytes, 'application/pdf') }
        
        data = {
            'to': to_id,
            'from': from_id,
            'description': description,
            'color': 'true',
            'express': 'true', # First Class Mail
            'envelopeType': 'standard_double_window',
            
            # --- CRITICAL FIX START ---
            # 'top_first_page' causes overlap errors if your PDF has text near the top.
            # 'insert_blank_page' adds a cover sheet, guaranteeing no content overlap.
            'addressPlacement': 'insert_blank_page', 
            # --- CRITICAL FIX END ---
        }

        if extra_service:
            data['extraService'] = extra_service

        response = requests.post(f"{BASE_URL}/letters", auth=(api_key, ""), data=data, files=files, timeout=30)

        if response.status_code in [200, 201]:
            letter_id = response.json().get('id')
            print(f"✅ Letter Sent! ID: {letter_id}")
            return letter_id
        else:
            print(f"❌ PostGrid Error: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Mailer Exception: {e}")
        return None