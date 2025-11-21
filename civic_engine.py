import requests
import streamlit as st
import urllib.parse

# Load Key
try:
    API_KEY = st.secrets["google"]["civic_key"]
except:
    API_KEY = None

def get_reps(address):
    if not API_KEY:
        st.error("❌ Google Civic API Key is missing.")
        return []

    # Standard Endpoint
    base_url = "https://www.googleapis.com/civicinfo/v2/representatives"
    
    def fetch_data(addr_str, strict_filters=True):
        params = {'key': API_KEY, 'address': addr_str}
        if strict_filters:
            params['levels'] = 'country'
            params['roles'] = ['legislatorUpperBody', 'legislatorLowerBody']
        return requests.get(base_url, params=params)

    # 1. Try Full Address (Strict Filters)
    r = fetch_data(address, strict_filters=True)
    
    # 2. Fallback: If failed, try Zip Code (Loose Filters)
    if r.status_code != 200 or 'offices' not in r.json():
        # Extract Zip
        zip_code = address.split()[-1] if address else ""
        if len(zip_code) == 5 and zip_code.isdigit():
             st.warning(f"⚠️ Exact address not matched. Searching by Zip Code ({zip_code}).")
             # Retry without filters to prevent "Method Not Found" on zips
             r = fetch_data(zip_code, strict_filters=False)

    data = r.json()
    
    # Error Handling
    if "error" in data:
        err_msg = data['error'].get('message', 'Unknown Error')
        # Suppress 404s on fallback, just return empty
        if r.status_code != 404:
            st.error(f"❌ Civic API Error: {err_msg}")
        return []

    targets = []
    if 'offices' not in data:
        return []

    for office in data.get('offices', []):
        name_lower = office['name'].lower()
        # Manual Filter for Federal Reps
        if "senate" in name_lower or "senator" in name_lower or "representative" in name_lower:
            for index in office['officialIndices']:
                official = data['officials'][index]
                
                # Address Parsing
                addr_list = official.get('address', [])
                if not addr_list:
                    clean_address = {'name': official['name'], 'street': 'United States Capitol', 'city': 'Washington', 'state': 'DC', 'zip': '20510'}
                else:
                    raw = addr_list[0]
                    clean_address = {
                        'name': official['name'],
                        'street': raw.get('line1', ''),
                        'city': raw.get('city', ''),
                        'state': raw.get('state', ''),
                        'zip': raw.get('zip', '')
                    }
                
                targets.append({
                    'name': official['name'],
                    'title': office['name'],
                    'address_obj': clean_address
                })
    
    return targets