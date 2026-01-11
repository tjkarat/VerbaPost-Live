import requests
import json
import os
import streamlit as st
import logging
import uuid

# --- IMPORTS ---
try: import audit_engine
except ImportError: audit_engine = None
try: import storage_engine 
except ImportError: storage_engine = None

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_api_config():
    """Retrieves Key, Secret, and URL."""
    key = None
    secret = None
    url = "https://v3.pcmintegrations.com" 

    # 1. Secrets
    if hasattr(st, "secrets") and "pcm" in st.secrets:
        key = st.secrets["pcm"].get("api_key")
        secret = st.secrets["pcm"].get("api_secret")
        if "base_url" in st.secrets["pcm"]:
            url = st.secrets["pcm"]["base_url"]
    
    # 2. Env Vars
    if not key:
        key = os.environ.get("PCM_API_KEY")
        secret = os.environ.get("PCM_API_SECRET")
    
    # Sanitize
    if key: key = str(key).strip().replace("'", "").replace('"', "")
    if secret: secret = str(secret).strip().replace("'", "").replace('"', "")

    return key, secret, url

def _get_auth_token(key, secret, base_url):
    """Exchanges Key/Secret for a Bearer Token."""
    try:
        resp = requests.post(f"{base_url}/auth/login", json={"apiKey": key, "apiSecret": secret})
        if resp.status_code == 200:
            return resp.json().get("token")
        logger.error(f"PCM Auth Failed {resp.status_code}: {resp.text}")
        return None
    except Exception as e:
        logger.error(f"PCM Auth Error: {e}")
        return None

def _map_tier_options(tier):
    t = str(tier).strip().title()
    options = {
        "addons": [],
        # CHANGED: 'Number10' is the standard non-window envelope
        "envelope": {"type": "Number10", "fontColor": "Black"}
    }
    # VINTAGE / HEIRLOOM / LEGACY -> Live Stamp
    if t in ["Vintage", "Heirloom", "Legacy"]:
        options["addons"].append({"addon": "Livestamping"})
    return options

def validate_address(address_dict):
    """Validates address via PCM V3."""
    key, secret, base_url = get_api_config()
    if not key or not secret: return True, address_dict

    token = _get_auth_token(key, secret, base_url)
    if not token: return True, address_dict 

    payload = [{
        "address": address_dict.get("address_line1") or address_dict.get("street"),
        "address2": address_dict.get("address_line2", ""),
        "city": address_dict.get("city"),
        "state": address_dict.get("state"), 
        "zipCode": address_dict.get("zip_code") or address_dict.get("zip")
    }]

    try:
        url = f"{base_url}/recipient/verify"
        resp = requests.post(url, json=payload, headers={"Authorization": f"Bearer {token}"})
        if resp.status_code == 201:
            data = resp.json()
            if data.get("results", {}).get("valid"): return True, address_dict
            else: return False, {"error": "Invalid Address"}
        return True, address_dict
    except Exception as e:
        logger.error(f"Validation Exception: {e}")
        return True, address_dict

def send_letter(pdf_bytes, to_addr, from_addr, tier="Standard", description="VerbaPost", user_email=None):
    """
    1. Upload PDF -> Get Signed URL.
    2. Login -> Get Token.
    3. Send JSON Order.
    """
    key, secret, base_url = get_api_config()
    if not key or not secret:
        logger.error("PCM: Missing API Key or Secret")
        return None

    # --- 1. UPLOAD PDF ---
    if not storage_engine:
        logger.error("PCM: Storage Engine missing.")
        return None
        
    file_name = f"letters/{uuid.uuid4()}.pdf"
    pdf_url = None
    
    try:
        client = storage_engine.get_storage_client()
        bucket = "heirloom-audio"
        
        if not client:
            logger.error("PCM: Storage Client Init Failed (Check Secrets)")
            return None
        
        client.storage.from_(bucket).upload(file_name, pdf_bytes, {"content-type": "application/pdf"})
        
        signed_resp = client.storage.from_(bucket).create_signed_url(file_name, 3600)
        
        if isinstance(signed_resp, dict): pdf_url = signed_resp.get("signedURL")
        elif isinstance(signed_resp, str): pdf_url = signed_resp
            
        if not pdf_url:
            logger.error("PCM: Failed to generate URL")
            return None
        logger.info(f"📄 PDF Ready: {pdf_url[:30]}...")
        
    except Exception as e:
        logger.error(f"PCM: Upload Error: {e}")
        return None

    # --- 2. AUTHENTICATE ---
    token = _get_auth_token(key, secret, base_url)
    if not token: return None

    # --- 3. CONSTRUCT ORDER ---
    try:
        opts = _map_tier_options(tier)
        
        payload = {
            "mailClass": "FirstClass",
            "letter": pdf_url, 
            "color": True,
            "printOnBothSides": False,
            "insertAddressingPage": False,
            "extRefNbr": description[:50],
            "envelope": opts["envelope"],
            "recipients": [{
                "firstName": to_addr.get("name", "").split(" ")[0],
                "lastName": " ".join(to_addr.get("name", "").split(" ")[1:]),
                "address": to_addr.get("address_line1") or to_addr.get("street"),
                "address2": to_addr.get("address_line2", ""),
                "city": to_addr.get("city"),
                "state": to_addr.get("state"),
                "zipCode": to_addr.get("zip_code") or to_addr.get("zip"),
                "variables": []
            }],
            "returnAddress": {
                "company": from_addr.get("name"),
                "address": from_addr.get("address_line1") or from_addr.get("street"),
                "city": from_addr.get("city"),
                "state": from_addr.get("state"),
                "zipCode": from_addr.get("zip_code") or from_addr.get("zip")
            }
        }
        
        if opts["addons"]: payload["addons"] = opts["addons"]

        # --- 4. SEND ---
        url = f"{base_url}/order/letter"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        logger.info(f"🚀 Sending Order to {url}")
        resp = requests.post(url, headers=headers, json=payload)

        # Audit
        if audit_engine and user_email:
            meta = {"status": resp.status_code}
            try: meta.update(resp.json())
            except: meta["raw"] = resp.text
            audit_engine.log_event(user_email, "PCM_API_ATTEMPT", metadata=meta)

        if resp.status_code == 201:
            order_id = resp.json().get("orderID")
            logger.info(f"✅ PCM Success! ID: {order_id}")
            return str(order_id)
        else:
            logger.error(f"❌ PCM Error {resp.status_code}: {resp.text}")
            return None

    except Exception as e:
        logger.error(f"❌ PCM Exception: {e}")
        return None