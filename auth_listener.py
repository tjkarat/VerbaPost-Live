import streamlit as st
import time

# Graceful import to prevent crashes during deployment builds
try:
    from streamlit_javascript import st_javascript
except ImportError:
    st_javascript = None

def listen_for_oauth():
    """
    Reads the URL hash directly using JavaScript and passes it to Python.
    No page reload or manual click required.
    """
    if not st_javascript:
        return # Skip if lib not installed

    # Stop if already logged in to prevent loops
    if st.session_state.get("authenticated"):
        return

    # 1. Execute JS to read the parent window's URL hash
    # The key is crucial to prevent constant re-execution
    raw_hash = st_javascript("window.parent.location.hash", key="oauth_hash_reader")

    # 2. Process the result in Python
    if raw_hash and "access_token" in raw_hash:
        try:
            # Parse the hash string (e.g., "#access_token=xyz&refresh=...")
            params = {}
            clean_str = raw_hash.lstrip("#")
            
            for pair in clean_str.split("&"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    params[k] = v
            
            token = params.get("access_token")
            
            if token:
                # 3. Verify immediately
                # DIRECT IMPORT to avoid circular dependency with main.py
                import auth_engine  
                
                email, err = auth_engine.verify_oauth_token(token)
                
                if email:
                    # SUCCESS: Set State & Redirect
                    st.session_state.authenticated = True
                    st.session_state.user_email = email
                    st.session_state.app_mode = "heirloom"
                    
                    # Force a rerun to load the Dashboard immediately
                    st.rerun()
                else:
                    st.error(f"Authentication Verification Failed: {err}")

        except Exception as e:
            # Log silent errors to console, don't break UI
            print(f"Auth Listener Error: {e}")