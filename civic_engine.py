import requests
import streamlit as st

# Load Key
try:
    API_KEY = st.secrets["geocodio"]["api_key"]
except:
    API_KEY = None

def get_reps(address):
    """
    Looks up federal legislators (2 Senators, 1 Representative) for a given address 
    using the Geocodio API and returns a list of targets for mailing.
    """
    if not API_KEY:
        st.error("❌ Configuration Error: Geocodio API Key is missing.")
        return []

    url = "https://api.geocod.io/v1.7/geocode"
    
    # 🎯 KEY UPDATE: Request 'all-legislators' field for Senators and Representative
    params = {
        'q': address,
        'fields': 'all-legislators', 
        'api_key': API_KEY
    }

    try:
        r = requests.get(url, params=params)
        data = r.json()

        if r.status_code != 200:
            error_msg = data.get('error', f"HTTP Error {r.status_code}")
            st.error(f"❌ Geocodio API Error: {error_msg}")
            return []

        if not data.get('results'):
            st.warning("⚠️ Address not found.")
            return []

        result = data['results'][0]
        targets = []
        target_names = set()

        # Retrieve the relevant legislator data
        legislators = result.get('fields', {}).get('current_legislators', [])

        for leg in legislators:
            role = leg.get('type')
            
            # Filter for Federal Officials: 'senator' and 'representative'
            if role in ['senator', 'representative']:
                
                # Assign Title
                title = "U.S. Senator" if role == 'senator' else "U.S. Representative"
                
                # Get Name
                first = leg.get('bio', {}).get('first_name') or leg.get('first_name', 'Unknown')
                last = leg.get('bio', {}).get('last_name') or leg.get('last_name', 'Official')
                full_name = f"{first} {last}"
                
                # Skip if already added (simple deduplication by name)
                if full_name in target_names:
                    continue
                
                # --- Prepare Mailing Address ---
                contact = leg.get('contact', {})
                # Use office address provided by Geocodio, defaulting to a general DC address
                addr_raw = contact.get('address') or 'United States Capitol, Washington DC 20510'

                # NOTE: For simplicity and reliability, we are only using the D.C. office address
                # that is typically returned by Geocodio for federal reps.
                clean_address = {
                    'name': full_name,
                    'street': addr_raw,
                    'city': "Washington",
                    'state': "DC",
                    'zip': "20510"
                }

                targets.append({
                    'name': full_name,
                    'title': title,
                    'address_obj': clean_address
                })
                target_names.add(full_name) # Add name to the set for deduplication

        if len(targets) != 3:
            st.warning(f"⚠️ Found {len(targets)} legislators. Expected 3 (2 Senators, 1 Rep).")
        
        return targets

    except Exception as e:
        st.error(f"❌ Civic Engine Error: Failed to process request: {e}")
        return []