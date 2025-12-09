import pandas as pd
import io

try: import letter_format
except ImportError: letter_format = None

def parse_csv(uploaded_file, max_rows=1000):
    """
    Parses a CSV file for Campaign Mode.
    Includes sanitization and row limits.
    """
    try:
        df = pd.read_csv(uploaded_file)
        
        # --- FIX: ROW LIMIT ---
        if len(df) > max_rows:
            return [], f"File contains {len(df)} rows. Maximum allowed is {max_rows}."

        df.columns = df.columns.str.strip().str.lower()
        
        required = ['name', 'street', 'city', 'state', 'zip']
        missing = [col for col in required if col not in df.columns]
        
        if missing:
            rename_map = {
                'address': 'street', 'address 1': 'street', 'address line 1': 'street',
                'recipient': 'name', 'full name': 'name',
                'postal': 'zip', 'zip code': 'zip', 'zipcode': 'zip',
                'province': 'state'
            }
            df.rename(columns=rename_map, inplace=True)
            missing = [col for col in required if col not in df.columns]
            if missing:
                return [], f"Missing columns: {', '.join(missing)}"

        contacts = []
        for index, row in df.iterrows():
            def clean(val):
                if pd.isna(val): return ""
                s_val = str(val).strip()
                if letter_format: return letter_format.sanitize_text(s_val)
                return s_val

            raw_zip = str(row.get('zip', '')).replace('.0', '').strip()
            
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
                "address_line2": addr2, 
                "city": clean(row.get('city')),
                "state": clean(row.get('state')),
                "zip": clean(raw_zip),
                "country": "US" 
            }
            
            if contact['name'] and contact['street']:
                contacts.append(contact)
            
        return contacts, None

    except Exception as e:
        return [], f"CSV Parse Error: {str(e)}"