import streamlit as st
import requests
import json

# Load API Key
try:
    LOB_API_KEY = st.secrets["LOB_API_KEY"]
except Exception:
    LOB_API_KEY = None

def send_letter(pdf_path, to_address, from_address):
    """
    Sends a PDF letter via Lob using direct REST API (No SDK required).
    """
    if not LOB_API_KEY:
        print("❌ Error: Lob API Key missing.")
        st.error("System Error: Mailing key is missing.")
        return None

    try:
        url = "https://api.lob.com/v1/letters"
        
        # Lob expects Basic Auth with the API Key as the username
        auth = (LOB_API_KEY, '')

        # Prepare the form data
        # We perform a multipart upload since we are sending a file + data
        files = {
            'file': open(pdf_path, 'rb')
        }
        
        data = {
            'description': f"VerbaPost to {to_address.get('name')}",
            'to[name]': to_address.get('name'),
            'to[address_line1]': to_address.get('address_line1'),
            'to[address_city]': to_address.get('address_city'),
            'to[address_state]': to_address.get('address_state'),
            'to[address_zip]': to_address.get('address_zip'),
            'from[name]': from_address.get('name'),
            'from[address_line1]': from_address.get('address_line1'),
            'from[address_city]': from_address.get('address_city'),
            'from[address_state]': from_address.get('address_state'),
            'from[address_zip]': from_address.get('address_zip'),
            'color': 'false', # Black and white is cheaper
            'double_sided': 'true'
        }

        # Send Request
        response = requests.post(url, auth=auth, data=data, files=files)
        
        # Close the file handle
        files['file'].close()

        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Lob Error: {response.text}")
            st.error(f"Mailing Error: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Connection Error: {e}")
        st.error(f"Mailing Connection Error: {e}")
        return None