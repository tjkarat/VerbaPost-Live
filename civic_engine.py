import requests
import streamlit as st
import secrets_manager

def get_reps(address):
    """
    Queries Geocodio to find Federal Legislators.
    Returns list of dicts with address_obj ready for PostGrid.
    """
    api_key = secrets_manager.get_secret("geocodio.api_key")
    if not api_key:
        st.error("❌ Missing Geocodio API Key.")
        return []

    url = "https://api.geocod.io/v1.7/geocode"
    params = {'q': address, 'fields': 'cd', 'api_key': api_key}

    try:
        r = requests.get(url, params=params)
        data = r.json()

        if r.status_code != 200 or not data.get('results'):
            st.warning("Address not found or invalid.")
            return []

        # Parse First Result
        result = data['results'][0]
        districts = result.get('fields', {}).get('congressional_districts', [])
        
        if not districts:
            st.warning("No congressional district data found.")
            return []

        # Get Legislators
        legislators = districts[0].get('current_legislators', [])
        targets = []
        
        for leg in legislators:
            role = leg.get('type', '').lower()
            if role in ['senator', 'representative']:
                
                # Name
                first = leg.get('bio', {}).get('first_name', '')
                last = leg.get('bio', {}).get('last_name', '')
                full_name = f"{first} {last}".strip()
                
                # Title
                title = "U.S. Senator" if role == 'senator' else "U.S. Representative"
                
                # Address Parsing
                contact = leg.get('contact', {})
                addr_lines = contact.get('address', '').split(',')
                
                # Fallback Address if API is empty
                if not addr_lines or not addr_lines[0]:
                    street = "United States Capitol"
                    city = "Washington"
                    state = "DC"
                    zip_code = "20510"
                else:
                    # Robust parsing attempt
                    street = addr_lines[0].strip()
                    city = "Washington" # Federal reps are always DC
                    state = "DC"
                    zip_code = "20510" # Default Capitol Zip if missing
                    
                    # Try to find zip in raw string
                    import re
                    zip_match = re.search(r'\b205\d{2}\b', contact.get('address', ''))
                    if zip_match: zip_code = zip_match.group(0)

                targets.append({
                    'name': f"{title} {full_name}",
                    'title': title,
                    'address_obj': {
                        'name': f"{title} {full_name}", 
                        'street': street,
                        'city': city, 
                        'state': state, 
                        'zip': zip_code,
                        'country': 'US'
                    }
                })

        return targets

    except Exception as e:
        st.error(f"Civic Lookup Error: {e}")
        return []