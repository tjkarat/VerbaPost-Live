import pandas as pd
import io

# Import letter_format for the sanitization logic
try: import letter_format
except ImportError: letter_format = None

def parse_csv(uploaded_file):
    """
    Parses a CSV file for Campaign Mode.
    1. Reads CSV using Pandas.
    2. Sanitizes all inputs (strips emojis, fixes encoding).
    3. Maps columns to standard keys (including address_line2).
    """
    try:
        # Load CSV
        df = pd.read_csv(uploaded_file)
        
        # Normalize headers to lowercase for easier matching
        df.columns = df.columns.str.strip().str.lower()
        
        # Required columns check
        required = ['name', 'street', 'city', 'state', 'zip']
        missing = [col for col in required if col not in df.columns]
        
        if missing:
            # Try to be smart about flexible headers
            rename_map = {
                'address': 'street', 'address 1': 'street', 'address line 1': 'street',
                'recipient': 'name', 'full name': 'name',
                'postal': 'zip', 'zip code': 'zip', 'zipcode': 'zip',
                'province': 'state'
            }
            df.rename(columns=rename_map, inplace=True)
            
            # Re-check
            missing = [col for col in required if col not in df.columns]
            if missing:
                return [], f"Missing columns: {', '.join(missing)}"

        contacts = []
        
        # Iterate and Sanitize
        for index, row in df.iterrows():
            
            def clean(val):
                """Helper to stringify and sanitize"""
                if pd.isna(val): return ""
                s_val = str(val).strip()
                if letter_format:
                    return letter_format.sanitize_text(s_val)
                return s_val

            # Handle Zip Code conversion (remove .0 from floats)
            raw_zip = str(row.get('zip', '')).replace('.0', '').strip()
            
            # Smart mapping for Address Line 2
            # Check for 'street 2', 'address 2', 'apt', 'suite', 'unit'
            addr2 = ""
            for possible_col in ['street 2', 'street2', 'address 2', 'address line 2', 'apt', 'suite', 'unit']:
                if possible_col in df.columns:
                    val = clean(row.get(possible_col))
                    if val:
                        addr2 = val
                        break

            contact = {
                "name": clean(row.get('name')),
                "street": clean(row.get('street')),
                "address_line2": addr2, # Standardized key
                "city": clean(row.get('city')),
                "state": clean(row.get('state')),
                "zip": clean(raw_zip),
                "country": "US" # Bulk engine defaults to US for now
            }
            
            # Basic validation
            if contact['name'] and contact['street']:
                contacts.append(contact)
            
        return contacts, None

    except Exception as e:
        return [], f"CSV Parse Error: {str(e)}"