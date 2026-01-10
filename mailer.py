import requests
import json
import os
import streamlit as st
import logging
import uuid

# --- IMPORTS ---
try: import audit_engine
except ImportError: audit_engine = None
try: import storage_engine # REQUIRED
except ImportError: storage_engine = None

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_api_config():
    key = None
    url = "https://v3.pcmintegrations.com" 

    if hasattr(st, "secrets") and "pcm" in st.secrets:
        key = st.secrets["pcm"].get("api_key")
    if not key:
        key = os.environ.get("PCM_API_KEY")
    
    if key: key = str(key).strip().replace("'", "").replace('"', "")
    return key, url

def _map_tier_options(tier):
    """
    Maps VerbaPost Tier to PCM V3 Options (Addons/Envelope).
    """
    t = str(tier).strip().title()
    options = {
        "addons": [],
        "envelope": {"type": "doubleWindow", "fontColor": "Black"}
    }
    
    # VINTAGE / HEIRLOOM / LEGACY -> Live Stamp
    if t in ["Vintage", "Heirloom", "Legacy"]:
        options["addons"].append({"addon": "Livestamping"})
        # Note: If you want specific envelopes, add envelopeID here
        
    return options

def validate_address(address_dict):
    """
    Validates address via PCM V3 (Batch Verify).
    """
    key, base_url = get_api_config()
    if not key: return True, address_dict

    payload = [{
        "address": address_dict.get("address_line1") or address_dict.get("street"),
        "address2": address_dict.get("address_line2", ""),
        "city": address_dict.get("city"),
        "state": address_dict.get("state"), 
        "zipCode": address_dict.get("zip_code") or address_dict.get("zip")
    }]

    try:
        url = f"{base_url}/recipient/verify"
        resp = requests.post(url, json=payload, headers={"Authorization": f"Bearer {key}"})
        
        if resp.status_code == 201:
            data = resp.json()
            if data.get("results", {}).get("valid"):
                return True, address_dict
            else:
                return False, {"error": "Invalid Address"}
        return True, address_dict # Fail open

    except Exception as e:
        logger.error(f"Validation Exception: {e}")
        return True, address_dict

def send_letter(pdf_bytes, to_addr, from_addr, tier="Standard", description="VerbaPost", user_email=None):
    """
    1. Upload PDF -> Get Signed URL.
    2. Send JSON Order to PCM V3.
    """
    key, base_url = get_api_config()
    if not key:
        logger.error("PCM: Missing API Key")
        return None

    if not storage_engine:
        logger.error("PCM: Storage Engine missing. Cannot upload PDF.")
        return None
        
    # --- 1. SECURE UPLOAD ---
    # Create unique path
    file_name = f"letters/{uuid.uuid4()}.pdf"
    
    try:
        # Upload using helper
        # Note: storage_engine.upload_audio usually targets 'heirloom-audio' bucket.
        # We will use the raw client here to ensure we get a SIGNED URL.
        client = storage_engine.get_storage_client()
        bucket = "heirloom-audio" # Ideally use a private bucket 'letters-secure' if created
        
        client.storage.from_(bucket).upload(
            file_name, 
            pdf_bytes, 
            {"content-type": "application/pdf"}
        )
        
        # --- GENERATE SIGNED URL (Valid 1 Hour) ---
        # This is the secure link we send to PCM
        signed_resp = client.storage.from_(bucket).create_signed_url(file_name, 3600)
        
        # Handle Supabase response variations
        pdf_url = None
        if isinstance(signed_resp, dict):
            pdf_url = signed_resp.get("signedURL")
        elif isinstance(signed_resp, str): # Should be dict, but defensive check
            pdf_url = signed_resp
            
        if not pdf_url:
            logger.error("PCM: Failed to generate Signed URL")
            return None
            
        logger.info(f"📄 PDF Secured: {pdf_url[:50]}...")
        
    except Exception as e:
        logger.error(f"PCM: Upload/Sign Error: {e}")
        return None

    # --- 2. CONSTRUCT V3 JSON ORDER ---
    try:
        opts = _map_tier_options(tier)
        
        payload = {
            "mailClass": "FirstClass",
            "letter": pdf_url, # SECURE LINK
            "color": True,
            "printOnBothSides": False,
            "insertAddressingPage": True,
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
        
        if opts["addons"]:
            payload["addons"] = opts["addons"]

        # --- 3. SEND TO PCM ---
        url = f"{base_url}/order/letter"
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"🚀 Sending Order to {url}")
        resp = requests.post(url, headers=headers, json=payload)

        # Audit Logging (Capture EVERYTHING)
        if audit_engine and user_email:
            meta = {"status": resp.status_code, "pdf_url": "SIGNED_URL_HIDDEN"}
            try: meta.update(resp.json())
            except: meta["raw_text"] = resp.text
            
            audit_engine.log_event(user_email, "PCM_API_ATTEMPT", metadata=meta)

        if resp.status_code == 201:
            res_json = resp.json()
            order_id = res_json.get("orderID")
            logger.info(f"✅ PCM Success! Order ID: {order_id}")
            return str(order_id)
        else:
            logger.error(f"❌ PCM Error {resp.status_code}: {resp.text}")
            return None

    except Exception as e:
        logger.error(f"❌ PCM Exception: {e}")
        return None