import requests
import streamlit as st
import json
import os

# --- CONFIGURATION ---
POSTGRID_BASE_URL = "https://api.postgrid.com/print-mail/v1"

def get_api_key():
    """
    Safely retrieves the PostGrid API key from Streamlit secrets OR OS Environment Variables.
    Prioritizes OS variables for Production stability (Cloud Run).
    """
    # 1. Try OS Environment Variables (PROD / Cloud Run)
    # Cloud Run injects secrets as standard environment variables
    env_key = os.environ.get("POSTGRID_API_KEY") or os.environ.get("postgrid_api_key")
    if env_key:
        return env_key.strip()

    # 2. Try Streamlit Secrets (QA / Local Dev with secrets.toml)
    try:
        # Check nested [postgrid] section
        key = st.secrets.get("postgrid", {}).get("api_key")
        if key: return key.strip()
        
        # Check flat key fallback
        return st.secrets.get("POSTGRID_API_KEY", "").strip()
    except Exception:
        return ""

def verify_address_details(address_dict):
    """
    Verifies an address by creating a temporary Contact in PostGrid.
    This method works for ALL Print & Mail API keys where the standalone /verifications endpoint might 404.
    """
    api_key = get_api_key()
    if not api_key:
        return "error", address_dict, ["PostGrid API Key is missing (Check Env Vars or Secrets)."]

    # Use the 'contacts' endpoint to trigger implicit CASS verification
    endpoint = f"{POSTGRID_BASE_URL}/contacts"
    
    # Payload: Map fields to PostGrid Contact object
    payload = {
        "firstName": "Verification Check", 
        "addressLine1": address_dict.get("line1", ""),
        "addressLine2": address_dict.get("line2", ""),
        "city": address_dict.get("city", ""),
        "provinceOrState": address_dict.get("state", ""),
        "postalOrZip": address_dict.get("zip", ""),
        "countryCode": "US"
    }
    
    try:
        # 15s timeout to be safe
        response = requests.post(endpoint, auth=(api_key, ""), json=payload, timeout=15)
        
        # Handle 400 Bad Request (Invalid Data)
        if response.status_code == 400:
             try:
                 err_msg = response.json().get("error", {}).get("message", "Invalid address data")
                 return "invalid", {}, [err_msg]
             except:
                 return "invalid", {}, ["Address format is invalid."]
             
        response.raise_for_status()
        data = response.json()
        
        # Extract the cleaned address from the response
        clean_addr = {
            "line1": data.get("addressLine1", ""),
            "line2": data.get("addressLine2", ""),
            "city": data.get("city", ""),
            "state": data.get("provinceOrState", ""),
            "zip": data.get("postalOrZip", ""),
            "country": "US"
        }

        # DETERMINE STATUS:
        # We compare the input ZIP vs output ZIP. 
        # If input was 5 digits and output is 9 (Zip+4), it was corrected/standardized.
        input_zip = str(address_dict.get("zip", "")).strip()
        output_zip = str(clean_addr.get("zip", "")).strip()
        
        input_street = str(address_dict.get("line1", "")).lower().strip()
        output_street = str(clean_addr.get("line1", "")).lower().strip()

        # If strict match
        if input_street == output_street and input_zip == output_zip:
            return "verified", clean_addr, []
        else:
            # If changed, it was corrected/standardized
            return "corrected", clean_addr, ["Address was standardized by USPS."]

    except requests.exceptions.ConnectTimeout:
        return "error", address_dict, ["Connection to PostGrid timed out."]
    except requests.exceptions.RequestException as e:
        # Handle 422 Unprocessable Entity (often means address is fake/undeliverable)
        if hasattr(e, 'response') and e.response is not None:
             if e.response.status_code == 422:
                 return "invalid", {}, ["Address rejected by USPS database (Undeliverable)."]
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
    data = {
        "to[addressLine1]": recipient_addr.get("line1", ""),
        "to[addressLine2]": recipient_addr.get("line2", ""),
        "to[city]": recipient_addr.get("city", ""),
        "to[provinceOrState]": recipient_addr.get("state", ""),
        "to[postalOrZip]": recipient_addr.get("zip", ""),
        "to[countryCode]": "US",
        "to[firstName]": recipient_addr.get("name", "Current Resident"),
        
        "description": description,
        "color": "true",
        "express": "true" if is_certified else "false", 
        "addressPlacement": "top_first_page",
        "envelopeType": "standard_double_window" 
    }

    if sender_addr:
        data.update({
            "from[addressLine1]": sender_addr.get("line1", ""),
            "from[addressLine2]": sender_addr.get("line2", ""),
            "from[city]": sender_addr.get("city", ""),
            "from[provinceOrState]": sender_addr.get("state", ""),
            "from[postalOrZip]": sender_addr.get("zip", ""),
            "from[countryCode]": "US",
            "from[firstName]": sender_addr.get("name", "VerbaPost User"),
        })

    # 2. Prepare the File Upload
    files = {}
    opened_file = None
    
    try:
        if isinstance(pdf_bytes, str):
            opened_file = open(pdf_bytes, 'rb')
            files["pdf"] = ("letter.pdf", opened_file, "application/pdf")
        else:
            files["pdf"] = ("letter.pdf", pdf_bytes, "application/pdf")

        # 3. Send Request
        response = requests.post(endpoint, auth=(api_key, ""), data=data, files=files, timeout=30)
        
        if response.status_code in [200, 201]:
            return True, response.json()
        else:
            error_msg = f"PostGrid Error {response.status_code}: {response.text}"
            # print(error_msg) # Logging handled by caller
            return False, error_msg

    except Exception as e:
        return False, f"Transmission Error: {str(e)}"
    finally:
        if opened_file:
            opened_file.close()