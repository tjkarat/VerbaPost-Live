import requests
import streamlit as st

def get_reps(address):
    """
    Production Mode: Queries Geocodio v1.9 and returns Federal Legislators.
    """
    # 1. Load Key
    try:
        api_key = st.secrets["geocodio"]["api_key"]
    except:
        st.error("❌ Missing API Key.")
        return []

    # 2. Request (Updated to v1.9)
    url = "https://api.geocod.io/v1.9/geocode"
    params = {
        'q': address,
        'fields': 'cd', # 'cd' includes congressional district & legislator data
        'api_key': api_key
    }

    try:
        r = requests.get(url, params=params)
        data = r.json()

        if r.status_code != 200:
            st.error(f"Address Lookup Failed: {data.get('error')}")
            return []

        if not data.get('results'):
            st.warning("Address not found.")
            return []

        # 3. Parse Results
        result = data['results'][0]
        fields = result.get('fields', {})
        
        # Geocodio v1.9 structure for 'cd' field
        districts = fields.get('congressional_districts', [])
        
        if not districts:
            st.warning("No congressional district found for this address.")
            return []

        # 4. Get Legislators
        # We grab the first district (correct for 99% of residential addresses)
        current_legislators = districts[0].get('current_legislators', [])
        
        targets = []
        
        for leg in current_legislators:
            # FIX: Normalize to lowercase for comparison
            role = leg.get('type', '').lower()
            
            # Accept 'senator' or 'representative' (case-insensitive)
            if role in ['senator', 'representative']:
                
                # Extract Name
                bio = leg.get('bio', {})
                first = bio.get('first_name', 'Unknown')
                last = bio.get('last_name', 'Official')
                full_name = f"{first} {last}"
                
                # Assign Title
                title = "U.S. Senator" if role == 'senator' else "U.S. Representative"
                
                # Extract Address
                contact = leg.get('contact', {})
                addr_raw = contact.get('address') or "United States Capitol, Washington DC 20510"
                
                targets.append({
                    'name': full_name,
                    'title': title,
                    'address_obj': {
                        'name': full_name, 
                        'street': addr_raw, 
                        'city': "Washington", 
                        'state': "DC", 
                        'zip': "20510"
                    }
                })

        return targets

    except Exception as e:
        st.error(f"Connection Error: {e}")
        return []