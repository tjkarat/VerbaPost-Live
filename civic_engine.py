import requests
import secrets_manager
import logging

logger = logging.getLogger(__name__)

def find_representatives(address_input):
    """
    Looks up US Senators and Representatives for a given address.
    
    Args:
        address_input (dict or str): The user's address.
        
    Returns:
        list: A list of dicts [{'name':..., 'office':..., 'address':...}]
    """
    api_key = secrets_manager.get_secret("geocodio.api_key") or secrets_manager.get_secret("GEOCIDIO_API_KEY")
    if not api_key:
        logger.error("Geocodio API Key missing")
        return []

    # 1. Format Address String
    if isinstance(address_input, dict):
        # Convert dict to single string for API
        parts = [
            address_input.get("street", ""),
            address_input.get("city", ""),
            address_input.get("state", ""),
            address_input.get("zip", "")
        ]
        address_str = ", ".join([p for p in parts if p])
    else:
        address_str = str(address_input)

    # 2. Call API
    url = "https://api.geocod.io/v1.7/geocode"
    params = {
        "q": address_str,
        "fields": "congress",
        "api_key": api_key
    }

    try:
        r = requests.get(url, params=params, timeout=5)
        if r.status_code != 200:
            logger.error(f"Geocodio API Error: {r.text}")
            return []
            
        data = r.json()
        results = []
        
        if 'results' in data and len(data['results']) > 0:
            # Parse Congress data
            fields = data['results'][0].get('fields', {}).get('congress', {})
            
            # Helper to format the official's DC address
            def _format_dc_address(addr_list):
                # Geocodio returns addresses as a list of strings sometimes, or logic varies
                # We will construct a generic DC address if detailed one is missing
                return {
                    "street": "United States Capitol",
                    "city": "Washington",
                    "state": "DC",
                    "zip": "20510"
                }

            # A. Process Senators
            for rep in fields.get('senate', []):
                results.append({
                    "name": f"Sen. {rep['name']['first']} {rep['name']['last']}",
                    "office": "Senate",
                    # Geocodio usually provides contact info, but address structure varies.
                    # We default to a standard structure for the UI to consume.
                    "address": {
                        "street": rep.get('address', 'United States Senate'),
                        "city": "Washington",
                        "state": "DC",
                        "zip": "20510"
                    }
                })
                
            # B. Process House Reps
            for rep in fields.get('house', []):
                results.append({
                    "name": f"Rep. {rep['name']['first']} {rep['name']['last']}",
                    "office": "House of Representatives",
                    "address": {
                        "street": rep.get('address', 'US House of Representatives'),
                        "city": "Washington",
                        "state": "DC",
                        "zip": "20515"
                    }
                })
                
        return results

    except Exception as e:
        logger.error(f"Civic Lookup Failed: {e}")
        return []