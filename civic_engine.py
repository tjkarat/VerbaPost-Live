import requests
import streamlit as st
import urllib.parse

# Load Key
try:
    API_KEY = st.secrets["google"]["civic_key"]
except:
    API_KEY = None

def get_reps(address):
    # 1. STRICT VALIDATION
    if not address or len(address.strip()) < 10:
        st.error("❌ Address Error: Please enter a full US street address.")
        return []

    if not API_KEY:
        st.error("❌ Config Error: Google API Key missing.")
        return []

    # 2. OFFICIAL ENDPOINT
    url = "https://www.googleapis.com/civicinfo/v2/representatives"
    
    params = {
        'key': API_KEY,
        'address': address,
        'levels': 'country',
        'roles': ['legislatorUpperBody', 'legislatorLowerBody']
    }

    try:
        r = requests.get(url, params=params)
        data = r.json()
        
        # 3. ERROR DECODING
        if "error" in data:
            msg = data['error'].get('message', 'Unknown')
            code = data['error'].get('code', 0)
            if code == 404:
                st.warning(f"⚠️ Address Not Found: Google could not match '{address}' to a voting district.")
            else:
                st.error(f"❌ Google API Error {code}: {msg}")
            return []

        targets = []
        if 'offices' not in data:
            st.warning("⚠️ No representatives found for this location.")
            return []

        # 4. PARSING
        for office in data.get('offices', []):
            name = office['name'].lower()
            if "senate" in name or "senator" in name or "representative" in name:
                for index in office['officialIndices']:
                    official = data['officials'][index]
                    
                    # Address Fallback
                    addr_list = official.get('address', [])
                    if addr_list:
                        raw = addr_list[0]
                        addr_obj = {
                            'name': official['name'],
                            'street': raw.get('line1', ''),
                            'city': raw.get('city', ''),
                            'state': raw.get('state', ''),
                            'zip': raw.get('zip', '')
                        }
                    else:
                        # Fallback for safety
                        addr_obj = {
                            'name': official['name'], 
                            'street': 'United States Capitol', 
                            'city': 'Washington', 'state': 'DC', 'zip': '20515'
                        }
                    
                    targets.append({
                        'name': official['name'],
                        'title': office['name'],
                        'address_obj': addr_obj
                    })
        
        return targets

    except Exception as e:
        st.error(f"System Error: {e}")
        return []