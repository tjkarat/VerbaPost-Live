import requests
import secrets_manager
import logging

logger = logging.getLogger(__name__)

def get_representatives(address_string):
    """
    Returns a list of dictionaries: [{'name': 'Sen. Ted Cruz', 'role': 'Senate'}, ...]
    """
    api_key = secrets_manager.get_secret("geocodio.api_key")
    if not api_key:
        logger.error("Geocodio API Key missing")
        return []

    url = "https://api.geocod.io/v1.7/geocode"
    params = {
        "q": address_string,
        "fields": "congress",
        "api_key": api_key
    }

    try:
        r = requests.get(url, params=params, timeout=5)
        data = r.json()
        
        results = []
        if 'results' in data and len(data['results']) > 0:
            # Parse Congress data
            fields = data['results'][0].get('fields', {}).get('congress', {})
            
            # Senators (usually 2)
            for rep in fields.get('senate', []):
                results.append(f"Sen. {rep['name']}")
                
            # House Rep (usually 1)
            for rep in fields.get('house', []):
                results.append(f"Rep. {rep['name']}")
                
        return results

    except Exception as e:
        logger.error(f"Civic Lookup Failed: {e}")
        return []