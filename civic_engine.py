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

    # 3. API CALL
    url = "https://api.geocod.io/v1.7/geocode"
    params = {
        "q": address_str,
        "fields": "congress",
        "api_key": api_key
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        
        if r.status_code != 200:
            print(f"❌ CIVIC API ERROR: {r.status_code} - {r.text}")
            return []
            
        data = r.json()
        
        # LOG RAW RESPONSE
        print(f"📦 CIVIC RAW: {json.dumps(data)}")

        results = []
        
        if 'results' in data and len(data['results']) > 0:
            result_block = data['results'][0]
            fields = result_block.get('fields', {})
            congress_data = fields.get('congress', {})
            
            # PARSE SENATE
            for rep in congress_data.get('senate', []):
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
                
            # PARSE HOUSE
            for rep in congress_data.get('house', []):
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
        print(f"❌ CIVIC EXCEPTION: {e}")
        return []