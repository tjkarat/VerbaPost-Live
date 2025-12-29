import streamlit as st
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import stripe safely
try:
    import stripe
except ImportError:
    stripe = None
    logger.error("Stripe module not found. Payments will be disabled.")

try: import secrets_manager
except ImportError: secrets_manager = None

try: import database
except ImportError: database = None

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

def check_subscription_status(user_email):
    """
    Checks if the user has an active subscription AND refills credits if a new month has started.
    Logic:
    1. Check Stripe for active subs.
    2. Get 'current_period_end' from Stripe.
    3. Compare with 'subscription_end_date' in local DB.
    4. If Stripe date is NEWER -> Refill to 4 credits & Update DB.
    """
    if not user_email or not stripe:
        return False

    api_key = get_api_key()
    if not api_key: return False
    
    stripe.api_key = api_key
    
    try:
        # 1. Find Customer
        customers = stripe.Customer.list(email=user_email, limit=1)
        if not customers.data:
            return False
        
        customer_id = customers.data[0].id
        
        # 2. Check for Active Subscriptions
        subscriptions = stripe.Subscription.list(
            customer=customer_id, 
            status='active',
            limit=1
        )
        
        if len(subscriptions.data) > 0:
            sub = subscriptions.data[0]
            stripe_end_ts = sub.current_period_end # Unix Timestamp
            stripe_end_dt = datetime.fromtimestamp(stripe_end_ts)
            
            # 3. Check DB for Last Known Refill
            if database:
                profile = database.get_user_profile(user_email)
                db_end_dt = profile.get("subscription_end_date")
                
                # 4. Refill Logic
                should_refill = False
                if not db_end_dt:
                    should_refill = True
                elif stripe_end_dt > db_end_dt:
                    should_refill = True
                
                if should_refill:
                    logger.info(f"Refilling credits for {user_email} (New Period: {stripe_end_dt})")
                    database.update_user_credits(user_email, 4)
                    database.update_subscription_state(user_email, stripe_end_dt)
                    database.update_user_subscription_id(user_email, sub.id)
            
            return True
            
        return False
        
    except Exception as e:
        logger.error(f"Subscription Check Error: {e}")
        return False

def cancel_subscription(user_email):
    """
    Cancels a user's subscription immediately in Stripe.
    Returns: (Success: bool, Message: str)
    """
    if not user_email or not stripe:
        return False, "Stripe module not initialized."

    api_key = get_api_key()
    if not api_key: return False, "API Key Missing."
    
    stripe.api_key = api_key
    
    try:
        # 1. Find Customer
        customers = stripe.Customer.list(email=user_email, limit=1)
        if not customers.data:
            return False, "User not found in Stripe."
        
        customer_id = customers.data[0].id
        
        # 2. Find Active Subscription
        subscriptions = stripe.Subscription.list(
            customer=customer_id, 
            status='active', 
            limit=1
        )
        
        if not subscriptions.data:
            return False, "No active subscription found."
            
        sub_id = subscriptions.data[0].id
        
        # 3. Cancel Immediately
        stripe.Subscription.delete(sub_id)
        return True, f"Subscription {sub_id} has been cancelled."
        
    except Exception as e:
        logger.error(f"Cancellation Error: {e}")
        return False, str(e)