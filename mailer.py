import requests
import streamlit as st
import json

# --- CONFIGURATION ---
POSTGRID_BASE_URL = "https://api.postgrid.com/v1"

def get_api_key():
    """
    Safely retrieves the PostGrid API key from Streamlit secrets.
    """
    try:
        return st.secrets.get("postgrid", {}).get("api_key", "").strip()
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
        - cleaned_address_dict: The standardized address from USPS/PostGrid
        - message_list: List of errors or warnings
    """
    api_key = get_api_key()
    if not api_key:
        return "error", address_dict, ["API Key missing"]

    endpoint = f"{POSTGRID_BASE_URL}/add_verifications"
    
    # Payload structure for PostGrid Verification
    payload = {
        "address": {
            "line1": address_dict.get("line1", ""),
            "line2": address_dict.get("line2", ""),
            "city": address_dict.get("city", ""),
            "state": address_dict.get("state", ""),
            "zip": address_dict.get("zip", ""),
            "country": address_dict.get("country", "US")
        }
    }
    
    try:
        response = requests.post(endpoint, auth=(api_key, ""), json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # PostGrid returns a 'result' object with the clean address
        # and a 'summary' object with the verification status
        res = data.get("result", {})
        summary = data.get("summary", {})
        
        # Build the clean address dictionary
        clean_addr = {
            "line1": res.get("line1", ""),
            "line2": res.get("line2", ""),
            "city": res.get("city", ""),
            "state": res.get("provinceOrState", ""),
            "zip": res.get("postalOrZip", ""),
            "country": res.get("country", "")
        }

        # Determine Status
        action = summary.get("action")
        
        if action == "verified":
             return "verified", clean_addr, []
             
        elif action == "corrected":
             # It was valid, but they changed something (e.g. added Zip+4 or fixed spelling)
             return "corrected", clean_addr, summary.get("errors", [])
             
        else:
             # Action is usually 'failed' here
             errors = summary.get("errors", ["Address could not be verified"])
             return "invalid", {}, errors

    except requests.exceptions.RequestException as e:
        print(f"Address Verification Connection Error: {e}")
        return "error", address_dict, [f"Connection failed: {str(e)}"]
    except Exception as e:
        print(f"Address Verification Error: {e}")
        return "error", address_dict, [str(e)]

def send_letter(pdf_bytes, recipient_addr, sender_addr=None, description="VerbaPost Letter"):
    """
    Uploads the PDF and creates a Letter order in PostGrid.
    
    Args:
        pdf_bytes (bytes): The raw PDF file data.
        recipient_addr (dict): The verified recipient address.
        sender_addr (dict): The return address (optional).
        description (str): Metadata for the order.
        
    Returns:
        tuple: (success, response_data_or_error_msg)
    """
    api_key = get_api_key()
    if not api_key:
        return False, "PostGrid API Key is missing."

    endpoint = f"{POSTGRID_BASE_URL}/letters"
    
    # 1. Prepare the Address Object (PostGrid expects flat parameters for creation)
    # Note: We send the address fields directly in the multipart form data
    
    data = {
        "to[line1]": recipient_addr.get("line1", ""),
        "to[line2]": recipient_addr.get("line2", ""),
        "to[city]": recipient_addr.get("city", ""),
        "to[provinceOrState]": recipient_addr.get("state", ""),
        "to[postalOrZip]": recipient_addr.get("zip", ""),
        "to[country]": recipient_addr.get("country", "US"),
        "to[firstName]": recipient_addr.get("name", "Current Resident"),
        
        "description": description,
        "color": "true",        # VerbaPost letters are color
        "express": "false",     # Standard First Class
        "addressPlacement": "top_first_page", # Ensure address is visible in window envelope
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
    # We send the PDF as a file tuple in the 'pdf' field
    files = {
        "pdf": ("letter.pdf", pdf_bytes, "application/pdf")
    }

    try:
        # 3. Send Request (Multipart/Form-Data)
        response = requests.post(endpoint, auth=(api_key, ""), data=data, files=files, timeout=30)
        
        if response.status_code in [200, 201]:
            return True, response.json()
        else:
            error_msg = f"PostGrid Error {response.status_code}: {response.text}"
            print(error_msg)
            return False, error_msg

    except Exception as e:
        return False, f"Transmission Error: {str(e)}"