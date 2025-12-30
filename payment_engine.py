import streamlit as st
import stripe
import logging
import secrets_manager
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import stripe safely
try:
    import stripe
except ImportError:
    stripe = None
    logger.error("Stripe module not found. Payments will be disabled.")

# NOTE: 'database' import removed from top-level to prevent circular dependency

def get_api_key():
    """
    Retrieves Stripe API Key with maximum robustness.
    """
    key = None
    # 1. Try Secrets Manager
    if secrets_manager:
        key = secrets_manager.get_secret("stripe.secret_key")
        if key: return key.strip()
    # 2. Try Standard Streamlit Secrets
    try:
        if "stripe" in st.secrets and "secret_key" in st.secrets["stripe"]:
            return st.secrets["stripe"]["secret_key"].strip()
    except Exception: pass
    # 3. Try Flat Key
    try:
        if "stripe_secret_key" in st.secrets:
            return st.secrets["stripe_secret_key"].strip()
    except Exception: pass
    # 4. Try Environment
    import os
    if os.environ.get("STRIPE_SECRET_KEY"):
        return os.environ.get("STRIPE_SECRET_KEY").strip()
    return None

def get_base_url():
    url = None
    if hasattr(st, "secrets") and "general" in st.secrets:
        url = st.secrets["general"].get("BASE_URL")
    if not url:
        import os
        url = os.environ.get("BASE_URL")
    if not url:
        url = "https://app.verbapost.com"
    return url.rstrip("/")

def create_checkout_session(line_items, user_email, draft_id="Unknown", mode="payment"):
    if not stripe:
        st.error("⚠️ Payment System Offline (Module Missing)")
        return None

    api_key = get_api_key()
    if not api_key:
        st.error("⚠️ Payment Error: Stripe API Key not found.")
        return None

    stripe.api_key = api_key
    base_url = get_base_url()
    
    success_url = f"{base_url}?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{base_url}?nav=store"

    metadata = {
        "user_email": user_email,
        "draft_id": str(draft_id),
        "service": "VerbaPost"
    }

    try:
        session_params = {
            "payment_method_types": ["card"],
            "line_items": line_items,
            "mode": mode,
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": metadata,
            "client_reference_id": str(draft_id)
        }
        if user_email and "guest" not in user_email.lower():
            session_params["customer_email"] = user_email
        
        checkout_session = stripe.checkout.Session.create(**session_params)
        return checkout_session.url
    except Exception as e:
        logger.error(f"Stripe Session Error: {e}")
        st.error(f"Payment Error: {e}")
        return None

def verify_session(session_id):
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

def check_subscription_status(user_email):
    """
    Checks if the user has an active subscription.
    Lazy imports 'database' to avoid circular import errors.
    """
    if not user_email or not stripe: return False

    api_key = get_api_key()
    if not api_key: return False
    stripe.api_key = api_key
    
    # LAZY IMPORT
    try: import database
    except ImportError: return False
    
    try:
        customers = stripe.Customer.list(email=user_email, limit=1)
        if not customers.data: return False
        
        customer_id = customers.data[0].id
        subscriptions = stripe.Subscription.list(customer=customer_id, status='active', limit=1)
        
        if len(subscriptions.data) > 0:
            sub = subscriptions.data[0]
            stripe_end_ts = sub.current_period_end 
            stripe_end_dt = datetime.fromtimestamp(stripe_end_ts)
            
            if database:
                profile = database.get_user_profile(user_email)
                db_end_dt = profile.get("subscription_end_date")
                
                should_refill = False
                if not db_end_dt: should_refill = True
                elif stripe_end_dt > db_end_dt: should_refill = True
                
                if should_refill:
                    database.update_user_credits(user_email, 4)
                    database.update_subscription_state(user_email, stripe_end_dt)
                    database.update_user_subscription_id(user_email, sub.id)
            return True
        return False
    except Exception as e:
        logger.error(f"Subscription Check Error: {e}")
        return False

def cancel_subscription(user_email):
    if not user_email or not stripe: return False, "Stripe module not initialized."
    api_key = get_api_key()
    if not api_key: return False, "API Key Missing."
    stripe.api_key = api_key
    
    try:
        customers = stripe.Customer.list(email=user_email, limit=1)
        if not customers.data: return False, "User not found."
        customer_id = customers.data[0].id
        
        subscriptions = stripe.Subscription.list(customer=customer_id, status='active', limit=1)
        if not subscriptions.data: return False, "No active subscription."
            
        sub_id = subscriptions.data[0].id
        stripe.Subscription.delete(sub_id)
        return True, f"Subscription {sub_id} has been cancelled."
    except Exception as e:
        logger.error(f"Cancellation Error: {e}")
        return False, str(e)