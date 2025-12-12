import pandas as pd
import io

# Try to import the letter formatting utility if it exists in your project
try:
    import letter_format
except ImportError:
    letter_format = None

class SmartBulkEngine:
    def __init__(self):
        # Dictionary mapping standard internal names to common CSV headers
        self.column_aliases = {
            'name': ['recipient', 'full name', 'fullname', 'contact', 'customer', 'client'],
            'street': ['address', 'address1', 'addr', 'address line 1', 'street address'],
            'street2': ['address2', 'address line 2', 'suite', 'apt', 'unit', 'building', 'address_line2'],
            'city': ['town', 'municipality'],
            'state': ['province', 'region', 'st'],
            'zip': ['zipcode', 'postal', 'postal code', 'zip code']
        }

    def _normalize_columns(self, df):
        """
        Auto-renames columns based on fuzzy matching.
        Example: Renames 'Postal Code' to 'zip' automatically.
        """
        # Standardize to lowercase/stripped
        df.columns = df.columns.str.strip().str.lower()
        
        # Create a lookup map (Alias -> Standard Name)
        lookup = {}
        for standard, aliases in self.column_aliases.items():
            for alias in aliases:
                lookup[alias] = standard
        
        # Rename any columns that match our aliases
        new_columns = {}
        for col in df.columns:
            if col in lookup:
                new_columns[col] = lookup[col]
        
        df.rename(columns=new_columns, inplace=True)
        return df

    def _construct_name(self, df):
        """
        If 'name' is missing, try to build it from 'First Name' + 'Last Name'.
        """
        if 'name' not in df.columns:
            # Find columns containing 'first' and 'last'
            first = next((c for c in df.columns if 'first' in c and 'name' in c), None)
            last = next((c for c in df.columns if 'last' in c and 'name' in c), None)
            
            if first and last:
                # Combine them into a single 'name' column
                df['name'] = df[first].astype(str).str.strip() + " " + df[last].astype(str).str.strip()
        return df

    def parse_file(self, uploaded_file, max_rows=1000):
        try:
            # Load CSV
            df = pd.read_csv(uploaded_file)
            
            # Check row limit
            if len(df) > max_rows:
                return [], f"File contains {len(df)} rows. Maximum allowed is {max_rows}."

            # smart processing
            df = self._normalize_columns(df)
            df = self._construct_name(df)

            # Define strict requirements (Columns we MUST have to mail)
            required = ['name', 'street', 'city', 'state', 'zip']
            missing = [c for c in required if c not in df.columns]
            
            if missing:
                return [], f"Could not find these columns: {', '.join(missing)}. \n(We auto-checked for common names like 'Recipient' or 'Address', but couldn't find a match)."

            valid_contacts = []
            error_log = []

            for index, row in df.iterrows():
                # Helper to clean data
                def clean(val):
                    if pd.isna(val): return ""
                    s_val = str(val).strip()
                    # Use existing sanitizer if available
                    if letter_format: 
                        return letter_format.sanitize_text(s_val)
                    return s_val

                # Extract data safely
                contact = {
                    "name": clean(row.get('name')),
                    "street": clean(row.get('street')),
                    "address_line2": clean(row.get('street2', '')), # Handles 'suite', 'apt' etc via alias
                    "city": clean(row.get('city')),
                    "state": clean(row.get('state')),
                    "zip": clean(str(row.get('zip', '')).replace('.0', ''))
                }

                # Validation: Check if any required field (except address2) is empty
                missing_fields = [k for k, v in contact.items() if not v and k != 'address_line2']
                
                if not missing_fields:
                    contact['country'] = 'US'
                    valid_contacts.append(contact)
                else:
                    # Log specific error for the user
                    error_log.append(f"Row {index+2} skipped: Missing {', '.join(missing_fields)}")

            # Return results
            if not valid_contacts:
                return [], "No valid contacts found.\nErrors:\n" + "\n".join(error_log[:5])
            
            # If some failed, return the valid ones but include a warning message
            error_msg = None
            if error_log:
                error_msg = f"Processed {len(valid_contacts)} contacts. \n{len(error_log)} rows were skipped due to missing data."

            return valid_contacts, error_msg

        except Exception as e:
            return [], f"Critical CSV Error: {str(e)}"

# --- MAIN ENTRY POINT ---
# This function matches your original signature so your app code doesn't break.
def parse_csv(uploaded_file, max_rows=1000):
    """
    Parses a CSV file for Campaign Mode using the Smart Engine.
    """
    engine = SmartBulkEngine()
    return engine.parse_file(uploaded_file, max_rows)