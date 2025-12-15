import requests
import secrets_manager
import logging
import streamlit as st

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_representatives(address_input):
    """
    Looks up US Senators and Representatives for a given address.
    Args: address_input (dict or str)
    """
    # 1. Get API Key
    api_key = secrets_manager.get_secret("geocodio.api_key") or secrets_manager.get_secret("GEOCODIO_API_KEY")
    
    if not api_key:
        print("❌ CIVIC DEBUG: API Key is MISSING.")
        return []
    
    masked_key = f"{api_key[:4]}...{api_key[-4:]}"
    print(f"🔍 CIVIC DEBUG: Using API Key: {masked_key}")

    # 2. Format Address
    if isinstance(address_input, dict):
        # Join non-empty parts
        parts = [
            address_input.get("street", ""),
            address_input.get("city", ""),
            address_input.get("state", ""),
            address_input.get("zip", "")
        ]
        address_str = ", ".join([p for p in parts if p])
    else:
        address_str = str(address_input)

    print(f"🔍 CIVIC DEBUG: Searching for Address: '{address_str}'")

    # 3. Call API
    url = "https://api.geocod.io/v1.7/geocode"
    params = {
        "q": address_str,
        "fields": "congress",
        "api_key": api_key
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        
        print(f"📡 CIVIC DEBUG: Status Code: {r.status_code}")
        
        if r.status_code != 200:
            print(f"❌ CIVIC DEBUG: API Error Response: {r.text}")
            return []
            
        data = r.json()
        
        # DEBUG: Print the raw structure of the first result
        if 'results' in data and len(data['results']) > 0:
            print(f"✅ CIVIC DEBUG: Raw Match found: {data['results'][0].get('formatted_address')}")
        else:
            print(f"⚠️ CIVIC DEBUG: No results found in Geocodio response: {data}")
            return []

        results = []
        
        # Parse Congress data
        fields = data['results'][0].get('fields', {}).get('congress', {})
        
        # Senators
        for rep in fields.get('senate', []):
            results.append({
                "name": f"Sen. {rep['name']['first']} {rep['name']['last']}",
                "office": "Senate",
                "address": {
                    "street": "United States Senate",
                    "city": "Washington",
                    "state": "DC",
                    "zip": "20510"
                }
            })
            
        # House Reps
        for rep in fields.get('house', []):
            results.append({
                "name": f"Rep. {rep['name']['first']} {rep['name']['last']}",
                "office": "House of Representatives",
                "address": {
                    "street": "US House of Representatives",
                    "city": "Washington",
                    "state": "DC",
                    "zip": "20515"
                }
            })
        
        print(f"✅ CIVIC DEBUG: Returning {len(results)} officials.")
        return results

    except Exception as e:
        print(f"❌ CIVIC DEBUG EXCEPTION: {e}")
        return []