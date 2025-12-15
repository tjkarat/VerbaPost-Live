import requests
import secrets_manager
import logging

logger = logging.getLogger(__name__)

def find_representatives(address_input):
    """
    Looks up US Senators and Representatives for a given address.
    """
    # 1. KEY RETRIEVAL (Try all common variations)
    api_key = (
        secrets_manager.get_secret("geocodio.api_key") or 
        secrets_manager.get_secret("GEOCODIO_API_KEY")
    )
    
    if not api_key:
        print("❌ CIVIC ERROR: Geocodio API Key is MISSING.")
        return []

    # 2. ADDRESS FORMATTING
    if isinstance(address_input, dict):
        parts = [
            address_input.get("street", ""),
            address_input.get("city", ""),
            address_input.get("state", ""),
            address_input.get("zip", "")
        ]
        address_str = ", ".join([p for p in parts if p])
    else:
        address_str = str(address_input)

    print(f"🔍 CIVIC LOOKUP: Sending '{address_str}' to Geocodio...")

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
            print(f"❌ CIVIC API FAIL: {r.status_code} - {r.text}")
            return []
            
        data = r.json()
        results = []
        
        if 'results' in data and len(data['results']) > 0:
            # Check for Congress data block
            fields = data['results'][0].get('fields', {}).get('congress', {})
            
            # --- PARSE SENATE ---
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
                
            # --- PARSE HOUSE ---
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
        
        if not results:
            print(f"⚠️ CIVIC: API returned success but no officials found.")
        else:
            print(f"✅ CIVIC: Found {len(results)} officials.")
            
        return results

    except Exception as e:
        print(f"❌ CIVIC EXCEPTION: {e}")
        return []