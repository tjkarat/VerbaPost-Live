import stripe
import logging
import secrets_manager
from datetime import datetime

# Optional Streamlit: the FastAPI backend runs without it. The stub turns
# st.error(...) into a no-op and gives st.secrets an empty dict, so all
# existing lookups fall through to env vars exactly as before.
try:
    import streamlit as st
except ImportError:
    class _StreamlitStub:
        secrets = {}
        def __getattr__(self, _name):
            def _noop(*args, **kwargs):
                return None
            return _noop
    st = _StreamlitStub()

logger = logging.getLogger(__name__)

# --- AUDIT IMPORT ---
try: import audit_engine
except ImportError: audit_engine = None

# Try to import stripe safely
try:
    import stripe
except ImportError:
    stripe = None
    logger.error("Stripe module not found. Payments will be disabled.")

# Database imported lazily inside functions to prevent circular refs

def _sget(obj, key, default=None):
    """
    Version-proof key lookup on Stripe objects.
    Old stripe-python: objects were dict subclasses (.get worked).
    New stripe-python: .get resolves as a data field and raises.
    Bracket access works on both; this wraps it safely.
    """
    if obj is None:
        return default
    try:
        return obj[key]
    except (KeyError, TypeError, IndexError):
        return default

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

def create_checkout_session(line_items, user_email, draft_id="Unknown", mode="payment", promo_code=None, success_path=None, payer_email=None, service=None, extra_metadata=None):
    """
    user_email  -> fulfillment target (webhook credits THIS account)
    payer_email -> who Stripe bills (defaults to user_email). Lets an advisor
                   pay for a story that is credited to the client family.
    service     -> metadata tag the webhook branches on. Default "VerbaPost"
                   (legacy: +1 engagement credit). "prospect_letters" credits
                   the advisor's prospect-letter ledger instead.
    extra_metadata -> additional string metadata for the session (e.g. letters).
    """
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
    
    # success_path lets callers land the buyer back where they came from
    # (e.g. "/advisor"). Default preserves legacy behavior (site root).
    _path = success_path or ""
    success_url = f"{base_url}{_path}?purchased=1&session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{base_url}{_path or '?nav=store'}"

    metadata = {
        "user_email": user_email,
        "draft_id": str(draft_id),
        "service": service or "VerbaPost"
    }
    if extra_metadata:
        for _k, _v in extra_metadata.items():
            metadata[str(_k)] = str(_v)
    
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

        # Handle Guest vs Logged In (payer may differ from fulfillment target)
        billing_email = payer_email or user_email
        if billing_email and "guest" not in billing_email.lower():
            session_params["customer_email"] = billing_email
        
        # Create Session
        checkout_session = stripe.checkout.Session.create(**session_params)

        # --- 🛡️ AUDIT LOG: PAYMENT INITIATED ---
        if audit_engine:
            try:
                audit_engine.log_event(
                    user_email=user_email, 
                    event_type="Payment Initiated", 
                    metadata={
                        "amount_total": final_line_items[0]['price_data']['unit_amount'],
                        "product": final_line_items[0]['price_data']['product_data']['name'],
                        "stripe_url": checkout_session.url
                    }
                )
            except: pass
        # ----------------------------------------
        
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

# --- 🆕 NEW: ROBUST IDEMPOTENT FULFILLMENT ---
def handle_payment_return(session_id):
    """
    Called by main.py when ?session_id= is present.
    1. Verify with Stripe.
    2. Check DB if already fulfilled (Idempotency).
    3. Fulfill (Add Credits).
    4. Mark as fulfilled.
    """
    import database # Lazy import
    
    # 1. Verify
    session = verify_session(session_id)
    if not session:
        return False, "Invalid Session"
        
    if session.payment_status != "paid":
        return False, "Payment Pending or Failed"

    # 2. Check Idempotency (Have we done this already?)
    if database.is_fulfillment_recorded(session_id):
        return True, "Already Fulfilled"

    # 3. Extract Data
    # Prefer metadata user_email, fallback to customer_details
    # (uses _sget: .get() on Stripe objects crashes on stripe-python v15+)
    user_email = _sget(session.metadata, "user_email")
    if not user_email and session.customer_details:
        user_email = session.customer_details.email
        
    if not user_email:
        return False, "No Email Found in Transaction"

    # 3b. PROSPECT ACQUISITION PATH: letter credits, not engagement credits.
    #     Ledger row reason="purchase" is what flips the advisor to repeat pricing.
    if _sget(session.metadata, "service") == "prospect_letters":
        try:
            letters = int(_sget(session.metadata, "letters") or 0)
        except (TypeError, ValueError):
            letters = 0
        if letters <= 0:
            return False, "Prospect purchase carries no letter count"
        try:
            if not database.add_prospect_credits(user_email, letters, "purchase", session_id):
                return False, "Ledger write failed"
            database.record_stripe_fulfillment(session_id, f"Prospect Letters x{letters}", user_email)
            if audit_engine:
                audit_engine.log_event(user_email, "Prospect Letters Purchased",
                                       metadata={"session_id": session_id, "letters": letters,
                                                 "amount": session.amount_total,
                                                 "kind": _sget(session.metadata, "kind")})
            return True, f"{letters} prospect letters added"
        except Exception as e:
            logger.error(f"Prospect fulfillment error: {e}")
            return False, f"DB Error: {e}"

    # 4. Fulfill (Add 1 Credit per $99 item roughly, or just 1 for now)
    # For MVP, we assume 1 credit purchase.
    try:
        # Add Credit to DB
        database.add_advisor_credit(user_email, 1)
        
        # Record Fulfillment to prevent double-counting
        product_name = "Legacy Project Credit"
        database.record_stripe_fulfillment(session_id, product_name, user_email)
        
        # Log Audit
        if audit_engine:
            audit_engine.log_event(
                user_email, 
                "Credit Purchased", 
                metadata={"session_id": session_id, "amount": session.amount_total}
            )
            
        return True, "Credit Added"
        
    except Exception as e:
        logger.error(f"Fulfillment Error: {e}")
        return False, f"DB Error: {e}"

# ==========================================
# 🔄 SUBSCRIPTION HELPERS (RESTORED)
# ==========================================

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
            # _sget handles both old and new stripe-python.
            stripe_end_ts = _sget(sub, 'current_period_end')
            if not stripe_end_ts:
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