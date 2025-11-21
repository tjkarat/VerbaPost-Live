import requests
import streamlit as st
import urllib.parse

try:
    API_KEY = st.secrets["google"]["civic_key"]
except:
    API_KEY = None

def get_reps(address):
    if not API_KEY:
        st.error("❌ Google API Key missing.")
        return []

    base_url = "https://www.googleapis.com/civicinfo/v2/representatives"
    
    # Function to call API
    def fetch_data(addr_str):
        params = {
            'key': API_KEY,
            'address': addr_str,
            'levels': 'country',
            'roles': ['legislatorUpperBody', 'legislatorLowerBody']
        }
        return requests.get(base_url, params=params)

    # 1. Try Full Address
    r = fetch_data(address)
    
    # 2. Fallback: If 404 or empty, try just Zip Code
    if r.status_code != 200 or 'offices' not in r.json():
        print(f"Specific address failed, retrying with Zip Code...")
        # Extract Zip from string (simple heuristic)
        zip_code = address.split()[-1] 
        if len(zip_code) == 5 and zip_code.isdigit():
             st.warning(f"⚠️ Exact address not matched. Searching by Zip Code ({zip_code}) instead.")
             r = fetch_data(zip_code)

    data = r.json()
    
    if "error" in data:
        st.error(f"❌ API Error: {data['error'].get('message', 'Unknown')}")
        return []

    targets = []
    for office in data.get('offices', []):
        name_lower = office['name'].lower()
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