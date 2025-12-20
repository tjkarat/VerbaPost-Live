import stripe
import streamlit as st
import logging

# --- CONFIGURATION ---
logger = logging.getLogger(__name__)

# Try to get secrets manager
try: import secrets_manager
except ImportError: secrets_manager = None

def _get_api_key():
    """Retrieve Stripe Key safely."""
    key = None
    if secrets_manager:
        key = secrets_manager.get_secret("stripe.secret_key")
    if not key and "stripe" in st.secrets:
        key = st.secrets["stripe"]["secret_key"]
    return key

def create_checkout_session(line_items, user_email, draft_id=None):
    """
    Creates a Stripe Checkout Session.
    CRITICAL: Maps 'draft_id' to 'client_reference_id' for tracking return type.
    """
    api_key = _get_api_key()
    if not api_key:
        logger.error("Stripe API Key Missing")
        return None

    stripe.api_key = api_key
    
    # Base URL determination
    base_url = "https://verbapost.streamlit.app"
    if "general" in st.secrets and "BASE_URL" in st.secrets["general"]:
        base_url = st.secrets["general"]["BASE_URL"]
    
    # Clean draft_id
    ref_id = str(draft_id) if draft_id else "UNKNOWN_DRAFT"

    try:
        # Build Session
        session_params = {
            "payment_method_types": ["card"],
            "line_items": line_items,
            "mode": "payment", # Use 'subscription' if selling recurring, 'payment' for one-time
            "success_url": f"{base_url}?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": f"{base_url}?error=payment_cancelled",
            "client_reference_id": ref_id,  # <--- THIS IS THE KEY TAG
            "metadata": {"draft_id": ref_id}
        }

        # Guest vs User logic
        if user_email and user_email != "guest":
            session_params["customer_email"] = user_email
            
        session = stripe.checkout.Session.create(**session_params)
        return session.url

    except Exception as e:
        logger.error(f"Stripe Create Error: {e}")
        return None

def verify_session(session_id):
    """
    Verifies a session and returns the FULL object.
    CRITICAL FIX: Returns dict, not string.
    """
    api_key = _get_api_key()
    if not api_key: return None

    stripe.api_key = api_key

    try:
        session = stripe.checkout.Session.retrieve(session_id)
        
        # Return the actual object so main.py can read client_reference_id
        return session
        
    except Exception as e:
        logger.error(f"Stripe Verify Error: {e}")
        return None