import requests
import streamlit as st
import json

# --- CONFIGURATION ---
# We use the Print & Mail base URL
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
    Verifies an address by creating a temporary Contact in PostGrid.
    This works for ALL Print & Mail API keys.
    
    Args:
        address_dict (dict): Contains line1, line2, city, state, zip, country.
        
    Returns:
        tuple: (status, cleaned_address_dict, message_list)
        - status: 'verified', 'corrected', 'invalid', or 'error'
    """
    api_key = get_api_key()
    if not api_key:
        return "error", address_dict, ["PostGrid API Key is missing from secrets."]

    # FIX: Use the 'contacts' endpoint. 
    # Creating a contact triggers CASS verification automatically.
    endpoint = f"{POSTGRID_BASE_URL}/contacts"
    
    # Payload: Map our fields to PostGrid Contact fields
    payload = {
        "firstName": "Verification Check", # Dummy name required for contact
        "addressLine1": address_dict.get("line1", ""),
        "addressLine2": address_dict.get("line2", ""),
        "city": address_dict.get("city", ""),
        "provinceOrState": address_dict.get("state", ""),
        "postalOrZip": address_dict.get("zip", ""),
        "countryCode": "US"
    }
    
    try:
        # We use a timeout to prevent hanging
        response = requests.post(endpoint, auth=(api_key, ""), json=payload, timeout=15)
        
        # Handle 400 Bad Request (Invalid data)
        if response.status_code == 400:
             try:
                 err_msg = response.json().get("error", {}).get("message", "Invalid address data")
                 return "invalid", {}, [err_msg]
             except:
                 return "invalid", {}, ["Address format is invalid."]
             
        response.raise_for_status()
        data = response.json()
        
        # PostGrid Contact Response contains the cleaned address directly
        # and metadata about validity.
        # Note: 'valid' is often boolean in older versions, or status string in newer.
        # We assume standard Print & Mail response structure.
        
        # 1. Check if valid
        # Some versions return 'metadata': {'validationStatus': 'valid'}
        # Others strictly return clean data if 200 OK.
        
        # We assume if it created successfully (200/201), it's at least usable.
        # We compare input vs output to detect "corrections".
        
        clean_addr = {
            "line1": data.get("addressLine1", ""),
            "line2": data.get("addressLine2", ""),
            "city": data.get("city", ""),
            "state": data.get("provinceOrState", ""),
            "zip": data.get("postalOrZip", ""),
            "country": "US"
        }

        # Determine Status
        # If input Zip was 5 digits and output is 9, that's a correction.
        input_zip = str(address_dict.get("zip", "")).strip()
        output_zip = str(clean_addr.get("zip", "")).strip()
        
        input_street = str(address_dict.get("line1", "")).lower().strip()
        output_street = str(clean_addr.get("line1", "")).lower().strip()

        if input_street == output_street and input_zip == output_zip:
            return "verified", clean_addr, []
        else:
            return "corrected", clean_addr, ["Address was standardized by USPS."]

    except requests.exceptions.ConnectTimeout:
        return "error", address_dict, ["Connection to PostGrid timed out."]
    except requests.exceptions.RequestException as e:
        # If API returns 400+ it usually means address is bad
        if hasattr(e, 'response') and e.response is not None:
             if e.response.status_code == 422 or e.response.status_code == 400:
                 return "invalid", {}, ["Address rejected by USPS database."]
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
        "to[addressLine1]": recipient_addr.get("line1", ""),
        "to[addressLine2]": recipient_addr.get("line2", ""),
        "to[city]": recipient_addr.get("city", ""),
        "to[provinceOrState]": recipient_addr.get("state", ""),
        "to[postalOrZip]": recipient_addr.get("zip", ""),
        "to[countryCode]": "US",
        "to[firstName]": recipient_addr.get("name", "Current Resident"),
        
        "description": description,
        "color": "true",        # We always print in color
        "express": "true" if is_certified else "false", 
        "addressPlacement": "top_first_page",
        "envelopeType": "standard_double_window" 
    }

    # Add Return Address if provided
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
        # Handle both file paths (str) and raw bytes
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
            print(error_msg) # Log to console
            return False, error_msg

    except Exception as e:
        return False, f"Transmission Error: {str(e)}"
    finally:
        # Ensure file handle is closed if we opened one
        if opened_file:
            opened_file.close()