import requests
import json
import os
import streamlit as st
import logging

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_api_config():
    """
    Retrieves PCM API credentials safely.
    Checks: st.secrets['pcm'] -> os.environ['PCM_API_KEY']
    """
    key = None
    url = "https://api.pcmintegrations.com/direct-mail/v3" # Default v3 Base URL

    # 1. Try Streamlit Secrets
    if hasattr(st, "secrets") and "pcm" in st.secrets:
        key = st.secrets["pcm"].get("api_key")
        if "base_url" in st.secrets["pcm"]:
            url = st.secrets["pcm"]["base_url"]
    
    # 2. Try Env Vars (Cloud Run)
    if not key:
        key = os.environ.get("PCM_API_KEY")
        if os.environ.get("PCM_BASE_URL"):
            url = os.environ.get("PCM_BASE_URL")

    return key, url

def _map_tier_attributes(tier):
    """
    Maps VerbaPost Tiers to PCM Order Attributes.
    """
    t = str(tier).strip().title()
    
    # Defaults (Standard, Civic, Campaign)
    specs = {
        "paper_type": "Standard",     # Update if PCM uses specific ID (e.g. '60# Text')
        "postage_type": "Metered",    # Standard Indicia
        "envelope": "#10 Double Window",
        "print_color": "Full Color"
    }

    # Premium Tiers (Vintage, Heirloom)
    if t in ["Vintage", "Heirloom"]:
        specs["paper_type"] = "70# Text"  # Request 70lb Paper
        specs["postage_type"] = "Live Stamp" # Request Real Stamp
        specs["envelope"] = "#10 Standard" # Standard envelope for manual feel

    return specs

def validate_address(address_dict):
    """
    Validates address via PCM API. 
    Returns (True, cleaned_data) or (False, error_msg).
    """
    key, base_url = get_api_config()
    if not key: return True, address_dict # Dev Mode bypass

    # Construct Payload
    payload = {
        "address_line1": address_dict.get("address_line1") or address_dict.get("street"),
        "address_line2": address_dict.get("address_line2", ""),
        "city": address_dict.get("city"),
        "state_code": address_dict.get("state"), # PCM usually expects 2-char code
        "postal_code": address_dict.get("zip_code") or address_dict.get("zip"),
        "country_code": "US"
    }

    try:
        # Attempt Validation
        url = f"{base_url}/address/validate"
        resp = requests.post(url, json=payload, headers={"Authorization": f"Bearer {key}"})
        
        if resp.status_code == 200:
            data = resp.json()
            if data.get("is_valid", True): # Adjust based on exact PCM response field
                return True, address_dict
            else:
                return False, {"error": "Invalid Address according to USPS data."}
        
        # If API Endpoint fails (404/500), Log it but ALLOW passage to not break app
        logger.warning(f"PCM Validation Endpoint Failed ({resp.status_code}). Allowing address.")
        return True, address_dict

    except Exception as e:
        logger.error(f"Validation Exception: {e}")
        return True, address_dict # Fail open

def send_letter(pdf_bytes, to_addr, from_addr, tier="Standard", description="VerbaPost Letter"):
    """
    Sends PDF to PCM Integrations for fulfillment.
    """
    key, base_url = get_api_config()
    if not key:
        logger.error("PCM: Missing API Key")
        return None

    logger.info(f"PCM: Processing {tier} Order...")
    
    try:
        # 1. Get Tier Config
        specs = _map_tier_attributes(tier)

        # 2. Prepare Metadata (JSON)
        # Note: PCM v3 often uses a 'json' field within multipart, or direct fields.
        # This implementation assumes the standard multipart pattern.
        order_details = {
            "external_id": description[:50],
            "recipient": {
                "name": to_addr.get("name"),
                "address_line1": to_addr.get("address_line1") or to_addr.get("street"),
                "address_line2": to_addr.get("address_line2", ""),
                "city": to_addr.get("city"),
                "state_code": to_addr.get("state"),
                "postal_code": to_addr.get("zip_code") or to_addr.get("zip"),
                "country_code": "US"
            },
            "sender": {
                "name": from_addr.get("name"),
                "address_line1": from_addr.get("address_line1") or from_addr.get("street"),
                "address_line2": from_addr.get("address_line2", ""),
                "city": from_addr.get("city"),
                "state_code": from_addr.get("state"),
                "postal_code": from_addr.get("zip_code") or from_addr.get("zip"),
                "country_code": "US"
            },
            "options": {
                "paper_type": specs["paper_type"],
                "postage_type": specs["postage_type"],
                "envelope_type": specs["envelope"],
                "color": specs["print_color"]
            }
        }

        # 3. Construct Request
        url = f"{base_url}/orders/create"
        
        # Files + Data
        files = {
            'file': ('letter.pdf', pdf_bytes, 'application/pdf')
        }
        data = {
            'order': json.dumps(order_details) # Most APIs expect JSON string here
        }

        resp = requests.post(
            url, 
            headers={"Authorization": f"Bearer {key}"},
            files=files,
            data=data
        )

        if resp.status_code in [200, 201]:
            res_json = resp.json()
            order_id = res_json.get("id") or res_json.get("order_id")
            logger.info(f"PCM Success! Order ID: {order_id}")
            return order_id
        else:
            logger.error(f"PCM Error {resp.status_code}: {resp.text}")
            return None

    except Exception as e:
        logger.error(f"PCM Exception: {e}")
        return None