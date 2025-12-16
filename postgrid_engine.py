import requests
import streamlit as st
import os

# Base URL for PostGrid Print & Mail API
BASE_URL = "https://api.postgrid.com/print-mail/v1"

def send_letter(pdf_path, recipient_data, sender_data=None):
    """
    Uploads the PDF and creates a Letter order in PostGrid.
    """
    api_key = st.secrets.get("postgrid", {}).get("api_key")
    
    # --- SIMULATION MODE ---
    if not api_key:
        print("⚠️ No PostGrid Key found. Simulating...")
        return {
            "success": True, 
            "id": "mock_letter_123", 
            "status": "ready",
            "note": "SIMULATION MODE"
        }

    # --- REAL MODE ---
    try:
        headers = {"x-api-key": api_key}

        # 1. CREATE RECIPIENT CONTACT ("TO")
        to_payload = {
            "firstName": recipient_data.get("first_name"),
            "lastName": recipient_data.get("last_name", ""),
            "addressLine1": recipient_data.get("address_line1"),
            "city": recipient_data.get("city"),
            "provinceOrState": recipient_data.get("state"),
            "countryCode": recipient_data.get("country_code", "US")
        }
        
        r_to = requests.post(f"{BASE_URL}/contacts", data=to_payload, headers=headers)
        if r_to.status_code not in [200, 201]:
            return {"success": False, "error": f"Recipient Error: {r_to.text}"}
        
        to_id = r_to.json().get("id")

        # 2. CREATE SENDER CONTACT ("FROM") - CRITICAL FIX
        # If no specific sender is provided, we use a default "VerbaPost Center" address
        # In the future, you can pull this from the User's "Heirloom Settings" (Mom's address)
        from_payload = {
            "firstName": "The Family Archive",
            "addressLine1": "123 Memory Lane", # Replace with your business address or Mom's address
            "city": "Nashville",
            "provinceOrState": "TN",
            "countryCode": "US",
            "postalOrZip": "37203"
        }
        
        r_from = requests.post(f"{BASE_URL}/contacts", data=from_payload, headers=headers)
        if r_from.status_code not in [200, 201]:
            return {"success": False, "error": f"Sender Error: {r_from.text}"}
            
        from_id = r_from.json().get("id")

        # 3. CREATE LETTER
        # We upload the PDF file directly
        files = {
            'pdf': open(pdf_path, 'rb')
        }
        
        data = {
            "to": to_id,
            "from": from_id,  # <--- Now we have a valid ID!
            "color": "false",
            "express": "false",
            "addressPlacement": "top_first_page" # Standard for letters with address on PDF
        }

        r_letter = requests.post(f"{BASE_URL}/letters", data=data, files=files, headers=headers)
        
        if r_letter.status_code in [200, 201]:
            return {"success": True, "id": r_letter.json().get("id"), "status": "sent"}
        else:
            return {"success": False, "error": r_letter.text}

    except Exception as e:
        return {"success": False, "error": str(e)}