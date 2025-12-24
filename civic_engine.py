import requests
import logging
import json
import streamlit as st

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to get secrets manager
try: import secrets_manager
except ImportError: secrets_manager = None

def get_api_key():
    """Retrieves Geocodio API Key safely."""
    key = None
    if secrets_manager:
        key = secrets_manager.get_secret("geocodio.api_key") or secrets_manager.get_secret("GEOCODIO_API_KEY")
    
    if not key and "geocodio" in st.secrets:
        key = st.secrets["geocodio"]["api_key"]
        
    return key

def get_legislators(address_input):
    """
    Looks up US Senators and Representatives.
    Uses 'cd' field (Congressional Districts) which includes legislators.
    """
    api_key = get_api_key()
    
    if not api_key:
        logger.error("❌ CIVIC DEBUG: Geocodio API Key is MISSING.")
        return []

    # 2. ADDRESS FORMATTING
    if isinstance(address_input, dict):
        parts = [
            address_input.get("street") or "",
            address_input.get("city") or "",
            address_input.get("state") or "",
            address_input.get("zip") or ""
        ]
        address_str = ", ".join([p for p in parts if p.strip()])
    else:
        address_str = str(address_input)

    logger.info(f"🔍 CIVIC DEBUG: Sending Address: '{address_str}'")

    # 3. API CALL
    url = "https://api.geocod.io/v1.7/geocode"
    params = {
        "q": address_str,
        "fields": "cd", # Congressional District
        "api_key": api_key
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        
        if r.status_code != 200:
            logger.error(f"❌ CIVIC API ERROR: {r.status_code} - {r.text}")
            return []
            
        data = r.json()
        results = []
        
        if 'results' in data and len(data['results']) > 0:
            result_block = data['results'][0]
            fields = result_block.get('fields', {})
            
            # PARSING: Geocodio returns 'congressional_districts' array
            districts = fields.get('congressional_districts', [])
            
            if not districts:
                logger.warning("⚠️ CIVIC DEBUG: No 'congressional_districts' found.")
                return []

            for dist in districts:
                # legislators are nested inside the district object
                legislators = dist.get('current_legislators', [])
                
                for leg in legislators:
                    role_type = leg.get('type') # 'senator' or 'representative'
                    # Safe extraction of bio
                    bio = leg.get('bio', {})
                    full_name = f"{bio.get('first_name', '')} {bio.get('last_name', '')}".strip()
                    
                    entry = {
                        "name": "", 
                        "office": "",
                        "address": {
                            "street": "United States Capitol", 
                            "city": "Washington", 
                            "state": "DC", 
                            "zip": "20515"
                        }
                    }

                    # Extract Contact Info if available
                    contact = leg.get('contact', {})
                    if contact.get('address'):
                        entry['address']['street'] = contact['address']

                    if role_type == 'senator':
                        entry['name'] = f"Sen. {full_name}"
                        entry['office'] = "Senate"
                        entry['address']['zip'] = "20510" # Senate Zip
                    elif role_type == 'representative':
                        entry['name'] = f"Rep. {full_name}"
                        entry['office'] = "House of Representatives"
                        entry['address']['zip'] = "20515" # House Zip
                    
                    if entry['name']:
                        results.append(entry)

        else:
            logger.warning("⚠️ CIVIC DEBUG: Geocodio returned 0 results.")
        
        return results

    except Exception as e:
        logger.error(f"❌ CIVIC EXCEPTION: {e}")
        return []

# --- SAFETY ALIAS ---
# This ensures older code calling 'find_representatives' still works
find_representatives = get_legislators