import requests
import streamlit as st

# Load Key
try:
    API_KEY = st.secrets["google"]["civic_key"]
except:
    API_KEY = None

def get_reps(address):
    if not API_KEY:
        print("❌ Error: Google Civic API Key missing.")
        return []

    url = "https://www.googleapis.com/civicinfo/v2/representatives"
    params = {
        'key': API_KEY,
        'address': address,
        'levels': 'country',
        'roles': ['legislatorUpperBody', 'legislatorLowerBody']
    }

    print(f"🔍 Searching Civic Data for: {address}")

    try:
        r = requests.get(url, params=params)
        data = r.json()
        
        if "error" in data:
            print(f"❌ Google API Error: {data['error']['message']}")
            return []

        targets = []
        
        # Debug: Print what offices were found
        offices = data.get('offices', [])
        print(f"✅ Found {len(offices)} offices.")

        for office in offices:
            # Looser matching to catch variations like "U.S. Senator"
            name_lower = office['name'].lower()
            if "senate" in name_lower or "senator" in name_lower or "representative" in name_lower:
                for index in office['officialIndices']:
                    official = data['officials'][index]
                    
                    # Parse Address safely
                    addr_list = official.get('address', [])
                    if not addr_list:
                        # Fallback: Use Washington DC dummy if real address is missing (common for some reps)
                        clean_address = {
                            'name': official['name'],
                            'street': 'United States Capitol',
                            'city': 'Washington',
                            'state': 'DC',
                            'zip': '20510'
                        }
                    else:
                        addr_raw = addr_list[0]
                        clean_address = {
                            'name': official['name'],
                            'street': addr_raw.get('line1', ''),
                            'city': addr_raw.get('city', ''),
                            'state': addr_raw.get('state', ''),
                            'zip': addr_raw.get('zip', '')
                        }
                    
                    targets.append({
                        'name': official['name'],
                        'title': office['name'],
                        'address_obj': clean_address
                    })
        
        print(f"✅ Returning {len(targets)} targets.")
        return targets

    except Exception as e:
        print(f"❌ Civic Engine Crash: {e}")
        return []