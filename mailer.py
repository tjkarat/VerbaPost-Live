import streamlit as st
import lob

# Load API Key
try:
    # Attempt to get key from secrets
    LOB_API_KEY = st.secrets["LOB_API_KEY"]
    lob.api_key = LOB_API_KEY
except Exception:
    LOB_API_KEY = None

def send_letter(pdf_path, to_address, from_address):
    """
    Sends a PDF letter via Lob.
    to_address and from_address should be dictionaries with keys:
    name, address_line1, address_city, address_state, address_zip
    """
    if not LOB_API_KEY:
        print("❌ Error: Lob API Key missing.")
        return None

    try:
        # 1. Create the address objects in Lob (optional but good for validation)
        # For simplicity in this demo, we pass dicts directly to the letter endpoint
        
        # 2. Upload and Send
        with open(pdf_path, 'rb') as file:
            response = lob.Letter.create(
                description=f"VerbaPost to {to_address['name']}",
                to_address=to_address,
                from_address=from_address,
                file=file,
                color=False,    # B&W is cheaper
                double_sided=True
            )
            
        return response

    except Exception as e:
        print(f"❌ Lob Error: {e}")
        st.error(f"Mailing Error: {e}")
        return None