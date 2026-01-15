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

# Database imported lazily to prevent circular refs

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

def get_base_url():
    """
    Returns the application base URL.
    Defaults to the production custom domain to prevent redirects to streamlit.app
    """
    url = None
    # 1. Try Secrets
    if hasattr(st, "secrets") and "general" in st.secrets:
        url = st.secrets["general"].get("BASE_URL")
    
    # 2. Try Env Vars
    if not url:
        import os
        url = os.environ.get("BASE_URL")
        
    # 3. Safe Default (Production)
    if not url:
        url = "https://app.verbapost.com"
        
    return url.rstrip("/")

def create_checkout_session(line_items, user_email, draft_id="Unknown", mode="payment", promo_code=None):
    """
    Creates a Stripe Checkout Session.
    Includes logic to Rebrand the $99 Tier as 'The Family Legacy Project'.
    """
    if not stripe:
        st.error("⚠️ Payment System Offline (Module Missing)")
        return None

    api_key = get_api_key()
    if not api_key:
        st.error("⚠️ Payment Error: Stripe API Key not found. Please check secrets.toml")
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
    
    # Add Promo Code to Metadata if present
    if promo_code:
        metadata["promo_code"] = str(promo_code)

    # --- STRATEGIC REBRANDING: B2B PIVOT ---
    # Intercept the $99 item to rename it for better perceived value
    final_line_items = []
    try:
        for item in line_items:
            # Check if this is the $99 B2B Activation item (9900 cents)
            price_data = item.get('price_data', {})
            if price_data.get('unit_amount') == 9900: 
                new_item = item.copy()
                # NEW NAME: "The Family Legacy Project"
                new_item['price_data']['product_data']['name'] = "The Family Legacy Project"
                # NEW TERMS: "30-Day Access" instead of Lifetime
                new_item['price_data']['product_data']['description'] = "Production Fee + Physical Manuscript + 30-Day Digital Access"
                final_line_items.append(new_item)
            else:
                final_line_items.append(item)
    except Exception as e:
        logger.warning(f"Failed to rebrand line item: {e}")
        final_line_items = line_items # Fallback to original if structure is unexpected

    try:
        # Build Session Params
        session_params = {
            "payment_method_types": ["card"],
            "line_items": final_line_items,
            "mode": mode,
            "success_url": success_url,
            "cancel_url": cancel_url,
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
    Retrieves session details from Stripe to verify payment.
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
    This is the "Lazy Check" called on login.
    """
    if not user_email or not stripe:
        return False

    api_key = get_api_key()
    if not api_key: return False
    
    stripe.api_key = api_key
    
    # --- LAZY IMPORT TO FIX CIRCULAR DEPENDENCY ---
    try: import database
    except ImportError: return False
    # ----------------------------------------------
    
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
            
            # --- FIX: SAFE ATTRIBUTE ACCESS ---
            # Stripe objects can behave like dicts or objects depending on version.
            # Using .get() or dictionary access is safest.
            stripe_end_ts = sub.get('current_period_end') 
            if not stripe_end_ts:
                # Fallback to attribute access if .get fails (rare object types)
                stripe_end_ts = getattr(sub, 'current_period_end', None)

            if not stripe_end_ts:
                return False # Cannot determine date

            stripe_end_dt = datetime.fromtimestamp(stripe_end_ts)
            
            # 3. Check DB for Last Known Refill
            profile = database.get_user_profile(user_email)
            db_end_dt = profile.get("subscription_end_date")
            
            # 4. Logic: Refill if DB is null OR if Stripe Period > DB Period
            should_refill = False
            if not db_end_dt:
                should_refill = True
            elif stripe_end_dt > db_end_dt:
                should_refill = True
            
            # 5. Update Database (Atomic)
            if should_refill or db_end_dt != stripe_end_dt:
                database.update_subscription_state(
                    email=user_email,
                    sub_id=sub.id,
                    customer_id=customer_id,
                    period_end_dt=stripe_end_dt,
                    refill_credits=should_refill
                )
                return should_refill
            
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