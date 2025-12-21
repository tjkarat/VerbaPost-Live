import requests
import secrets_manager
import logging
import json
# FIX 1: Import the missing module
try:
    import address_standard
except ImportError:
    address_standard = None

logger = logging.getLogger(__name__)

def validate_address(address_data):
    """
    Validates an address using PostGrid's verification API.
    Accepts Dict or StandardAddress object.
    """
    api_key = secrets_manager.get_secret("postgrid.api_key") or secrets_manager.get_secret("POSTGRID_API_KEY")
    if not api_key:
        return False, {"error": "API Key Missing"}

    # FIX 2: Handle Input Types Safely
    payload = {}
    if hasattr(address_data, 'to_postgrid_payload'):
        payload = address_data.to_postgrid_payload()
    elif isinstance(address_data, dict):
        # Map raw dict to PostGrid expected keys if needed, or pass as is if keys match
        # Ideally, convert to StandardAddress first to ensure consistency
        if address_standard:
            obj = address_standard.StandardAddress.from_dict(address_data)
            payload = obj.to_postgrid_payload()
        else:
            payload = address_data # Risky fallback
    
    url = "https://api.postgrid.com/v1/add_verifications"
    
    try:
        r = requests.post(url, json={"address": payload}, headers={"x-api-key": api_key})
        if r.status_code == 200:
            res = r.json()
            if res.get('status') == 'verified':
                return True, res.get('data', {})
            else:
                # Return the suggested address or error
                return False, {"error": "Address could not be verified.", "details": res}
        return False, {"error": f"API Error {r.status_code}"}
    except Exception as e:
        return False, {"error": str(e)}

def send_letter(pdf_bytes, to_addr, from_addr, description="VerbaPost Letter", tier="Standard"):
    """
    Sends the PDF to PostGrid for printing and mailing.
    FIX 3: Handles 'Certified' and 'Legacy' tiers correctly.
    """
    api_key = secrets_manager.get_secret("postgrid.api_key") or secrets_manager.get_secret("POSTGRID_API_KEY")
    if not api_key:
        logger.error("PostGrid API Key missing.")
        return None

    # 1. Prepare Addresses
    if address_standard:
        # Ensure we are working with Objects, not Dicts
        if isinstance(to_addr, dict): to_addr = address_standard.StandardAddress.from_dict(to_addr)
        if isinstance(from_addr, dict): from_addr = address_standard.StandardAddress.from_dict(from_addr)
        
        to_payload = to_addr.to_postgrid_payload()
        from_payload = from_addr.to_postgrid_payload()
    else:
        # Fallback if module missing (unsafe but prevents total crash)
        to_payload = to_addr if isinstance(to_addr, dict) else to_addr.__dict__
        from_payload = from_addr if isinstance(from_addr, dict) else from_addr.__dict__

    # 2. Determine Service Level (FIX 3)
    # Default: US First Class
    extra_service = None
    express = False
    
    if tier in ["Legacy", "Certified", "certified"]:
        extra_service = "certified" # PostGrid flag for Certified Mail
    elif tier == "Priority": # If you add this later
        express = True

    # 3. Construct Payload
    # PostGrid Create Letter Endpoint
    url = "https://api.postgrid.com/print-mail/v1/letters"
    
    # We send the PDF as a file upload (multipart/form-data) usually, 
    # OR create the contact first. 
    # For simplicity/reliability, we'll assume PDF upload via 'files'.
    
    files = {
        'pdf': ('letter.pdf', pdf_bytes, 'application/pdf')
    }
    
    data = {
        'to': json.dumps(to_payload),
        'from': json.dumps(from_payload),
        'description': description,
        'color': True, # Always print color?
        'doubleSided': True,
        'express': express,
        'addressPlacement': 'top_first_page', # Ensures address shows in window envelope
    }
    
    if extra_service:
        data['extraService'] = extra_service

    try:
        r = requests.post(url, headers={"x-api-key": api_key}, data=data, files=files)
        
        if r.status_code in [200, 201]:
            res = r.json()
            return res.get('id') # Return the Letter ID (e.g. "letter_123...")
        else:
            logger.error(f"PostGrid Fail: {r.status_code} - {r.text}")
            return None
            
    except Exception as e:
        logger.error(f"Mailing Exception: {e}")
        return None