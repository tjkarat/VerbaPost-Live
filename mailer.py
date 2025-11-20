import requests
import streamlit as st
import os

# Load API Key
try:
    LOB_API_KEY = st.secrets["lob"]["api_key"]
    LOB_AVAILABLE = True
except:
    LOB_AVAILABLE = False
    LOB_API_KEY = ""

def send_letter(pdf_path):
    """
    Uploads the PDF to Lob using direct API calls (No library required).
    """
    if not LOB_AVAILABLE:
        print("⚠️ Simulation: Mail sent (No Lob API Key).")
        return True

    print(f"📮 Sending to Lob (Direct API): {os.path.basename(pdf_path)}")
    
    url = "https://api.lob.com/v1/letters"
    
    try:
        with open(pdf_path, 'rb') as file:
            # Define the letter data
            # In Day 4, we will make these addresses dynamic variables!
            payload = {
                "description": "VerbaPost Letter",
                "to[name]": "VerbaPost User",
                "to[address_line1]": "185 Berry St",
                "to[address_city]": "San Francisco",
                "to[address_state]": "CA",
                "to[address_zip]": "94107",
                "from[name]": "Tarak Robbana",
                "from[address_line1]": "1008 Brandon Court",
                "from[address_city]": "Mt Juliet",
                "from[address_state]": "TN",
                "from[address_zip]": "37122",
                "color": "false"
            }
            
            # Send the request with Basic Auth (Key is username, password is blank)
            response = requests.post(
                url, 
                auth=(LOB_API_KEY, ''), 
                data=payload, 
                files={'file': file}
            )
            
            if response.status_code == 200:
                print(f"✅ Lob Success: {response.json()['id']}")
                return True
            else:
                error_msg = response.json().get('error', {}).get('message', 'Unknown Error')
                print(f"❌ Lob Error: {error_msg}")
                st.error(f"Mailing Failed: {error_msg}")
                return False

    except Exception as e:
        st.error(f"Connection Error: {e}")
        return False