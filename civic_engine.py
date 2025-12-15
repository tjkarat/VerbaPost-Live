import requests
import secrets_manager
import logging
import json

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_representatives(address_input):
    """
    Looks up US Senators and Representatives.
    Uses 'cd' field (Congressional Districts) which includes legislators.
    """
    # 1. KEY RETRIEVAL
    api_key = (
        secrets_manager.get_secret("geocodio.api_key") or 
        secrets_manager.get_secret("GEOCODIO_API_KEY")
    )
    
    if not api_key:
        print("❌ CIVIC DEBUG: Geocodio API Key is MISSING.")
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

    print(f"🔍 CIVIC DEBUG: Sending Address: '{address_str}'")

    # 3. API CALL (Updated to use 'cd' instead of 'congress')
    # Use v1.7 as per your logs, but 'cd' is the standard field now.
    url = "https://api.geocod.io/v1.7/geocode"
    params = {
        "q": address_str,
        "fields": "cd", # FIX: Changed from 'congress' to 'cd'
        "api_key": api_key
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        
        if r.status_code != 200:
            print(f"❌ CIVIC API ERROR: {r.status_code} - {r.text}")
            return []
            
        data = r.json()
        
        # DEBUG: Print raw to confirm structure
        print(f"📦 CIVIC RAW RESPONSE: {json.dumps(data)}")

        results = []
        
        if 'results' in data and len(data['results']) > 0:
            result_block = data['results'][0]
            fields = result_block.get('fields', {})
            
            # PARSING UPDATE: Geocodio returns 'congressional_districts' array
            # We default to the first one found (standard for single address)
            districts = fields.get('congressional_districts', [])
            
            if not districts:
                print("⚠️ CIVIC DEBUG: No 'congressional_districts' found in response.")
                return []

            for dist in districts:
                # legislators are nested inside the district object
                legislators = dist.get('current_legislators', [])
                
                for leg in legislators:
                    role_type = leg.get('type') # 'senator' or 'representative'
                    full_name = f"{leg['bio']['first_name']} {leg['bio']['last_name']}"
                    
                    # Map Geocodio structure to our App structure
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
                    
                    results.append(entry)
                    print(f"   -> Found {entry['name']}")

        else:
            print("⚠️ CIVIC DEBUG: Geocodio returned 0 results for this address.")
        
        return results

    except Exception as e:
        print(f"❌ CIVIC EXCEPTION: {e}")
        return []