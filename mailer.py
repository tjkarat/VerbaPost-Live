import requests
import json
import logging
import streamlit as st

# --- CONFIGURATION ---
logger = logging.getLogger(__name__)

# Try to get API key from secrets, else None
API_KEY = None
try:
    if "postgrid" in st.secrets:
        API_KEY = st.secrets["postgrid"]["api_key"]
except Exception:
    pass

# PostGrid API Endpoint (Live or Test based on key)
BASE_URL = "https://api.postgrid.com/print-mail/v1/letters"

def send_letter(pdf_bytes, sender, recipient, tier="Standard"):
    """
    Uploads PDF to PostGrid and creates a letter order.
    Adapts postage and print quality based on the Tier.
    """
    if not API_KEY:
        logger.error("PostGrid API Key missing.")
        return {"error": "API Key Missing"}

    try:
        # 1. Determine Settings based on Tier
        extra_service = None
        color_print = False # Default to B/W for standard to save cost
        
        if tier == "Legacy":
            # $15.99 Tier: Needs Tracking & High Quality
            extra_service = "certified" 
            color_print = True # Forces higher quality digital press
            
        elif tier == "Santa":
            # Santa Tier: Color is nice
            color_print = True
            
        elif tier == "Civic":
            # Congress letters are standard
            pass

        # 2. Prepare the Multipart Payload
        # We send the PDF as a file and the metadata as form fields
        files = {
            'pdf': ('letter.pdf', pdf_bytes, 'application/pdf')
        }
        
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
            
            'color': str(color_print).lower(), # "true" or "false"
            'doubleSided': 'false' if tier == "Legacy" else 'true', # Legacy usually single-sided for formality
            'addressPlacement': 'top_first_page',
        }

        # 3. Add Certified Mail flag if needed
        if extra_service:
            data['extraService'] = extra_service

        # 4. Send Request
        response = requests.post(
            BASE_URL,
            headers={"x-api-key": API_KEY},
            files=files,
            data=data
        )
        
        # 5. Handle Response
        if response.status_code in [200, 201]:
            res_json = response.json()
            return {
                "success": True, 
                "id": res_json.get("id"),
                "status": res_json.get("status"),
                "tracking": extra_service == "certified" # Flag for UI to show tracking later
            }
        else:
            logger.error(f"PostGrid Error: {response.text}")
            return {"success": False, "error": response.text}

    except Exception as e:
        logger.error(f"Mailer Exception: {e}")
        return {"success": False, "error": str(e)}