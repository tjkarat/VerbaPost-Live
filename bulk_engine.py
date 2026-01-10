import pandas as pd
import io
import streamlit as st
import logging
import time

# --- IMPORTS ---
try: import letter_format
except ImportError: letter_format = None
try: import mailer
except ImportError: mailer = None
try: import audit_engine
except ImportError: audit_engine = None

logger = logging.getLogger(__name__)

def parse_csv(uploaded_file):
    """
    Parses CSV and normalizes column headers.
    Returns: List of dicts [{"name": "...", "street": "...", ...}]
    """
    try:
        df = pd.read_csv(uploaded_file)
        
        # 1. Normalize Headers (Case insensitive)
        df.columns = [c.strip().lower() for c in df.columns]
        
        # 2. Map variations to standard keys
        # Standard: name, street, city, state, zip
        column_map = {
            "full name": "name", "recipient": "name",
            "address": "street", "address 1": "street", "addr": "street", "address_line1": "street",
            "town": "city",
            "province": "state",
            "postal": "zip", "zip code": "zip", "zipcode": "zip"
        }
        df.rename(columns=column_map, inplace=True)
        
        # 3. Validate Required Fields
        required = ["name", "street", "city", "state", "zip"]
        missing = [req for req in required if req not in df.columns]
        
        if missing:
            logger.warning(f"CSV Missing columns: {missing}")
            return None
            
        # 4. Fill NaNs
        df.fillna("", inplace=True)
        
        return df.to_dict(orient="records")
        
    except Exception as e:
        logger.error(f"CSV Parse Error: {e}")
        return None

def process_campaign(contacts, letter_body, from_addr, user_email):
    """
    Iterates through contacts and sends letters via Mailer API.
    """
    if not mailer or not letter_format:
        return 0, "Engines Missing"
        
    success_count = 0
    fail_count = 0
    
    # Progress Bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total = len(contacts)
    
    for i, contact in enumerate(contacts):
        # Update UI
        status_text.text(f"Processing {i+1}/{total}: {contact.get('name')}")
        progress_bar.progress((i + 1) / total)
        
        try:
            # 1. Prepare To-Address
            to_addr = {
                "name": contact.get("name"),
                "street": contact.get("street"),
                "city": contact.get("city"),
                "state": contact.get("state"),
                "zip": contact.get("zip")
            }
            
            # 2. Generate PDF
            pdf_bytes = letter_format.create_pdf(letter_body, to_addr, from_addr, tier="Campaign")
            
            # 3. Send (PCM API)
            # Use 'Campaign' tier so mailer defaults to Standard/Metered
            track_id = mailer.send_letter(
                pdf_bytes, 
                to_addr, 
                from_addr, 
                tier="Campaign", 
                description=f"Bulk {user_email}",
                user_email=user_email # <--- PASS USER EMAIL HERE
            )
            
            if track_id:
                success_count += 1
                # Log Success (Now redundant if mailer logs, but harmless to keep)
                if audit_engine:
                    audit_engine.log_event(user_email, "BULK_SENT", metadata={"recipient": to_addr['name'], "id": track_id})
            else:
                fail_count += 1
                
            # Rate limit safety
            time.sleep(0.5) 
            
        except Exception as e:
            logger.error(f"Bulk Error on row {i}: {e}")
            fail_count += 1

    status_text.text(f"Done! Sent: {success_count}, Failed: {fail_count}")
    return success_count, fail_count