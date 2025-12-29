import streamlit as st
import stripe
import database
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# --- INIT STRIPE ---
try:
    if "stripe" in st.secrets:
        stripe.api_key = st.secrets["stripe"]["secret_key"]
except Exception:
    pass

def create_checkout_session(line_items, user_email, draft_id="N/A", mode="payment"):
    """
    Creates a Stripe Checkout Session.
    Supports both One-time Payment (mode='payment') and Subscription (mode='subscription').
    """
    try:
        base_url = st.secrets["general"]["BASE_URL"]
        success_url = f"{base_url}?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{base_url}?cancel=true"
        
        # Handling for 'Guest' email flow to avoid Stripe crashes
        customer_email_param = user_email
        if user_email and "guest" in user_email.lower():
            customer_email_param = None
        
        session_params = {
            "payment_method_types": ["card"],
            "line_items": line_items,
            "mode": mode,
            "success_url": success_url,
            "cancel_url": cancel_url,
            "client_reference_id": str(draft_id),
            "metadata": {
                "user_email": user_email,
                "draft_id": str(draft_id),
                "service": "VerbaPost"
            }
        }

        # Only add customer_email if it's a real email
        if customer_email_param:
            session_params["customer_email"] = customer_email_param

        checkout_session = stripe.checkout.Session.create(**session_params)
        return checkout_session.url
        
    except Exception as e:
        logger.error(f"Stripe Error: {e}")
        return None

def verify_session(session_id):
    """
    Verifies the session status with Stripe.
    """
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        return session
    except Exception as e:
        logger.error(f"Stripe Verification Error: {e}")
        return None

def check_subscription_status(user_email):
    """
    Lazy Sync: Checks if a subscription has renewed since the last login.
    If so, resets credits to 4 and updates the sync date.
    Returns True if a refill occurred.
    """
    try:
        # 1. Get Profile
        profile = database.get_user_profile(user_email)
        sub_id = profile.get('stripe_subscription_id')
        
        if not sub_id:
            return False
            
        # 2. Query Stripe
        sub = stripe.Subscription.retrieve(sub_id)
        if sub.status != 'active':
            return False
            
        # 3. Check Dates
        # Stripe returns unix timestamp
        stripe_end_ts = sub.current_period_end
        stripe_end_dt = datetime.fromtimestamp(stripe_end_ts)
        
        stored_end_dt = profile.get('subscription_end_date')
        
        # Logic: If we have no stored date, OR if the stored date is in the past compared to Stripe
        # It means a renewal happened (or it's the first sync)
        should_refill = False
        
        if not stored_end_dt:
            should_refill = True
        elif stored_end_dt < stripe_end_dt:
            should_refill = True
            
        if should_refill:
            logger.info(f"Subscription Renewal Detected for {user_email}. Refilling Credits.")
            # Reset Credits to 4 (Heirloom plan default)
            database.update_user_credits(user_email, 4)
            # Update the tracking date
            database.update_subscription_dates(user_email, stripe_end_dt)
            return True
            
        return False

    except Exception as e:
        logger.error(f"Subscription Sync Error: {e}")
        return False