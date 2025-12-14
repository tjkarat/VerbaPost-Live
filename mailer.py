import requests
import json
import logging
import streamlit as st

# --- CONFIGURATION ---
logger = logging.getLogger(__name__)

# PostGrid API Endpoint
BASE_URL = "https://api.postgrid.com/print-mail/v1/letters"

def send_letter(pdf_bytes, sender, recipient, tier="Standard"):
    """
    Uploads PDF to PostGrid. Returns dict with success status and tracking info.
    """
    # 1. Get Key
    api_key = None
    try:
        api_key = st.secrets["postgrid"]["api_key"]
    except:
        return {"success": False, "error": "API Key Missing"}

    try:
        # 2. Configure Tier Settings
        extra_service = None
        color_print = False 
        
        if tier == "Legacy":
            extra_service = "certified" 
            color_print = True 
        elif tier == "Santa":
            color_print = True
            
        # 3. Build Payload
        files = { 'pdf': ('letter.pdf', pdf_bytes, 'application/pdf') }
        
        data = {
            'to[name]': recipient.get("name"),
            'to[addressLine1]': recipient.get("street"),
            'to[city]': recipient.get("city"),
            'to[provinceOrState]': recipient.get("state"),
            'to[postalOrZip]': recipient.get("zip"),
            'to[countryCode]': recipient.get("country", "US"),
            'from[name]': sender.get("name"),
            'from[addressLine1]': sender.get("street"),
            'from[city]': sender.get("city"),
            'from[provinceOrState]': sender.get("state"),
            'from[postalOrZip]': sender.get("zip"),
            'from[countryCode]': "US",
            'color': str(color_print).lower(),
            'doubleSided': 'false' if tier == "Legacy" else 'true',
            'addressPlacement': 'top_first_page',
        }

        if extra_service:
            data['extraService'] = extra_service

        # 4. Send Request
        response = requests.post(
            BASE_URL,
            headers={"x-api-key": api_key},
            files=files,
            data=data
        )
        
        # 5. Parse Response
        if response.status_code in [200, 201]:
            res_json = response.json()
            
            # CRITICAL: Extract Tracking Number if available
            tracking_num = res_json.get("trackingNumber")
            
            return {
                "success": True, 
                "id": res_json.get("id"),
                "status": res_json.get("status"),
                "tracking_number": tracking_num  # Return this to UI
            }
        else:
            logger.error(f"PostGrid Error: {response.text}")
            return {"success": False, "error": response.text}

    except Exception as e:
        return {"success": False, "error": str(e)}