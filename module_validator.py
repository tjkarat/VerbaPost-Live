import logging
import streamlit as st
import sys

# Configure a separate logger for validation
logger = logging.getLogger("SystemValidator")

def validate_critical_modules():
    """
    Attempts to import critical engines and verifies essential configuration.
    Returns: (bool, list of error messages)
    """
    errors = []
    
    # 1. Critical Module Imports
    # These are modules that, if missing, render the app useless.
    critical_modules = [
        "secrets_manager",
        "database",
        "payment_engine", 
        "mailer",
        "ai_engine"
    ]

    for mod_name in critical_modules:
        try:
            __import__(mod_name)
        except ImportError as e:
            # Check if it's a missing dependency (e.g., 'no module named stripe')
            msg = f"MISSING MODULE: {mod_name} could not be loaded. ({e})"
            logger.critical(msg)
            errors.append(msg)
        except Exception as e:
            msg = f"CRITICAL ERROR: {mod_name} crashed on import. ({e})"
            logger.critical(msg)
            errors.append(msg)

    # 2. Database Connection String Check
    # We don't connect yet, just check if the CREDENTIAL exists.
    try:
        import secrets_manager
        db_url = secrets_manager.get_secret("DATABASE_URL")
        
        # Fallback check for Streamlit secrets if not in env vars
        if not db_url and "DATABASE_URL" in st.secrets:
            db_url = st.secrets["DATABASE_URL"]
            
        if not db_url:
            # Check for legacy Supabase keys if DB URL is missing
            if not secrets_manager.get_secret("supabase.url") and "supabase" not in st.secrets:
                 errors.append("MISSING CONFIG: No Database URL or Supabase credentials found.")
    except Exception:
        # If secrets_manager failed to import, it's already caught in step 1.
        pass

    return (len(errors) == 0), errors
