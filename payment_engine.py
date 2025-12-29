import streamlit as st
import logging

logger = logging.getLogger(__name__)

# Try to import stripe safely
try:
    import stripe
except ImportError:
    stripe = None
    logger.error("Stripe module not found. Payments will be disabled.")

try: import secrets_manager
except ImportError: secrets_manager = None

def get_api_key():
    """
    Retrieves Stripe API Key with maximum robustness.
    Checks: SecretsManager -> st.secrets[stripe][secret_key] -> st.secrets[stripe_secret_key]
    """
    key = None
    
    # 1. Try Secrets Manager (Env Vars / Cloud Run)
    if secrets_manager:
        key = secrets_manager.get_secret("stripe.secret_key")
        if key: return key.strip()

    # 2. Try Standard Streamlit Secrets [stripe] > secret_key
    try:
        if "stripe" in st.secrets and "secret_key" in st.secrets["stripe"]:
            return st.secrets["stripe"]["secret_key"].strip()
    except Exception: pass

    # 3. Try Flat Key in Secrets (stripe_secret_key)
    try:
        if "stripe_secret_key" in st.secrets:
            return st.secrets["stripe_secret_key"].strip()
    except Exception: pass
    
    # 4. Try Environment Variable Fallback
    import os
    if os.environ.get("STRIPE_SECRET_KEY"):
        return os.environ.get("STRIPE_SECRET_KEY").strip()

    return None

def create_checkout_session(line_items, user_email, draft_id="Unknown", mode="payment"):
    """
    Creates a Stripe Checkout Session.
    """
    if not stripe:
        st.error("⚠️ Payment System Offline (Module Missing)")
        return None

    api_key = get_api_key()
    if not api_key:
        st.error("⚠️ Payment Error: Stripe API Key not found. Please check secrets.toml")
        return None

    stripe.api_key = api_key
    
    # Base URL for redirects (Safe Lookup)
    # FIX: Use safe .get() to prevent 'st.secrets has no key "general"' error
    base_url = "https://verbapost.streamlit.app"
    try:
        general_config = st.secrets.get("general", {})
        if "BASE_URL" in general_config:
            base_url = general_config["BASE_URL"]
    except Exception: 
        pass # Keep default if fails
    
    # Metadata for fulfillment
    metadata = {
        "user_email": user_email,
        "draft_id": str(draft_id),
        "service": "VerbaPost"
    }

    try:
        # Build Session Params
        session_params = {
            "payment_method_types": ["card"],
            "line_items": line_items,
            "mode": mode,
            "success_url": f"{base_url}?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": f"{base_url}",
            "metadata": metadata,
            "client_reference_id": str(draft_id)
        }

        # Handle Guest vs Logged In
        if user_email and "guest" not in user_email.lower():
            session_params["customer_email"] = user_email
        
        # Create Session
        checkout_session = stripe.checkout.Session.create(**session_params)
        return checkout_session.url

    except Exception as e:
        logger.error(f"Stripe Session Error: {e}")
        st.error(f"Payment Error: {e}")
        return None

def verify_session(session_id):
    """
    Verifies a session ID with Stripe to ensure payment success.
    """
    if not stripe or not session_id: return None
    
    api_key = get_api_key()
    if not api_key: return None

    stripe.api_key = api_key

    try:
        session = stripe.checkout.Session.retrieve(session_id)
        return session
    except Exception as e:
        logger.error(f"Stripe Verification Error: {e}")
        return None