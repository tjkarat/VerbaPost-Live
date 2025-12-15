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
    Includes DEEP DEBUGGING to trace 'No Officials Found' issues.
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
        # Filter out None values to prevent "None" appearing in string
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
        print(f"📡 CIVIC DEBUG: Requesting {url}...")
        r = requests.get(url, params=params, timeout=10)
        
        if r.status_code != 200:
            print(f"❌ CIVIC API ERROR: {r.status_code} - {r.text}")
            return []
            
        data = r.json()
        
        # --- DEEP DEBUGGING: PRINT RAW RESPONSE ---
        # This will show up in your Cloud logs. Look for "RAW RESPONSE".
        # It tells us exactly what Geocodio sees.
        print(f"📦 CIVIC RAW RESPONSE: {json.dumps(data)}")

        results = []
        
        if 'results' in data and len(data['results']) > 0:
            result_block = data['results'][0]
            
            # Check accuracy/parsing
            accuracy = result_block.get('accuracy')
            formatted = result_block.get('formatted_address')
            print(f"✅ CIVIC DEBUG: Geocodio matched: '{formatted}' (Accuracy: {accuracy})")

            # Parse Congress data
            fields = result_block.get('fields', {})
            congress_data = fields.get('congress', {})
            
            if not congress_data:
                print("⚠️ CIVIC DEBUG: 'congress' field is missing in API response! Check API tier features.")
            
            # --- PARSE SENATE ---
            for rep in congress_data.get('senate', []):
                name = f"Sen. {rep['name']['first']} {rep['name']['last']}"
                print(f"   -> Found Senator: {name}")
                results.append({
                    "name": name,
                    "office": "Senate",
                    "address": {
                        "street": "United States Senate",
                        "city": "Washington",
                        "state": "DC",
                        "zip": "20510"
                    }
                })
                
            # --- PARSE HOUSE ---
            for rep in congress_data.get('house', []):
                name = f"Rep. {rep['name']['first']} {rep['name']['last']}"
                print(f"   -> Found Rep: {name}")
                results.append({
                    "name": name,
                    "office": "House of Representatives",
                    "address": {
                        "street": "US House of Representatives",
                        "city": "Washington",
                        "state": "DC",
                        "zip": "20515"
                    }
                })
        else:
            print("⚠️ CIVIC DEBUG: Geocodio returned 0 results for this address.")
        
        return results

    except Exception as e:
        print(f"❌ CIVIC EXCEPTION: {e}")
        return []