import requests
import secrets_manager
import logging
import json

# Import the missing module safely
try:
    import address_standard
except ImportError:
    address_standard = None

logger = logging.getLogger(__name__)

def _to_camel_case_payload(snake_payload):
    """
    CRITICAL FIX: 
    1. Maps snake_case keys to PostGrid CamelCase.
    2. SPLITS single 'name' field into 'firstName' and 'lastName' (Required by API).
    """
    # 1. Name Splitting Logic
    full_name = snake_payload.get('name', '').strip()
    first_name = full_name
    last_name = ""
    
    if " " in full_name:
        # Split on first space only (e.g. "John Von Neumann" -> First: "John", Last: "Von Neumann")
        parts = full_name.split(" ", 1)
        first_name = parts[0]
        last_name = parts[1]

    # 2. Construct Payload
    return {
        'firstName': first_name,
        'lastName': last_name,
        'addressLine1': snake_payload.get('address_line1', '') or snake_payload.get('street', ''),
        'addressLine2': snake_payload.get('address_line2', '') or snake_payload.get('addressLine2', ''),
        'city': snake_payload.get('address_city', '') or snake_payload.get('city', ''),
        'provinceOrState': snake_payload.get('address_state', '') or snake_payload.get('state', ''),
        'postalOrZip': snake_payload.get('address_zip', '') or snake_payload.get('zip', '') or snake_payload.get('zip_code', ''),
        'countryCode': snake_payload.get('country_code', 'US') or snake_payload.get('country', 'US')
    }

def _create_postgrid_contact(payload, api_key):
    """
    Helper: Creates a contact in PostGrid and returns the Contact ID.
    """
    url = "https://api.postgrid.com/print-mail/v1/contacts"
    
    # Apply the Name Split & Key Mapping fix
    clean_payload = _to_camel_case_payload(payload)
    
    try:
        r = requests.post(url, json=clean_payload, headers={"x-api-key": api_key})
        if r.status_code in [200, 201]:
            return r.json().get('id')
        else:
            logger.error(f"Contact Creation Failed: {r.status_code} - {r.text}")
            return None
    except Exception as e:
        logger.error(f"Contact Creation Exception: {e}")
        return None

def validate_address(address_data):
    """
    Validates an address using PostGrid's verification API.
    """
    api_key = secrets_manager.get_secret("postgrid.api_key") or secrets_manager.get_secret("POSTGRID_API_KEY")
    if not api_key:
        return False, {"error": "API Key Missing"}

    # Handle Input Types Safely
    payload = {}
    if hasattr(address_data, 'to_postgrid_payload'):
        payload = address_data.to_postgrid_payload()
    elif isinstance(address_data, dict):
        if address_standard:
            obj = address_standard.StandardAddress.from_dict(address_data)
            payload = obj.to_postgrid_payload()
        else:
            payload = address_data 
            
    # Apply mapping fix
    clean_payload = _to_camel_case_payload(payload)
    
    # NOTE: The Verification API uses slightly different keys (line1 vs addressLine1),
    # but PostGrid often accepts both aliases. If this 404s, it's likely an API Key scope issue.
    # We will try the standard address verification endpoint.
    url = "https://api.postgrid.com/v1/add_verifications"
    
    try:
        r = requests.post(url, json={"address": clean_payload}, headers={"x-api-key": api_key})
        if r.status_code == 200:
            res = r.json()
            if res.get('status') == 'verified':
                return True, res.get('data', {})
            else:
                return False, {"error": "Address could not be verified.", "details": res}
        return False, {"error": f"API Error {r.status_code}"}
    except Exception as e:
        return False, {"error": str(e)}

def send_letter(pdf_bytes, to_addr, from_addr, description="VerbaPost Letter", tier="Standard"):
    """
    Sends the PDF to PostGrid.
    """
    api_key = secrets_manager.get_secret("postgrid.api_key") or secrets_manager.get_secret("POSTGRID_API_KEY")
    if not api_key:
        logger.error("PostGrid API Key missing.")
        return None

    # 1. Prepare Address Payloads (Internal Format)
    if address_standard:
        if isinstance(to_addr, dict): to_addr = address_standard.StandardAddress.from_dict(to_addr)
        if isinstance(from_addr, dict): from_addr = address_standard.StandardAddress.from_dict(from_addr)
        
        to_payload = to_addr.to_postgrid_payload()
        from_payload = from_addr.to_postgrid_payload()
    else:
        to_payload = to_addr if isinstance(to_addr, dict) else to_addr.__dict__
        from_payload = from_addr if isinstance(from_addr, dict) else from_addr.__dict__

    # 2. CREATE CONTACTS FIRST (With Name Split Fix)
    to_id = _create_postgrid_contact(to_payload, api_key)
    from_id = _create_postgrid_contact(from_payload, api_key)

    if not to_id or not from_id:
        logger.error("Failed to create contacts. Aborting letter send.")
        return None

    # 3. Determine Service Level
    extra_service = None
    express = False
    
    if tier in ["Legacy", "Certified", "certified"]:
        extra_service = "certified"
    elif tier == "Priority":
        express = True

    # 4. Send Letter
    url = "https://api.postgrid.com/print-mail/v1/letters"
    
    files = {
        'pdf': ('letter.pdf', pdf_bytes, 'application/pdf')
    }
    
    data = {
        'to': to_id,
        'from': from_id,
        'description': description,
        'color': True,
        'doubleSided': True,
        'express': express,
        'addressPlacement': 'top_first_page',
    }
    
    if extra_service:
        data['extraService'] = extra_service

    try:
        r = requests.post(url, headers={"x-api-key": api_key}, data=data, files=files)
        
        if r.status_code in [200, 201]:
            res = r.json()
            return res.get('id')
        else:
            logger.error(f"PostGrid Fail: {r.status_code} - {r.text}")
            return None
            
    except Exception as e:
        logger.error(f"Mailing Exception: {e}")
        return None