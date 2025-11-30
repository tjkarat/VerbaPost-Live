import pandas as pd
import streamlit as st

def parse_csv(uploaded_file):
    """
    Reads a CSV and normalizes headers to: name, street, city, state, zip, country
    """
    try:
        df = pd.read_csv(uploaded_file)
        
        # 1. Normalize Column Names (Case insensitive)
        df.columns = [c.lower().strip() for c in df.columns]
        
        # 2. Map common variations to our required keys
        # We need: name, street, city, state, zip
        mappings = {
            'full name': 'name', 'recipient': 'name',
            'address': 'street', 'address1': 'street', 'address line 1': 'street',
            'zipcode': 'zip', 'postal code': 'zip', 'postal': 'zip'
        }
        df.rename(columns=mappings, inplace=True)
        
        # 3. Validation
        required = ['name', 'street', 'city', 'state', 'zip']
        missing = [col for col in required if col not in df.columns]
        
        if missing:
            return None, f"Missing columns: {', '.join(missing)}. Please check CSV headers."
            
        # 4. Convert to List of Dicts
        # Force US for now (Political campaigns are domestic)
        df['country'] = 'US'
        contacts = df[required + ['country']].to_dict('records')
        
        return contacts, None
        
    except Exception as e:
        return None, f"CSV Error: {str(e)}"
