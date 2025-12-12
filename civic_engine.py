import requests
import streamlit as st
import secrets_manager
import logging
import re

logger = logging.getLogger(__name__)

def get_reps(address):
    """
    Queries Geocodio v1.7 and returns Federal Legislators.
    Returns a list of dictionaries with 'address_obj' formatted for PostGrid.
    """
    api_key = secrets_manager.get_secret("geocodio.api_key") or secrets_manager.get_secret("GEOCODIO_API_KEY")
    if not api_key:
        st.error("❌ Missing Geocodio API Key.")
        return []

    url = "https://api.geocod.io/v1.7/geocode"
    params = {
        'q': address,
        'fields': 'cd', 
        'api_key': api_key
    }

    try:
        r = requests.get(url, params=params)
        data = r.json()

        if r.status_code != 200 or not data.get('results'):
            st.warning("Address not found.")
            return []

        # Parse First Result
        result = data['results'][0]
        fields = result.get('fields', {})
        districts = fields.get('congressional_districts', [])
        
        if not districts:
            return []

        # Get Legislators
        current_legislators = districts[0].get('current_legislators', [])
        targets = []
        
        for leg in current_legislators:
            role = leg.get('type', '').lower()
            
            # Accept 'senator' or 'representative'
            if role in ['senator', 'representative']:
                
                # Extract Name
                bio = leg.get('bio', {})
                first = bio.get('first_name', 'Unknown')
                last = bio.get('last_name', 'Official')
                full_name = f"{first} {last}"
                
                # Assign Title
                title = "U.S. Senator" if role == 'senator' else "U.S. Representative"
                
                # --- CRITICAL FIX: ADDRESS PARSING ---
                contact = leg.get('contact', {})
                raw_address = contact.get('address', '')
                
                # Defaults
                street = "United States Capitol"
                city = "Washington"
                state = "DC"
                zip_code = "20510"
                
                # Parse raw string "123 Main St, Washington, DC 20510"
                if raw_address:
                    parts = raw_address.split(',')
                    if len(parts) >= 1:
                        street = parts[0].strip()
                    
                    # Extract Zip
                    zip_match = re.search(r'\b205\d{2}\b', raw_address)
                    if zip_match:
                        zip_code = zip_match.group(0)

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
        logger.error(f"Civic Engine Error: {e}")
        return []