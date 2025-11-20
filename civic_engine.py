import requests
import streamlit as st

# Load Key
try:
    API_KEY = st.secrets["google"]["civic_key"]
except:
    API_KEY = None

def get_reps(address):
    if not API_KEY:
        return []

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
        
        if "error" in data:
            # Print error to logs for debugging
            print(f"Google API Error: {data['error']['message']}")
            return []

        targets = []
        
        for office in data.get('offices', []):
            if "United States Senate" in office['name'] or "House of Representatives" in office['name']:
                for index in office['officialIndices']:
                    official = data['officials'][index]
                    addr_raw = official.get('address', [{}])[0]
                    
                    clean_address = {
                        'name': official['name'],
                        'street': addr_raw.get('line1', ''),
                        'city': addr_raw.get('city', ''),
                        'state': addr_raw.get('state', ''),
                        'zip': addr_raw.get('zip', '')
                    }
                    
                    if clean_address['street']:
                        targets.append({
                            'name': official['name'],
                            'title': office['name'],
                            'address_obj': clean_address
                        })
        
        return targets

    except Exception as e:
        print(f"Civic Engine Crash: {e}")
        return []