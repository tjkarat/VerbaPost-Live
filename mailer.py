import requests
import streamlit as st
import json

# --- CONFIGURATION ---
# CRITICAL FIX: We must use the 'print-mail' endpoint for your API key type.
# The previous error (404) happened because we were hitting the wrong API product.
POSTGRID_BASE_URL = "https://api.postgrid.com/print-mail/v1"

def get_api_key():
    """
    Safely retrieves the PostGrid API key from Streamlit secrets.
    """
    try:
        # Check standard location
        key = st.secrets.get("postgrid", {}).get("api_key")
        if key: return key.strip()
        
        # Fallback for alternative secret structure
        return st.secrets.get("POSTGRID_API_KEY", "").strip()
    except Exception:
        return ""

def verify_address_details(address_dict):
    """
    Sends an address to PostGrid for CASS standardization/verification.
    
    Args:
        address_dict (dict): Contains line1, line2, city, state, zip, country.
        
    Returns:
        tuple: (status, cleaned_address_dict, message_list)
        - status: 'verified', 'corrected', 'invalid', or 'error'
    """
    api_key = get_api_key()
    if not api_key:
        return "error", address_dict, ["PostGrid API Key is missing from secrets."]

    # Endpoint for verifying addresses within the Print & Mail API
    endpoint = f"{POSTGRID_BASE_URL}/verifications"
    
    # Payload: PostGrid Print & Mail expects the address object wrapped in "address"
    payload = {
        "address": {
            "line1": address_dict.get("line1", ""),
            "line2": address_dict.get("line2", ""),
            "city": address_dict.get("city", ""),
            "provinceOrState": address_dict.get("state", ""),
            "postalOrZip": address_dict.get("zip", ""),
            "country": address_dict.get("country", "US")
        }
    }
    
    try:
        # We use a timeout to prevent hanging if the API is slow
        response = requests.post(endpoint, auth=(api_key, ""), json=payload, timeout=15)
        
        # Handle 400 Bad Request (often means data format is wrong or empty)
        if response.status_code == 400:
             return "invalid", {}, ["Address format is invalid or fields are missing."]
             
        response.raise_for_status()
        data = response.json()
        
        # In the Print & Mail API, the verification result is inside a 'data' key
        # If 'data' is missing, fallback to root (just in case of API version diffs)
        res = data.get("data", data)
        
        # Check specific status field
        status_code = res.get("status") # values: 'verified', 'corrected', 'failed'
        
        # Build the Clean Address Dictionary from the response
        clean_addr = {
            "line1": res.get("line1", ""),
            "line2": res.get("line2", ""),
            "city": res.get("city", ""),
            "state": res.get("provinceOrState", ""),
            "zip": res.get("postalOrZip", ""),
            "country": res.get("country", "US")
        }

        # Return status based on PostGrid's analysis
        if status_code == "verified":
             return "verified", clean_addr, []
             
        elif status_code == "corrected":
             return "corrected", clean_addr, ["Address was standardized by USPS data."]
             
        else:
             # If status is 'failed' or anything else
             errors = res.get("errors", {})
             # Flatten error values if it's a dict, otherwise use as list
             if isinstance(errors, dict):
                 error_list = list(errors.values())
             elif isinstance(errors, list):
                 error_list = errors
             else:
                 error_list = ["Address could not be verified."]
                 
             return "invalid", {}, error_list

    except requests.exceptions.ConnectTimeout:
        return "error", address_dict, ["Connection to PostGrid timed out."]
    except requests.exceptions.RequestException as e:
        return "error", address_dict, [f"API Error: {str(e)}"]
    except Exception as e:
        return "error", address_dict, [f"System Error: {str(e)}"]

def send_letter(pdf_bytes, recipient_addr, sender_addr=None, description="VerbaPost Letter", is_certified=False):
    """
    Uploads the PDF and creates a Letter order in PostGrid.
    """
    api_key = get_api_key()
    if not api_key:
        return False, "PostGrid API Key is missing."

    endpoint = f"{POSTGRID_BASE_URL}/letters"
    
    # 1. Prepare Address Data (Multipart compatible)
    # PostGrid expects flattened keys like 'to[line1]' when sending files via multipart
    data = {
        "to[line1]": recipient_addr.get("line1", ""),
        "to[line2]": recipient_addr.get("line2", ""),
        "to[city]": recipient_addr.get("city", ""),
        "to[provinceOrState]": recipient_addr.get("state", ""),
        "to[postalOrZip]": recipient_addr.get("zip", ""),
        "to[country]": recipient_addr.get("country", "US"),
        "to[firstName]": recipient_addr.get("name", "Current Resident"),
        
        "description": description,
        "color": "true",        # We always print in color
        "express": "true" if is_certified else "false", # Express usually maps to Certified/Priority
        "addressPlacement": "top_first_page",
        "envelopeType": "standard_double_window" 
    }

    # Add Return Address if provided
    if sender_addr:
        data.update({
            "from[line1]": sender_addr.get("line1", ""),
            "from[line2]": sender_addr.get("line2", ""),
            "from[city]": sender_addr.get("city", ""),
            "from[provinceOrState]": sender_addr.get("state", ""),
            "from[postalOrZip]": sender_addr.get("zip", ""),
            "from[country]": sender_addr.get("country", "US"),
            "from[firstName]": sender_addr.get("name", "VerbaPost User"),
        })

    # 2. Prepare the File Upload
    files = {}
    opened_file = None
    
    try:
        # Handle both file paths (str) and raw bytes
        if isinstance(pdf_bytes, str):
            # It's a file path
            opened_file = open(pdf_bytes, 'rb')
            files["pdf"] = ("letter.pdf", opened_file, "application/pdf")
        else:
            # It's raw bytes (from ui_main.py generation)
            files["pdf"] = ("letter.pdf", pdf_bytes, "application/pdf")

        # 3. Send Request
        response = requests.post(endpoint, auth=(api_key, ""), data=data, files=files, timeout=30)
        
        if response.status_code in [200, 201]:
            return True, response.json()
        else:
            error_msg = f"PostGrid Error {response.status_code}: {response.text}"
            print(error_msg) # Log to console
            return False, error_msg

    except Exception as e:
        return False, f"Transmission Error: {str(e)}"
    finally:
        # Ensure file handle is closed if we opened one
        if opened_file:
            opened_file.close()