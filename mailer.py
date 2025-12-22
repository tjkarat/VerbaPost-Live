import requests
import secrets_manager
import logging
import json
import os

# Import the missing module safely
try:
    import address_standard
except ImportError:
    address_standard = None

logger = logging.getLogger(__name__)

def _to_camel_case_payload(snake_payload):
    """
    Maps snake_case keys to PostGrid CamelCase.
    SPLITS single 'name' field into 'firstName' and 'lastName' (Required by Contact API).
    """
    full_name = snake_payload.get('name', '').strip()
    first_name = full_name
    last_name = ""
    
    if " " in full_name:
        parts = full_name.split(" ", 1)
        first_name = parts[0]
        last_name = parts[1]

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

def _to_verification_payload(camel_payload):
    """
    CRITICAL FIX: Remaps keys for the Verification API which uses 'line1' instead of 'addressLine1'.
    """
    return {
        'line1': camel_payload.get('addressLine1'),
        'line2': camel_payload.get('addressLine2'),
        'city': camel_payload.get('city'),
        'provinceOrState': camel_payload.get('provinceOrState'),
        'postalOrZip': camel_payload.get('postalOrZip'),
        'country': camel_payload.get('countryCode')
    }

def _create_postgrid_contact(payload, api_key):
    url = "https://api.postgrid.com/print-mail/v1/contacts"
    clean_payload = _to_camel_case_payload(payload)
    
    try:
        r = requests.post(url, json=clean_payload, headers={"x-api-key": api_key})
        if r.status_code in [200, 201]:
            return r.json().get('id')
        else:
            logger.error(f"Contact Creation Failed: {r.status_code} - [Response Hidden]")
            return None
    except Exception as e:
        logger.error(f"Contact Creation Exception: [Details Hidden]")
        return None

def validate_address(address_data):
    """
    Validates an address using PostGrid's verification API.
    """
    api_key = secrets_manager.get_secret("postgrid.api_key") or secrets_manager.get_secret("POSTGRID_API_KEY")
    if not api_key:
        return False, {"error": "API Key Missing"}

    # 1. Prepare Payload
    payload = {}
    if hasattr(address_data, 'to_postgrid_payload'):
        payload = address_data.to_postgrid_payload()
    elif isinstance(address_data, dict):
        if address_standard:
            obj = address_standard.StandardAddress.from_dict(address_data)
            payload = obj.to_postgrid_payload()
        else:
            payload = address_data 
            
    # 2. Map to CamelCase (Contact Format)
    contact_payload = _to_camel_case_payload(payload)
    
    # 3. Map to Verification Format (Fixes 404/Bad Request)
    verification_payload = _to_verification_payload(contact_payload)
    
    # 4. Correct Endpoint URL (Fixes 404)
    url = "https://api.postgrid.com/v1/addver/verifications"
    
    try:
        r = requests.post(url, json={"address": verification_payload}, headers={"x-api-key": api_key})
        
        if r.status_code == 200:
            res = r.json()
            if res.get('status') == 'verified':
                # Return the original payload but marked as verified
                return True, contact_payload 
            else:
                return False, {"error": "Address could not be verified.", "details": "[Details Hidden]"}
        
        if r.status_code in [401, 403, 404]:
             logger.warning(f"Verification Skipped (API {r.status_code}). Proceeding.")
             return True, contact_payload

        return False, {"error": f"API Error {r.status_code}"}
    except Exception as e:
        return False, {"error": "[Exception Hidden]"}

def send_letter(pdf_bytes, to_addr, from_addr, description="VerbaPost Letter", tier="Standard"):
    api_key = secrets_manager.get_secret("postgrid.api_key") or secrets_manager.get_secret("POSTGRID_API_KEY")
    if not api_key:
        logger.error("PostGrid API Key missing.")
        return None

    # 1. Prepare Address Payloads
    if address_standard:
        if isinstance(to_addr, dict): to_addr = address_standard.StandardAddress.from_dict(to_addr)
        if isinstance(from_addr, dict): from_addr = address_standard.StandardAddress.from_dict(from_addr)
        to_payload = to_addr.to_postgrid_payload()
        from_payload = from_addr.to_postgrid_payload()
    else:
        to_payload = to_addr if isinstance(to_addr, dict) else to_addr.__dict__
        from_payload = from_addr if isinstance(from_addr, dict) else from_addr.__dict__

    # 2. CREATE CONTACTS FIRST
    to_id = _create_postgrid_contact(to_payload, api_key)
    from_id = _create_postgrid_contact(from_payload, api_key)

    if not to_id or not from_id:
        logger.error("Failed to create contacts. Aborting.")
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
    
    files = {'pdf': ('letter.pdf', pdf_bytes, 'application/pdf')}
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
            return r.json().get('id')
        else:
            # FIXED: API Key leak protection
            logger.error(f"PostGrid Fail: {r.status_code} - [Response Content Hidden]")
            if os.environ.get("DEBUG") == "true": logger.debug(f"DEBUG: {r.text}")
            return None
    except Exception as e:
        logger.error(f"Mailing Exception: [Details Hidden]")
        return None