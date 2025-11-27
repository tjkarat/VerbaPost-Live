import streamlit as st
import os

def get_secret(key_path):
    """
    Retrieves secrets with logging to help debug Cloud Run issues.
    """
    
    # --- 1. ENVIRONMENT VARIABLES (GCP Priority) ---
    # Flatten key: "stripe.secret_key" -> "STRIPE_SECRET_KEY"
    env_key = key_path.replace(".", "_").upper()
    value = os.environ.get(env_key)
    
    # DEBUG LOGGING
    if value:
        # We found it! Print success (masked)
        print(f"✅ SECRETS_MANAGER: Found '{env_key}' in Environment Variables.")
        return value
    else:
        # We missed. Print failure.
        print(f"⚠️ SECRETS_MANAGER: Could NOT find '{env_key}' in Environment Variables.")

    # --- 2. STREAMLIT SECRETS (Local Fallback) ---
    try:
        # Check Exact Match
        if key_path in st.secrets:
            return st.secrets[key_path]
            
        # Check Nested Match
        if "." in key_path:
            section, key = key_path.split(".")
            if section in st.secrets:
                return st.secrets[section].get(key)
                
    except FileNotFoundError:
        print("ℹ️ SECRETS_MANAGER: No secrets.toml found (Expected in Cloud Run).")
        return None
    except Exception as e:
        print(f"❌ SECRETS_MANAGER: Error reading secrets.toml: {e}")
        return None
        
    print(f"❌ SECRETS_MANAGER: Could NOT find '{key_path}' anywhere.")
    return None